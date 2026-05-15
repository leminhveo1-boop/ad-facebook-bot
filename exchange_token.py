import requests
import json
import sys

app_id = "1595918954813262"
app_secret = "1176be676c24f216bf2144529308e286"
short_token = "EAAWretZAkV04BRbMLBrWHo7aXenpe9Jdr1VH4TTSXZBZAbuo4ucGVPRFxiGuSgQc4WQpi0Cit9iDPkiI3BsnZAo8ofRvnmtUorwQnDTBbxb8dU71QtVXjZBCanO2gPZA3ZAgJq68ZB776qHdUmHlihIAgt9mBl9uYHn3tzcuqSmT9RZCPCZCGUN59G2Mrq39CIrWn9xl7xHZAp2YhBkGV7VZBY5GCJlIL3QcZA5Xc2UZBEtsdvEISmZC39YWWtdlFfNttcAJd9KLIcAX5qsB0ZA1"

url = f"https://graph.facebook.com/v20.0/oauth/access_token"
params = {
    "grant_type": "fb_exchange_token",
    "client_id": app_id,
    "client_secret": app_secret,
    "fb_exchange_token": short_token
}

response = requests.get(url, params=params)
if response.status_code == 200:
    data = response.json()
    print("SUCCESS")
    print("LONG_LIVED_TOKEN=" + data.get("access_token", ""))
else:
    print("FAILED")
    print(response.text)
