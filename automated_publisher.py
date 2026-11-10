"""
Automated Cloud Publishing Dispatcher
Designed to run on GitHub Actions or a scheduled cloud worker.

Workflow:
1. Reads tracking Google Sheet to find rows where:
   - Status == 'APPROVED' (approved by you locally)
   - Scheduled Time <= Current Time
   - Upload Status == 'PENDING'
2. Downloads the approved MP4 file from Google Drive using Drive File ID.
3. Authenticates with YouTube Data API using channel OAuth credentials stored in GitHub Secrets.
4. Uploads video to YouTube with exact title, description, tags, and category from the Sheet.
5. Updates Google Sheet row with:
   - Upload Status = 'PUBLISHED'
   - Published YouTube Video URL
   - Published Timestamp
"""

import os
import sys
import json
import base64
import tempfile
from datetime import datetime, timezone
import gspread
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# Required scopes
SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"]
SCOPES_YOUTUBE = ["https://www.googleapis.com/auth/youtube.upload"]

def get_sheets_client():
    """Authenticates with Google Sheets via Service Account JSON stored in GitHub Secret."""
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_JSON environment secret.")
    
    # Can be raw JSON or base64 encoded JSON
    if sa_json.strip().startswith("{"):
        creds_dict = json.loads(sa_json)
    else:
        creds_dict = json.loads(base64.b64decode(sa_json).decode('utf-8'))
        
    creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=SCOPES_SHEETS)
    return gspread.authorize(creds), creds

def get_youtube_client(channel_token_secret_name):
    """
    Authenticates with YouTube using a cached OAuth token stored in GitHub Secrets.
    Supports multiple channels by passing different secret names (e.g., YOUTUBE_TOKEN_HINDI, YOUTUBE_TOKEN_ENGLISH).
    """
    token_json = os.environ.get(channel_token_secret_name)
    if not token_json:
        raise ValueError(f"Missing YouTube OAuth token secret: {channel_token_secret_name}")
        
    if token_json.strip().startswith("{"):
        token_data = json.loads(token_json)
    else:
        token_data = json.loads(base64.b64decode(token_json).decode('utf-8'))
        
    creds = UserCredentials.from_authorized_user_info(token_data, SCOPES_YOUTUBE)
    return build("youtube", "v3", credentials=creds)

def download_video_from_drive(drive_service, file_id, dest_path):
    print(f"[*] Downloading file {file_id} from Google Drive...")
    request = drive_service.files().get_media(fileId=file_id)
    with open(dest_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"    Drive Download: {int(status.progress() * 100)}%")
    print(f"[+] Download complete: {dest_path}")

def upload_video_to_youtube(youtube_service, file_path, title, description, tags, category_id="27", privacy="public"):
    print(f"[*] Uploading to YouTube: '{title}' [{privacy}]")
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': [t.strip() for t in tags.split(",") if t.strip()] if isinstance(tags, str) else tags,
            'categoryId': category_id
        },
        'status': {
            'privacyStatus': privacy,
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
    return watch_url

def process_scheduled_uploads():
    sheet_name = os.environ.get("TRACKING_SHEET_NAME", "Stickman Automation Tracker")
    print(f"[*] Connecting to Google Sheet: '{sheet_name}'")
    
    gc, sa_creds = get_sheets_client()
    drive_service = build("drive", "v3", credentials=sa_creds)
    sheet = gc.open(sheet_name).sheet1
    rows = sheet.get_all_records()
    
    now = datetime.now(timezone.utc)
    print(f"[*] Current UTC Time: {now.isoformat()} | Found {len(rows)} rows to evaluate.")
    
    for idx, row in enumerate(rows, start=2): # row 2 is first data row
        approval = str(row.get("Approval_Status", "")).strip().upper()
        upload_status = str(row.get("Upload_Status", "")).strip().upper()
        scheduled_time_str = str(row.get("Scheduled_Time_UTC", "")).strip()
        drive_file_id = str(row.get("Drive_File_ID", "")).strip()
        channel_name = str(row.get("Target_Channel", "HINDI")).strip().upper()
        
        # Check if row is ready for publishing
        if approval == "APPROVED" and upload_status in ["PENDING", "QUEUED", ""]:
            # Evaluate schedule time if present
            should_upload = True
            if scheduled_time_str:
                try:
                    sched_dt = datetime.fromisoformat(scheduled_time_str)
                    if sched_dt > now:
                        print(f"[-] Row {idx} scheduled for {scheduled_time_str} is in the future. Skipping.")
                        should_upload = False
                except Exception as e:
                    print(f"[!] Warning: Could not parse time '{scheduled_time_str}' on row {idx}: {e}")
                    
            if not should_upload:
                continue
                
            if not drive_file_id:
                print(f"[!] Error: Row {idx} is APPROVED but has no Drive_File_ID. Skipping.")
                continue
                
            print(f"\n[>>>] Triggering upload for Row {idx}: '{row.get('Title')}'")
            
            # Map channel to corresponding GitHub Secret
            secret_key = "YOUTUBE_TOKEN_HINDI" if "HINDI" in channel_name else "YOUTUBE_TOKEN_ENGLISH"
            youtube_service = get_youtube_client(secret_key)
            
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                
            try:
                download_video_from_drive(drive_service, drive_file_id, tmp_path)
                video_url = upload_video_to_youtube(
                    youtube_service=youtube_service,
                    file_path=tmp_path,
                    title=row.get("Title", "Daily Fun Facts"),
                    description=row.get("Description", "#Shorts #Facts"),
                    tags=row.get("Tags", "Shorts,Facts"),
                    privacy=row.get("Privacy", "public")
                )
                
                # Update Sheet row
                # Header assumed: Col F: Upload_Status, Col G: Published_URL, Col H: Published_At
                sheet.update_cell(idx, sheet.find("Upload_Status").col, "PUBLISHED")
                sheet.update_cell(idx, sheet.find("Published_URL").col, video_url)
                sheet.update_cell(idx, sheet.find("Published_At").col, datetime.now(timezone.utc).isoformat())
                print(f"[+] Sheet row {idx} successfully updated with URL {video_url}!")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

if __name__ == "__main__":
    process_scheduled_uploads()
