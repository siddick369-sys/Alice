import sys
import importlib
import os
import shutil

print("=== CHECK PYTHON PACKAGES ===")
modules = [
    "websockets", "requests", "numpy", "cv2", "cryptography", 
    "pytesseract", "mss", "speech_recognition", "pyaudio", 
    "dotenv", "jwt"
]

results = {}
for m in modules:
    try:
        mod = importlib.import_module(m)
        ver = getattr(mod, "__version__", "installed")
        results[m] = f"OK ({ver})"
    except Exception as e:
        results[m] = f"MISSING/ERROR: {e}"

for m, status in results.items():
    print(f"  {m:20s}: {status}")

print("\n=== SYSTEM BINARIES ===")
for b in ["node", "npm", "tesseract", "ffmpeg"]:
    p = shutil.which(b)
    print(f"  {b:15s}: {p if p else 'NOT_IN_PATH'}")

print("\n=== ENV FILES ===")
env_file = os.path.join("Jarvis Final - SITE", ".env")
print(f"  .env exists: {os.path.exists(env_file)}")
if os.path.exists(env_file):
    # Check variables without printing their values
    with open(env_file, "r", encoding="utf-8", errors="ignore") as f:
        vars_found = []
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k = line.split("=")[0].strip()
                vars_found.append(k)
        print(f"  .env keys defined: {len(vars_found)} variables ({', '.join(vars_found[:8])}...)")
