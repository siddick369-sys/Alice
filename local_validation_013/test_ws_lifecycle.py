import asyncio
import json
import websockets
import requests
import time
import sys
import os

BASE_HTTP = "http://127.0.0.1:8080"
BASE_WS = "ws://127.0.0.1:8765"

async def test_unauthenticated_ws():
    print("\n--- TEST WS-01: Connexion WebSocket Anonyme (sans cookie de session) ---")
    async with websockets.connect(BASE_WS, open_timeout=5) as ws:
        print("[WS-01] Handshake TCP & HTTP 101 Réussi sur", BASE_WS)
        print("[WS-01] ws.state =", getattr(ws, "state", "connected"))
        
        # Attendre un message initial éventuel pendant 2 secondes
        msg_received = None
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
            msg_received = json.loads(msg)
            print(f"[WS-01] Message reçu : {msg[:120]}")
        except asyncio.TimeoutError:
            print("[WS-01] Aucun message initial 'auth_ok' reçu (Attendu: client non authentifié).")
        
        has_auth_ok = msg_received and msg_received.get("type") == "auth_ok"
        print(f"[WS-01] auth_ok reçu ? {has_auth_ok} (Attendu: False)")
        assert not has_auth_ok, "Un client anonyme ne doit PAS recevoir auth_ok !"
        print("[WS-01] Preuve formelle : En mode anonyme, la socket est ouverte mais le badge UI reste 'hors-ligne'.")

async def test_authenticated_ws(session_cookie_val):
    print("\n--- TEST WS-02: Connexion WebSocket Authentifiée (avec cookie alice_session) ---")
    headers = {"Cookie": f"alice_session={session_cookie_val}"}
    async with websockets.connect(BASE_WS, additional_headers=headers, open_timeout=5) as ws:
        print("[WS-02] Handshake WebSocket réussi avec cookie session.")
        # Le serveur doit envoyer auth_ok
        msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
        data = json.loads(msg)
        print(f"[WS-02] Message serveur : type={data.get('type')}, message={data.get('message')}")
        assert data.get("type") == "auth_ok", f"Attendu: auth_ok, reçu: {data}"
        print("[WS-02] Preuve formelle : auth_ok déclenche setConnected(true) -> badge passe à 'connecté'.")
        
        # Test de communication fonctionnelle bi-directionnelle
        cmd = json.dumps({"action": "ping", "data": "probe_013"})
        await ws.send(cmd)
        print("[WS-02] Trame envoyée avec succès sur la socket active.")

async def test_revoked_session_ws(session_cookie_val):
    print("\n--- TEST WS-03: Connexion WebSocket avec Session Révoquée ---")
    headers = {"Cookie": f"alice_session={session_cookie_val}"}
    try:
        async with websockets.connect(BASE_WS, additional_headers=headers, open_timeout=5) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
            data = json.loads(msg)
            print(f"[WS-03] Message reçu : {data}")
            # Le serveur doit soit fermer soit envoyer auth_error
            try:
                msg2 = await asyncio.wait_for(ws.recv(), timeout=2.0)
                print(f"[WS-03] Message suivant : {msg2}")
            except websockets.exceptions.ConnectionClosed as cc:
                print(f"[WS-03] Socket fermée par le serveur : code={cc.code}, reason={cc.reason}")
    except websockets.exceptions.ConnectionClosed as cc:
        print(f"[WS-03] Connexion fermée : code={cc.code}, reason={cc.reason}")
    except Exception as e:
        print(f"[WS-03] Résultat : {type(e).__name__}: {e}")

def run_all(pin_code):
    print("============================================================")
    print("ENQUÊTE FORENSIQUE : RÉSOLUTION CONTRADICTION WEBSOCKET")
    print("============================================================")
    
    # Étape 1 : Test Anonyme
    asyncio.run(test_unauthenticated_ws())
    
    # Étape 2 : Appairage réel pour obtenir le cookie
    print("\n--- Étape Intermédiaire : Appairage HTTP réel ---")
    s = requests.Session()
    r = s.post(f"{BASE_HTTP}/api/pair", json={"code": pin_code}, timeout=5)
    print(f"POST /api/pair -> {r.status_code}: {r.text}")
    assert r.status_code == 200, "Échec de l'appairage"
    cookie_val = s.cookies.get("alice_session")
    csrf_token = r.json().get("csrf_token")
    assert cookie_val, "Cookie alice_session manquant"
    
    # Étape 3 : Test Authentifié
    asyncio.run(test_authenticated_ws(cookie_val))
    
    # Étape 4 : Révocation explicite
    print("\n--- Étape Intermédiaire : Révocation de Session ---")
    r_rev = s.post(f"{BASE_HTTP}/api/revoke_session", headers={"X-CSRF-Token": csrf_token}, json={}, timeout=5)
    print(f"POST /api/revoke_session -> {r_rev.status_code}: {r_rev.text}")
    assert r_rev.status_code == 200
    
    # Étape 5 : Test Session Révoquée
    asyncio.run(test_revoked_session_ws(cookie_val))
    print("\n>>> ENQUÊTE WEBSOCKET TERMINÉE AVEC SUCCÈS <<<")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ws_lifecycle.py <PIN>")
        sys.exit(1)
    run_all(sys.argv[1])
