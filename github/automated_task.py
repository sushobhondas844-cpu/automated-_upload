"""
Automated Task: Local Output -> Google Drive Sync & Local Cleanup
Monitors 'output/English' and 'output/Hindi' for rendered videos and metadata.
Uploads them to the target Google Drive folder, queues them in Task_Queue,
and deletes the local video and metadata files upon confirmed upload.
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

def sync_single_video(video_path, metadata_path, channel_key):
    channel_key = channel_key.upper()
    ch_info = CHANNELS[channel_key]
    parent_folder_id = ch_info["folder_id"]

    video_filename = os.path.basename(video_path)
    base_name = os.path.splitext(video_filename)[0]
    folder_name = base_name.replace("_explainer", "").replace("_", " ").title().replace(" ", "_")

    drive_service, sheets_service = get_services()

    parsed_meta = {
        "title": base_name.replace("_", " ").title(),
        "topic": base_name.replace("_", " ").title(),
        "description": f"Explaining {base_name}! #Shorts #Facts",
        "tags": ["facts", "stickman", "animation", "curiosity"],
        "category_id": "27",
        "privacy": "public"
    }
    raw_meta_text = ""

    if metadata_path and os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as mf:
            raw_meta_text = mf.read()
            parsed_meta = parse_metadata_file(raw_meta_text)

    print(f"\n[+] Found complete video package:")
    print(f"    Video: {video_filename} ({round(os.path.getsize(video_path)/(1024*1024), 2)} MB)")
    print(f"    Channel: {ch_info['name']}")
    print(f"    Title: {parsed_meta['title']}")

    # 1. Create Folder on Drive
    folder_meta = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id]
    }
    drive_folder = drive_service.files().create(body=folder_meta, fields='id').execute()
    folder_id = drive_folder.get('id')
    print(f"    [+] Created Drive Folder: '{folder_name}' (ID: {folder_id})")

    # 2. Upload Video to Drive
    print(f"    [*] Uploading video file to Drive...")
    media_video = MediaFileUpload(video_path, chunksize=1024*1024*5, resumable=True, mimetype="video/mp4")
    v_file = drive_service.files().create(
        body={'name': 'video.mp4', 'parents': [folder_id]},
        media_body=media_video,
        fields='id'
    ).execute()
    video_drive_id = v_file.get('id')
    print(f"    [+] Video uploaded to Drive (ID: {video_drive_id})")

    # 3. Upload metadata.txt to Drive
    if not raw_meta_text:
        raw_meta_text = (
            f"Title: {parsed_meta['title']}\n"
            f"Topic: {parsed_meta['topic']}\n"
            f"Description: {parsed_meta['description']}\n"
            f"Tags: {', '.join(parsed_meta['tags'])}\n"
            f"Category: 27\n"
            f"Privacy: public\n"
        )
    media_meta = MediaInMemoryUpload(raw_meta_text.encode('utf-8'), mimetype='text/plain')
    drive_service.files().create(
        body={'name': 'metadata.txt', 'parents': [folder_id]},
        media_body=media_meta,
        fields='id'
    ).execute()
    print(f"    [+] metadata.txt uploaded to Drive")

    # 4. Enqueue in Task_Queue
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

    # 5. Safe local cleanup of video and metadata
    if video_drive_id:
        print(f"    [*] Upload confirmed on Drive. Purging local video file...")
        try:
            os.remove(video_path)
            print(f"    [-] Deleted local video: {video_filename}")
        except Exception as e:
            print(f"    [!] Warning deleting video: {e}")

        if metadata_path and os.path.exists(metadata_path):
            try:
                os.remove(metadata_path)
                print(f"    [-] Deleted local metadata: {os.path.basename(metadata_path)}")
            except Exception as e:
                print(f"    [!] Warning deleting metadata: {e}")

    print(f"[SUCCESS] Package fully synced and local disk cleaned up!\n")

def run_sync():
    targets = [
        (os.path.join(OUTPUT_DIR, "English"), "ENGLISH"),
        (os.path.join(OUTPUT_DIR, "Hindi"), "HINDI"),
    ]

    synced_count = 0
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

            sync_single_video(v_full, m_found, channel_key)
            synced_count += 1

    return synced_count

if __name__ == "__main__":
    count = run_sync()
    if count == 0:
        print("[*] Automated Task: No new pending videos found in output/English or output/Hindi.")
