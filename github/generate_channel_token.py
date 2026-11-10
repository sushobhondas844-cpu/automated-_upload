"""
Helper Script to Generate a Reusable YouTube OAuth Token JSON.
Run this once on your local machine to authenticate each channel.

Usage:
  python generate_channel_token.py --client_secrets client_secrets.json --output token_hindi.json
  python generate_channel_token.py --client_secrets client_secrets.json --output token_english.json
"""

import sys
import argparse
from google_auth_oauthlib.flow import InstalledAppFlow

YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]

def main():
    parser = argparse.ArgumentParser(description="Generate YouTube OAuth Token JSON for GitHub Secrets")
    parser.add_argument("--client_secrets", default="client_secrets.json", help="Path to your OAuth Client ID JSON from Google Cloud")
    parser.add_argument("--output", default="youtube_token.json", help="Where to save the generated token JSON")
    args = parser.parse_args()

    print(f"[*] Starting OAuth flow using '{args.client_secrets}'...")
    flow = InstalledAppFlow.from_client_secrets_file(args.client_secrets, YOUTUBE_UPLOAD_SCOPE)
    creds = flow.run_local_server(port=0)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    print(f"\n[+] Success! Token generated and saved to: {args.output}")
    print("[*] Next steps:")
    print("    1. Open this file and copy its contents.")
    print("    2. Go to your GitHub repo > Settings > Secrets and variables > Actions > New repository secret.")
    print("    3. Paste the contents into your secret (e.g. name it YOUTUBE_TOKEN_HINDI).")
    print("    4. Delete the local JSON token or keep it safe; do not commit it to GitHub!")

if __name__ == "__main__":
    main()
