import random
import time 
import json
import pymongo
from datetime import datetime
from playwright.sync_api import sync_playwright
from rich import print 
import os

# --- CONFIGURATION ---
# Update this path to where your auth.json actually lives
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Go up one level
AUTH_FILE = os.path.join(BASE_DIR, "data", "auth.json")

# MongoDB Config (Matches your Docker setup)
MONGO_URI = "mongodb://admin:password123@localhost:27017/" 
DB_NAME = "bh_scraper"
COLLECTION_NAME = "cameras_raw"
# ---------------------

# 1. Initialize MongoDB Connection (Global)
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    # Test connection
    client.server_info() 
    print("✅ Connected to MongoDB successfully.")
except Exception as e:
    print(f"❌ Critical MongoDB Error: {e}")
    exit()

def save_to_mongo(data, url):
    """Helper to save data to MongoDB with error handling"""
    try:
        # Add metadata
        data["_scraped_at"] = datetime.utcnow()
        data["_source_url"] = url
        
        # Insert
        collection.insert_one(data)
        print("      💾 Saved to MongoDB")
        
    except Exception as e:
        print(f"      ⚠️ MongoDB Write Error: {e}")
        # Backup to file if DB fails
        with open("failed_inserts.jsonl", "a") as f:
            f.write(json.dumps(data) + "\n")

def run_scraper():
    with sync_playwright() as p:
        print("🚀 Launching scraper as Microsoft Edge...")
        
        # 2. Launch Browser
        # We use 'msedge' channel to match the cookies you created manually
        browser = p.chromium.launch(
            channel="msedge",  
            headless=False,    
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        # 3. Load Context
        # We DO NOT set a custom UserAgent here. We let Edge use its default one.
        context = browser.new_context(
            storage_state=AUTH_FILE,
            viewport={"width": 1920, "height": 1080}
        )
        
        # Extra Stealth: Remove 'navigator.webdriver' flag
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        
        page = context.new_page()
        
        i = 1
        body_url = "https://www.bhphotovideo.com/c/buy/Digital-Cameras/ci/9811/N/4288586282"
        navigating_url = "https://www.bhphotovideo.com"

        try:
            while True:
                # --- PAGINATION LOOP ---
                if i == 1:
                    current_url = body_url
                else:
                    current_url = f"{body_url}/pn/{i}"
                
                print(f"🌍 Navigated to: {current_url}")
                page.goto(current_url)
                
                # Check for Silent Redirect (End of Pages)
                final_url = page.url
                if "/pn/" not in final_url and i > 1:
                    print("🛑 Redirected to base URL. Reached end of pages.")
                    break
                
                # Wait for Product List to Load
                try:
                    page.wait_for_selector("a[data-selenium='miniProductPageProductNameLink']", timeout=15000)
                except:
                    print("❌ Page load timeout or Cloudflare block.")
                    break
                
                # --- COLLECT LINKS ---
                product_links = []
                elements = page.locator("a[data-selenium='miniProductPageProductNameLink']").all()
                for el in elements:
                    href = el.get_attribute("href")
                    if href:
                        product_links.append(href)
                
                print(f"   📦 Found {len(product_links)} products. Processing...")

                # --- VISIT PRODUCTS LOOP ---
                for link in product_links: 
                    full_link = f"{navigating_url}{link}"
                    print("-" * 50)
                    print(f"   🔗 Visiting: {full_link}")
                    
                    # Navigate
                    page.goto(full_link)
                    
                    # --- DATA EXTRACTION ---
                    try:
                        # FIX: Wait for the VISIBLE TITLE, not the hidden script.
                        # This guarantees the HTML is fully loaded.
                        page.wait_for_selector("h1[data-selenium='productTitle']", timeout=15000)
                        
                        # Now grab all JSON-LD scripts
                        scripts = page.locator("script[type='application/ld+json']").all()
                        found_data = False
                        
                        for script in scripts:
                            try:
                                text = script.text_content()
                                data = json.loads(text)
                                
                                # Filter for the "Product" schema
                                target_data = None
                                if isinstance(data, list):
                                    for item in data:
                                        if item.get("@type") == "Product":
                                            target_data = item
                                            break
                                elif data.get("@type") == "Product":
                                    target_data = data
                                
                                if target_data:
                                    print("      ✅ Found Product Schema!")
                                    save_to_mongo(target_data, full_link)
                                    found_data = True
                                    break # Stop checking other scripts on this page
                                    
                            except Exception:
                                continue
                        
                        if not found_data:
                            print("      ⚠️ No JSON-LD Product data found.")

                    except Exception as e:
                        print(f"      ❌ Error processing page: {e}")

                    # Random sleep between products (Humanizing)
                    randome_time = random.uniform(2.5, 4.5)
                    print(f"      ⏳ Sleeping {randome_time:.1f}s...")
                    time.sleep(randome_time)

                # --- NEXT PAGE PREP ---
                sleep_time = random.uniform(3.5, 6.5)
                print(f"   💤 Page finished. Sleeping {sleep_time:.1f}s before next page...")
                time.sleep(sleep_time)
                
                i += 1
                
        except Exception as e:
            print(f"❌ CRITICAL ERROR: {e}")

        browser.close()

if __name__ == "__main__":
    run_scraper()