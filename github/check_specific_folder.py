import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def inspect_folder(folder_id):
    token_path = r"C:\Users\susho\Desktop\keygen\drive_token.json"
    if not os.path.exists(token_path):
        print("[!] drive_token.json not found")
        return

    data = json.load(open(token_path))
    creds = Credentials.from_authorized_user_info(data)
    drive = build('drive', 'v3', credentials=creds)

    print(f"[*] Accessing Folder ID: {folder_id}...")
    try:
        folder = drive.files().get(fileId=folder_id, fields="id, name, mimeType, capabilities").execute()
        print(f"[+] Folder Name: '{folder.get('name')}' (ID: {folder.get('id')})")
        
        # List contents inside this folder
        query = f"'{folder_id}' in parents and trashed = false"
        results = drive.files().list(q=query, pageSize=20, fields="files(id, name, mimeType)").execute()
        files = results.get('files', [])
        print(f"[+] Items inside folder ({len(files)}):")
        for f in files:
            print(f"  - {f['name']} [{f['mimeType']}] (ID: {f['id']})")
    except Exception as e:
        print(f"[!] Error accessing folder: {e}")

if __name__ == '__main__':
    inspect_folder("1b9MZR5idAK4EqLi2akxFX-FAMycA8rDe")
