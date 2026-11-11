"""
Auto Sync Watcher: Local Output -> Telegram Media Vault -> Task Queue
Continuously monitors the local 'output/English' and 'output/Hindi' folders.
When both a video (.mp4) and metadata (.txt) are generated:
1. Vaults them to Telegram as uncompressed documents (preserving 100% quality, 0 Drive bloat).
2. Extracts Telegram File IDs (video + metadata).
3. Registers the task in Task_Queue on the Master Spreadsheet.
4. Notifies via Telegram that the video is vaulted and queued.
5. Deletes local video and metadata from output/ to keep storage clean.
"""

import os
import sys
import time
import json
import asyncio
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "output")
ENV_PATH = os.path.join(WORKSPACE_DIR, ".env")
load_dotenv(ENV_PATH)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
SPREADSHEET_ID = "1xXpZpx_xencUSD7QzoZMt7ZuKtrf-SfTDurx2h-C5V4"
TOKEN_PATH = r"C:\Users\susho\Desktop\keygen\drive_token.json"

CHANNELS = {
    "HINDI": {
        "name": "Daily fun facts (Hindi)",
        "tab_name": "Daily Fun Facts (Hindi)"
    },
    "ENGLISH": {
        "name": "How did that happen (English)",
        "tab_name": "How Did That Happen (English)"
    }
}

def get_sheets_service():
    if not os.path.exists(TOKEN_PATH):
        raise FileNotFoundError(f"Google OAuth token not found at {TOKEN_PATH}")
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        token_data = json.load(f)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file"
    ]
    creds = Credentials.from_authorized_user_info(token_data, scopes=scopes)
    return build("sheets", "v4", credentials=creds)

def is_file_locked(filepath):
    """Check if file is currently open or being written to."""
    if not os.path.exists(filepath):
        return False
    try:
        with open(filepath, "ab") as f:
            pass
        return False
    except (IOError, PermissionError):
        return True

def safe_remove(filepath, max_retries=3, delay=1.0):
    if not os.path.exists(filepath):
        return True
    for _ in range(max_retries):
        try:
            os.remove(filepath)
            return True
        except (IOError, PermissionError):
            time.sleep(delay)
    return not os.path.exists(filepath)

def parse_metadata_file(content_text):
    data = {
        "topic": "General Curiosity",
        "title": "Daily Explainer Video",
        "description": "",
        "tags": ["facts", "shorts", "stickman", "animation"],
        "category_id": "27",
        "privacy": "public"
    }
    lines = content_text.splitlines()
    current_section = None
    desc_lines = []

    for line in lines:
        stripped = line.strip()
        upper = stripped.upper()
        if upper in ["TITLE:", "TITLE"]:
            current_section = "title"
            continue
        elif upper in ["DESCRIPTION:", "DESCRIPTION"]:
            current_section = "description"
            continue
        elif upper in ["HASHTAGS:", "TAGS:", "HASHTAGS", "TAGS"]:
            current_section = "tags"
            continue
        elif upper in ["TOPIC:", "TOPIC"]:
            current_section = "topic"
            continue

        if ":" in line and current_section is None:
            k, v = line.split(":", 1)
            kl = k.strip().lower()
            vl = v.strip()
            if kl == "title":
                data["title"] = vl
            elif kl == "topic":
                data["topic"] = vl
            elif kl in ["tags", "hashtags"]:
                data["tags"] = [t.strip().replace("#", "") for t in vl.split(",") if t.strip()]
            elif kl == "description":
                data["description"] = vl
            elif kl == "privacy":
                data["privacy"] = vl
            continue

        if current_section == "title" and stripped:
            data["title"] = stripped
            data["topic"] = stripped.split("(")[0].replace("?", "").strip()
            current_section = None
        elif current_section == "topic" and stripped:
            data["topic"] = stripped
            current_section = None
        elif current_section == "description":
            desc_lines.append(line)
        elif current_section == "tags" and stripped:
            if "#" in stripped:
                raw_tags = [t.strip("#").strip() for t in stripped.split() if t.strip()]
                data["tags"].extend(raw_tags)
            else:
                raw_tags = [t.strip() for t in stripped.split(",") if t.strip()]
                data["tags"].extend(raw_tags)

    if desc_lines:
        data["description"] = "\n".join(desc_lines).strip()

    return data

def upload_document_to_telegram(file_path, caption=None):
    """Uploads a document uncompressed to Telegram vault and returns file_id."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    filename = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        files = {"document": (filename, f)}
        data = {"chat_id": TELEGRAM_CHAT_ID}
        if caption:
            data["caption"] = caption
        res = requests.post(url, data=data, files=files, timeout=120)
        json_res = res.json()
        if not json_res.get("ok"):
            raise RuntimeError(f"Telegram upload failed: {json_res}")
        doc = json_res["result"].get("document") or json_res["result"].get("video")
        return doc["file_id"]

def send_telegram_alert(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=15)
    except Exception as e:
        print(f"[!] Warning sending Telegram alert: {e}")

def is_already_queued(sheets_service, folder_name):
    try:
        res = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="Task_Queue!C2:C100"
        ).execute()
        rows = res.get("values", [])
        for r in rows:
            if r and r[0].strip().lower() == folder_name.strip().lower():
                return True
    except Exception as e:
        print(f"[!] Warning checking Task_Queue: {e}")
    return False

def sync_single_video(video_path, metadata_path, channel_key):
    channel_key = channel_key.upper()
    ch_info = CHANNELS[channel_key]

    video_filename = os.path.basename(video_path)
    base_name = os.path.splitext(video_filename)[0]
    folder_name = base_name.replace("_explainer", "").replace("_", " ").title().replace(" ", "_")

    if is_file_locked(video_path):
        print(f"[-] Video file '{video_filename}' is locked. Skipping until unlocked.")
        return False
    if metadata_path and is_file_locked(metadata_path):
        print(f"[-] Metadata file is locked. Skipping until unlocked.")
        return False

    sheets_service = get_sheets_service()

    if is_already_queued(sheets_service, folder_name):
        print(f"[!] '{folder_name}' is already in Task_Queue. Safely purging local copies.")
        safe_remove(video_path)
        if metadata_path:
            safe_remove(metadata_path)
        return True

    with open(metadata_path, "r", encoding="utf-8") as mf:
        raw_meta = mf.read()
    parsed_meta = parse_metadata_file(raw_meta)

    print(f"\n[+] Processing Video Package:")
    print(f"    Video: {video_filename} ({round(os.path.getsize(video_path)/(1024*1024), 2)} MB)")
    print(f"    Channel: {ch_info['name']}")
    print(f"    Title: {parsed_meta['title']}")

    # 1. Upload uncompressed video document to Telegram
    print(f"    [*] Vaulting video document to Telegram...")
    video_file_id = upload_document_to_telegram(
        video_path,
        caption=f"Vaulted: {parsed_meta['title']} ({ch_info['name']})"
    )
    print(f"    [+] Telegram Video File ID: {video_file_id}")

    # 2. Upload metadata document to Telegram
    print(f"    [*] Vaulting metadata document to Telegram...")
    meta_file_id = upload_document_to_telegram(
        metadata_path,
        caption=f"Metadata: {parsed_meta['title']}"
    )
    print(f"    [+] Telegram Metadata File ID: {meta_file_id}")

    # 3. Register in Task_Queue
    task_id = f"TASK_{datetime.now().strftime('%m%d_%H%M%S')}"
    new_task_row = [
        task_id,
        ch_info["name"],
        folder_name,
        parsed_meta["title"],
        "",  # Scheduled_Time_UTC (empty for next scheduled window)
        "READY_FOR_UPLOAD",
        "HIGH",
        "Telegram Document Vault",
        video_file_id,
        meta_file_id
    ]

    sheets_service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Task_Queue!A1",
        valueInputOption="USER_ENTERED",
        body={"values": [new_task_row]}
    ).execute()
    print(f"    [+] Enqueued in Task_Queue: {task_id} (READY_FOR_UPLOAD)")

    # 4. Notify via Telegram
    send_telegram_alert(
        f"📦 New Video Vaulted in Telegram!\n\n"
        f"📌 Channel: {ch_info['name']}\n"
        f"🎬 Title: {parsed_meta['title']}\n"
        f"🆔 Task ID: {task_id}\n"
        f"📂 Status: READY_FOR_UPLOAD"
    )

    # 5. Clean up local files
    print(f"    [*] Purging local video and metadata from output/...")
    safe_remove(video_path)
    safe_remove(metadata_path)
    print(f"[SUCCESS] Video package vaulted and local output freed!\n")
    return True

def scan_once():
    targets = [
        (os.path.join(OUTPUT_DIR, "English"), "ENGLISH"),
        (os.path.join(OUTPUT_DIR, "Hindi"), "HINDI"),
    ]

    count = 0
    for folder_path, channel_key in targets:
        if not os.path.exists(folder_path):
            continue

        files = os.listdir(folder_path)
        mp4s = [f for f in files if f.lower().endswith(".mp4")]

        for mp4 in mp4s:
            v_full = os.path.join(folder_path, mp4)
            base = os.path.splitext(mp4)[0]
            m_candidates = [
                os.path.join(folder_path, f"{base}_metadata.txt"),
                os.path.join(folder_path, "metadata.txt"),
                os.path.join(folder_path, f"{base}.txt")
            ]
            m_found = None
            for cand in m_candidates:
                if os.path.exists(cand):
                    m_found = cand
                    break

            if not m_found:
                print(f"[-] Video '{mp4}' found but metadata .txt is missing. Waiting for complete pair...")
                continue

            try:
                if sync_single_video(v_full, m_found, channel_key):
                    count += 1
            except Exception as e:
                print(f"[!] Error syncing video '{mp4}': {e}")

    return count

def main():
    print("=" * 60)
    print("   TELEGRAM VAULT AUTO-SYNC WATCHER STARTED")
    print(f"   Monitoring: {OUTPUT_DIR}")
    print("=" * 60)
    while True:
        try:
            scan_once()
        except Exception as e:
            print(f"[!] Watcher error: {e}")
        time.sleep(15)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        c = scan_once()
        print(f"Scan complete. Processed {c} packages.")
    else:
        main()
