import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_fb():
    token = os.getenv("FB_ACCESS_TOKEN")
    account_id = os.getenv("FB_AD_ACCOUNT_ID")
    
    print(f"Testing connection for Account: {account_id}")
    
    url = f"https://graph.facebook.com/v19.0/{account_id}/insights"
    params = {
        "access_token": token,
        "date_preset": "today",
        "fields": "spend,impressions"
    }
    
    try:
        r = requests.get(url, params=params)
        data = r.json()
        if "error" in data:
            print(f"[ERROR] FB API Error: {data['error'].get('message')}")
            return False
        else:
            print("[OK] FB API Connection Success!")
            print(f"   Data received: {data.get('data')}")
            return True
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return False

def test_tg():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/getMe"
    
    try:
        r = requests.get(url)
        data = r.json()
        if data.get("ok"):
            print(f"[OK] Telegram Bot Connection Success! Bot: @{data['result']['username']}")
            return True
        else:
            print(f"[ERROR] Telegram API Error: {data.get('description')}")
            return False
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return False

if __name__ == "__main__":
    print("--- STARTING SYSTEM TEST ---")
    fb_ok = test_fb()
    tg_ok = test_tg()
    print("--- TEST FINISHED ---")
    if fb_ok and tg_ok:
        print("\n[SUCCESS] ALL SYSTEMS GO!")
    else:
        print("\n[FAIL] SOME TESTS FAILED. Check credentials.")
