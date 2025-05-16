import os
import time
import requests
from datetime import datetime, timezone, timedelta
from requests_oauthlib import OAuth1

# === 從環境變數讀取設定 ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

APP_KEY = os.getenv("PLURK_APP_KEY")
APP_SECRET = os.getenv("PLURK_APP_SECRET")
ACCESS_TOKEN = os.getenv("PLURK_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("PLURK_ACCESS_TOKEN_SECRET")

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

def get_latest_plurk(query="麥當勞"):
    url = "https://www.plurk.com/APP/PlurkSearch/search"
    params = {"query": query, "limit": 1}
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, params=params, auth=auth, headers=headers)
        print("🌐 Plurk API status:", response.status_code)
        data = response.json()
        print("📦 API 回傳內容:", data)

        if 'plurks' in data and data['plurks']:
            plurk = data['plurks'][0]
            content = plurk.get('content_raw', '')
            plurk_id = plurk.get('plurk_id')
            posted_time = plurk.get('posted')
            time_tw = convert_to_taiwan_time(posted_time)
            link = f"https://www.plurk.com/p/{base36_encode(plurk_id)}"
            return plurk_id, content, time_tw, link

    except Exception as e:
        print("❌ 發生錯誤（Plurk API）:", e)

    return None, None, None, None

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        response = requests.post(url, data=payload)
        print("📨 傳送 Telegram 結果:", response.status_code, response.text)
    except Exception as e:
        print("❌ 發送 Telegram 時出錯:", e)

if __name__ == "__main__":
    print("✅ 啟動 Plurk 監聽")
    print("🔐 環境變數載入測試:")
    print({
        "TELEGRAM_TOKEN": bool(TELEGRAM_TOKEN),
        "CHAT_ID": bool(CHAT_ID),
        "PLURK_APP_KEY": bool(APP_KEY),
        "PLURK_APP_SECRET": bool(APP_SECRET),
        "ACCESS_TOKEN": bool(ACCESS_TOKEN),
        "ACCESS_TOKEN_SECRET": bool(ACCESS_TOKEN_SECRET),
    })

    last_time = None
    no_new_post_printed = False

    pid, content, time_tw, link = get_latest_plurk()
    if pid:
        time_obj = datetime.strptime(time_tw, "%Y-%m-%d %H:%M:%S")
        if last_time is None or time_obj > last_time:
            last_time = time_obj
            no_new_post_printed = False
            msg = f"🆕 Plurk 有新貼文！\n\n📝 {content}\n⏰ {time_tw}\n🔗 {link}"
            print(msg)
            send_telegram_message(msg)
        else:
            print("🔍 沒有新貼文（時間未更新）")
    else:
        print("❌ 找不到任何貼文")
