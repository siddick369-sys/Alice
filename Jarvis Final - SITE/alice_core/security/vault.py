#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEATURE 29 — ENCRYPTED SENSITIVE DATA VAULT (ALICE-SEC-029, Wave 6).
Coffre-fort chiffré AES-256-GCM avec dérivation Scrypt + sel aléatoire,
nonce unique par opération, rotation de clé, verrouillage automatique,
journalisation d'audit sans fuite, contrôle RBAC strict (OWNER + step-up)
et isolation absolue hors RAG, logs et prompts IA.
"""

import os
import json
import time
import uuid
import base64
import threading
from typing import Dict, Any, Optional, List
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from alice_core.feature_flags import FEATURE_FLAGS
from alice_core.contracts import AliceSecurityError
from alice_core.security.rbac import RBAC, UserPrincipal, Role
from alice_core.security.audit import AUDIT_LOGGER


class EncryptedDataVault:
    """Coffre-fort AES-256-GCM isolé de la mémoire ordinaire et du RAG."""

    VAULT_VERSION = 1

    def __init__(self, vault_dir: Optional[str] = None, auto_lock_seconds: float = 300.0):
        self._lock = threading.RLock()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.vault_dir = vault_dir or os.path.join(base_dir, "alice_outputs", "secure_vault")
        self.vault_file = os.path.join(self.vault_dir, "alice_vault.vault")
        self.auto_lock_seconds = float(auto_lock_seconds)
        self._active_key: Optional[bytes] = None
        self._unlocked_until: float = 0.0
        self._owner_id: Optional[str] = None

    @staticmethod
    def _derive_key(passphrase: str, salt: bytes) -> bytes:
        if not passphrase or len(passphrase) < 8:
            raise ValueError("La phrase secrète du coffre-fort doit comporter au moins 8 caractères.")
        kdf = Scrypt(salt=salt, length=32, n=2 ** 14, r=8, p=1)
        return kdf.derive(passphrase.encode("utf-8"))

    @staticmethod
    def _encrypt_blob(key: bytes, plaintext_bytes: bytes, aad: bytes) -> Dict[str, str]:
        nonce = os.urandom(12)  # 96-bit nonce unique
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, plaintext_bytes, aad)
        return {
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ct).decode("ascii"),
        }

    @staticmethod
    def _decrypt_blob(key: bytes, enc_obj: Dict[str, str], aad: bytes) -> bytes:
        nonce = base64.b64decode(enc_obj["nonce"])
        ct = base64.b64decode(enc_obj["ciphertext"])
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ct, aad)

    def _require_vault_access(self, principal: UserPrincipal, action: str):
        FEATURE_FLAGS.require_enabled("encrypted_vault")
        if principal.role != Role.OWNER:
            AUDIT_LOGGER.log("VAULT", f"{action}_denied_role", principal.user_id, principal.role.value, principal.session_id, "DENIED")
            raise AliceSecurityError("Accès au coffre-fort strictement réservé au propriétaire (OWNER).")
        ok, reason = RBAC.authorize(principal, "vault", action)
        if not ok:
            raise AliceSecurityError(reason)

    def _load_raw_vault(self) -> Dict[str, Any]:
        if not os.path.exists(self.vault_file):
            raise FileNotFoundError("Coffre-fort non initialisé.")
        with open(self.vault_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_raw_vault(self, data: Dict[str, Any]):
        os.makedirs(self.vault_dir, exist_ok=True)
        tmp = f"{self.vault_file}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.vault_file)

    def initialize(self, principal: UserPrincipal, master_passphrase: str) -> Dict[str, Any]:
        self._require_vault_access(principal, "write")
        with self._lock:
            if os.path.exists(self.vault_file):
                raise FileExistsError("Le coffre-fort est déjà initialisé.")
            salt = os.urandom(16)
            key = self._derive_key(master_passphrase, salt)
            verifier = self._encrypt_blob(key, b"ALICE_VAULT_VERIFIED", b"vault_verifier_v1")
            vault_data = {
                "version": self.VAULT_VERSION,
                "key_epoch": 1,
                "owner_id": principal.user_id,
                "salt": base64.b64encode(salt).decode("ascii"),
                "verifier": verifier,
                "entries": {},
            }
            self._save_raw_vault(vault_data)
            self._active_key = key
            self._owner_id = principal.user_id
            self._unlocked_until = time.time() + self.auto_lock_seconds
            AUDIT_LOGGER.log("VAULT", "vault_initialized", principal.user_id, principal.role.value, principal.session_id, "OK")
            return {"initialized": True, "version": self.VAULT_VERSION, "key_epoch": 1}

    def unlock(self, principal: UserPrincipal, master_passphrase: str) -> bool:
        self._require_vault_access(principal, "read")
        with self._lock:
            data = self._load_raw_vault()
            salt = base64.b64decode(data["salt"])
            key = self._derive_key(master_passphrase, salt)
            try:
                plain = self._decrypt_blob(key, data["verifier"], f"vault_verifier_v{data['key_epoch']}".encode("utf-8"))
                if data["key_epoch"] == 1:
                    pass
                if plain != b"ALICE_VAULT_VERIFIED":
                    raise ValueError("Invalid verifier")
            except Exception:
                # Re-tester avec AAD générique si key_epoch > 1
                try:
                    plain2 = self._decrypt_blob(key, data["verifier"], b"vault_verifier_v1")
                    if plain2 != b"ALICE_VAULT_VERIFIED":
                        raise ValueError("Invalid verifier")
                except Exception:
                    AUDIT_LOGGER.log("VAULT", "unlock_failed", principal.user_id, principal.role.value, principal.session_id, "DENIED")
                    raise AliceSecurityError("Phrase secrète du coffre-fort incorrecte.")

            self._active_key = key
            self._owner_id = data["owner_id"]
            self._unlocked_until = time.time() + self.auto_lock_seconds
            AUDIT_LOGGER.log("VAULT", "vault_unlocked", principal.user_id, principal.role.value, principal.session_id, "OK")
            return True

    def lock(self):
        with self._lock:
            self._active_key = None
            self._unlocked_until = 0.0
            AUDIT_LOGGER.log("VAULT", "vault_locked", outcome="OK")

    def is_unlocked(self) -> bool:
        with self._lock:
            if self._active_key is None:
                return False
            if time.time() > self._unlocked_until:
                self.lock()
                return False
            return True

    def _get_active_key(self, principal: UserPrincipal, action: str) -> bytes:
        self._require_vault_access(principal, action)
        with self._lock:
            if not self.is_unlocked():
                raise AliceSecurityError("Coffre-fort verrouillé : déverrouillage requis.")
            return self._active_key

    def store_secret(self, principal: UserPrincipal, label: str, secret_value: str, category: str = "general") -> str:
        key = self._get_active_key(principal, "write")
        with self._lock:
            data = self._load_raw_vault()
            item_id = f"sec_{uuid.uuid4().hex[:10]}"
            epoch = data["key_epoch"]
            aad = f"{item_id}|{epoch}|{category}".encode("utf-8")
            payload = json.dumps({"label": label, "value": secret_value, "category": category, "ts": time.time()}).encode("utf-8")
            enc = self._encrypt_blob(key, payload, aad)
            data["entries"][item_id] = {
                "item_id": item_id,
                "key_epoch": epoch,
                "category": category,
                "enc": enc,
                "created_at": time.time(),
            }
            self._save_raw_vault(data)
            self._unlocked_until = time.time() + self.auto_lock_seconds
            # Jamais la valeur secrète dans l'audit !
            AUDIT_LOGGER.log("VAULT", "secret_stored", principal.user_id, principal.role.value, principal.session_id, "OK", {"item_id": item_id})
            return item_id

    def read_secret(self, principal: UserPrincipal, item_id: str) -> Dict[str, Any]:
        key = self._get_active_key(principal, "read")
        with self._lock:
            data = self._load_raw_vault()
            entry = data["entries"].get(item_id)
            if not entry:
                raise KeyError("Entrée introuvable dans le coffre-fort.")
            aad = f"{item_id}|{entry['key_epoch']}|{entry['category']}".encode("utf-8")
            plain = self._decrypt_blob(key, entry["enc"], aad)
            obj = json.loads(plain.decode("utf-8"))
            self._unlocked_until = time.time() + self.auto_lock_seconds
            AUDIT_LOGGER.log("VAULT", "secret_read", principal.user_id, principal.role.value, principal.session_id, "OK", {"item_id": item_id})
            return obj

    def delete_secret(self, principal: UserPrincipal, item_id: str) -> bool:
        self._get_active_key(principal, "write")
        with self._lock:
            data = self._load_raw_vault()
            if item_id in data["entries"]:
                del data["entries"][item_id]
                self._save_raw_vault(data)
                AUDIT_LOGGER.log("VAULT", "secret_deleted", principal.user_id, principal.role.value, principal.session_id, "OK", {"item_id": item_id})
                return True
            return False

    def rotate_master_key(self, principal: UserPrincipal, old_passphrase: str, new_passphrase: str) -> int:
        self._require_vault_access(principal, "write")
        with self._lock:
            data = self._load_raw_vault()
            old_salt = base64.b64decode(data["salt"])
            old_key = self._derive_key(old_passphrase, old_salt)
            try:
                self._decrypt_blob(old_key, data["verifier"], b"vault_verifier_v1")
            except Exception:
                raise AliceSecurityError("Ancienne phrase secrète invalide pour la rotation.")

            new_salt = os.urandom(16)
            new_key = self._derive_key(new_passphrase, new_salt)
            new_epoch = data["key_epoch"] + 1
            new_entries = {}
            for iid, entry in data["entries"].items():
                old_aad = f"{iid}|{entry['key_epoch']}|{entry['category']}".encode("utf-8")
                plain = self._decrypt_blob(old_key, entry["enc"], old_aad)
                new_aad = f"{iid}|{new_epoch}|{entry['category']}".encode("utf-8")
                new_entries[iid] = {
                    "item_id": iid,
                    "key_epoch": new_epoch,
                    "category": entry["category"],
                    "enc": self._encrypt_blob(new_key, plain, new_aad),
                    "created_at": entry["created_at"],
                }

            data["salt"] = base64.b64encode(new_salt).decode("ascii")
            data["key_epoch"] = new_epoch
            data["verifier"] = self._encrypt_blob(new_key, b"ALICE_VAULT_VERIFIED", b"vault_verifier_v1")
            data["entries"] = new_entries
            self._save_raw_vault(data)
            self._active_key = new_key
            AUDIT_LOGGER.log("VAULT", "master_key_rotated", principal.user_id, principal.role.value, principal.session_id, "OK", {"new_epoch": new_epoch})
            return new_epoch


VAULT_MANAGER = EncryptedDataVault()
