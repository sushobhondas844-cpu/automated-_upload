"""
YouTube Channel Token Generator
Uses your existing 'client_secrets.json' to authorize and create 'youtube_token.json'.

Usage:
  python generate_youtube_token.py
"""

import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

# The required YouTube upload scope
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

def main():
    # Check default locations for client_secrets
    secrets_path = "client_secrets.json"
    fallback_path = r"C:\Users\susho\Desktop\keygen\client_secrets.json"
    
    if not os.path.exists(secrets_path):
        if os.path.exists(fallback_path):
            secrets_path = fallback_path
        else:
            print("[!] Error: 'client_secrets.json' not found.")
            sys.exit(1)

    print(f"[*] Found client secrets at: {secrets_path}")
    print("[*] Launching browser for YouTube OAuth authorization...")
    print("[*] TIP: Click your Google account, then SELECT YOUR YOUTUBE CHANNEL (e.g. Daily fun facts).")
    
    flow = InstalledAppFlow.from_client_secrets_file(secrets_path, YOUTUBE_SCOPES)
    creds = flow.run_local_server(port=0)

    output_token_file = "youtube_token.json"
    with open(output_token_file, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    print("\n" + "="*50)
    print(f" [SUCCESS] Token generated successfully: {output_token_file}")
    print("="*50)
    print("Next steps:")
    print("1. Run `python test_youtube_token.py youtube_token.json` to verify channel details.")
    print("2. Copy the text inside youtube_token.json and paste it into GitHub Secret Vault as:")
    print("   YOUTUBE_TOKEN_HINDI")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
