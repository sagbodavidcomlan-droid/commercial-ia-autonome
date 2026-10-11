#!/bin/bash
# Setup Script for Social Media Auto Content System

set -e

echo "========================================="
echo "Social Media Auto Content System Setup"
echo "========================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Installing Python3..."
    sudo apt update && sudo apt install -y python3 python3-pip python3-venv
fi

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing FFmpeg..."
    sudo apt install -y ffmpeg
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Create project structure
echo "Creating project folders..."
mkdir -p project/{assets/{videos,images,music},assets_cache,output/{videos,logs},templates,scripts,n8n}

# Create Python virtual environment
echo "Setting up Python environment..."
cd project
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# Copy requirements and install
cat > requirements.txt << 'EOF'
moviepy>=1.0.3
requests>=2.28.0
python-dotenv>=1.0.0
pexels-api>=2.0.0
Pillow>=9.0.0
numpy>=1.24.0
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.1.0
google-api-python-client>=2.0.0
EOF

pip install -r requirements.txt

# Create .env template
cat > .env << 'EOF'
# API Keys
PEXELS_API_KEY=your_pexels_api_key_here
PIXABAY_API_KEY=your_pixabay_api_key_here
NUELINK_API_KEY=your_nuelink_api_key_here

# Google Sheets
GOOGLE_SHEET_ID=your_google_sheet_id_here
GOOGLE_SERVICE_ACCOUNT_PATH=/project/google_credentials.json

# System
PREVIEW_BASE_URL=http://localhost:8080
EOF

# Create fallback assets
echo "Creating fallback assets..."
cd assets/videos
ffmpeg -f lavfi -i color=c=black:s=1080x1920:d=10 -vf "drawtext=text='Fallback Video':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2" -y fallback.mp4 2>/dev/null

cd ../music
# Create silent fallback audio (3 seconds silence)
ffmpeg -f lavfi -i anullsrc=r=44100:cl=stereo -t 3 -q:a 9 -acodec libmp3lame -y fallback.mp3 2>/dev/null

cd ../..
echo "Setup complete!"

# Return to root
cd ..

echo ""
echo "========================================="
echo "Setup completed successfully!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit project/.env with your API keys"
echo "2. Place Google Service Account JSON at project/google_credentials.json"
echo "3. Run: docker-compose up -d"
echo "4. Access n8n at http://localhost:5678"
echo "5. Import workflow from n8n/workflow.json"
echo ""
