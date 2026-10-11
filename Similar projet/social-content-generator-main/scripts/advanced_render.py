#!/usr/bin/env python3
"""
Advanced Video Render Engine with All Features:
- 12 zodiac templates
- Fade in/out, Zoom fan, Rainbow, Blur effects
- Scrolling text (left/right/bottom/center)
- Text watermark (zodiac name in center)
- Logo text (username sosmed in any corner)
- Font selection
- Shadow/Blink/Box text effects
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
from zodiac_templates import ZODIAC_TEMPLATES, VIDEO_EFFECTS, TEXT_ANIMATIONS, get_zodiac_template

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Configuration
CONFIG = {
    "output_size": (1080, 1920),
    "fps": 30,
    "video_bitrate": "4000k",
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AdvancedVideoRenderer:
    """Advanced video renderer with all requested features"""
    
    def __init__(self, template_name: str, zodiac_sign: str = None, config: dict = None):
        """
        Initialize renderer with template and optional overrides
        
        Args:
            template_name: Base template (motivational, educational, tips)
            zodiac_sign: Zodiac sign (aries, taurus, etc.)
            config: Optional override config
        """
        self.base_template = template_name
        
        # Load zodiac config if provided
        if zodiac_sign:
            self.zodiac_config = get_zodiac_template(zodiac_sign)
            self.zodiac_name = self.zodiac_config["name"]
            logger.info(f"Using zodiac template: {self.zodiac_name}")
        else:
            self.zodiac_config = None
            self.zodiac_name = None
        
        # Merge configurations
        self.config = self._merge_configs(config or {})
    
    def _merge_configs(self, overrides: dict) -> dict:
        """Merge base template with zodiac and overrides"""
        base_config = {
            "font": "Arial-Bold",
            "font_size": 48,
            "text_color": "#FFFFFF",
            "stroke_color": "#000000",
            "stroke_width": 2,
            "bg_opacity": 0.5,
            "bg_color": "#000000",
            "duration_per_text": 5,
            "animation": "fade",
            "text_effect": "shadow",
            "transition": "center",
            "scrolling": False,
            "scrolling_direction": "left",
            "scrolling_speed": 50,
            "watermark": {
                "enabled": False,
                "text": "",
                "position": "center",
                "font_size": 24
            },
            "logo": {
                "enabled": False,
                "text": "",
                "position": "top_right",
                "font_size": 20
            }
        }
        
        # Apply zodiac overrides if available
        if self.zodiac_config:
            base_config.update({
                "text_color": self.zodiac_config.get("color_primary", "#FFFFFF"),
                "bg_color": self.zodiac_config.get("color_bg", "#000000"),
                "font": self.zodiac_config.get("font", "Arial-Bold"),
                "animation": self.zodiac_config.get("animation", "fade"),
                "text_effect": self.zodiac_config.get("text_effect", "shadow"),
                "transition": self.zodiac_config.get("transition", "center"),
            })
        
        # Apply user overrides
        base_config.update(overrides)
        
        return base_config
    
    def _escape_ffmpeg_text(self, text: str) -> str:
        """Escape text for FFmpeg drawtext filter"""
        # Escape special characters
        escapes = {
            "'": "\\'",
            ":": "\\:",
            "\\": "\\\\",
            "%": "\\\\%",
            "=": "\\=",
            ";": "\\;",
        }
        for char, esc in escapes.items():
            text = text.replace(char, esc)
        return text
    
    def _build_drawtext_filter(
        self,
        text: str,
        index: int,
        start_time: float,
        duration: float,
        x: str = "(w-text_w)/2",
        y: str = "(h-text_h)/2"
    ) -> str:
        """Build FFmpeg drawtext filter with all effects"""
        
        escaped_text = self._escape_ffmpeg_text(text)
        font_path = self._get_font_path()
        font_size = self.config["font_size"]
        text_color = self.config["text_color"]
        stroke_color = self.config["stroke_color"]
        stroke_width = self.config["stroke_width"]
        bg_color = self.config["bg_color"]
        bg_opacity = self.config["bg_opacity"]
        
        # Start with basic drawtext
        filter_parts = [
            f"drawtext=text='{escaped_text}'",
            f"fontfile={font_path}",
            f"fontsize={font_size}",
            f"fontcolor={text_color}",
            f"x={x}",
            f"y={y}",
            f"enable='between(t,{start_time},{start_time + duration})'"
        ]
        
        # Add text effects
        if self.config["text_effect"] == "shadow":
            filter_parts.append(f"shadowcolor=black@0.5:shadowx=3:shadowy=3")
        elif self.config["text_effect"] == "blink":
            filter_parts.append(f"alpha='if(mod(t*2,1),1,0.3)'")
        elif self.config["text_effect"] == "box":
            filter_parts.append(f"box=1:boxcolor={bg_color}@{bg_opacity}:boxborderw=15")
        elif self.config["text_effect"] == "rainbow":
            # Rainbow effect via gradient (simplified)
            filter_parts.append(f"fontcolor_expr='if(lt(mod(t,1),0.5),red,blue)'")
        
        # Add border if not using box
        if self.config["text_effect"] != "box":
            filter_parts.append(f"bordercolor={stroke_color}:borderw={stroke_width}")
        
        # Scrolling text animation
        if self.config.get("scrolling", False):
            direction = self.config["scrolling_direction"]
            speed = self.config["scrolling_speed"]
            total_width = 1920  # Screen width
            text_width = f"text_w"
            
            if direction == "left":
                scroll_x = f"if(lt(t,{start_time + 0.5}), w, w - (t-{start_time})*{speed})"
                filter_parts.append(f"x='{scroll_x}'")
            elif direction == "right":
                scroll_x = f"if(lt(t,{start_time + 0.5}), -text_w, -text_w + (t-{start_time})*{speed})"
                filter_parts.append(f"x='{scroll_x}'")
            elif direction == "up":
                scroll_y = f"if(lt(t,{start_time + 0.5}), h, h - (t-{start_time})*{speed})"
                filter_parts.append(f"y='{scroll_y}'")
            elif direction == "down":
                scroll_y = f"if(lt(t,{start_time + 0.5}), -text_h, -text_h + (t-{start_time})*{speed})"
                filter_parts.append(f"y='{scroll_y}'")
        
        # Add animation effect
        if self.config["animation"] == "fade":
            filter_parts.append(f"alpha='if(lt(t-{start_time},0.5), (t-{start_time})/0.5, if(gt({start_time + duration}-t,0.5), 1, ({start_time + duration}-t)/0.5))'")
        elif self.config["animation"] == "zoom_fan":
            filter_parts.append(f"fontsize='{font_size} * if(lt(t-{start_time},0.5), 0.5 + (t-{start_time}), 1)'")
        elif self.config["animation"] == "blur":
            filter_parts.append(f"blur=if(lt(t-{start_time},0.5), 20*(1-(t-{start_time})/0.5), 0)")
        
        return ":".join(filter_parts)
    
    def _get_font_path(self) -> str:
        """Get path to selected font"""
        font_map = {
            "Arial-Bold": "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "Georgia-Bold": "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
            "Times-Bold": "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
            "Courier-Bold": "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
            "Helvetica-Bold": "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        }
        
        font_name = self.config["font"]
        font_path = font_map.get(font_name)
        
        if font_path and Path(font_path).exists():
            return font_path
        
        # Try to find any font
        common_fonts = [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:\\Windows\\Fonts\\Arial.ttf",
        ]
        for font in common_fonts:
            if Path(font).exists():
                return font
        
        return "Arial"
    
    def _get_position_coords(self, position: str) -> Tuple[str, str]:
        """Convert position name to FFmpeg x,y coordinates"""
        positions = {
            "center": ("(w-text_w)/2", "(h-text_h)/2"),
            "top_left": ("50", "50"),
            "top_right": ("w-text_w-50", "50"),
            "bottom_left": ("50", "h-text_h-50"),
            "bottom_right": ("w-text_w-50", "h-text_h-50"),
            "top_center": ("(w-text_w)/2", "100"),
            "bottom_center": ("(w-text_w)/2", "h-text_h-150"),
        }
        return positions.get(position, positions["center"])
    
    def render(
        self,
        texts: List[str],
        background_path: str,
        music_path: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> str:
        """Render final video with all features"""
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = CONFIG["output_dir"] / f"video_{timestamp}.mp4"
        
        output_path = Path(output_path)
        duration_per_text = self.config["duration_per_text"]
        total_duration = min(len(texts) * duration_per_text, 60)
        
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Build all drawtext filters
            text_filters = []
            current_time = 0
            
            for i, text in enumerate(texts):
                if not text or not text.strip():
                    current_time += duration_per_text
                    continue
                
                # Main text position
                x_main, y_main = self._get_position_coords("center")
                text_filter = self._build_drawtext_filter(
                    text, i, current_time, duration_per_text,
                    x_main, y_main
                )
                text_filters.append(text_filter)
                
                # Add watermark (zodiac name in center, subtle)
                if self.config["watermark"]["enabled"]:
                    watermark_x, watermark_y = self._get_position_coords(
                        self.config["watermark"]["position"]
                    )
                    watermark_filter = self._build_drawtext_filter(
                        self.config["watermark"]["text"],
                        i + 100,
                        current_time,
                        duration_per_text,
                        watermark_x,
                        watermark_y
                    )
                    # Override font size for watermark
                    watermark_filter = watermark_filter.replace(
                        f"fontsize={self.config['font_size']}",
                        f"fontsize={self.config['watermark']['font_size']}"
                    )
                    text_filters.append(watermark_filter)
                
                # Add logo (username sosmed)
                if self.config["logo"]["enabled"]:
                    logo_x, logo_y = self._get_position_coords(
                        self.config["logo"]["position"]
                    )
                    logo_filter = self._build_drawtext_filter(
                        self.config["logo"]["text"],
                        i + 200,
                        current_time,
                        duration_per_text,
                        logo_x,
                        logo_y
                    )
                    logo_filter = logo_filter.replace(
                        f"fontsize={self.config['font_size']}",
                        f"fontsize={self.config['logo']['font_size']}"
                    )
                    text_filters.append(logo_filter)
                
                current_time += duration_per_text
            
            # Process background video
            processed_bg = self._process_background(background_path, total_duration, temp_dir)
            
            # Build final FFmpeg command
            filter_complex = f"[0:v]{processed_bg['filter']}"
            
            # Add video effect (zoom, blur, rainbow)
            video_effect = self.config.get("video_effect", "fade")
            if video_effect in VIDEO_EFFECTS:
                effect = VIDEO_EFFECTS[video_effect]
                if effect["in_filter"]:
                    filter_complex += f",{effect['in_filter']}"
            
            # Add all text overlays
            for i, text_filter in enumerate(text_filters):
                filter_complex += f",{text_filter}"
            
            filter_complex += "[v]"
            
            # Build command
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
                processed_audio = self._process_audio(music_path, total_duration, temp_dir)
                cmd.extend(["-i", processed_audio])
                cmd.extend(["-c:a", "aac", "-b:a", CONFIG["audio_bitrate"], "-shortest"])
            
            cmd.append(str(output_path))
            
            # Execute render
            logger.info(f"Rendering with FFmpeg...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                raise RuntimeError(f"Render failed: {result.stderr[:500]}")
            
            logger.info(f"Video rendered: {output_path}")
            return str(output_path)
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _process_background(self, bg_path: str, duration: int, temp_dir: Path) -> dict:
        """Process background video (loop, resize)"""
        output_path = temp_dir / "background.mp4"
        
        # Get background duration
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", bg_path],
            capture_output=True, text=True
        )
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
        
        # Resize and apply transition effect
        transition = self.config.get("transition", "center")
        filter_str = f"scale={CONFIG['output_size'][0]}:{CONFIG['output_size'][1]}:force_original_aspect_ratio=1,pad={CONFIG['output_size'][0]}:{CONFIG['output_size'][1]}:(ow-iw)/2:(oh-ih)/2"
        
        if transition == "center":
            filter_str += ",fade=t=in:st=0:d=1,fade=t=out:st={duration-1}:d=1"
        elif transition == "left":
            filter_str = f"crop=iw:ih:0:0,setpts=PTS,fade=t=in:st=0:d=1"
        elif transition == "right":
            filter_str = f"crop=iw:ih:iw*0.1:0,setpts=PTS,fade=t=in:st=0:d=1"
        elif transition == "bottom":
            filter_str = f"crop=iw:ih:0:ih*0.1,setpts=PTS,fade=t=in:st=0:d=1"
        
        processed = temp_dir / "processed_bg.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(output_path),
            "-vf", filter_str.format(duration=duration),
            "-c:v", "libx264", "-preset", "fast",
            str(processed)
        ], capture_output=True, check=True)
        
        return {"path": str(processed), "filter": ""}
    
    def _process_audio(self, audio_path: str, duration: int, temp_dir: Path) -> str:
        """Process audio (loop, trim, normalize)"""
        output_path = temp_dir / "audio_processed.m4a"
        
        # Get audio duration
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True
        )
        audio_duration = float(probe.stdout.strip())
        
        if audio_duration < duration:
            # Loop audio
            concat_file = temp_dir / "audio_concat.txt"
            loops = int(duration / audio_duration) + 1
            with open(concat_file, "w") as f:
                for _ in range(loops):
                    f.write(f"file '{audio_path}'\n")
            
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_file), "-c", "copy", "-t", str(duration),
                str(output_path)
            ], capture_output=True, check=True)
        else:
            subprocess.run([
                "ffmpeg", "-y", "-i", audio_path, "-t", str(duration),
                "-c", "copy", str(output_path)
            ], capture_output=True, check=True)
        
        # Normalize volume
        normalized = temp_dir / "audio_normalized.m4a"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(output_path),
            "-af", "volume=0.3,loudnorm=I=-16:LRA=11:TP=-1.5",
            "-c:a", "aac", str(normalized)
        ], capture_output=True, check=True)
        
        return str(normalized)


# ============ MAIN FUNCTION ============
def main():
    """Entry point with support for all features"""
    
    if len(sys.argv) > 1:
        input_data = json.loads(sys.argv[1])
    else:
        input_data = json.loads(sys.stdin.read())
    
    try:
        # Parse input
        template = input_data.get("template", "motivational")
        zodiac_sign = input_data.get("zodiac_sign", None)
        
        # Extract texts
        texts = [input_data.get(f"text_{i}", "") for i in range(1, 6)]
        texts = [t.strip() for t in texts if t and t.strip()]
        
        if not texts:
            raise ValueError("No text content provided")
        
        # Build custom config from input
        custom_config = {
            "duration_per_text": input_data.get("duration_per_text", 5),
            "animation": input_data.get("animation", "fade"),
            "text_effect": input_data.get("text_effect", "shadow"),
            "transition": input_data.get("transition", "center"),
            "video_effect": input_data.get("video_effect", "fade"),
            "scrolling": input_data.get("scrolling", False),
            "scrolling_direction": input_data.get("scrolling_direction", "left"),
        }
        
        # Watermark config
        if input_data.get("watermark_enabled", False):
            custom_config["watermark"] = {
                "enabled": True,
                "text": input_data.get("watermark_text", zodiac_sign or ""),
                "position": input_data.get("watermark_position", "center"),
                "font_size": input_data.get("watermark_font_size", 24)
            }
        
        # Logo config
        if input_data.get("logo_enabled", False):
            custom_config["logo"] = {
                "enabled": True,
                "text": input_data.get("logo_text", "@username"),
                "position": input_data.get("logo_position", "top_right"),
                "font_size": input_data.get("logo_font_size", 20)
            }
        
        # Font config
        if input_data.get("font"):
            custom_config["font"] = input_data.get("font")
        if input_data.get("font_size"):
            custom_config["font_size"] = input_data.get("font_size")
        if input_data.get("text_color"):
            custom_config["text_color"] = input_data.get("text_color")
        
        # Initialize renderer
        renderer = AdvancedVideoRenderer(
            template_name=template,
            zodiac_sign=zodiac_sign,
            config=custom_config
        )
        
        # Get assets (simplified - use fallback for demo)
        background_path = input_data.get("background_path", str(CONFIG["assets_dir"] / "videos" / "fallback.mp4"))
        music_path = input_data.get("music_path", None)
        
        # Render video
        output_path = renderer.render(
            texts=texts,
            background_path=background_path,
            music_path=music_path
        )
        
        # Prepare result
        result = {
            "status": "success",
            "video_path": output_path,
            "preview_url": f"http://localhost:8080/{Path(output_path).name}",
            "row_id": input_data.get("id"),
            "zodiac": renderer.zodiac_name,
            "config_used": custom_config
        }
        
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
