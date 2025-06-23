# check_plurk.py
import os
import json
import requests
from datetime import datetime, timezone, timedelta
from requests_oauthlib import OAuth1

# === 環境變數設定 ===
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
APP_KEY = os.environ["PLURK_APP_KEY"]
APP_SECRET = os.environ["PLURK_APP_SECRET"]
ACCESS_TOKEN = os.environ["PLURK_ACCESS_TOKEN"]
ACCESS_TOKEN_SECRET = os.environ["PLURK_ACCESS_TOKEN_SECRET"]

STATE_FILE = ".github/state/last_plurk.json"
auth = OAuth1(APP_KEY, APP_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

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

def get_latest_plurks(query="麥當勞", limit=10):
    url = "https://www.plurk.com/APP/PlurkSearch/search"
    params = {"query": query, "limit": limit}
    response = requests.get(url, params=params, auth=auth)
    data = response.json()

    results = []
    if 'plurks' in data:
        for plurk in data['plurks']:
            content = plurk.get('content_raw', '')
            plurk_id = plurk.get('plurk_id')
            posted_time = plurk.get('posted')
            time_tw = convert_to_taiwan_time(posted_time)
            link = f"https://www.plurk.com/p/{base36_encode(plurk_id)}"
            results.append({
                "plurk_id": plurk_id,
                "content": content,
                "post_time": time_tw,
                "link": link
            })
    return results

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=payload)

def load_last_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_last_state(plurk_id, post_time):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"plurk_id": plurk_id, "post_time": post_time}, f, ensure_ascii=False, indent=2)

def main():
    print("✅ 開始檢查 Plurk")
    last_state = load_last_state()
    last_id = last_state.get("plurk_id")
    last_time_str = last_state.get("post_time")
    last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S") if last_time_str else None

    new_plurks = get_latest_plurks()

    # 🔍 Debug 印出最新10則貼文
    print("📋 取得的最新 10 則貼文：")
    for p in new_plurks:
        print(f"  - plurk_id: {p['plurk_id']}, post_time: {p['post_time']}")

    # 過濾比 last 更新的貼文
    filtered = []
    for p in new_plurks:
        pid = str(p["plurk_id"])
        time_tw = p["post_time"]
        current_time = datetime.strptime(time_tw, "%Y-%m-%d %H:%M:%S")
        if (last_id is None or pid != str(last_id)) and (last_time is None or current_time > last_time):
            filtered.append((current_time, p))

    # 按時間排序（由舊到新）
    filtered.sort(key=lambda x: x[0])

    for _, plurk in filtered:
        msg = f"\U0001f195 Plurk 有新貼文！\n\n\U0001f4dd {plurk['content']}\n\u23f0 {plurk['post_time']}\n\U0001f517 {plurk['link']}"
        print(msg)
        send_telegram_message(msg)
        save_last_state(plurk['plurk_id'], plurk['post_time'])

    if not filtered:
        print("🔍 沒有新貼文（無更新）")

if __name__ == "__main__":
    main()
