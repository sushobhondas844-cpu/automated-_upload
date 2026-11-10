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

def upload_video_package(video_path, metadata_path=None, channel_key="HINDI", folder_name=None, schedule_time=None):
    channel_key = channel_key.upper()
    if channel_key not in CHANNELS:
        raise ValueError(f"Unknown channel: {channel_key}. Valid options: HINDI, ENGLISH")

    ch_info = CHANNELS[channel_key]
    parent_folder_id = ch_info["folder_id"]

    video_filename = os.path.basename(video_path)
    base_name = os.path.splitext(video_filename)[0]
    folder_name = folder_name or base_name

    drive_service, sheets_service = get_services()

    print(f"\n[*] Preparing upload for: '{video_filename}'")
    print(f"[*] Target Channel : {ch_info['name']}")
    print(f"[*] Drive Folder   : {folder_name}")

    # 1. Create subfolder inside Channel Drive folder
    folder_meta = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id]
    }
    drive_folder = drive_service.files().create(body=folder_meta, fields='id').execute()
    folder_id = drive_folder.get('id')
    print(f"[+] Created Drive folder: '{folder_name}' (ID: {folder_id})")

    # 2. Upload video file
    print(f"[*] Uploading video file ({round(os.path.getsize(video_path) / (1024*1024), 2)} MB)...")
    media_video = MediaFileUpload(video_path, chunksize=1024*1024*5, resumable=True, mimetype="video/mp4")
    video_drive_file = drive_service.files().create(
        body={'name': 'video.mp4', 'parents': [folder_id]},
        media_body=media_video,
        fields='id, name'
    ).execute()
    print(f"[+] Video uploaded successfully (ID: {video_drive_file.get('id')})")

    # 3. Handle & Upload metadata.txt
    title = base_name.replace("_", " ").title()
    desc = f"Explaining {title}! #Shorts #Facts #Curiosity"
    tags = "facts, stickman, animation, curiosity, educational, viral"

    if metadata_path and os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as mf:
            meta_content = mf.read()
            for line in meta_content.splitlines():
                if line.lower().startswith("title:"):
                    title = line.split(":", 1)[1].strip()
    else:
        # Generate default metadata content
        meta_content = (
            f"Title: {title}\n"
            f"Description: {desc}\n"
            f"Tags: {tags}\n"
            f"Category: 27\n"
            f"Privacy: public\n"
        )

    media_meta = MediaInMemoryUpload(meta_content.encode('utf-8'), mimetype='text/plain')
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
        title,
        sched_utc,
        "READY_FOR_UPLOAD",
        "HIGH",
        f"Uploaded from local workspace on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    ]

    sheets_service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Task_Queue!A1",
        valueInputOption="USER_ENTERED",
        body={'values': [new_task_row]}
    ).execute()

    print(f"[+] Task successfully registered in Task_Queue: {task_id}")
    print(f"[+] Status: READY_FOR_UPLOAD")
    print(f"============================================================")
    print(f"Spreadsheet Tracker: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    return task_id

def scan_and_upload():
    if not os.path.exists(OUTPUT_DIR):
        print(f"[!] Output directory not found: {OUTPUT_DIR}")
        return

    mp4_files = [f for f in os.listdir(OUTPUT_DIR) if f.lower().endswith(".mp4")]
    if not mp4_files:
        print(f"[*] No MP4 files currently in {OUTPUT_DIR}")
        return

    print(f"[*] Available MP4 files in output folder:")
    for idx, f in enumerate(mp4_files, start=1):
        full_p = os.path.join(OUTPUT_DIR, f)
        size_mb = round(os.path.getsize(full_p) / (1024*1024), 2)
        print(f"  [{idx}] {f} ({size_mb} MB)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload video package to Drive & Queue in Sheets")
    parser.add_argument("--video", help="Path to video file (or filename in output/)")
    parser.add_argument("--metadata", help="Path to metadata.txt file (optional)")
    parser.add_argument("--channel", default="HINDI", choices=["HINDI", "ENGLISH", "hindi", "english"], help="Target Channel (HINDI or ENGLISH)")
    parser.add_argument("--folder", help="Custom folder name on Drive")
    parser.add_argument("--schedule", help="Scheduled time in ISO format (e.g. 2026-11-12T14:00:00Z)")
    parser.add_argument("--scan", action="store_true", help="List files in output directory")

    args = parser.parse_args()

    if args.scan or not args.video:
        scan_and_upload()
    else:
        v_path = args.video
        if not os.path.isabs(v_path) and not os.path.exists(v_path):
            v_path = os.path.join(OUTPUT_DIR, v_path)

        if not os.path.exists(v_path):
            print(f"[!] File not found: {v_path}")
            sys.exit(1)

        upload_video_package(
            video_path=v_path,
            metadata_path=args.metadata,
            channel_key=args.channel.upper(),
            folder_name=args.folder,
            schedule_time=args.schedule
        )
