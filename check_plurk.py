import json
import os
import requests
from datetime import datetime, timezone, timedelta
from requests_oauthlib import OAuth1

# === Telegram 設定 ===
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# === Plurk OAuth 認證 ===
APP_KEY = os.environ["PLURK_APP_KEY"]
APP_SECRET = os.environ["PLURK_APP_SECRET"]
ACCESS_TOKEN = os.environ["PLURK_ACCESS_TOKEN"]
ACCESS_TOKEN_SECRET = os.environ["PLURK_ACCESS_TOKEN_SECRET"]

auth = OAuth1(APP_KEY, APP_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

STATE_FILE = "last_plurk.json"

def base36_encode(number):
    chars = '0123456789abcdefghijklmnopqrstuvwxyz'
    base36 = ''
    while number > 0:
        number, i = divmod(number, 36)
        base36 = chars[i] + base36
    return base36

def convert_to_taiwan_time(utc_str):
    dt_utc = datetime.strptime(utc_str, "%a, %d %b %Y %H:%M:%S %Z")
    dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    dt_tw = dt_utc.astimezone(timezone(timedelta(hours=8)))
    return dt_tw.strftime("%Y-%m-%d %H:%M:%S")

def get_latest_plurk(query="麥當勞"):
    url = "https://www.plurk.com/APP/PlurkSearch/search"
    params = {"query": query, "limit": 1}
    response = requests.get(url, params=params, auth=auth)
    data = response.json()

    if 'plurks' in data and data['plurks']:
        plurk = data['plurks'][0]
        content = plurk.get('content_raw', '')
        plurk_id = plurk.get('plurk_id')
        posted_time = plurk.get('posted')
        time_tw = convert_to_taiwan_time(posted_time)
        link = f"https://www.plurk.com/p/{base36_encode(plurk_id)}"
        return plurk_id, content, time_tw, link
    return None, None, None, None

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=payload)

def load_last_state():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_last_state(plurk_id, time_str):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"plurk_id": plurk_id, "time": time_str}, f)

if __name__ == "__main__":
    last_state = load_last_state()
    pid, content, time_tw, link = get_latest_plurk()
    if pid and content:
        if not last_state or pid != last_state["plurk_id"]:
            msg = f"🆕 Plurk 有新貼文！\n\n📝 {content}\n⏰ {time_tw}\n🔗 {link}"
            print(msg)
            send_telegram_message(msg)
            save_last_state(pid, time_tw)
        else:
            print("🔍 沒有新貼文")
    else:
        print("❌ 找不到任何貼文")
