import subprocess
import time
import os
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
# 1. Common Paths for Edge. Check which one you have.
# Try the first one. If it fails, uncomment the second one.
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
# EDGE_PATH = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"


USER_DATA_DIR = os.path.abspath("edge_bot_profile")

# 3. Target
TARGET_URL = "https://www.bhphotovideo.com/c/buy/Digital-Cameras/ci/9811/N/4288586282"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Go up one level
AUTH_FILE = os.path.join(BASE_DIR, "data", "auth.json")
# ---------------------

def get_real_edge_cookies():
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR)

    print(f"🚀 Step 1: Launching REAL EDGE from: {EDGE_PATH}")
    
   
    cmd = [
        EDGE_PATH,
        f"--user-data-dir={USER_DATA_DIR}", 
        "--remote-debugging-port=9223", # Note: 9223
        "--no-first-run",
        "--no-default-browser-check",
        TARGET_URL
    ]
    
    # Start Edge in background
    edge_process = subprocess.Popen(cmd)
    
    print("⏳ Waiting 5 seconds for Edge to initialize...")
    time.sleep(5)

    print("🔗 Step 2: Connecting Playwright to Edge...")
    with sync_playwright() as p:
        try:
            # Connect to port 9223
            browser = p.chromium.connect_over_cdp("http://localhost:9223")
            
            context = browser.contexts[0]
            page = context.pages[0]
            
            print("\n" + "="*50)
            print("🛑 ACTION REQUIRED (IN EDGE WINDOW):")
            print("1. Click 'Verify' if the box appears.")
            print("2. Wait for the Camera Page.")
            print("3. Come back here and press ENTER.")
            print("="*50 + "\n")
            
            input("Press Enter to save cookies...") 
            
            # Save the cookies
            context.storage_state(path=AUTH_FILE)
            print(f"✅ Success! Cookies saved to {AUTH_FILE} using Edge.")
            
            browser.close()
            
        except Exception as e:
            print(f"❌ Error connecting: {e}")
            print("Check if your EDGE_PATH is correct at the top of the script.")

    print("💀 Closing Edge...")
    edge_process.terminate()

if __name__ == "__main__":
    get_real_edge_cookies()