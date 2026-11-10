import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def list_folders():
    token_path = r"C:\Users\susho\Desktop\keygen\drive_token.json"
    if not os.path.exists(token_path):
        print("[!] drive_token.json not found")
        return

    data = json.load(open(token_path))
    creds = Credentials.from_authorized_user_info(data)
    drive = build('drive', 'v3', credentials=creds)

    print("[*] Searching Google Drive for folders...")
    query = "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = drive.files().list(q=query, pageSize=30, fields="files(id, name, parents)").execute()
    
    items = results.get('files', [])
    if not items:
        print("[!] No folders found in this Drive.")
        return

    print(f"[+] Found {len(items)} folders:")
    for item in items:
        print(f"  - {item['name']} | ID: {item['id']}")

if __name__ == '__main__':
    list_folders()
