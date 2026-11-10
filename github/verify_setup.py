"""
Diagnostics & Verification Script (Updated Scope Fix)
"""

import os
import sys
import json
import base64
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build

MASTER_FOLDER_ID = "1b9MZR5idAK4EqLi2akxFX-FAMycA8rDe"

def test_drive():
    print("="*60)
    print("[1] TESTING GOOGLE DRIVE ACCESS")
    print("="*60)
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not sa_json:
        print("[!] Missing secret: GOOGLE_SERVICE_ACCOUNT_JSON")
        return False
        
    try:
        if sa_json.startswith("{"):
            creds_dict = json.loads(sa_json)
        else:
            creds_dict = json.loads(base64.b64decode(sa_json).decode('utf-8'))
            
        print(f"[*] Secret JSON format detected. Top keys: {list(creds_dict.keys())}")
        
        # Check if it's a Service Account OR an OAuth User Token
        if "client_email" in creds_dict and creds_dict.get("type") == "service_account":
            print(f"[*] Detected Type: Google Service Account ({creds_dict.get('client_email')})")
            scopes = ["https://www.googleapis.com/auth/drive.readonly"]
            creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=scopes)
        elif "token" in creds_dict or "refresh_token" in creds_dict:
            print("[*] Detected Type: OAuth User Token (from drive_token.json)")
            # Do NOT pass artificial scopes that conflict with the token's original granted scopes!
            token_scopes = creds_dict.get("scopes")
            print(f"[*] Token scopes from JSON: {token_scopes}")
            creds = UserCredentials.from_authorized_user_info(creds_dict, scopes=token_scopes)
        elif "installed" in creds_dict or "web" in creds_dict:
            print("[!] Detected Type: client_secrets.json (OAuth App Gateway, not an authorized token or service account)")
            return False
        else:
            print(f"[!] Unrecognized credentials structure. Keys: {list(creds_dict.keys())}")
            return False

        drive = build("drive", "v3", credentials=creds)
        print(f"[*] Querying master folder ID: {MASTER_FOLDER_ID}...")
        folder = drive.files().get(fileId=MASTER_FOLDER_ID, fields="id, name, mimeType").execute()
        print(f"[+] SUCCESS! Found Drive Folder: '{folder.get('name')}' (ID: {folder.get('id')})")
        
        # List contents
        items = drive.files().list(q=f"'{MASTER_FOLDER_ID}' in parents and trashed = false", pageSize=10).execute().get("files", [])
        print(f"[+] Items inside folder ({len(items)}):")
        if not items:
            print("    (Folder is currently empty or has no subfiles yet - perfectly ready!)")
        for it in items:
            print(f"    - {it.get('name')} [{it.get('mimeType')}]")
        return True
    except Exception as e:
        print(f"[!] FAILED to access Drive: {e}")
        return False

def test_youtube(token_env_var, label):
    print("\n" + "="*60)
    print(f"[2] TESTING YOUTUBE CHANNEL: {label} ({token_env_var})")
    print("="*60)
    token_str = os.environ.get(token_env_var, "").strip()
    if not token_str:
        print(f"[-] Secret {token_env_var} is not set. Skipping.")
        return False
        
    try:
        if token_str.startswith("{"):
            token_dict = json.loads(token_str)
        else:
            token_dict = json.loads(base64.b64decode(token_str).decode('utf-8'))
            
        token_scopes = token_dict.get("scopes", ["https://www.googleapis.com/auth/youtube.readonly"])
        creds = UserCredentials.from_authorized_user_info(token_dict, scopes=token_scopes)
        yt = build("youtube", "v3", credentials=creds)
        resp = yt.channels().list(part="snippet,statistics", mine=True).execute()
        items = resp.get("items", [])
        if not items:
            print(f"[!] Warning: Token is valid, but no YouTube channel found directly under this login.")
            return False
            
        ch = items[0]
        print(f"[+] SUCCESS! Authenticated with YouTube Channel:")
        print(f"    Channel Title : {ch['snippet']['title']}")
        print(f"    Channel ID    : {ch['id']}")
        print(f"    Subscribers   : {ch['statistics'].get('subscriberCount', 'Hidden')}")
        print(f"    Total Videos  : {ch['statistics'].get('videoCount', '0')}")
        return True
    except Exception as e:
        print(f"[!] FAILED to authenticate {label}: {e}")
        return False

def main():
    drive_ok = test_drive()
    hindi_ok = test_youtube("YOUTUBE_TOKEN_HINDI", "Hindi Channel")
    english_ok = test_youtube("YOUTUBE_TOKEN_ENGLISH", "English Channel")
    
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY:")
    print(f"  Google Drive Folder : {' PASS' if drive_ok else ' FAIL'}")
    print(f"  YouTube Hindi       : {' PASS' if hindi_ok else ' FAIL'}")
    print(f"  YouTube English     : {' PASS' if english_ok else ' FAIL'}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
