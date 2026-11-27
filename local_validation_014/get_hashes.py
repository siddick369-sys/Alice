import hashlib
import os
import sys
import platform
import socket

files = [
    'Jarvis Final - SITE/main2.py',
    'Jarvis Final - SITE/alice_modules.py',
    'Jarvis Final - SITE/jarvis_agent.py',
    'Jarvis Final - SITE/alice_web_guard.py',
    'Jarvis Final - SITE/alice_rag.py',
    'Jarvis Final - SITE/vision_ocr.py',
    'Jarvis Final - SITE/alice_core/security/rbac.py',
    'Jarvis Final - SITE/alice_core/api_bridge.py',
    'Jarvis Final - SITE/mobile/app.js',
    'Jarvis Final - SITE/mobile/index.html',
    'Jarvis Final - SITE/mobile/orb.js',
    'Jarvis Final - SITE/mobile/sw.js',
    'Jarvis Final - SITE/frontend/src/main.ts'
]

print("=== PLATFORM INFO ===")
print("OS:", platform.platform())
print("Python:", sys.version)
print("Hostname:", socket.gethostname())

print("\n=== INITIAL FILE HASHES (MISSION 014) ===")
for f in files:
    norm_f = os.path.normpath(f)
    if os.path.exists(norm_f):
        h = hashlib.sha256(open(norm_f, 'rb').read()).hexdigest()
        print(f"{norm_f} | {h}")
    else:
        print(f"{norm_f} | NOT_FOUND")
