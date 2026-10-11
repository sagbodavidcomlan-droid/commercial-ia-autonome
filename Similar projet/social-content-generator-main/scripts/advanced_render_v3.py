#!/usr/bin/env python3
"""
Advanced Video Render Engine V3 - Complete Integration
Features:
- Music search (YouTube/SoundCloud)
- Multiple audio tracks (background + outro)
- Beat detection for text sync
- All previous features (zodiac, animations, etc.)
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
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
load_dotenv()

# Import modules
from music_search import MusicSearchEngine
from multi_track_audio import MultiTrackAudioMixer, AudioTrack, TrackType
from beat_detector import BeatDetector, BeatInfo

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
for dir_path in CONFIG.values():
    if isinstance(dir_path, Path):
        dir_path.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AdvancedVideoRendererV3:
    """Complete video renderer with all features"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.music_search = MusicSearchEngine()
        self.beat_detector = BeatDetector()
    
    def render(self, request: Dict) -> Dict:
        """
        Main render method with full feature support
        
        Request format:
        {
            "id": "row_id",
            "texts": ["text1", "text2", ...],
            "template": "motivational",
            "zodiac_sign": "leo",  # optional
            "background": "path_or_keyword",
            
            # Music options
            "music": {
                "source": "youtube_search",  # or "soundcloud_search", "url", "local"
                "query": "lofi hip hop beats",  # for search
                "url": "https://...",  # for direct URL
                "mode": "background",  # background, full, trim
                "volume": 0.5,
                "fade_in": 2,
                "fade_out": 3
            },
            
            # Multi-track options
            "outro_music": {
                "source": "local",
                "path": "assets/music/outro.mp3",
                "duration": 8
            },
            "sound_effects": [
                {"path": "ding.mp3", "time": 5, "volume": 0.7}
            ],
            
            # Beat sync options
            "beat_sync": {
                "enabled": true,
                "use_madmom": false  # slower but more accurate
            },
            
            # Text effects
            "animation": "fade",
            "text_effect": "shadow",
            "transition": "center",
            "scrolling": false,
            
            # Watermark & Logo
            "watermark": {"text": "♌ LEO", "position": "bottom_center"},
            "logo": {"text": "@zodiac", "position": "top_right"}
        }
        """
        
        try:
            # Extract texts
            texts = request.get("texts", [])
            if not texts:
                raise ValueError("No text content provided")
            
            # Get background video
            background_path = self._get_background(request.get("background", "nature"))
            if not background_path:
                background_path = str(CONFIG["assets_dir"] / "videos" / "fallback.mp4")
            
            # Calculate video duration
            duration_per_text = self.config.get("duration_per_text", 5)
            video_duration = min(len(texts) * duration_per_text, 60)
            
            # Process music (may download from YouTube/SoundCloud)
            music_config = request.get("music", {})
            main_music_path = self._process_music_source(music_config, video_duration)
            
            # Create multi-track audio mixer
            mixer = MultiTrackAudioMixer(video_duration)
            
            # Add main music
            if main_music_path:
                mode = music_config.get("mode", "background")
                volume = music_config.get("volume", 0.5 if mode == "background" else 0.8)
                mixer.add_background_music(
                    main_music_path, 
                    volume=volume,
                    fade_in=music_config.get("fade_in", 2),
                    fade_out=music_config.get("fade_out", 3)
                )
            
            # Add outro music if provided
            outro_config = request.get("outro_music")
            if outro_config:
                outro_path = self._resolve_music_source(outro_config)
                if outro_path:
                    mixer.add_outro_music(
                        outro_path,
                        duration=outro_config.get("duration", 8),
                        fade_in=outro_config.get("fade_in", 1),
                        fade_out=outro_config.get("fade_out", 2)
                    )
            
            # Add sound effects
            for sfx in request.get("sound_effects", []):
                sfx_path = self._resolve_local_audio(sfx.get("path"))
                if sfx_path:
                    mixer.add_sound_effect(
                        sfx_path,
                        start_time=sfx.get("time", 0),
                        volume=sfx.get("volume", 0.7)
                    )
            
            # Mix all audio tracks
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mixed_audio = CONFIG["temp_dir"] / f"mixed_audio_{timestamp}.m4a"
            mixed_audio_path = mixer.mix(str(mixed_audio))
            
            # Detect beats for text sync
            beat_info = None
            if request.get("beat_sync", {}).get("enabled") and mixed_audio_path:
                use_madmom = request.get("beat_sync", {}).get("use_madmom", False)
                beat_info = self.beat_detector.detect_bpm(mixed_audio_path, use_madmom)
                
                if beat_info:
                    # Generate beat-synced text timings
                    timings = self.beat_detector.get_beat_sync_timings(beat_info, len(texts), video_duration)
                    logger.info(f"Beat sync enabled: {beat_info.bpm:.1f} BPM")
                else:
                    timings = None
            
            # Render video with text overlays
            output_path = CONFIG["output_dir"] / f"video_{timestamp}.mp4"
            video_path = self._render_video(
                texts=texts,
                background_path=background_path,
                audio_path=mixed_audio_path,
                output_path=output_path,
                duration=video_duration,
                beat_info=beat_info,
                request=request
            )
            
            # Cleanup
            mixer.cleanup()
            self.beat_detector.cleanup()
            
            return {
                "status": "success",
                "video_path": video_path,
                "preview_url": f"http://localhost:8080/{Path(video_path).name}",
                "duration": video_duration,
                "beat_sync_used": beat_info is not None,
                "bpm": beat_info.bpm if beat_info else None
            }
            
        except Exception as e:
            logger.exception("Render failed")
            return {
                "status": "error",
                "error_message": str(e),
                "row_id": request.get("id", "unknown")
            }
    
    def _process_music_source(self, config: Dict, video_duration: int) -> Optional[str]:
        """Process music from various sources"""
        if not config:
            return None
        
        source_type = config.get("source", "")
        
        if source_type == "youtube_search":
            # Search and download first result
            results = self.music_search.search_youtube(config.get("query", ""), limit=1)
            if results:
                return self.music_search.download_youtube_audio(results[0]["url"])
        
        elif source_type == "soundcloud_search":
            results = self.music_search.search_soundcloud(config.get("query", ""), limit=1)
            if results:
                return self.music_search.download_soundcloud_audio(results[0]["url"])
        
        elif source_type == "url":
            url = config.get("url", "")
            if "youtube.com" in url or "youtu.be" in url:
                return self.music_search.download_youtube_audio(url)
            elif "soundcloud.com" in url:
                return self.music_search.download_soundcloud_audio(url)
        
        elif source_type == "local":
            return self._resolve_local_audio(config.get("path", ""))
        
        # If no search/URL, treat as direct path or filename
        return self._resolve_local_audio(source_type)
    
    def _resolve_music_source(self, config: Dict) -> Optional[str]:
        """Resolve music source to file path"""
        if not config:
            return None
        
        source_type = config.get("source", "local")
        
        if source_type == "local":
            return self._resolve_local_audio(config.get("path", ""))
        elif source_type == "url":
            url = config.get("url", "")
            if "youtube.com" in url:
                return self.music_search.download_youtube_audio(url)
            else:
                return self.music_search.download_soundcloud_audio(url)
        
        return self._resolve_local_audio(source_type)
    
    def _resolve_local_audio(self, path_or_name: str) -> Optional[str]:
        """Resolve local audio file path"""
        if not path_or_name:
            return None
        
        # Check if absolute path exists
        if Path(path_or_name).exists():
            return str(path_or_name)
        
        # Check in music directory
        music_path = CONFIG["music_dir"] / path_or_name
        if music_path.exists():
            return str(music_path)
        
        # Try with extensions
        for ext in ['.mp3', '.m4a', '.wav', '.ogg']:
            test_path = CONFIG["music_dir"] / f"{path_or_name}{ext}"
            if test_path.exists():
                return str(test_path)
        
        return None
    
    def _get_background(self, source: str) -> Optional[str]:
        """Get background video from keyword or path"""
        # Check if it's a file path
        if Path(source).exists():
            return str(source)
        
        # Check assets folder
        video_path = CONFIG["assets_dir"] / "videos" / f"{source}.mp4"
        if video_path.exists():
            return str(video_path)
        
        # For now, return None to use fallback
        # In production, this would search Pexels/Pixabay
        return None
    
    def _render_video(
        self,
        texts: List[str],
        background_path: str,
        audio_path: Optional[str],
        output_path: Path,
        duration: int,
        beat_info: Optional[BeatInfo] = None,
        request: Dict = None
    ) -> str:
        """Core video rendering with FFmpeg"""
        
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Process background
            processed_bg = self._process_background(background_path, duration, temp_dir)
            
            # Build text overlay filters
            text_filters = self._build_text_filters(
                texts, duration, temp_dir, beat_info, request
            )
            
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
            if audio_path and Path(audio_path).exists():
                cmd.extend(["-i", audio_path])
                cmd.extend(["-c:a", "aac", "-b:a", "192k", "-shortest"])
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
        
        return {"path": str(processed), "filter": ""}
    
    def _build_text_filters(
        self,
        texts: List[str],
        duration: int,
        temp_dir: Path,
        beat_info: Optional[BeatInfo],
        request: Dict
    ) -> List[str]:
        """Build text overlays with effects and optional beat sync"""
        filters = []
        
        # Get timing method
        if beat_info and request.get("beat_sync", {}).get("enabled"):
            timings = self.beat_detector.get_beat_sync_timings(beat_info, len(texts), duration)
        else:
            # Even distribution
            duration_per_text = duration / len(texts) if texts else 5
            timings = [
                {"start": i * duration_per_text, "end": (i + 1) * duration_per_text}
                for i in range(len(texts))
            ]
        
        # Get text effects
        animation = request.get("animation", "fade")
        text_effect = request.get("text_effect", "shadow")
        
        for i, text in enumerate(texts):
            if not text.strip():
                continue
            
            timing = timings[i] if i < len(timings) else {"start": 0, "end": duration}
            escaped_text = text.replace("'", "\\'").replace(":", "\\:")
            
            # Build filter with animation
            filter_parts = [
                f"drawtext=text='{escaped_text}'",
                f"fontfile=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                f"fontsize=48",
                f"fontcolor=white",
                f"x=(w-text_w)/2",
                f"y=(h-text_h)/2",
                f"enable='between(t,{timing['start']},{timing['end']})'"
            ]
            
            # Add text effect
            if text_effect == "shadow":
                filter_parts.append("shadowcolor=black@0.5:shadowx=3:shadowy=3")
            elif text_effect == "box":
                filter_parts.append("box=1:boxcolor=black@0.5:boxborderw=10")
            
            # Add border
            filter_parts.append("bordercolor=black:borderw=2")
            
            # Add animation
            if animation == "fade":
                alpha_expr = f"if(lt(t-{timing['start']},0.5), (t-{timing['start']})/0.5, if(gt({timing['end']}-t,0.5), 1, ({timing['end']}-t)/0.5))"
                filter_parts.append(f"alpha='{alpha_expr}'")
            
            filters.append(":".join(filter_parts))
        
        # Add watermark if configured
        watermark = request.get("watermark")
        if watermark and watermark.get("text"):
            pos = watermark.get("position", "bottom_center")
            x, y = self._get_position_coords(pos)
            
            filter_parts = [
                f"drawtext=text='{watermark['text']}'",
                f"fontsize=24",
                f"fontcolor={watermark.get('color', 'white')}",
                f"x={x}",
                f"y={y}",
                "shadowcolor=black@0.5:shadowx=1:shadowy=1"
            ]
            filters.append(":".join(filter_parts))
        
        # Add logo if configured
        logo = request.get("logo")
        if logo and logo.get("text"):
            pos = logo.get("position", "top_right")
            x, y = self._get_position_coords(pos)
            
            filter_parts = [
                f"drawtext=text='{logo['text']}'",
                f"fontsize=20",
                f"fontcolor={logo.get('color', '#FFD700')}",
                f"x={x}",
                f"y={y}"
            ]
            filters.append(":".join(filter_parts))
        
        return filters
    
    def _get_position_coords(self, position: str) -> Tuple[str, str]:
        """Get FFmpeg coordinates for position name"""
        positions = {
            "top_left": ("50", "50"),
            "top_right": ("w-text_w-50", "50"),
            "top_center": ("(w-text_w)/2", "50"),
            "bottom_left": ("50", "h-text_h-50"),
            "bottom_right": ("w-text_w-50", "h-text_h-50"),
            "bottom_center": ("(w-text_w)/2", "h-text_h-50"),
            "center": ("(w-text_w)/2", "(h-text_h)/2")
        }
        return positions.get(position, positions["center"])


# ============ MAIN FUNCTION ============
def main():
    """Entry point"""
    
    if len(sys.argv) > 1:
        request = json.loads(sys.argv[1])
    else:
        request = json.loads(sys.stdin.read())
    
    # Convert old format to new format
    if "text_1" in request:
        texts = []
        for i in range(1, 6):
            text = request.get(f"text_{i}", "")
            if text:
                texts.append(text)
        request["texts"] = texts
    
    renderer = AdvancedVideoRendererV3()
    result = renderer.render(request)
    
    result["row_id"] = request.get("id", "unknown")
    print(json.dumps(result))
    
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
