# check_plurk.py
import requests
from datetime import datetime, timezone, timedelta
from requests_oauthlib import OAuth1
import os
import json

# === 載入環境變數 ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
APP_KEY = os.environ.get("PLURK_APP_KEY")
APP_SECRET = os.environ.get("PLURK_APP_SECRET")
ACCESS_TOKEN = os.environ.get("PLURK_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.environ.get("PLURK_ACCESS_TOKEN_SECRET")

auth = OAuth1(APP_KEY, APP_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# Artifact 紀錄檔案
ARTIFACT_FILE = "last_plurk.json"


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
    if response.status_code != 200:
        print(f"Plurk API Error {response.status_code}: {response.text}")
        return None, None, None, None

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


def load_last_info():
    if os.path.exists(ARTIFACT_FILE):
        with open(ARTIFACT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"id": 0, "time": "2000-01-01 00:00:00"}


def save_last_info(pid, time_tw):
    with open(ARTIFACT_FILE, "w", encoding="utf-8") as f:
        json.dump({"id": pid, "time": time_tw}, f)


if __name__ == "__main__":
    print("✅ 啟動 Plurk 監聽")
    last_info = load_last_info()
    last_time = datetime.strptime(last_info["time"], "%Y-%m-%d %H:%M:%S")
    last_id = last_info["id"]

    pid, content, time_tw, link = get_latest_plurk()
    if pid:
        time_obj = datetime.strptime(time_tw, "%Y-%m-%d %H:%M:%S")
        if pid != last_id and time_obj > last_time:
            msg = f"🆕 Plurk 有新貼文！\n\n📝 {content}\n⏰ {time_tw}\n🔗 {link}"
            print(msg)
            send_telegram_message(msg)
            save_last_info(pid, time_tw)
        else:
            print("🔍 沒有新貼文（ID 或時間未更新）")
    else:
        print("❌ 找不到任何貼文")
        save_last_info(last_id, last_time.strftime("%Y-%m-%d %H:%M:%S"))

