#!/usr/bin/env python3
"""
Advanced Video Render Engine V2 with Music Manager
Includes: Manual music from folder/URL, fade in/out, full music mode
'{"id":"test","text_1":"Hello","music_source":"/path/to/song.mp3","music_mode":"background","music_fade_in":2}'
"""

import os
import sys
import json
import logging
import subprocess
import tempfile
import shutil
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
from typing import Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

# Import modules
from music_manager import MusicManager

# Configuration
CONFIG = {
    "output_size": (1080, 1920),
    "fps": 30,
    "video_bitrate": "4000k",
    "temp_dir": Path("/project/assets_cache"),
    "output_dir": Path("/project/output/videos"),
    "log_dir": Path("/project/output/logs"),
    "assets_dir": Path("/project/assets"),
    "music_dir": Path("/project/assets/music"),
}

# Create directories
for dir_path in [CONFIG["temp_dir"], CONFIG["output_dir"], CONFIG["log_dir"], CONFIG["music_dir"]]:
    dir_path.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AdvancedVideoRendererV2:
    """Video renderer with full music control"""
    
    def __init__(self, template_name: str, config: Dict = None):
        self.template_name = template_name
        self.config = config or {}
        self.music_manager = MusicManager(CONFIG["music_dir"])
    
    def render(
        self,
        texts: List[str],
        background_path: str,
        music_config: Dict = None,
        output_path: Optional[str] = None
    ) -> Dict:
        """
        Render video with music control
        
        Args:
            texts: List of text overlays
            background_path: Path to background video
            music_config: Music configuration with keys:
                - source: Local path, URL, or filename
                - mode: "full", "background", or "trim"
                - fade_in: Fade in seconds
                - fade_out: Fade out seconds
                - volume: Volume multiplier
                - duration: Target duration (auto from video if not specified)
            output_path: Output video path
        
        Returns:
            Dict with render results
        """
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = CONFIG["output_dir"] / f"video_{timestamp}.mp4"
        
        output_path = Path(output_path)
        
        # Calculate video duration from texts
        duration_per_text = self.config.get("duration_per_text", 5)
        video_duration = min(len(texts) * duration_per_text, 60)
        
        # Process music if configured
        processed_music = None
        if music_config and music_config.get("source"):
            music_config["duration"] = music_config.get("duration", video_duration)
            processed_music = self.music_manager.load_music(
                music_config["source"],
                music_config
            )
            logger.info(f"Music processed: {music_config.get('mode', 'background')} mode")
        
        # Build video (simplified - reuse from previous version)
        video_path = self._render_video(
            texts=texts,
            background_path=background_path,
            music_path=processed_music,
            output_path=output_path,
            duration=video_duration
        )
        
        # Cleanup music temp files
        self.music_manager.cleanup()
        
        return {
            "status": "success",
            "video_path": video_path,
            "preview_url": f"http://localhost:8080/{Path(video_path).name}",
            "duration": video_duration,
            "music_used": processed_music is not None,
            "music_mode": music_config.get("mode") if music_config else None
        }
    
    def _render_video(
        self,
        texts: List[str],
        background_path: str,
        music_path: Optional[str],
        output_path: Path,
        duration: int
    ) -> str:
        """Core video rendering with FFmpeg"""
        
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Process background
            processed_bg = self._process_background(background_path, duration, temp_dir)
            
            # Build text overlay filters
            text_filters = self._build_text_filters(texts, duration, temp_dir)
            
            # Build FFmpeg command
            filter_complex = f"[0:v]{processed_bg['filter']}"
            for text_filter in text_filters:
                filter_complex += f",{text_filter}"
            filter_complex += "[v]"
            
            cmd = [
                "ffmpeg", "-y",
                "-i", processed_bg["path"],
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-b:v", CONFIG["video_bitrate"],
                "-pix_fmt", "yuv420p",
                "-r", str(CONFIG["fps"]),
            ]
            
            # Add audio if provided
            if music_path and Path(music_path).exists():
                cmd.extend(["-i", music_path])
                cmd.extend(["-c:a", "aac", "-b:a", "128k", "-shortest"])
            else:
                cmd.append("-an")
            
            cmd.append(str(output_path))
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg error: {result.stderr[:500]}")
            
            return str(output_path)
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _process_background(self, bg_path: str, duration: int, temp_dir: Path) -> Dict:
        """Process background video"""
        output_path = temp_dir / "background.mp4"
        
        # Get background duration
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", bg_path
        ], capture_output=True, text=True)
        bg_duration = float(probe.stdout.strip())
        
        if bg_duration < duration:
            # Loop with concat
            concat_file = temp_dir / "concat.txt"
            loops = int(duration / bg_duration) + 1
            with open(concat_file, "w") as f:
                for _ in range(loops):
                    f.write(f"file '{bg_path}'\n")
            
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_file), "-c", "copy", "-t", str(duration),
                str(output_path)
            ], capture_output=True, check=True)
        else:
            subprocess.run([
                "ffmpeg", "-y", "-i", bg_path, "-t", str(duration),
                "-c", "copy", str(output_path)
            ], capture_output=True, check=True)
        
        # Resize to vertical
        processed = temp_dir / "processed_bg.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(output_path),
            "-vf", f"scale={CONFIG['output_size'][0]}:{CONFIG['output_size'][1]}:force_original_aspect_ratio=1,pad={CONFIG['output_size'][0]}:{CONFIG['output_size'][1]}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-preset", "fast",
            str(processed)
        ], capture_output=True, check=True)
        
        return {"path": str(processed), "filter": "null"}
    
    def _build_text_filters(self, texts: List[str], duration: int, temp_dir: Path) -> List[str]:
        """Build FFmpeg drawtext filters"""
        filters = []
        duration_per_text = duration / len(texts) if texts else 5
        
        for i, text in enumerate(texts):
            if not text.strip():
                continue
            
            start_time = i * duration_per_text
            escaped_text = text.replace("'", "\\'").replace(":", "\\:")
            
            filter_str = (
                f"drawtext=text='{escaped_text}':fontfile=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf:"
                f"fontsize=48:fontcolor=white:bordercolor=black:borderw=2:"
                f"x=(w-text_w)/2:y=(h-text_h)/2:"
                f"enable='between(t,{start_time},{start_time + duration_per_text})'"
            )
            
            # Add fade animation
            if self.config.get("animation") == "fade":
                filter_str += f":alpha='if(lt(t-{start_time},0.5), (t-{start_time})/0.5, if(gt({start_time + duration_per_text}-t,0.5), 1, ({start_time + duration_per_text}-t)/0.5))'"
            
            filters.append(filter_str)
        
        return filters


# ============ MAIN FUNCTION ============
def main():
    """Entry point with full music control"""
    
    if len(sys.argv) > 1:
        input_data = json.loads(sys.argv[1])
    else:
        input_data = json.loads(sys.stdin.read())
    
    try:
        # Parse inputs
        texts = [input_data.get(f"text_{i}", "") for i in range(1, 6)]
        texts = [t.strip() for t in texts if t and t.strip()]
        
        if not texts:
            raise ValueError("No text content provided")
        
        # Parse music configuration
        music_config = None
        if input_data.get("music_source"):
            music_config = {
                "source": input_data["music_source"],
                "mode": input_data.get("music_mode", "background"),
                "fade_in": float(input_data.get("music_fade_in", 2)),
                "fade_out": float(input_data.get("music_fade_out", 2)),
                "volume": float(input_data.get("music_volume", 0.7)),
                "normalize": input_data.get("music_normalize", True),
                "duration": input_data.get("video_duration", 30)
            }
        
        # Handle manual music upload from form data
        if input_data.get("music_file_b64"):
            # Decode base64 file
            import base64
            music_data = base64.b64decode(input_data["music_file_b64"])
            temp_music = CONFIG["temp_dir"] / "uploaded_music.mp3"
            temp_music.write_bytes(music_data)
            music_config = music_config or {}
            music_config["source"] = str(temp_music)
        
        # Initialize renderer
        renderer = AdvancedVideoRendererV2(
            template_name=input_data.get("template", "motivational"),
            config={
                "duration_per_text": input_data.get("duration_per_text", 5),
                "animation": input_data.get("animation", "fade")
            }
        )
        
        # Get background (fallback for demo)
        background_path = input_data.get(
            "background_path",
            str(CONFIG["assets_dir"] / "videos" / "fallback.mp4")
        )
        
        # Render
        result = renderer.render(
            texts=texts,
            background_path=background_path,
            music_config=music_config
        )
        
        result["row_id"] = input_data.get("id")
        print(json.dumps(result))
        return 0
        
    except Exception as e:
        logger.exception("Render failed")
        result = {
            "status": "error",
            "error_message": str(e),
            "row_id": input_data.get("id", "unknown")
        }
        print(json.dumps(result))
        return 1


if __name__ == "__main__":
    sys.exit(main())
