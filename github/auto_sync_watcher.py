"""
Auto Sync Watcher: Local Output -> Google Drive -> Task Queue
Continuously watches the 'output' directory (both English/ and Hindi/ subfolders).
Safe & Idempotent:
1. Requires BOTH .mp4 and metadata (.txt) before uploading.
2. Checks file locks to ensure rendering/writing is 100% finished before touching files.
3. Strict Deduplication: Checks Google Drive and Task_Queue to prevent duplicate folders and repeat uploads.
4. Atomically cleans up local video and metadata once Drive upload is confirmed.
5. Cleans up orphaned metadata files whose video is already processed.
"""

import os
import sys
import time
import json
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaInMemoryUpload

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "output")
TOKEN_PATH = r"C:\Users\susho\Desktop\keygen\drive_token.json"

CHANNELS = {
    "HINDI": {
        "name": "Daily fun facts (Hindi)",
        "folder_id": "1Ww-gru4SivDvrjwuhxhYlGKYojNkzcqO",
        "tab_name": "Daily Fun Facts (Hindi)"
    },
    "ENGLISH": {
        "name": "How did that happen (English)",
        "folder_id": "1_lHICM5g06az4GsKIcyXX8E5YAKegQNZ",
        "tab_name": "How Did That Happen (English)"
    }
}

SPREADSHEET_ID = "1xXpZpx_xencUSD7QzoZMt7ZuKtrf-SfTDurx2h-C5V4"

def get_services():
    if not os.path.exists(TOKEN_PATH):
        raise FileNotFoundError(f"OAuth token not found at {TOKEN_PATH}")

    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        token_data = json.load(f)

    scopes = token_data.get("scopes", [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/spreadsheets"
    ])

    creds = Credentials.from_authorized_user_info(token_data, scopes=scopes)
    drive_service = build("drive", "v3", credentials=creds)
    sheets_service = build("sheets", "v4", credentials=creds)
    return drive_service, sheets_service

def is_file_locked(filepath):
    """Check if a file is currently locked by another process (rendering, copying, etc)."""
    if not os.path.exists(filepath):
        return False
    try:
        # Try opening for appending in binary mode
        with open(filepath, "ab") as f:
            pass
        return False
    except (IOError, PermissionError):
        return True

def safe_remove(filepath, max_retries=3, delay=1.0):
    """Safely remove a file with retries in case of transient Windows locks."""
    if not os.path.exists(filepath):
        return True
    for attempt in range(max_retries):
        try:
            os.remove(filepath)
            return True
        except (IOError, PermissionError) as e:
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

def is_already_queued_or_published(sheets_service, folder_name):
    """Check if folder_name is already recorded in Task_Queue."""
    try:
        res = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="Task_Queue!C2:F100"
        ).execute()
        rows = res.get("values", [])
        for r in rows:
            if len(r) >= 1 and r[0].strip().lower() == folder_name.strip().lower():
                return True
    except Exception as e:
        print(f"[!] Warning reading Task_Queue: {e}")
    return False

def sync_single_video(video_path, metadata_path, channel_key):
    channel_key = channel_key.upper()
    ch_info = CHANNELS[channel_key]
    parent_folder_id = ch_info["folder_id"]

    video_filename = os.path.basename(video_path)
    base_name = os.path.splitext(video_filename)[0]
    folder_name = base_name.replace("_explainer", "").replace("_", " ").title().replace(" ", "_")

    # Check file locks first
    if is_file_locked(video_path):
        print(f"[-] Video file '{video_filename}' is locked by another process. Skipping until unlocked.")
        return False
    if metadata_path and is_file_locked(metadata_path):
        print(f"[-] Metadata file is locked by another process. Skipping until unlocked.")
        return False

    drive_service, sheets_service = get_services()

    # Deduplication Guard 1: Check if already registered in Task_Queue
    if is_already_queued_or_published(sheets_service, folder_name):
        print(f"[!] Package for '{folder_name}' is already recorded in Task_Queue. Skipping duplicate upload.")
        # If already recorded and uploaded, safe to purge local files
        safe_remove(video_path)
        if metadata_path:
            safe_remove(metadata_path)
        return True

    # Read and parse metadata
    with open(metadata_path, "r", encoding="utf-8") as mf:
        raw_meta_text = mf.read()
    parsed_meta = parse_metadata_file(raw_meta_text)

    print(f"\n[+] Processing Video Package:")
    print(f"    Video: {video_filename} ({round(os.path.getsize(video_path)/(1024*1024), 2)} MB)")
    print(f"    Channel: {ch_info['name']}")
    print(f"    Title: {parsed_meta['title']}")
    print(f"    Folder: {folder_name}")

    # Deduplication Guard 2: Check if folder already exists on Google Drive
    q_existing = f"'{parent_folder_id}' in parents and name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    res_f = drive_service.files().list(q=q_existing, fields="files(id, name)").execute().get("files", [])
    if res_f:
        folder_id = res_f[0]["id"]
        print(f"    [+] Found existing Drive folder '{folder_name}' (ID: {folder_id})")
    else:
        folder_meta = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        drive_folder = drive_service.files().create(body=folder_meta, fields='id').execute()
        folder_id = drive_folder.get('id')
        print(f"    [+] Created Drive Folder: '{folder_name}' (ID: {folder_id})")

    # Upload Video
    print(f"    [*] Uploading video file to Drive...")
    media_video = MediaFileUpload(video_path, chunksize=1024*1024*5, resumable=True, mimetype="video/mp4")
    v_file = drive_service.files().create(
        body={'name': 'video.mp4', 'parents': [folder_id]},
        media_body=media_video,
        fields='id'
    ).execute()
    video_drive_id = v_file.get('id')
    print(f"    [+] Video uploaded to Drive (ID: {video_drive_id})")

    # Upload Metadata
    media_meta = MediaInMemoryUpload(raw_meta_text.encode('utf-8'), mimetype='text/plain')
    m_file = drive_service.files().create(
        body={'name': 'metadata.txt', 'parents': [folder_id]},
        media_body=media_meta,
        fields='id'
    ).execute()
    meta_drive_id = m_file.get('id')
    print(f"    [+] metadata.txt uploaded to Drive (ID: {meta_drive_id})")

    # Enqueue in Task_Queue
    task_id = f"TASK_{datetime.now().strftime('%m%d_%H%M%S')}"
    new_task_row = [
        task_id,
        ch_info["name"],
        folder_name,
        parsed_meta["title"],
        "",  # Immediate publish
        "READY_FOR_UPLOAD",
        "HIGH",
        f"Auto-synced from workspace on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    ]
    sheets_service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Task_Queue!A1",
        valueInputOption="USER_ENTERED",
        body={'values': [new_task_row]}
    ).execute()
    print(f"    [+] Registered in Task_Queue: {task_id} (READY_FOR_UPLOAD)")

    # Confirmed cleanup: ONLY delete after BOTH uploads succeeded
    if video_drive_id and meta_drive_id:
        print(f"    [*] Upload confirmed on Drive. Purging local files...")
        v_deleted = safe_remove(video_path)
        m_deleted = safe_remove(metadata_path)
        if v_deleted:
            print(f"    [-] Deleted local video: {video_filename}")
        else:
            print(f"    [!] Warning: Could not delete local video (locked)")
        if m_deleted:
            print(f"    [-] Deleted local metadata: {os.path.basename(metadata_path)}")

    print(f"[SUCCESS] Package fully synced and cleaned up!\n")
    return True

def scan_once():
    """Scans output folders for complete pairs of mp4 + txt and uploads them."""
    targets = [
        (os.path.join(OUTPUT_DIR, "English"), "ENGLISH"),
        (os.path.join(OUTPUT_DIR, "Hindi"), "HINDI"),
    ]

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

            # STRICT RULE: Both video AND metadata must exist before proceeding!
            if not m_found:
                print(f"[-] Video '{mp4}' found but metadata .txt is missing. Waiting for metadata generation...")
                continue

            try:
                sync_single_video(v_full, m_found, channel_key)
            except Exception as e:
                print(f"[!] Error syncing video '{mp4}': {e}")

        # Clean up any orphaned metadata files if video is already uploaded and registered
        txts = [f for f in files if f.lower().endswith(".txt")]
        for txt in txts:
            t_full = os.path.join(folder_path, txt)
            t_base = os.path.splitext(txt)[0].replace("_metadata", "")
            matching_mp4 = [m for m in mp4s if os.path.splitext(m)[0].replace("_explainer", "") == t_base]
            if not matching_mp4:
                # Video already gone, check if task is already in sheets
                folder_name = t_base.replace("_", " ").title().replace(" ", "_")
                try:
                    _, sheets_service = get_services()
                    if is_already_queued_or_published(sheets_service, folder_name):
                        print(f"[*] Removing orphaned metadata for already processed '{folder_name}'...")
                        safe_remove(t_full)
                except Exception:
                    pass

def main():
    print("=" * 60)
    print("      AUTO SYNC WATCHER STARTED")
    print(f"      Monitoring: {OUTPUT_DIR}")
    print("=" * 60)
    while True:
        try:
            scan_once()
        except Exception as e:
            print(f"[!] Watcher error: {e}")
        time.sleep(15)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        scan_once()
    else:
        main()
