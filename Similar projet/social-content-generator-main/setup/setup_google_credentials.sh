#!/bin/bash
# Auto-setup Google Credentials

echo "Google Service Account Setup"
echo "============================"

# Cek apakah file sudah ada
if [ -f "project/google_credentials.json" ]; then
    echo "File google_credentials.json already exists."
    echo "Do you want to replace it? (y/n)"
    read -r answer
    if [ "$answer" != "y" ]; then
        echo "Exiting..."
        exit 0
    fi
fi

# Input from user
echo "Please paste the entire content of your Google Service Account JSON file:"
echo "(Paste then press Ctrl+D on a new line)"
echo ""

# Read multiline input
json_content=$(cat)

# Validate JSON
if ! echo "$json_content" | jq . > /dev/null 2>&1; then
    echo "Error: Invalid JSON format"
    exit 1
fi

# Save to file
mkdir -p project
echo "$json_content" > project/google_credentials.json

# Set permissions
chmod 600 project/google_credentials.json

# Extract client email
client_email=$(echo "$json_content" | jq -r '.client_email')

echo ""
echo "✓ Credentials saved to project/google_credentials.json"
echo "✓ Permissions set to 600 (readable only by owner)"
echo ""

echo "Next steps:"
echo "1. Share your Google Sheet with: $client_email"
echo "2. Add to .env: GOOGLE_SERVICE_ACCOUNT_PATH=/project/google_credentials.json"
echo "3. Test connection: python test_google_sheet.py"