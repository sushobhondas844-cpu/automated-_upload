import os
import sys
import argparse
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Scopes required for YouTube Video Upload and Google Drive Upload
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def get_authenticated_service(client_secrets_file, token_pickle_file, scopes, api_name, api_version):
    creds = None
    if os.path.exists(token_pickle_file):
        with open(token_pickle_file, 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secrets_file):
                print(f"[!] Error: Credentials file '{client_secrets_file}' not found.")
                print(f"    Please place your Google OAuth client_secrets.json in this directory.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
            creds = flow.run_local_server(port=0)
        with open(token_pickle_file, 'wb') as token:
            pickle.dump(creds, token)

    return build(api_name, api_version, credentials=creds)

def upload_to_drive(file_path, folder_id=None, client_secrets="client_secrets.json"):
    print(f"[*] Uploading to Google Drive: {file_path}")
    service = get_authenticated_service(
        client_secrets, 
        "drive_token.pickle", 
        DRIVE_SCOPES, 
        "drive", 
        "v3"
    )
    
    file_metadata = {'name': os.path.basename(file_path)}
    if folder_id:
        file_metadata['parents'] = [folder_id]
        
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    print(f"[+] Successfully uploaded to Drive!")
    print(f"    File ID: {file.get('id')}")
    print(f"    Link: {file.get('webViewLink')}")
    return file

def upload_to_youtube(file_path, title, description, tags=None, category_id="27", privacy_status="private", client_secrets="client_secrets.json"):
    print(f"[*] Uploading to YouTube: {title}")
    youtube = get_authenticated_service(
        client_secrets, 
        "youtube_token.pickle", 
        YOUTUBE_SCOPES, 
        "youtube", 
        "v3"
    )
    
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags or ['Shorts', 'Facts', 'Hindi Facts', 'Daily Fun Facts', 'Stickman'],
            'categoryId': category_id # 27 = Education
        },
        'status': {
            'privacyStatus': privacy_status, # Start private for safety
            'selfDeclaredMadeForKids': False
        }
    }
    
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"    Uploaded {int(status.progress() * 100)}%...")
            
    print(f"[+] Successfully uploaded to YouTube!")
    print(f"    Video ID: {response.get('id')}")
    print(f"    Watch URL: https://youtu.be/{response.get('id')}")
    return response

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload videos to Google Drive or YouTube")
    parser.add_argument("--file", required=True, help="Path to the MP4 video file")
    parser.add_argument("--action", choices=["drive", "youtube", "both"], default="drive", help="Target upload destination")
    parser.add_argument("--title", default="Daily Fun Fact Hindi Explainer", help="YouTube video title")
    parser.add_argument("--desc", default="Daily Fun Facts Hindi #Shorts #Facts", help="YouTube video description")
    parser.add_argument("--folder_id", help="Google Drive target folder ID")
    parser.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private", help="YouTube privacy status")
    
    args = parser.parse_args()
    
    if args.action in ["drive", "both"]:
        upload_to_drive(args.file, folder_id=args.folder_id)
        
    if args.action in ["youtube", "both"]:
        upload_to_youtube(args.file, args.title, args.desc, privacy_status=args.privacy)
