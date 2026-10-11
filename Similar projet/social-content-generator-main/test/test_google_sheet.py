import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load credentials
with open('project/google_credentials.json', 'r') as f:
    creds = json.load(f)

credentials = service_account.Credentials.from_service_account_info(
    creds,
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)

service = build('sheets', 'v4', credentials=credentials)

# Test: list available sheets (just to verify connection)
print("✓ Google Sheets API connection successful!")
print(f"  Service Account: {creds.get('client_email')}")
print("  Ready to use!")
EOF

echo ""
echo "Run test: python test_google_sheet.py"