# SOCIAL MEDIA AUTO CONTENT

## Complete Documentation

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Installation](#quick-installation)
4. [Detailed Setup Guide](#detailed-setup-guide)
5. [Configuration](#configuration)
6. [Google Sheet Setup](#google-sheet-setup)
7. [API Keys Setup](#api-keys-setup)
8. [Features Guide](#features-guide)
9. [Usage Instructions](#usage-instructions)
10. [Testing](#testing)
11. [Troubleshooting](#troubleshooting)
12. [File Reference](#file-reference)

---

## System Overview

This system automates short-form video generation and posting to social media platforms including TikTok, Instagram Reels, and Facebook Reels.

### Core Capabilities

- Generate vertical videos (1080x1920, 9:16 aspect ratio)
- Support multiple templates including zodiac quotes, motivational content, educational tips
- Auto-fetch background videos from Pexels and Pixabay APIs
- Auto-fetch background music with mood-based selection
- Schedule and post automatically via Nuelink API
- Manual approval workflow before posting

### Advanced Features

- YouTube and SoundCloud music search and download
- Multiple audio tracks (background music plus outro)
- Beat detection for text synchronization with music
- 12 zodiac sign templates with custom colors and animations
- Text effects including shadow, blink, box, and rainbow
- Scrolling text in four directions
- Custom watermark and logo placement

---

## Prerequisites

### Hardware Requirements

- VPS or dedicated server with minimum 4 CPU cores
- 4GB RAM minimum (8GB recommended)
- 20GB free storage space

### Software Requirements

- Ubuntu 20.04 or 22.04 (other Linux distributions may work)
- Docker and Docker Compose
- Python 3.8 or higher
- FFmpeg
- Internet connection for API access

### Required API Keys

- Pexels API key (free)
- Pixabay API key (free)
- Nuelink API key (paid subscription required)
- Google Service Account credentials (free)

---

## Quick Installation

Run this single command to set up everything:

```bash
curl -fsSL https://raw.githubusercontent.com/social_auto_content/setup.sh | bash
```
or
```bash
curl -O https://raw.githubusercontent.com/your-repo/setup.sh
chmod +x setup.sh
./setup.sh
```

---

## Detailed Manual Setup Guide

### Step 1: Install System Dependencies

For Ubuntu/Debian systems:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg yt-dlp docker docker-compose git
```

For Debian systems:

```bash
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt install -y python3 python3-pip python3-venv ffmpeg yt-dlp docker.io docker-compose git
```

For CentOS/RHEL:

```bash
sudo yum install -y python3 python3-pip ffmpeg yt-dlp docker docker-compose git
```

### Step 2: Create Project Directory

```bash
mkdir -p ~/social-auto-content
cd ~/social-auto-content
```

### Step 3: Clone Project Files

```bash
git clone https://github.com/readloud/social_auto_content.git
```

### Step 4: Set Up Python Virtual Environment

```bash
cd project
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### Step 5: Install Python Packages

```bash
pip install -r requirements.txt
```

### Step 6: Create Environment Configuration

```bash
cp .env.example .env
```

### Step 7: Create Fallback Assets

Generate fallback video:

```bash
cd assets/videos
ffmpeg -f lavfi -i color=c=black:s=1080x1920:d=60 -vf "drawtext=text='No Video Found':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2" -y fallback.mp4
```

Generate fallback audio (silence):

```bash
cd ../music
ffmpeg -f lavfi -i anullsrc=r=44100:cl=stereo -t 3 -q:a 9 -acodec libmp3lame -y fallback.mp3
```

### Step 8: Start Docker Services

```bash
docker-compose up -d
```

---

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| PEXELS_API_KEY | API key from pexels.com | Yes |
| PIXABAY_API_KEY | API key from pixabay.com | Yes |
| NUELINK_API_KEY | API key from nuelink.com | Yes |
| GOOGLE_SHEET_ID | ID of your Google Sheet | Yes |
| PREVIEW_BASE_URL | Public URL for video previews | Yes |
| SOUNDCLOUD_CLIENT_ID | Optional SoundCloud API key | No |
| TZ | Timezone for scheduling | No |

### Google Service Account Setup

1. Go to Google Cloud Console (console.cloud.google.com)
2. Create a new project or select existing
3. Enable Google Sheets API
4. Go to Credentials > Create Credentials > Service Account
5. Name the service account
6. Click "Done" then select the new service account
7. Go to Keys tab > Add Key > Create New Key > JSON
8. Download the JSON file
9. Place it at `project/google_credentials.json`
10. Share your Google Sheet with the service account email

---

## Google Sheet Setup

### Column Structure

Create a new Google Sheet with the following columns:

Column A: id (auto-increment)
Column B: status (dropdown)
Column C: approval_status (dropdown)
Column D: template (dropdown)
Column E: music_mood (dropdown)
Column F: timezone (dropdown)
Column G: title
Column H: text_1
Column I: text_2
Column J: text_3
Column K: text_4
Column L: text_5
Column M: caption
Column N: hashtags
Column O: asset_keyword
Column P: schedule_datetime
Column Q: music_source
Column R: music_mode
Column S: music_fade_in
Column T: music_fade_out
Column U: music_volume
Column V: video_output_path
Column W: preview_url
Column X: nuelink_post_id
Column Y: retry_count
Column Z: last_error
Column AA: approved_by
Column AB: approved_at
Column AC: reject_reason

### Dropdown Values

For column B (status):
DRAFT, READY_RENDER, RENDERING, RENDERED, WAITING_APPROVAL, APPROVED, REJECTED, SENT_TO_NUELINK, ERROR

For column C (approval_status):
WAITING_APPROVAL, APPROVED, REJECTED

For column D (template):
zodiac_dark, motivational, educational, quote_simple, tips_daily

For column E (music_mood):
dark, cinematic, upbeat, motivational, lofi, ambient, epic, happy, sad, beats

For column R (music_mode):
background, full, trim

### How to Set Up Dropdowns

1. Select the column
2. Go to Data > Data validation
3. Select "List of items"
4. Enter values separated by commas
5. Click Save

---

## API Keys Setup

### Pexels API

1. Go to pexels.com/api
2. Sign up or log in
3. Create a new API key
4. Copy the key to your .env file

Free tier: 200 requests per hour, 10,000 requests per month

### Pixabay API

1. Go to pixabay.com/api/docs
2. Sign up or log in
3. Your API key is shown on the documentation page
4. Copy the key to your .env file

Free tier: 5,000 requests per day

### Nuelink API

1. Go to nuelink.com
2. Sign up for an account
3. Go to Settings > API
4. Generate an API key
5. Copy the key to your .env file

Paid subscription required starting at $29 per month

---

## Features Guide

### Template System

The system includes five default templates:

| Template | Description | Best For |
|----------|-------------|----------|
| zodiac_dark | Dark theme with bold text | Zodiac predictions |
| motivational | Bright gold text on dark background | Quote videos |
| educational | Blue background with white text | Tips and tutorials |
| quote_simple | Minimalist design | Short quotes |
| tips_daily | Left-aligned text with green accent | Daily tips |

### 12 Zodiac Templates

Each zodiac sign has custom colors and animations:

Fire Signs (Aries, Leo, Sagittarius): Red, orange, and gold themes with zoom animations
Earth Signs (Taurus, Virgo, Capricorn): Green and earth tones with fade animations
Air Signs (Gemini, Libra, Aquarius): Light colors with blur animations
Water Signs (Cancer, Scorpio, Pisces): Blue and purple with zoom animations

### Text Effects

| Effect | Description |
|--------|-------------|
| shadow | Adds drop shadow to text |
| blink | Text flashes on and off |
| box | Text appears inside a colored box |
| rainbow | Text cycles through colors |
| none | Plain text without effects |

### Animations

| Animation | Description |
|-----------|-------------|
| fade | Text fades in and out |
| zoom_fan | Text scales up then returns |
| blur | Text blurs in and out |

### Transitions

| Transition | Description |
|------------|-------------|
| center | Fade transition from center |
| left | Slide transition from left |
| right | Slide transition from right |
| bottom | Slide transition from bottom |

### Scrolling Text

Text can scroll in four directions:
- Left to right
- Right to left
- Top to bottom
- Bottom to top

Configure scroll speed in the configuration file.

### Music Features

#### Music Sources

- Local files in project/assets/music folder
- Direct URLs to MP3 files
- YouTube search and download
- SoundCloud search and download

#### Music Modes

| Mode | Behavior |
|------|----------|
| background | Loops to match video length, lower volume (0.5x) |
| full | Plays entire track without looping |
| trim | Cuts track to exact video duration |

#### Audio Controls

- Fade in duration (seconds)
- Fade out duration (seconds)
- Volume multiplier (0 to 1)
- Normalization (automatic volume leveling)

#### Multi-Track Audio

Combine multiple audio sources:
- Background music (plays throughout)
- Outro music (plays at end)
- Sound effects (trigger at specific times)
- Voiceover (ducks background music)

### Beat Detection

The system can detect beats in music and sync text appearance to them:

1. Music is analyzed using librosa library
2. BPM (beats per minute) is calculated
3. Text timings are adjusted to match beat intervals
4. Text appears in rhythm with the music

This creates a more engaging viewer experience.

### Watermark and Logo

| Element | Position Options |
|---------|------------------|
| Watermark | top_left, top_center, top_right, center, bottom_left, bottom_center, bottom_right |
| Logo | top_left, top_right, bottom_left, bottom_right |

Configure text, font size, and color for each.

---

## Usage Instructions

### Basic Workflow

1. Prepare content in Google Sheet
   - Set status to "DRAFT"
   - Fill in text fields (text_1 through text_5)
   - Select template and music mood
   - Add asset keyword for background search
   - Set schedule date and time

2. Change status to "READY_RENDER"
   - System will detect the row
   - Video rendering starts automatically
   - Preview URL appears when complete

3. Review the video
   - Click preview URL to watch
   - Change approval_status to "APPROVED" or "REJECTED"

4. Automatic posting
   - If approved, video sends to Nuelink
   - Scheduled post is created
   - Status updates to "SENT_TO_NUELINK"

### Using Custom Music

Option 1: Local file
- Place MP3 file in project/assets/music/
- Set music_source column to filename

Option 2: URL
- Set music_source column to direct URL
- System downloads automatically

Option 3: YouTube search
- Set music_source to "youtube_search"
- Set music_query column to search term
- System downloads first result

Option 4: SoundCloud search
- Set music_source to "soundcloud_search"
- Set music_query column to search term

### Using Beat Sync

To enable beat-synced text:
- Add column "beat_sync" set to TRUE
- Ensure music source is provided
- System will detect BPM and align text timing

### Multiple Audio Tracks

To add outro music:
- Add column "outro_source" with file path or URL
- Set "outro_duration" in seconds

To add sound effects:
- Add column "sfx_path" with file path
- Add column "sfx_time" for when to play (seconds)

---

## Testing

### Run System Diagnostics

```bash
cd project
python debug_system.py
```

This checks:
- Python version
- FFmpeg installation
- Required packages
- Environment variables
- Folder structure
- API connectivity
- Disk space
- Memory availability

### Test Video Rendering

```bash
cd project
test/python test_local.py
```

Expected output:
Render SUCCESS
Video path: /project/outputs/videos/video_timestamp.mp4
Preview URL: http://localhost:8080/video_timestamp.mp4

### Test All Features

```bash
cd project
test/python test_complete_features.py
```

Tests include:
- YouTube music search and download
- Multi-track audio mixing
- Beat detection and sync
- SoundCloud search

### Test Specific Components

Test YouTube search only:
```bash
test/python scripts/music_search.py search --query "lofi beats" --platform youtube --limit 5
```

Test beat detection on audio file:
```bash
test/python scripts/beat_detector.py assets/music/sample.mp3
```

List available music files:
```bash
test/python scripts/music_manager.py list
```

---

## Troubleshooting

### Common Issues and Solutions

Issue: FFmpeg not found
Solution:
```bash
sudo apt update
sudo apt install ffmpeg
```

Issue: Python packages missing
Solution:
```bash
cd project
source venv/bin/activate
pip install -r requirements.txt
```

Issue: Google Sheets connection failed
Solution:
- Verify GOOGLE_SHEET_ID in .env
- Check google_credentials.json exists
- Confirm service account has access to sheet
- Re-share the sheet with service account email

Issue: Pexels API rate limit
Solution:
- Free tier limited to 200 requests per hour
- Add delay between renders
- Use more fallback local assets

Issue: Video render fails with memory error
Solution:
- Reduce video resolution (change in CONFIG)
- Render fewer videos simultaneously
- Add more RAM to VPS

Issue: YouTube download fails
Solution:
- Install yt-dlp: pip install yt-dlp
- Update yt-dlp: pip install -U yt-dlp
- Check network connectivity

Issue: Beat detection not working
Solution:
- Install librosa: pip install librosa
- Install soundfile: pip install soundfile
- Ensure audio file is MP3 format

Issue: Preview URL not loading
Solution:
- Check preview-server container: docker ps
- Restart preview-server: docker-compose restart preview-server
- Verify file permissions: chmod 755 project/outputs/videos

Issue: n8n workflow not triggering
Solution:
- Check n8n container logs: docker logs n8n_automation
- Verify schedule trigger settings
- Check Google Sheet connection in n8n

### Logs Location

Render logs: project/outputs/logs/render_YYYYMMDD.log
n8n logs: docker logs n8n_automation
System logs: journalctl -u docker

### Getting Help

Check the following resources:
- System debug: python debug_system.py
- Render logs: tail -f project/outputs/logs/render_*.log
- n8n interface: http://localhost:5678

---

## File Reference

### Core Scripts

| File | Purpose |
|------|---------|
| render_video.py | Basic video rendering with FFmpeg |
| advanced_render_v3.py | Complete renderer with all features |
| music_manager.py | Music file management and processing |
| music_search.py | YouTube and SoundCloud search/download |
| multi_track_audio.py | Multiple audio track mixing |
| beat_detector.py | BPM detection and text sync |
| zodiac_templates.py | 12 zodiac sign configurations |
| debug_system.py | System diagnostic tool |
| test_complete_features.py | Full feature testing |

### Configuration Files

| File | Purpose |
|------|---------|
| .env | API keys and environment variables |
| requirements.txt | Python package dependencies |
| docker-compose.yml | Docker services configuration |
| workflow.json | n8n automation workflow |

---

## Version History

Version 1.0 - Initial release
- Basic video rendering
- Google Sheets integration
- n8n workflow
- Nuelink posting

Version 2.0 - Advanced features
- 12 zodiac templates
- YouTube and SoundCloud search
- Beat detection and sync
- Multiple audio tracks
- Text effects and animations

---

## License

This software is for internal use only. Do not redistribute or resell.

---

## Support

For technical support:
1. Run debug_system.py to identify issues
2. Check render logs in project/outputs/logs/
3. Review n8n workflow logs in the n8n interface
4. Ensure all API keys are valid and have quota remaining

---

## Document Version

Version 2.0
Last Updated: 2026-01-16
