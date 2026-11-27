#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS ADVERSARIAUX — ALICE-P1-REMEDIATION-010 (F01, F02, F03, F05, F07)
"""

import os
import re
import sys
import json
import time
import zipfile
import tempfile
import unittest
import subprocess
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SITE_DIR = os.path.join(REPO_ROOT, "Jarvis Final - SITE")
if SITE_DIR not in sys.path:
    sys.path.insert(0, SITE_DIR)

import main2
from alice_core.security.rbac import RBAC, Role, ACTION_TO_PERMISSION, PUBLIC_CONVERSATIONAL_ACTIONS
from alice_core.api_bridge import API_BRIDGE
from alice_web_guard import WEB_GUARD
from alice_core.automation.web_agent import AutonomousWebAgent, _pin_dns_to_validated_ips
from alice_rag import AliceRAGEngine


class TestF03SecretContainment(unittest.TestCase):
    def test_01_git_config_contains_no_pat(self):
        cfg_path = os.path.join(REPO_ROOT, ".git", "config")
        with open(cfg_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotRegex(content, r"ghp_[A-Za-z0-9_]+")
        self.assertNotRegex(content, r"github_pat_[A-Za-z0-9_]+")
        self.assertIn("https://github.com/siddick369-sys/Alice.git", content)


class TestF02RBACFailClosed(unittest.TestCase):
    def setUp(self):
        self.guest_sid = "adv_guest_010"
        self.owner_sid = "adv_owner_010"
        RBAC.register_principal(self.guest_sid, "guest_010", Role.GUEST)
        RBAC.register_principal(self.owner_sid, "owner_010", Role.OWNER)

    def tearDown(self):
        RBAC.revoke_principal(self.guest_sid)
        RBAC.revoke_principal(self.owner_sid)

    def test_01_guest_allowed_only_on_explicit_public_actions(self):
        ok, _ = RBAC.check_action(self.guest_sid, "meteo")
        self.assertTrue(ok)
        ok2, _ = RBAC.check_action(self.guest_sid, "alice_status")
        self.assertTrue(ok2)

    def test_02_fail_closed_on_unknown_empty_none_and_whitespace_actions(self):
        for bad_act in ("", "   ", None, "arbitrary_injected_action", "unknown_tool_xyz"):
            ok, _ = RBAC.check_action(self.owner_sid, bad_act)
            self.assertFalse(ok, f"Action '{bad_act}' aurait dû être refusée")
            ok_g, _ = RBAC.check_action(self.guest_sid, bad_act)
            self.assertFalse(ok_g)

    def test_03_guest_blocked_on_extended_actions(self):
        for act in ("web_agent_check", "iot_health", "iot_eco", "daily_briefing", "executive_briefing", "knowledge_graph_add"):
            ok, _ = RBAC.check_action(self.guest_sid, act)
            self.assertFalse(ok, f"GUEST ne doit pas pouvoir exécuter {act}")

    def test_04_case_and_whitespace_normalization(self):
        ok_g, _ = RBAC.check_action(self.guest_sid, "  SHUTDOWN  ")
        self.assertFalse(ok_g)
        ok_o, _ = RBAC.check_action(self.owner_sid, "  SHUTDOWN  ")
        self.assertTrue(ok_o)

    def test_05_session_absent_unknown_or_revoked_blocked_on_pc_actions(self):
        RBAC.revoke_principal("revoked_010")
        for sid in ("", None, "unregistered_sid_010", "revoked_010", self.guest_sid):
            res_read = main2.executer_action_pc(r"lis C:\nonexistent_secret_010.txt", session_id=sid)
            self.assertIn("refusé", res_read.lower())
            res_web = main2.executer_action_pc("ouvre evil.example.com", session_id=sid)
            self.assertIn("refusé", res_web.lower())
            res_yt = main2.executer_action_pc("lance youtube test", session_id=sid)
            self.assertIn("refusé", res_yt.lower())
            res_app = main2.executer_action_pc("ouvre chrome", session_id=sid)
            self.assertIn("refusé", res_app.lower())

    def test_06_all_main2_actions_are_mapped(self):
        with open(os.path.join(SITE_DIR, "main2.py"), "r", encoding="utf-8") as f:
            src = f.read()
        found = set(re.findall(r'elif action == "([a-zA-Z0-9_]+)"', src))
        found |= set(re.findall(r'if action == "([a-zA-Z0-9_]+)"', src))
        unmapped = [a for a in found if a not in ACTION_TO_PERMISSION and a not in PUBLIC_CONVERSATIONAL_ACTIONS]
        self.assertEqual(unmapped, [], f"Actions non mappées dans RBAC : {unmapped}")


class TestF01MultiAccountIndexedDBIsolation(unittest.TestCase):
    def test_01_node_real_account_switch_and_late_callback_isolation(self):
        app_js_path = os.path.join(SITE_DIR, "mobile", "app.js")
        node_script = r"""
const fs = require("fs");
const vm = require("vm");

// Minimal in-memory IndexedDB + DOM + sessionStorage harness exercising real app.js functions
const databases = new Map();
function getDbObj(name) {
  if (!databases.has(name)) databases.set(name, { stores: new Map() });
  return databases.get(name);
}
const fakeIndexedDB = {
  open(name, ver) {
    const req = { result: null, error: null, onupgradeneeded: null, onsuccess: null, onerror: null };
    setTimeout(() => {
      const dbObj = getDbObj(name);
      const db = {
        objectStoreNames: { contains: (s) => dbObj.stores.has(s) },
        createObjectStore(s) {
          if (!dbObj.stores.has(s)) dbObj.stores.set(s, new Map());
          return { createIndex() {} };
        },
        transaction(storeName) {
          const st = dbObj.stores.get(storeName) || new Map();
          const tx = { oncomplete: null, onerror: null, objectStore: () => ({
            put(obj) {
              const key = obj.item_id || obj.op_id;
              st.set(key, JSON.parse(JSON.stringify(obj)));
              setTimeout(() => tx.oncomplete && tx.oncomplete(), 0);
            },
            getAll() {
              const r = { result: Array.from(st.values()).map(v => JSON.parse(JSON.stringify(v))), onsuccess: null, onerror: null };
              setTimeout(() => r.onsuccess && r.onsuccess(), 0);
              return r;
            },
            clear() {
              st.clear();
              setTimeout(() => tx.oncomplete && tx.oncomplete(), 0);
            }
          })};
          return tx;
        }
      };
      req.result = db;
      if (req.onupgradeneeded) req.onupgradeneeded();
      if (req.onsuccess) req.onsuccess();
    }, 0);
    return req;
  },
  deleteDatabase(name) { databases.delete(name); }
};

const sStore = new Map();
const fakeWindow = {
  location: { protocol: "https:", hostname: "localhost", host: "localhost:8080" },
  indexedDB: fakeIndexedDB,
  speechSynthesis: { addEventListener(){}, getVoices: () => [], cancel(){}, speak(){} },
  addEventListener() {},
};
const makeEl = () => ({
  style: {},
  classList: { add(){}, remove(){}, toggle(){}, contains: () => false },
  dataset: {},
  textContent: "",
  value: "",
  disabled: false,
  addEventListener() {},
  appendChild() {},
  replaceChildren() {},
  querySelector: () => makeEl(),
  querySelectorAll: () => [],
});
const sandbox = {
  window: fakeWindow,
  indexedDB: fakeIndexedDB,
  navigator: { onLine: false, mediaDevices: {}, serviceWorker: { register: async () => ({}) } },
  sessionStorage: {
    getItem: (k) => sStore.get(k) || null,
    setItem: (k, v) => sStore.set(k, String(v)),
    removeItem: (k) => sStore.delete(k),
  },
  localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  document: { body: makeEl(), getElementById: () => makeEl(), createElement: () => makeEl(), cookie: "", addEventListener() {} },
  WebSocket: function() { return { addEventListener(){}, readyState: 3 }; },
  fetch: async () => ({ ok: true, json: async () => ({}) }),
  console,
  setTimeout,
  clearTimeout,
};
vm.createContext(sandbox);
const src = fs.readFileSync(process.argv[2], "utf8");
vm.runInContext(src, sandbox);

(async () => {
  // 1. Account A logs in and writes private note + pending_op
  await sandbox.transitionAccountContext("user_A");
  const epochA = sandbox.accountEpoch;
  await sandbox.idbPut("notes", { item_id: "n1", title: "Secret A", content: "Alpha", version: 0 }, "user_A", epochA);
  await sandbox.idbPut("pending_ops", { op_id: "op1", item_id: "n1", title: "Secret A", content: "Alpha", base_version: 0 }, "user_A", epochA);
  const notesA = await sandbox.idbGetAll("notes", "user_A", epochA);
  if (notesA.length !== 1) throw new Error("Expected 1 note for A");

  // 2. Logout A -> Login B
  await sandbox.transitionAccountContext("");
  await sandbox.transitionAccountContext("user_B");
  const epochB = sandbox.accountEpoch;

  // 3. B must see ZERO notes and ZERO pending_ops from A
  const notesB = await sandbox.idbGetAll("notes", "user_B", epochB);
  const opsB = await sandbox.idbGetAll("pending_ops", "user_B", epochB);
  if (notesB.length !== 0 || opsB.length !== 0) {
    throw new Error("Cross-account leak A->B detected!");
  }

  // 4. Late callback from A's epoch must be rejected
  let lateRejected = false;
  try {
    await sandbox.idbPut("notes", { item_id: "n_late", title: "Late", content: "X", version: 0 }, "user_A", epochA);
  } catch (e) {
    lateRejected = true;
  }
  if (!lateRejected) throw new Error("Late callback after account switch was not rejected!");
  console.log("F01_NODE_ISOLATION_OK");
})().catch((e) => { console.error(e); process.exit(1); });
"""
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
            tf.write(node_script)
            tf_path = tf.name
        try:
            proc = subprocess.run(["node", tf_path, app_js_path], capture_output=True, text=True, timeout=15)
            self.assertEqual(proc.returncode, 0, f"Node F01 test failed: {proc.stdout}\n{proc.stderr}")
            self.assertIn("F01_NODE_ISOLATION_OK", proc.stdout)
        finally:
            os.remove(tf_path)


class TestF05SSRFHardening(unittest.TestCase):
    def test_01_reject_userinfo_and_port_8080_and_mapped_loopback(self):
        for bad_url in (
            "http://user:pass@example.com/",
            "http://example.com:8080/",
            "http://[::ffff:127.0.0.1]/",
            "http://127.0.0.1/",
            "http://169.254.169.254/latest/meta-data/",
        ):
            ok, _ = WEB_GUARD.is_safe_url(bad_url)
            self.assertFalse(ok, f"URL dangereuse acceptée : {bad_url}")

    def test_02_dns_pinning_prevents_rebinding(self):
        import urllib3.util.connection as uconn
        captured = []
        orig = uconn.create_connection
        try:
            uconn.create_connection = lambda addr, *a, **kw: captured.append(addr)
            with _pin_dns_to_validated_ips("rebind.example.com", ["93.184.216.34"]):
                uconn.create_connection(("rebind.example.com", 443))
            self.assertEqual(captured, [("93.184.216.34", 443)])
        finally:
            uconn.create_connection = orig


class TestF07ZipBombAndTraversal(unittest.TestCase):
    def test_01_reject_zip_traversal_and_oversized_entry(self):
        rag = AliceRAGEngine()
        with tempfile.TemporaryDirectory() as td:
            # 1. Path traversal DOCX
            trav_docx = os.path.join(td, "trav.docx")
            with zipfile.ZipFile(trav_docx, "w") as z:
                z.writestr("../../evil.txt", "boom")
                z.writestr("word/document.xml", "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p><w:r><w:t>ok</w:t></w:r></w:p></w:body></w:document>")
            self.assertEqual(rag.extract_text_from_docx(trav_docx), [])

            # 2. Oversized compressed bomb (6 MB zeros -> tiny zip)
            bomb_docx = os.path.join(td, "bomb.docx")
            with zipfile.ZipFile(bomb_docx, "w", compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr("word/document.xml", b"A" * (6 * 1024 * 1024))
            self.assertEqual(rag.extract_text_from_docx(bomb_docx), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
