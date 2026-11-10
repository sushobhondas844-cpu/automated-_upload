import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

MASTER_FOLDER_ID = "1b9MZR5idAK4EqLi2akxFX-FAMycA8rDe"
TOKEN_PATH = r"C:\Users\susho\Desktop\keygen\drive_token.json"

CHANNELS = [
    {
        "name": "Daily fun facts (Hindi)",
        "channel_id": "UCELk-MRZG0RqANttLh28uzg",
        "tab_name": "Daily Fun Facts (Hindi)",
        "key": "HINDI"
    },
    {
        "name": "How did that happen (English)",
        "channel_id": "UCn0TqxhbISb-9m-t4el66tg",
        "tab_name": "How Did That Happen (English)",
        "key": "ENGLISH"
    }
]

def main():
    if not os.path.exists(TOKEN_PATH):
        print(f"[!] Token file not found at {TOKEN_PATH}")
        return

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

    print(f"[*] Accessing Master Folder: {MASTER_FOLDER_ID}")

    # Check existing items in master folder
    existing_items = drive_service.files().list(
        q=f"'{MASTER_FOLDER_ID}' in parents and trashed = false",
        fields="files(id, name, mimeType)"
    ).execute().get("files", [])

    existing_map = {item["name"]: item for item in existing_items}
    print(f"[*] Existing items in master folder: {list(existing_map.keys())}")

    # 1. Create channel-named folders inside master folder
    channel_folder_ids = {}
    for ch in CHANNELS:
        ch_name = ch["name"]
        if ch_name in existing_map and existing_map[ch_name]["mimeType"] == "application/vnd.google-apps.folder":
            folder_id = existing_map[ch_name]["id"]
            print(f"[+] Channel folder '{ch_name}' exists (ID: {folder_id})")
        else:
            file_meta = {
                'name': ch_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [MASTER_FOLDER_ID]
            }
            folder = drive_service.files().create(body=file_meta, fields='id').execute()
            folder_id = folder.get('id')
            print(f"[+] Created Channel folder '{ch_name}' (ID: {folder_id})")
        channel_folder_ids[ch_name] = folder_id

        # Inside each channel folder, create a sample video directory if not existing
        sub_items = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="files(id, name, mimeType)"
        ).execute().get("files", [])
        sub_map = {item["name"]: item for item in sub_items}

        sample_dir_name = "Video_001_Demo"
        if sample_dir_name not in sub_map:
            sub_meta = {
                'name': sample_dir_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [folder_id]
            }
            sample_dir = drive_service.files().create(body=sub_meta, fields='id').execute()
            sample_dir_id = sample_dir.get('id')
            print(f"    [+] Created sample folder '{sample_dir_name}' in {ch_name}")

            # Create sample metadata.txt in sample dir
            sample_meta_content = (
                f"Title: Amazing Stickman Explainer Episode 1\n"
                f"Description: Watch this incredible stickman breakdown! Subscribe for daily curiosity insights.\n"
                f"Tags: facts, stickman, animation, curiosity, educational, viral\n"
                f"Category: 27\n"
                f"Privacy: public\n"
            )
            media = MediaInMemoryUpload(sample_meta_content.encode('utf-8'), mimetype='text/plain')
            drive_service.files().create(
                body={'name': 'metadata.txt', 'parents': [sample_dir_id]},
                media_body=media
            ).execute()
            print(f"    [+] Added metadata.txt template in {sample_dir_name}")

    # 2. Check or Create the Tracking Spreadsheet
    sheet_title = "YouTube Content Pipeline & Dispatcher"
    if sheet_title in existing_map:
        spreadsheet_id = existing_map[sheet_title]["id"]
        print(f"[+] Spreadsheet '{sheet_title}' exists (ID: {spreadsheet_id})")
    else:
        file_meta = {
            'name': sheet_title,
            'mimeType': 'application/vnd.google-apps.spreadsheet',
            'parents': [MASTER_FOLDER_ID]
        }
        sh_file = drive_service.files().create(body=file_meta, fields='id').execute()
        spreadsheet_id = sh_file.get('id')
        print(f"[+] Created central Spreadsheet '{sheet_title}' (ID: {spreadsheet_id})")

    # 3. Configure Tabs and Headers using Sheets API
    ss_meta = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_tabs = {s['properties']['title']: s['properties']['sheetId'] for s in ss_meta.get('sheets', [])}

    # Prepare batch requests for missing sheets
    requests = []
    target_tabs = ["Task_Queue", "Daily Fun Facts (Hindi)", "How Did That Happen (English)"]
    for tab in target_tabs:
        if tab not in sheet_tabs:
            requests.append({
                'addSheet': {
                    'properties': {
                        'title': tab
                    }
                }
            })

    if requests:
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()
        # Refresh metadata
        ss_meta = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheet_tabs = {s['properties']['title']: s['properties']['sheetId'] for s in ss_meta.get('sheets', [])}

    # Delete Sheet1 if all target tabs exist
    if "Sheet1" in sheet_tabs and len(sheet_tabs) > 1:
        try:
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': [{'deleteSheet': {'sheetId': sheet_tabs['Sheet1']}}]}
            ).execute()
        except Exception:
            pass

    # Populate Headers
    queue_headers = [
        "Task_ID", "Target_Channel", "Folder_Name", "Video_Title",
        "Scheduled_Time_UTC", "Status", "Priority", "Notes"
    ]
    sample_queue_row = [
        "TASK_001", "Daily fun facts (Hindi)", "Video_001_Demo", "Sample Hindi Explainer Video",
        "2026-11-12T10:00:00Z", "READY_FOR_UPLOAD", "HIGH", "Place MP4 in Video_001_Demo folder"
    ]
    channel_headers = [
        "Video_Title", "YouTube_URL", "Video_ID", "Published_At", "Views", "Likes", "Comments", "Status"
    ]

    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Task_Queue!A1:H2",
        valueInputOption="USER_ENTERED",
        body={'values': [queue_headers, sample_queue_row]}
    ).execute()

    for ch in CHANNELS:
        tab_name = ch["tab_name"]
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{tab_name}'!A1:H1",
            valueInputOption="USER_ENTERED",
            body={'values': [channel_headers]}
        ).execute()

    print("\n============================================================")
    print(f"[SUCCESS] Complete Drive & Sheet Infrastructure Ready!")
    print(f"Spreadsheet Name : {sheet_title}")
    print(f"Spreadsheet Link : https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    print(f"Channel Folders  : {[c['name'] for c in CHANNELS]}")
    print("============================================================")

if __name__ == "__main__":
    main()
