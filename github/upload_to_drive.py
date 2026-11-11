"""
Local Workspace to Google Drive & Task Queue Dispatcher
Monitors or uploads generated videos and metadata from the 'output' directory
directly to the appropriate Google Drive channel folder and registers the task in Google Sheets.
"""

import os
import sys
import json
import argparse
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

def upload_video_package(video_path, metadata_path=None, channel_key="ENGLISH", folder_name=None, schedule_time=None):
    channel_key = channel_key.upper()
    if channel_key not in CHANNELS:
        raise ValueError(f"Unknown channel: {channel_key}. Valid options: HINDI, ENGLISH")

    ch_info = CHANNELS[channel_key]
    parent_folder_id = ch_info["folder_id"]

    video_filename = os.path.basename(video_path)
    base_name = os.path.splitext(video_filename)[0]
    folder_name = folder_name or base_name

    drive_service, sheets_service = get_services()

    # Parse metadata if file provided
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

    print(f"\n============================================================")
    print(f"[*] Target Channel : {ch_info['name']}")
    print(f"[*] Video File     : {video_filename} ({round(os.path.getsize(video_path) / (1024*1024), 2)} MB)")
    print(f"[*] Title          : {parsed_meta['title']}")
    print(f"[*] Topic          : {parsed_meta['topic']}")
    print(f"[*] Folder Name    : {folder_name}")
    print(f"============================================================")

    # 1. Check if folder already exists in parent folder, or create new
    q_existing = f"'{parent_folder_id}' in parents and name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    res_f = drive_service.files().list(q=q_existing, fields="files(id, name)").execute().get("files", [])
    if res_f:
        folder_id = res_f[0]["id"]
        print(f"[+] Found existing Drive folder '{folder_name}' (ID: {folder_id})")
    else:
        folder_meta = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        drive_folder = drive_service.files().create(body=folder_meta, fields='id').execute()
        folder_id = drive_folder.get('id')
        print(f"[+] Created Drive folder: '{folder_name}' (ID: {folder_id})")

    # 2. Upload video file to the folder
    print(f"[*] Uploading video to Drive...")
    media_video = MediaFileUpload(video_path, chunksize=1024*1024*5, resumable=True, mimetype="video/mp4")
    video_drive_file = drive_service.files().create(
        body={'name': 'video.mp4', 'parents': [folder_id]},
        media_body=media_video,
        fields='id, name'
    ).execute()
    print(f"[+] Video uploaded: ID={video_drive_file.get('id')}")

    # 3. Upload metadata.txt
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
    print(f"[+] metadata.txt uploaded")

    # 4. Register Task in Google Sheet Task_Queue
    task_id = f"TASK_{datetime.now().strftime('%m%d_%H%M%S')}"
    sched_utc = schedule_time if schedule_time else ""

    new_task_row = [
        task_id,
        ch_info["name"],
        folder_name,
        parsed_meta["title"],
        sched_utc,
        "READY_FOR_UPLOAD",
        "HIGH",
        f"Uploaded from workspace on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    ]

    sheets_service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Task_Queue!A1",
        valueInputOption="USER_ENTERED",
        body={'values': [new_task_row]}
    ).execute()

    print(f"[+] Successfully queued in Task_Queue: {task_id}")
    print(f"[+] Status: READY_FOR_UPLOAD (Ready for GitHub Actions!)")
    print(f"============================================================")
    print(f"Drive Folder : https://drive.google.com/drive/folders/{folder_id}")
    print(f"Spreadsheet  : https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    print(f"============================================================\n")
    return task_id

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload video package to Drive & Queue in Sheets")
    parser.add_argument("--video", help="Path to video file")
    parser.add_argument("--metadata", help="Path to metadata.txt file")
    parser.add_argument("--channel", default="ENGLISH", choices=["HINDI", "ENGLISH", "hindi", "english"], help="Target Channel")
    parser.add_argument("--folder", help="Custom folder name on Drive")
    parser.add_argument("--schedule", help="Scheduled time in ISO format")

    args = parser.parse_args()

    v_path = args.video
    if not v_path:
        # Default to the english prune video if present
        candidate = os.path.join(OUTPUT_DIR, "English", "fingers_prune_explainer.mp4")
        if os.path.exists(candidate):
            v_path = candidate
            args.metadata = os.path.join(OUTPUT_DIR, "English", "fingers_prune_metadata.txt")
            args.channel = "ENGLISH"
            args.folder = "Fingers_Prune_Explainer"

    if v_path and os.path.exists(v_path):
        upload_video_package(
            video_path=v_path,
            metadata_path=args.metadata,
            channel_key=args.channel,
            folder_name=args.folder,
            schedule_time=args.schedule
        )
    else:
        print(f"[!] Please provide --video path.")
