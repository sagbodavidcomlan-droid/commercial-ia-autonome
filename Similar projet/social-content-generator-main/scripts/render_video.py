#!/usr/bin/env python3
"""
Complete Video Render Engine for Social Media Content
Supports: Pexels API, Pixabay API, Multiple Templates, Animations
"""

import os
import sys
import json
import logging
import tempfile
import shutil
import subprocess
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load credentials
with open('google_credentials.json', 'r') as f:
    creds_json = json.load(f)

credentials = service_account.Credentials.from_service_account_info(
    creds_json,
    scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.readonly']
)

# Build service
service = build('sheets', 'v4', credentials=credentials)

# Read sheet
sheet_id = os.getenv('GOOGLE_SHEET_ID')
range_name = 'Content_Queue!A:Z'
result = service.spreadsheets().values().get(
    spreadsheetId=sheet_id,
    range=range_name
).execute()

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv()

# ============ CONFIGURATION ============
CONFIG = {
    "output_size": (1080, 1920),
    "fps": 24,
    "video_bitrate": "3000k",
    "audio_bitrate": "128k",
    "temp_dir": Path("/project/assets_cache"),
    "output_dir": Path("/project/output/videos"),
    "log_dir": Path("/project/output/logs"),
    "assets_dir": Path("/project/assets"),
    "pexels_api_key": os.getenv("PEXELS_API_KEY"),
    "pixabay_api_key": os.getenv("PIXABAY_API_KEY"),
}

# Create directories
for dir_path in [CONFIG["temp_dir"], CONFIG["output_dir"], CONFIG["log_dir"]]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Setup logging
log_file = CONFIG["log_dir"] / f"render_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============ TEMPLATE CONFIGURATIONS ============
TEMPLATES = {
    "zodiac_dark": {
        "font": "Arial-Bold",
        "font_size": 52,
        "text_color": "#FFFFFF",
        "stroke_color": "#000000",
        "stroke_width": 3,
        "position": ("center", "center"),
        "bg_opacity": 0.5,
        "bg_color": "#000000",
        "animation": "fade",
        "duration_per_text": 5,
        "has_shadow": True,
    },
    "motivational": {
        "font": "Helvetica-Bold",
        "font_size": 56,
        "text_color": "#FFD700",
        "stroke_color": "#000000",
        "stroke_width": 4,
        "position": ("center", "center"),
        "bg_opacity": 0.3,
        "bg_color": "#1a1a2e",
        "animation": "slide",
        "duration_per_text": 6,
        "has_shadow": True,
    },
    "educational": {
        "font": "Arial",
        "font_size": 44,
        "text_color": "#FFFFFF",
        "stroke_color": "#000000",
        "stroke_width": 2,
        "position": ("center", "bottom"),
        "bg_opacity": 0.7,
        "bg_color": "#0f3460",
        "animation": "scale",
        "duration_per_text": 7,
        "has_shadow": False,
    },
    "quote_simple": {
        "font": "Georgia",
        "font_size": 48,
        "text_color": "#F5F5F5",
        "stroke_color": "#333333",
        "stroke_width": 1,
        "position": ("center", "center"),
        "bg_opacity": 0.4,
        "bg_color": "#2c2c2c",
        "animation": "fade",
        "duration_per_text": 5,
        "has_shadow": True,
    },
    "tips_daily": {
        "font": "Arial-Bold",
        "font_size": 40,
        "text_color": "#00FF88",
        "stroke_color": "#000000",
        "stroke_width": 2,
        "position": ("left", "top"),
        "bg_opacity": 0.6,
        "bg_color": "#000000",
        "animation": "slide",
        "duration_per_text": 4,
        "has_shadow": True,
    }
}


# ============ ASSET FETCHER ============
class AssetFetcher:
    """Handle fetching video and music from APIs"""
    
    def __init__(self):
        self.temp_dir = CONFIG["temp_dir"]
        self.downloaded_files = []
    
    def search_video(self, keyword: str) -> Optional[str]:
        """Search and download video from Pexels"""
        if not CONFIG["pexels_api_key"]:
            logger.warning("No Pexels API key, using fallback")
            return None
        
        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": CONFIG["pexels_api_key"]}
        params = {"query": keyword, "per_page": 5, "orientation": "portrait"}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("videos"):
                # Prefer vertical video (portrait)
                for video in data["videos"]:
                    for video_file in video["video_files"]:
                        if video_file.get("height", 0) >= 1920:
                            return self._download_file(video_file["link"], "background.mp4")
                
                # Fallback to first available
                first_video = data["videos"][0]
                video_url = first_video["video_files"][0]["link"]
                return self._download_file(video_url, "background.mp4")
        except Exception as e:
            logger.error(f"Pexels error: {e}")
        
        return None
    
    def search_music(self, mood: str) -> Optional[str]:
        """Search and download music from Pixabay"""
        if not CONFIG["pixabay_api_key"]:
            logger.warning("No Pixabay API key, using fallback")
            return None
        
        url = "https://pixabay.com/api/v2/music/search/"
        params = {
            "key": CONFIG["pixabay_api_key"],
            "q": mood,
            "duration": "short",
            "instrumental": 1,
            "limit": 3
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("hits"):
                track = data["hits"][0]
                # Get best quality audio
                audio_url = track.get("audio_file_url") or track.get("url")
                if audio_url:
                    return self._download_file(audio_url, "music.mp3")
        except Exception as e:
            logger.error(f"Pixabay error: {e}")
        
        return None
    
    def _download_file(self, url: str, filename: str) -> str:
        """Download file to temp directory"""
        local_path = self.temp_dir / filename
        logger.info(f"Downloading: {url[:100]}...")
        
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=32768):
                f.write(chunk)
        
        self.downloaded_files.append(local_path)
        logger.info(f"Downloaded: {local_path} ({local_path.stat().st_size / 1024:.1f} KB)")
        return str(local_path)
    
    def cleanup(self):
        """Delete temporary files"""
        for file_path in self.downloaded_files:
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Cleaned up: {file_path}")
            except Exception as e:
                logger.warning(f"Cleanup failed for {file_path}: {e}")
        
        # Also clean entire temp dir if empty
        try:
            for f in self.temp_dir.iterdir():
                if f.is_file():
                    f.unlink()
        except Exception:
            pass
        
        self.downloaded_files = []


# ============ VIDEO RENDERER ============
class VideoRenderer:
    """FFmpeg-based video renderer (faster than MoviePy for simple tasks)"""
    
    def __init__(self, template_name: str):
        self.template = TEMPLATES.get(template_name, TEMPLATES["motivational"])
        self.template_name = template_name
    
    def render_with_ffmpeg(
        self,
        texts: List[str],
        background_path: str,
        music_path: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        Render video using FFmpeg with drawtext filters
        This is faster and more memory-efficient than MoviePy
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = CONFIG["output_dir"] / f"video_{timestamp}.mp4"
        
        output_path = Path(output_path)
        duration_per_text = self.template["duration_per_text"]
        total_duration = len(texts) * duration_per_text
        total_duration = min(total_duration, 60)  # Max 60 seconds
        
        # Step 1: Create text overlay videos with FFmpeg
        text_clips = []
        temp_dir = Path(tempfile.mkdtemp())
        
        for i, text in enumerate(texts):
            if not text or not text.strip():
                continue
            
            # Create text overlay video
            text_output = temp_dir / f"text_{i}.mp4"
            start_offset = i * duration_per_text
            
            # Build drawtext filter
            font_size = self.template["font_size"]
            font_color = self.template["text_color"]
            font_file = self._get_font_path()
            
            # Position calculation
            pos_x, pos_y = self.template["position"]
            if pos_x == "center":
                x_expr = "(w-text_w)/2"
            elif pos_x == "left":
                x_expr = "50"
            elif pos_x == "right":
                x_expr = "w-text_w-50"
            else:
                x_expr = str(pos_x)
            
            if pos_y == "center":
                y_expr = "(h-text_h)/2"
            elif pos_y == "top":
                y_expr = "100"
            elif pos_y == "bottom":
                y_expr = "h-text_h-150"
            else:
                y_expr = str(pos_y)
            
            # Escape text for FFmpeg
            escaped_text = text.replace("'", "\\'").replace(":", "\\:")
            
            # Build filter chain
            filter_parts = [
                f"drawtext=text='{escaped_text}':fontfile={font_file}:fontsize={font_size}:fontcolor={font_color}",
                f"x={x_expr}:y={y_expr}",
                f"shadowcolor=black@0.5:shadowx=2:shadowy=2" if self.template.get("has_shadow") else "",
                f"bordercolor={self.template['stroke_color']}:borderw={self.template['stroke_width']}",
                f"box=1:boxcolor={self.template['bg_color']}@{self.template['bg_opacity']}:boxborderw=10",
            ]
            filter_chain = ":".join([p for p in filter_parts if p])
            
            # Generate text video
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=black:s={CONFIG['output_size'][0]}x{CONFIG['output_size'][1]}:d={duration_per_text}",
                "-vf", filter_chain,
                "-c:v", "libx264", "-preset", "ultrafast",
                "-t", str(duration_per_text),
                str(text_output)
            ]
            
            try:
                subprocess.run(cmd, capture_output=True, check=True)
                text_clips.append((text_output, start_offset))
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg text render error: {e.stderr}")
        
        # Step 2: Process background video
        processed_bg = temp_dir / "background_processed.mp4"
        
        # Loop background if needed
        probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", background_path]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        bg_duration = float(result.stdout.strip())
        
        if bg_duration < total_duration:
            # Create loop with concat
            loops = int(total_duration / bg_duration) + 1
            concat_file = temp_dir / "concat_list.txt"
            with open(concat_file, "w") as f:
                for _ in range(loops):
                    f.write(f"file '{background_path}'\n")
            
            loop_cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", str(concat_file),
                "-c", "copy", "-t", str(total_duration),
                str(processed_bg)
            ]
        else:
            # Just trim
            loop_cmd = [
                "ffmpeg", "-y",
                "-i", background_path,
                "-t", str(total_duration),
                "-c", "copy",
                str(processed_bg)
            ]
        
        subprocess.run(loop_cmd, capture_output=True, check=True)
        
        # Step 3: Overlay text clips onto background
        # Build overlay filter chain
        overlay_filters = []
        current_filter = f"[0:v]"
        
        for i, (text_clip_path, start_offset) in enumerate(text_clips):
            input_label = f"[{i+1}:v]"
            output_label = f"[v{i}]" if i < len(text_clips) - 1 else "[v]"
            
            overlay_filters.append(f"{current_filter}{input_label}overlay=shortest=1:enable='between(t,{start_offset},{start_offset + duration_per_text})'{output_label}")
            current_filter = output_label
        
        if not overlay_filters:
            # No text, just use background
            overlay_filters = ["[0:v]copy[v]"]
        
        filter_complex = ";".join(overlay_filters)
        
        # Build input files array
        inputs = ["-i", str(processed_bg)]
        for text_clip_path, _ in text_clips:
            inputs.extend(["-i", str(text_clip_path)])
        
        # Final render command
        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-b:v", CONFIG["video_bitrate"],
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-r", str(CONFIG["fps"]),
        ]
        
        # Add audio if available
        if music_path and Path(music_path).exists():
            # Check music duration and loop if needed
            audio_probe = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", music_path]
            audio_result = subprocess.run(audio_probe, capture_output=True, text=True)
            audio_duration = float(audio_result.stdout.strip())
            
            if audio_duration < total_duration:
                # Loop audio
                loops = int(total_duration / audio_duration) + 1
                audio_concat = temp_dir / "audio_concat.txt"
                with open(audio_concat, "w") as f:
                    for _ in range(loops):
                        f.write(f"file '{music_path}'\n")
                
                looped_audio = temp_dir / "looped_audio.m4a"
                loop_cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat", "-safe", "0", "-i", str(audio_concat),
                    "-c", "copy", "-t", str(total_duration),
                    str(looped_audio)
                ]
                subprocess.run(loop_cmd, capture_output=True, check=True)
                music_path = str(looped_audio)
            
            cmd.extend(["-i", music_path, "-c:a", "aac", "-b:a", CONFIG["audio_bitrate"], "-shortest"])
            cmd.append(str(output_path))
        else:
            cmd.append("-an")  # No audio
            cmd.append(str(output_path))
        
        # Execute render
        logger.info(f"Rendering with FFmpeg...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise RuntimeError(f"FFmpeg render failed: {result.stderr}")
        
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        logger.info(f"Video rendered: {output_path} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")
        return str(output_path)
    
    def _get_font_path(self) -> str:
        """Get path to system font"""
        font_names = [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:\\Windows\\Fonts\\Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ]
        
        for font in font_names:
            if Path(font).exists():
                return font
        
        return "Arial"  # Fallback to system default


# ============ MAIN FUNCTION ============
def main():
    """Entry point for n8n integration"""
    
    # Read input
    if len(sys.argv) > 1:
        try:
            input_data = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            input_data = json.loads(sys.stdin.read())
    else:
        input_data = json.loads(sys.stdin.read())
    
    result = {
        "status": "error",
        "error_message": "Unknown error",
        "row_id": input_data.get("id", "unknown")
    }
    
    try:
        row_id = input_data.get("id")
        template = input_data.get("template", "motivational")
        
        # Extract texts
        texts = []
        for i in range(1, 6):
            text = input_data.get(f"text_{i}", "")
            if text and text.strip():
                texts.append(text.strip())
        
        if not texts:
            raise ValueError("No text content provided")
        
        asset_keyword = input_data.get("asset_keyword", "nature beautiful")
        music_mood = input_data.get("music_mood", "ambient")
        
        logger.info(f"Starting render for row {row_id}")
        logger.info(f"  Template: {template}")
        logger.info(f"  Texts: {len(texts)} lines")
        logger.info(f"  Keyword: {asset_keyword}")
        logger.info(f"  Music mood: {music_mood}")
        
        # Fetch assets
        fetcher = AssetFetcher()
        
        # Get background video
        video_path = fetcher.search_video(asset_keyword)
        if not video_path:
            fallback_video = CONFIG["assets_dir"] / "videos" / "fallback.mp4"
            if fallback_video.exists():
                video_path = str(fallback_video)
                logger.warning(f"Using fallback video")
            else:
                # Create black background on the fly
                video_path = str(CONFIG["temp_dir"] / "black_bg.mp4")
                subprocess.run([
                    "ffmpeg", "-y", "-f", "lavfi", "-i", 
                    f"color=c=black:s={CONFIG['output_size'][0]}x{CONFIG['output_size'][1]}:d=60",
                    "-c:v", "libx264", "-t", "60", video_path
                ], capture_output=True)
        
        # Get background music
        music_path = fetcher.search_music(music_mood)
        if not music_path:
            fallback_music = CONFIG["assets_dir"] / "music" / "fallback.mp3"
            if fallback_music.exists():
                music_path = str(fallback_music)
                logger.warning(f"Using fallback music")
        
        # Render video
        renderer = VideoRenderer(template)
        output_path = renderer.render_with_ffmpeg(
            texts=texts,
            background_path=video_path,
            music_path=music_path
        )
        
        # Cleanup temp assets
        fetcher.cleanup()
        
        # Prepare success result
        preview_url = f"{os.getenv('PREVIEW_BASE_URL', 'http://localhost:8080')}/{Path(output_path).name}"
        
        result = {
            "status": "success",
            "video_path": output_path,
            "preview_url": preview_url,
            "row_id": row_id,
            "duration": len(texts) * TEMPLATES.get(template, TEMPLATES["motivational"])["duration_per_text"]
        }
        
        logger.info(f"Render complete: {output_path}")
        
    except Exception as e:
        logger.exception("Render failed")
        result["error_message"] = str(e)
        result["status"] = "error"
    
    # Output JSON for n8n
    print(json.dumps(result))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
