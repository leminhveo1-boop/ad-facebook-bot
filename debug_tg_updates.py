import os
import requests
from dotenv import load_dotenv

load_dotenv()

def check_updates():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    try:
        r = requests.get(url, params={"limit": 5, "timeout": 1})
        data = r.json()
        if data.get("ok"):
            results = data.get("result", [])
            if not results:
                print("No recent messages found. Please send a message to the bot first.")
            for item in results:
                msg = item.get("message", {})
                chat = msg.get("chat", {})
                from_user = msg.get("from", {})
                text = msg.get("text", "")
                print(f"--- UPDATE ---")
                print(f"From: {from_user.get('first_name')} (@{from_user.get('username')})")
                print(f"Chat ID: {chat.get('id')}")
                print(f"Text: {text}")
        else:
            print(f"Error: {data.get('description')}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    check_updates()
