import os
import sys

# Ensure current working directory has Jarvis Final - SITE
site_dir = os.path.abspath("Jarvis Final - SITE")
sys.path.insert(0, site_dir)
os.chdir(site_dir)

print("Attempting to import main2...")
try:
    import main2
    print("SUCCESS: main2 imported successfully without syntax or module error.")
except Exception as e:
    print(f"FAILED to import main2: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
