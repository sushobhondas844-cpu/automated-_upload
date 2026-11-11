"""
GitHub Secrets & Connection Diagnostics Checker
Validates, cleans, and live-tests all secrets for:
- Google Sheets / Drive (Service Account)
- YouTube Channels (English & Hindi OAuth Tokens)
- Telegram Bot API (Token & Chat ID)
- Telegram MTProto Client (API_ID & API_HASH)
"""

import os
import sys
import json
import urllib.request
import asyncio
from google.oauth2.service_account import Credentials as SACredentials
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build

def clean_val(val: str) -> str:
    if not val:
        return ""
    # Strip inline bash/python comments and extra whitespace/quotes
    cleaned = val.split("#")[0].strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()
    return cleaned

def check_all():
    print("=" * 60)
    print("      GITHUB ACTIONS CREDENTIALS & CONNECTION AUDIT")
    print("=" * 60)
    
    all_ok = True
    
    # 1. Telegram Credentials
    bot_token = clean_val(os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN"))
    chat_id = clean_val(os.environ.get("CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID"))
    api_id_raw = clean_val(os.environ.get("TELEGRAM_API_ID", "30360141"))
    api_hash = clean_val(os.environ.get("TELEGRAM_API_HASH", "ecb0dc6dbe73524409a14f7dfff7b6e2"))

    print("\n[1] Auditing Telegram Bot API...")
    if not bot_token:
        print("  [FAIL] BOT_TOKEN / TELEGRAM_BOT_TOKEN is missing!")
        all_ok = False
    else:
        try:
            req = urllib.request.Request(f"https://api.telegram.org/bot{bot_token}/getMe")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                username = data["result"]["username"]
                print(f"  [OK] Telegram Bot Token verified! Connected as: @{username}")
            else:
                print(f"  [FAIL] Telegram Bot Token rejected: {data}")
                all_ok = False
        except Exception as e:
            print(f"  [FAIL] Telegram Bot connection error: {e}")
            all_ok = False

    print("\n[2] Auditing Telegram MTProto Large-File Client...")
    try:
        api_id = int(api_id_raw)
        from pyrogram import Client
        async def test_mtproto():
            async with Client("audit_session", api_id=api_id, api_hash=api_hash, bot_token=bot_token, in_memory=True) as app:
                me = await app.get_me()
                print(f"  [OK] MTProto Client authorized! Bot: @{me.username} (API_ID: {api_id})")
        asyncio.run(test_mtproto())
    except Exception as e:
        print(f"  [FAIL] Telegram MTProto authorization failed: {e}")
        all_ok = False

    # 3. Google Service Account / OAuth User Token (Sheets)
    print("\n[3] Auditing Google Credentials (Google Sheets access)...")
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not sa_json:
        print("  [FAIL] GOOGLE_SERVICE_ACCOUNT_JSON secret is empty!")
        all_ok = False
    else:
        try:
            import base64
            if sa_json.startswith("{"):
                creds_dict = json.loads(sa_json)
            else:
                creds_dict = json.loads(base64.b64decode(sa_json).decode("utf-8"))

            if "client_email" in creds_dict and creds_dict.get("type") == "service_account":
                scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                creds = SACredentials.from_service_account_info(creds_dict, scopes=scopes)
                cred_type = "Service Account"
            elif "token" in creds_dict or "refresh_token" in creds_dict:
                token_scopes = creds_dict.get("scopes")
                creds = UserCredentials.from_authorized_user_info(creds_dict, scopes=token_scopes)
                cred_type = "OAuth User Token"
            else:
                raise ValueError("Unrecognized Google credentials JSON format.")

            sheets = build("sheets", "v4", credentials=creds)
            res = sheets.spreadsheets().get(spreadsheetId="1xXpZpx_xencUSD7QzoZMt7ZuKtrf-SfTDurx2h-C5V4").execute()
            sheet_title = res.get("properties", {}).get("title", "YouTube Content Pipeline & Dispatcher")
            print(f"  [OK] Google Credentials verified ({cred_type})! Master Sheet connected: '{sheet_title}'")
        except Exception as e:
            print(f"  [FAIL] Google Credentials error: {e}")
            all_ok = False

    # 4. YouTube English Token
    print("\n[4] Auditing YouTube English Channel Token...")
    yt_en_json = os.environ.get("YOUTUBE_TOKEN_ENGLISH", "").strip()
    if not yt_en_json:
        print("  [FAIL] YOUTUBE_TOKEN_ENGLISH secret is empty!")
        all_ok = False
    else:
        try:
            yt_data = json.loads(yt_en_json)
            creds = UserCredentials.from_authorized_user_info(yt_data)
            yt = build("youtube", "v3", credentials=creds)
            ch_res = yt.channels().list(part="snippet", mine=True).execute()
            items = ch_res.get("items", [])
            if items:
                title = items[0]["snippet"]["title"]
                print(f"  [OK] YouTube English Token verified! Channel: '{title}'")
            else:
                print("  [WARN] YouTube token valid, but no channel found for this account.")
        except Exception as e:
            print(f"  [FAIL] YouTube English Token error: {e}")
            all_ok = False

    # 5. YouTube Hindi Token
    print("\n[5] Auditing YouTube Hindi Channel Token...")
    yt_hi_json = os.environ.get("YOUTUBE_TOKEN_HINDI", "").strip()
    if not yt_hi_json:
        print("  [FAIL] YOUTUBE_TOKEN_HINDI secret is empty!")
        all_ok = False
    else:
        try:
            yt_data = json.loads(yt_hi_json)
            creds = UserCredentials.from_authorized_user_info(yt_data)
            yt = build("youtube", "v3", credentials=creds)
            ch_res = yt.channels().list(part="snippet", mine=True).execute()
            items = ch_res.get("items", [])
            if items:
                title = items[0]["snippet"]["title"]
                print(f"  [OK] YouTube Hindi Token verified! Channel: '{title}'")
            else:
                print("  [WARN] YouTube token valid, but no channel found for this account.")
        except Exception as e:
            print(f"  [FAIL] YouTube Hindi Token error: {e}")
            all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print(" [SUCCESS] ALL SECRETS & CONNECTIONS ARE 100% HEALTHY!")
    else:
        print(" [WARNING] SOME CONNECTIONS FAILED. Review the logs above.")
    print("=" * 60 + "\n")
    return all_ok

if __name__ == "__main__":
    ok = check_all()
    if not ok:
        sys.exit(1)
