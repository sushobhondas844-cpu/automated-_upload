"""
Automated Cloud Publishing Dispatcher
Designed to run on GitHub Actions or a scheduled cloud worker.

Workflow:
1. Connects to Google Drive and Google Sheets via GOOGLE_SERVICE_ACCOUNT_JSON (supports both Service Account & OAuth User Tokens).
2. Reads the central workbook 'YouTube Content Pipeline & Dispatcher'.
3. Checks the 'Task_Queue' tab for any pending tasks where:
   - Status in ['READY_FOR_UPLOAD', 'PENDING', 'APPROVED']
   - Scheduled_Time_UTC <= Current UTC Time (or immediate if blank)
4. Locates the video in Drive (either by Folder_Name in the channel directory or by Drive_File_ID).
   - If folder has metadata.txt, extracts Title, Description, Tags, Category, Privacy.
5. Uploads to the appropriate YouTube channel via YOUTUBE_TOKEN_HINDI or YOUTUBE_TOKEN_ENGLISH.
6. Updates 'Task_Queue' row to 'PUBLISHED'.
7. Records the video details into the channel's dedicated tab:
   - Title, Video URL, Video ID, Published_At, Views, Likes, Comments, Status.
8. Automatically updates View Counters for all previously published videos across channel tabs.
"""

import os
import sys
import json
import base64
import tempfile
import re
from datetime import datetime, timezone
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

MASTER_FOLDER_ID = "1b9MZR5idAK4EqLi2akxFX-FAMycA8rDe"
DEFAULT_SHEET_NAME = "YouTube Content Pipeline & Dispatcher"
SCOPES_YOUTUBE = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]

def get_google_clients():
    """Authenticates with Drive & Sheets APIs using GOOGLE_SERVICE_ACCOUNT_JSON."""
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_JSON environment secret.")

    if sa_json.strip().startswith("{"):
        creds_dict = json.loads(sa_json)
    else:
        creds_dict = json.loads(base64.b64decode(sa_json).decode('utf-8'))

    if "client_email" in creds_dict and creds_dict.get("type") == "service_account":
        scopes = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
        creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=scopes)
    elif "token" in creds_dict or "refresh_token" in creds_dict:
        token_scopes = creds_dict.get("scopes")
        creds = UserCredentials.from_authorized_user_info(creds_dict, scopes=token_scopes)
    else:
        raise ValueError(f"Unrecognized credentials format with keys: {list(creds_dict.keys())}")

    drive_service = build("drive", "v3", credentials=creds)
    sheets_service = build("sheets", "v4", credentials=creds)
    return drive_service, sheets_service

def get_youtube_client(channel_key):
    """Authenticates with YouTube using channel OAuth credentials stored in GitHub Secrets."""
    secret_key = "YOUTUBE_TOKEN_HINDI" if "HINDI" in channel_key.upper() else "YOUTUBE_TOKEN_ENGLISH"
    token_json = os.environ.get(secret_key)
    if not token_json:
        raise ValueError(f"Missing YouTube OAuth secret: {secret_key}")

    if token_json.strip().startswith("{"):
        token_data = json.loads(token_json)
    else:
        token_data = json.loads(base64.b64decode(token_json).decode('utf-8'))

    creds = UserCredentials.from_authorized_user_info(token_data, scopes=SCOPES_YOUTUBE)
    return build("youtube", "v3", credentials=creds)

def find_spreadsheet_id(drive_service, sheet_name):
    """Finds the spreadsheet ID inside the master folder."""
    q = f"'{MASTER_FOLDER_ID}' in parents and name = '{sheet_name}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
    res = drive_service.files().list(q=q, fields="files(id, name)").execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    # Fallback search across user's drive
    q2 = f"name = '{sheet_name}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
    res2 = drive_service.files().list(q=q2, fields="files(id, name)").execute()
    files2 = res2.get("files", [])
    if files2:
        return files2[0]["id"]
    raise FileNotFoundError(f"Spreadsheet '{sheet_name}' not found.")

def download_file_from_drive(drive_service, file_id, dest_path):
    print(f"[*] Downloading file {file_id} from Drive...")
    request = drive_service.files().get_media(fileId=file_id)
    with open(dest_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"    Download progress: {int(status.progress() * 100)}%")
    print(f"[+] Download complete: {dest_path}")

def parse_metadata_file(content_text):
    """Parses key-value metadata from metadata.txt."""
    data = {
        "title": "Daily Explainer Video",
        "description": "#Shorts #Facts #Explainer",
        "tags": ["facts", "shorts", "stickman", "animation"],
        "category_id": "27",
        "privacy": "public"
    }
    for line in content_text.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            k = key.strip().lower()
            v = val.strip()
            if k == "title":
                data["title"] = v
            elif k == "description":
                data["description"] = v
            elif k == "tags":
                data["tags"] = [t.strip() for t in v.split(",") if t.strip()]
            elif k == "category":
                data["category_id"] = v
            elif k in ["privacy", "status"]:
                data["privacy"] = v.lower()
    return data

def upload_video_to_youtube(youtube_service, file_path, meta):
    print(f"[*] Uploading to YouTube: '{meta['title']}' [{meta['privacy']}]")
    body = {
        'snippet': {
            'title': meta['title'],
            'description': meta['description'],
            'tags': meta['tags'],
            'categoryId': meta.get('category_id', '27')
        },
        'status': {
            'privacyStatus': meta.get('privacy', 'public'),
            'selfDeclaredMadeForKids': False
        }
    }
    media = MediaFileUpload(file_path, chunksize=1024*1024*5, resumable=True, mimetype="video/mp4")
    request = youtube_service.videos().insert(part=','.join(body.keys()), body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"    YouTube Upload: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    watch_url = f"https://youtu.be/{video_id}"
    print(f"[+] Upload successful! Video URL: {watch_url}")
    return video_id, watch_url

def update_view_counters(youtube_services, sheets_service, spreadsheet_id, channel_tabs):
    """Iterates through channel tabs and updates Views, Likes, Comments via YouTube Data API."""
    print("\n[*] Updating view counters & statistics for published videos...")
    for tab_name, channel_key in channel_tabs.items():
        yt = youtube_services.get(channel_key)
        if not yt:
            continue
        try:
            res = sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{tab_name}'!A1:H100"
            ).execute()
            rows = res.get("values", [])
            if len(rows) <= 1:
                continue

            for row_idx, r in enumerate(rows[1:], start=2):
                if len(r) >= 3 and r[2]: # Video_ID is at Col C (idx 2)
                    vid = r[2].strip()
                    if vid and len(vid) >= 10:
                        try:
                            stat_res = yt.videos().list(part="statistics", id=vid).execute()
                            items = stat_res.get("items", [])
                            if items:
                                stats = items[0]["statistics"]
                                views = stats.get("viewCount", "0")
                                likes = stats.get("likeCount", "0")
                                comments = stats.get("commentCount", "0")
                                # Col E: Views, Col F: Likes, Col G: Comments
                                sheets_service.spreadsheets().values().update(
                                    spreadsheetId=spreadsheet_id,
                                    range=f"'{tab_name}'!E{row_idx}:G{row_idx}",
                                    valueInputOption="USER_ENTERED",
                                    body={'values': [[views, likes, comments]]}
                                ).execute()
                                print(f"    [{tab_name}] Video '{vid}': {views} views, {likes} likes")
                        except Exception as e:
                            print(f"    [!] Failed to update stats for {vid}: {e}")
        except Exception as e:
            print(f"[!] Warning reading tab '{tab_name}': {e}")

def process_queue():
    sheet_name = os.environ.get("TRACKING_SHEET_NAME", DEFAULT_SHEET_NAME)
    drive_service, sheets_service = get_google_clients()
    spreadsheet_id = find_spreadsheet_id(drive_service, sheet_name)
    print(f"[*] Connected to Spreadsheet: '{sheet_name}' (ID: {spreadsheet_id})")

    # Read Task_Queue
    queue_res = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="Task_Queue!A1:H100"
    ).execute()
    queue_rows = queue_res.get("values", [])

    if not queue_rows or len(queue_rows) <= 1:
        print("[*] No tasks found in Task_Queue.")
        return

    headers = [h.strip() for h in queue_rows[0]]
    now = datetime.now(timezone.utc)
    channel_tabs = {
        "Daily Fun Facts (Hindi)": "HINDI",
        "How Did That Happen (English)": "ENGLISH"
    }
    youtube_services = {
        "HINDI": get_youtube_client("HINDI"),
        "ENGLISH": get_youtube_client("ENGLISH")
    }

    for row_idx, row in enumerate(queue_rows[1:], start=2):
        row_dict = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
        status = row_dict.get("Status", "").strip().upper()
        target_channel = row_dict.get("Target_Channel", "HINDI").strip()
        folder_name = row_dict.get("Folder_Name", "").strip()
        sched_time_str = row_dict.get("Scheduled_Time_UTC", "").strip()

        if status in ["READY_FOR_UPLOAD", "PENDING", "APPROVED"]:
            # Check scheduled time
            if sched_time_str:
                try:
                    sched_dt = datetime.fromisoformat(sched_time_str.replace("Z", "+00:00"))
                    if sched_dt > now:
                        print(f"[-] Task at row {row_idx} scheduled for {sched_time_str} is in the future. Skipping.")
                        continue
                except Exception as e:
                    print(f"[!] Warning parsing time '{sched_time_str}': {e}")

            print(f"\n[>>>] Processing Task at row {row_idx}: Folder '{folder_name}' for channel '{target_channel}'")

            # Search for the video folder inside master folder or channel folder
            folder_q = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            f_res = drive_service.files().list(q=folder_q, fields="files(id, name, parents)").execute()
            f_items = f_res.get("files", [])

            if not f_items:
                print(f"[-] Video folder '{folder_name}' not found in Drive. Skipping row {row_idx}.")
                continue

            video_folder_id = f_items[0]["id"]
            # List contents of video folder
            files_res = drive_service.files().list(
                q=f"'{video_folder_id}' in parents and trashed = false",
                fields="files(id, name, mimeType)"
            ).execute().get("files", [])

            mp4_file = None
            meta_file = None
            for item in files_res:
                if item["name"].lower().endswith(".mp4") or "video" in item["mimeType"]:
                    mp4_file = item
                elif item["name"].lower() == "metadata.txt":
                    meta_file = item

            if not mp4_file:
                print(f"[-] No MP4 video file found inside folder '{folder_name}'. Skipping row {row_idx}.")
                continue

            # Parse metadata
            meta = {
                "title": row_dict.get("Video_Title") or folder_name,
                "description": "#Shorts #Facts #Curiosity",
                "tags": ["facts", "stickman", "shorts", "animation"],
                "category_id": "27",
                "privacy": "public"
            }

            with tempfile.TemporaryDirectory() as tmp_dir:
                if meta_file:
                    meta_path = os.path.join(tmp_dir, "metadata.txt")
                    download_file_from_drive(drive_service, meta_file["id"], meta_path)
                    with open(meta_path, "r", encoding="utf-8") as mf:
                        meta = parse_metadata_file(mf.read())

                # If spreadsheet specified a title, prefer it
                if row_dict.get("Video_Title"):
                    meta["title"] = row_dict["Video_Title"]

                video_path = os.path.join(tmp_dir, "upload_video.mp4")
                download_file_from_drive(drive_service, mp4_file["id"], video_path)

                channel_key = "HINDI" if "HINDI" in target_channel.upper() else "ENGLISH"
                yt_service = youtube_services[channel_key]
                vid_id, watch_url = upload_video_to_youtube(yt_service, video_path, meta)

                # Mark Task_Queue as PUBLISHED
                sheets_service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"Task_Queue!F{row_idx}",
                    valueInputOption="USER_ENTERED",
                    body={'values': [["PUBLISHED"]]}
                ).execute()

                # Archive into the Channel Tab
                dest_tab = "Daily Fun Facts (Hindi)" if channel_key == "HINDI" else "How Did That Happen (English)"
                archive_row = [
                    meta["title"], watch_url, vid_id, datetime.now(timezone.utc).isoformat(), "0", "0", "0", "PUBLISHED"
                ]
                sheets_service.spreadsheets().values().append(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{dest_tab}'!A1",
                    valueInputOption="USER_ENTERED",
                    body={'values': [archive_row]}
                ).execute()
                print(f"[+] Task successfully moved and archived in '{dest_tab}'!")

    # Update view counts for all published videos
    update_view_counters(youtube_services, sheets_service, spreadsheet_id, channel_tabs)

if __name__ == "__main__":
    process_queue()
