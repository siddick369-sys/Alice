import requests
import json
import asyncio
import websockets

def test_http_endpoints():
    print("=== PROBING HTTP ENDPOINTS ===")
    
    # 1. Mobile index.html
    try:
        r1 = requests.get("http://127.0.0.1:8080/index.html", timeout=5)
        print(f"GET http://127.0.0.1:8080/index.html -> Status: {r1.status_code}, Length: {len(r1.content)} bytes, Content-Type: {r1.headers.get('Content-Type')}")
    except Exception as e:
        print(f"GET http://127.0.0.1:8080/index.html FAILED: {e}")

    # 2. Mobile pairing status
    try:
        r2 = requests.get("http://127.0.0.1:8080/api/pair/status", timeout=5)
        print(f"GET http://127.0.0.1:8080/api/pair/status -> Status: {r2.status_code}, Body: {r2.text.strip()}")
    except Exception as e:
        print(f"GET http://127.0.0.1:8080/api/pair/status FAILED: {e}")

    # 3. Mobile Manifest
    try:
        r3 = requests.get("http://127.0.0.1:8080/manifest.json", timeout=5)
        print(f"GET http://127.0.0.1:8080/manifest.json -> Status: {r3.status_code}, Length: {len(r3.content)} bytes")
    except Exception as e:
        print(f"GET http://127.0.0.1:8080/manifest.json FAILED: {e}")

    # 4. Vite Frontend
    try:
        r4 = requests.get("http://localhost:5173/", timeout=5)
        print(f"GET http://localhost:5173/ -> Status: {r4.status_code}, Length: {len(r4.content)} bytes, Title: {'voice-assistant-ui' in r4.text}")
    except Exception as e:
        print(f"GET http://localhost:5173/ FAILED: {e}")

async def test_ws_connection():
    print("\n=== PROBING WEBSOCKET GATEWAY ===")
    try:
        async with websockets.connect("ws://127.0.0.1:8765", open_timeout=5) as ws:
            print("WebSocket handshake connected successfully!")
            
            # Send an anonymous ping or hello message
            hello_msg = json.dumps({"action": "ping", "data": "probe"})
            await ws.send(hello_msg)
            try:
                reply = await asyncio.wait_for(ws.recv(), timeout=3)
                print(f"WebSocket received message: {reply[:120]}...")
            except asyncio.TimeoutError:
                print("WebSocket connected (no immediate response to ping, normal behavior for state broadcast).")
    except Exception as e:
        print(f"WebSocket probe FAILED: {e}")

if __name__ == "__main__":
    test_http_endpoints()
    asyncio.run(test_ws_connection())
