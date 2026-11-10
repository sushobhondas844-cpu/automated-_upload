# Run this script on your PC to generate 'drive_token.json' with FULL Drive & Sheets permissions
from google_auth_oauthlib.flow import InstalledAppFlow

# Full Google Drive scope (includes Drive, Docs, Sheets, and file management)
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets'
]

def get_token():
    print("Launching browser for Full Google Drive & Sheets authorization...")
    print("TIP: Log in with the Google account that has access to your master folder.")
    
    flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
    creds = flow.run_local_server(port=0)
    
    output_file = 'drive_token.json'
    with open(output_file, 'w', encoding='utf-8') as token:
        token.write(creds.to_json())
        
    print(f"\n✅ Success! Fresh '{output_file}' with full Drive & Sheets access has been created.")
    print("Now copy the text inside 'drive_token.json' and update your GitHub Secret: GOOGLE_SERVICE_ACCOUNT_JSON")

if __name__ == '__main__':
    get_token()
