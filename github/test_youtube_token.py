import sys
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def test_token(token_file_or_snippet):
    try:
        # Check if it's a file path or raw token string
        if token_file_or_snippet.endswith(".json"):
            with open(token_file_or_snippet, "r", encoding="utf-8") as f:
                data = json.load(f)
            creds = Credentials.from_authorized_user_info(data)
        else:
            # Bare access token test
            creds = Credentials(token=token_file_or_snippet)

        print("[*] Testing token with YouTube Data API...")
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.channels().list(part="snippet,contentDetails,statistics", mine=True)
        response = request.execute()

        items = response.get("items", [])
        if not items:
            print("[!] Token is valid, but NO YouTube channel was found directly under this login.")
            return False

        channel = items[0]
        title = channel["snippet"]["title"]
        channel_id = channel["id"]
        subs = channel["statistics"].get("subscriberCount", "Hidden")
        videos = channel["statistics"].get("videoCount", "0")
        
        print("\n" + "="*50)
        print(" [SUCCESS] TOKEN IS 100% YOUTUBE AUTHENTICATED!")
        print("="*50)
        print(f"  Channel Title : {title}")
        print(f"  Channel ID    : {channel_id}")
        print(f"  Subscribers   : {subs}")
        print(f"  Total Videos  : {videos}")
        print("="*50 + "\n")
        return True

    except Exception as e:
        print("\n" + "!"*50)
        print(f" [FAILED] Authentication Check Failed:")
        print(f" Error: {e}")
        print("!"*50 + "\n")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_token(sys.argv[1])
    else:
        print("Usage: python test_youtube_token.py <path_to_token.json_or_token_string>")
