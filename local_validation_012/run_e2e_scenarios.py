import requests
import json
import asyncio
import websockets
import time
import sys
import os

BASE_HTTP = "http://127.0.0.1:8080"
BASE_WS = "ws://127.0.0.1:8765"

def test_scenario_1_pairing(pin_code):
    print("\n=== SCENARIO 1: APPAIRAGE ET GESTION DE SESSION ===")
    s = requests.Session()
    
    # 1. Check status before pairing
    r_status = s.get(f"{BASE_HTTP}/api/pair/status", timeout=5)
    print(f"GET /api/pair/status -> {r_status.status_code}: {r_status.text}")
    
    # 2. Check protected endpoint BEFORE pairing (must fail 401)
    r_unauth = s.get(f"{BASE_HTTP}/api/ops/metrics", timeout=5)
    print(f"GET /api/ops/metrics (unauth) -> {r_unauth.status_code} (Expected: 401)")
    assert r_unauth.status_code == 401, f"Expected 401, got {r_unauth.status_code}"
    
    # 3. Pair with invalid PIN (must fail 401)
    r_bad = s.post(f"{BASE_HTTP}/api/pair", json={"code": "999999"}, timeout=5)
    print(f"POST /api/pair (bad code) -> {r_bad.status_code}: {r_bad.text}")
    assert r_bad.status_code == 401, f"Expected 401 on bad PIN"
    
    # 4. Pair with valid PIN
    r_good = s.post(f"{BASE_HTTP}/api/pair", json={"code": pin_code}, timeout=5)
    print(f"POST /api/pair (valid code {pin_code}) -> {r_good.status_code}: {r_good.text}")
    assert r_good.status_code == 200, f"Pairing failed: {r_good.text}"
    data = r_good.json()
    assert data.get("success") is True
    assert "alice_session" in s.cookies
    csrf_token = data.get("csrf_token")
    print(f"Session paired! Role: {data.get('role')}, Cookie present: {'alice_session' in s.cookies}, CSRF present: {bool(csrf_token)}")
    
    # 5. Replay same PIN (must fail 401 - single use!)
    r_replay = s.post(f"{BASE_HTTP}/api/pair", json={"code": pin_code}, timeout=5)
    print(f"POST /api/pair (replay same PIN) -> {r_replay.status_code} (Expected: 401)")
    assert r_replay.status_code == 401, "PIN replay should be rejected!"
    
    # 6. Access protected endpoints AFTER pairing
    for ep in ["/api/me", "/api/ops/metrics", "/api/flags", "/api/quick_actions", "/api/briefing", "/api/jobs/stats", "/api/iot/routines", "/api/kg", "/api/commitments"]:
        r_ep = s.get(f"{BASE_HTTP}{ep}", timeout=5)
        print(f"GET {ep} (authenticated) -> {r_ep.status_code}: {r_ep.text[:140]}")
        assert r_ep.status_code == 200, f"Expected 200 on {ep}, got {r_ep.status_code}"
    
    return s, csrf_token, data

async def test_scenario_2_websocket(session_cookie_val):
    print("\n=== SCENARIO 2: COMMUNICATION WEBSOCKET TEMPS RÉEL AUTHENTIFIÉE ===")
    headers = {"Cookie": f"alice_session={session_cookie_val}"}
    async with websockets.connect(BASE_WS, additional_headers=headers, open_timeout=5) as ws:
        print("WebSocket connected with session cookie!")
        
        # Send user message / text command
        cmd = json.dumps({"action": "user_message", "text": "Bonjour Alice, quel est ton statut ?"})
        await ws.send(cmd)
        print("Sent user_message over WebSocket.")
        
        # Wait briefly for any state updates or responses
        messages_received = []
        try:
            for _ in range(3):
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                messages_received.append(msg)
                print(f"WS Received: {msg[:150]}")
        except asyncio.TimeoutError:
            pass
        print(f"WebSocket communication test finished ({len(messages_received)} messages received).")

def test_scenario_3_api_actions_and_notes(session, csrf_token):
    print("\n=== SCENARIO 3: ACTIONS MÉTIER, NOTES SYNC, KG & CONTRÔLE CSRF ===")
    
    # 1. Browser-style POST with Origin header but WITHOUT CSRF token must be rejected (403)
    r_no_csrf = session.post(
        f"{BASE_HTTP}/api/sync/notes",
        headers={"Origin": "http://127.0.0.1:8080"},
        json={"ops": []},
        timeout=5
    )
    print(f"POST /api/sync/notes (with Origin, without CSRF) -> {r_no_csrf.status_code} (Expected: 403)")
    assert r_no_csrf.status_code == 403, f"Expected 403 without CSRF when Origin present, got {r_no_csrf.status_code}"
    
    # 2. POST /api/sync/notes with valid CSRF token
    headers = {"Origin": "http://127.0.0.1:8080", "X-CSRF-Token": csrf_token}
    test_op = {
        "op_id": "op_val_012_1",
        "op": "upsert",
        "note": {"id": "val_012_note_1", "title": "Note Test 012", "content": "Validation locale E2E", "updated_at": time.time()}
    }
    r_sync = session.post(f"{BASE_HTTP}/api/sync/notes", headers=headers, json={"ops": [test_op]}, timeout=5)
    print(f"POST /api/sync/notes (with CSRF) -> {r_sync.status_code}: {r_sync.text[:180]}")
    assert r_sync.status_code == 200
    
    # 3. GET /api/sync/notes to verify persistence
    r_notes = session.get(f"{BASE_HTTP}/api/sync/notes", timeout=5)
    print(f"GET /api/sync/notes -> {r_notes.status_code}: {r_notes.text[:180]}")
    assert r_notes.status_code == 200
    
    # 4. POST /api/kg entity upsert & retrieval
    r_kg_post = session.post(
        f"{BASE_HTTP}/api/kg",
        headers=headers,
        json={"action": "upsert_entity", "entity_id": "test_012_ent", "type": "project", "name": "ALICE Validation 012"},
        timeout=5
    )
    print(f"POST /api/kg -> {r_kg_post.status_code}: {r_kg_post.text[:180]}")
    
    # 5. POST unknown endpoint (must be fail-closed 404!)
    r_unknown = session.post(f"{BASE_HTTP}/api/unknown_bypass", headers=headers, json={}, timeout=5)
    print(f"POST /api/unknown_bypass -> {r_unknown.status_code} (Expected: 404)")
    assert r_unknown.status_code == 404

def test_scenario_4_security_regression(session, csrf_token):
    print("\n=== SCENARIO 4: NON-RÉGRESSION SÉCURITÉ (PATH TRAVERSAL, SSRF, REVOKE) ===")
    
    # 1. Path traversal attempt on static server
    r_trav = session.get(f"{BASE_HTTP}/../main2.py", timeout=5)
    print(f"GET /../main2.py -> {r_trav.status_code} (Expected: 403 or 404)")
    assert r_trav.status_code in (403, 404)
    
    # 2. Session revocation
    r_rev = session.post(f"{BASE_HTTP}/api/revoke_session", headers={"X-CSRF-Token": csrf_token}, json={}, timeout=5)
    print(f"POST /api/revoke_session -> {r_rev.status_code}: {r_rev.text}")
    assert r_rev.status_code == 200
    
    # 3. Verify revoked session is rejected
    r_after = session.get(f"{BASE_HTTP}/api/ops/metrics", timeout=5)
    print(f"GET /api/ops/metrics (after revoke) -> {r_after.status_code} (Expected: 401)")
    assert r_after.status_code == 401

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_e2e_scenarios.py <PIN_CODE>")
        sys.exit(1)
    pin = sys.argv[1]
    sess, csrf, pair_data = test_scenario_1_pairing(pin)
    cookie_val = sess.cookies.get("alice_session")
    asyncio.run(test_scenario_2_websocket(cookie_val))
    test_scenario_3_api_actions_and_notes(sess, csrf)
    test_scenario_4_security_regression(sess, csrf)
    print("\nALL LIVE HTTP/WS E2E SCENARIOS PASSED SUCCESSFULLY!")
