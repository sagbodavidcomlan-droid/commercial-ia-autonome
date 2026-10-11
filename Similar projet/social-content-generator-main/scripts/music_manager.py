#!/usr/bin/env python3
"""
Music Manager - Handle manual music from folder or URL
Features:
- Load music from local folder
- Download music from URL
- Full music mode vs trimmed mode
- Fade in / fade out effects
- Volume normalization
- Music preview generation
"""

import os
import re
import json
import logging
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)


class MusicManager:
    """Handle music operations: download, fade, normalize, trim"""
    
    # Supported audio formats
    SUPPORTED_FORMATS = ['.mp3', '.m4a', '.wav', '.ogg', '.aac', '.flac']
    
    # Free music APIs for fallback
    FREE_MUSIC_SOURCES = {
        "pixabay": "https://pixabay.com/api/v2/music/search/",
        "freesound": "https://freesound.org/apiv2/search/text/",
    }
    
    def __init__(self, music_dir: Path = None):
        self.music_dir = music_dir or Path("/project/assets/music")
        self.music_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp())
        self.downloaded_files = []
    
    def load_music(self, source: str, config: Dict = None) -> Optional[str]:
        """
        Load music from various sources
        
        Args:
            source: Local path, URL, or filename in music folder
            config: Music configuration with keys:
                - mode: "full" (use entire track) or "trim" (trim to duration)
                - duration: Target duration in seconds (for trim mode)
                - fade_in: Fade in duration in seconds (default 0)
                - fade_out: Fade out duration in seconds (default 0)
                - volume: Volume multiplier (default 0.7 for background)
                - normalize: Whether to normalize volume (default True)
        
        Returns:
            Path to processed audio file
        """
        config = config or {}
        mode = config.get("mode", "background")  # background, full, trim
        target_duration = config.get("duration", 60)
        fade_in = config.get("fade_in", 0)
        fade_out = config.get("fade_out", 0)
        volume = config.get("volume", 0.7)
        normalize = config.get("normalize", True)
        
        # Get original audio file
        audio_path = self._get_audio_file(source)
        if not audio_path:
            logger.error(f"Cannot load music from: {source}")
            return None
        
        # Process based on mode
        if mode == "full":
            return self._process_full_music(audio_path, fade_in, fade_out, volume, normalize)
        elif mode == "background":
            # Background mode: trim to duration, lower volume
            return self._process_background_music(audio_path, target_duration, fade_in, fade_out, volume, normalize)
        elif mode == "trim":
            return self._trim_music(audio_path, target_duration, fade_in, fade_out, volume, normalize)
        else:
            return self._process_full_music(audio_path, fade_in, fade_out, volume, normalize)
    
    def _get_audio_file(self, source: str) -> Optional[str]:
        """Get audio file from local path, folder, or URL"""
        
        # Check if it's a URL
        if source.startswith(('http://', 'https://')):
            return self._download_from_url(source)
        
        # Check if it's a local path
        if Path(source).exists():
            return str(Path(source).absolute())
        
        # Check in music folder
        local_path = self.music_dir / source
        if local_path.exists():
            return str(local_path)
        
        # Try to find by name pattern
        for ext in self.SUPPORTED_FORMATS:
            pattern_path = self.music_dir / f"{source}{ext}"
            if pattern_path.exists():
                return str(pattern_path)
        
        # Search in music folder
        matches = list(self.music_dir.glob(f"*{source}*"))
        for match in matches:
            if match.suffix.lower() in self.SUPPORTED_FORMATS:
                return str(match)
        
        return None
    
    def _download_from_url(self, url: str) -> Optional[str]:
        """Download audio from URL"""
        try:
            # Parse URL to get filename
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path)
            if not filename or '.' not in filename:
                filename = "downloaded_music.mp3"
            
            output_path = self.temp_dir / filename
            
            # Download with progress
            logger.info(f"Downloading music from: {url[:100]}...")
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=32768):
                    f.write(chunk)
            
            self.downloaded_files.append(output_path)
            logger.info(f"Downloaded: {output_path} ({output_path.stat().st_size / 1024:.1f} KB)")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None
    
    def _process_full_music(self, audio_path: str, fade_in: float, fade_out: float, volume: float, normalize: bool) -> str:
        """Process full music track (no trimming)"""
        output_path = self.temp_dir / "full_music_processed.mp3"
        
        # Build audio filters
        filters = []
        
        if normalize:
            filters.append("loudnorm=I=-16:LRA=11:TP=-1.5")
        
        if volume != 1.0:
            filters.append(f"volume={volume}")
        
        if fade_in > 0:
            filters.append(f"afade=t=in:st=0:d={fade_in}")
        
        # Get audio duration for fade out
        duration = self._get_audio_duration(audio_path)
        if fade_out > 0:
            filters.append(f"afade=t=out:st={duration - fade_out}:d={fade_out}")
        
        filter_str = ",".join(filters) if filters else "anull"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-af", filter_str,
            "-c:a", "libmp3lame",
            "-q:a", "2",  # High quality
            str(output_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        logger.info(f"Full music processed: {output_path}")
        return str(output_path)
    
    def _process_background_music(self, audio_path: str, target_duration: int, fade_in: float, fade_out: float, volume: float, normalize: bool) -> str:
        """Process as background music - loop if shorter, trim if longer"""
        output_path = self.temp_dir / "background_music_processed.mp3"
        
        duration = self._get_audio_duration(audio_path)
        
        # Handle looping
        if duration < target_duration:
            # Loop audio to reach target duration
            loops = int(target_duration / duration) + 1
            concat_file = self.temp_dir / "concat_list.txt"
            with open(concat_file, "w") as f:
                for _ in range(loops):
                    f.write(f"file '{audio_path}'\n")
            
            looped_path = self.temp_dir / "looped_audio.m4a"
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_file), "-c", "copy", "-t", str(target_duration),
                str(looped_path)
            ], capture_output=True, check=True)
            audio_path = str(looped_path)
            self.downloaded_files.append(Path(looped_path))
        
        # Build filters
        filters = []
        
        if normalize:
            filters.append("loudnorm=I=-20:LRA=11:TP=-2")  # Quieter for background
        
        if volume != 1.0:
            filters.append(f"volume={volume}")
        
        if fade_in > 0:
            filters.append(f"afade=t=in:st=0:d={fade_in}")
        
        if fade_out > 0:
            filters.append(f"afade=t=out:st={target_duration - fade_out}:d={fade_out}")
        
        filter_str = ",".join(filters) if filters else "anull"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-t", str(target_duration),
            "-af", filter_str,
            "-c:a", "libmp3lame",
            "-q:a", "5",  # Lower quality for background (smaller file)
            str(output_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        logger.info(f"Background music processed: {output_path}")
        return str(output_path)
    
    def _trim_music(self, audio_path: str, duration: int, fade_in: float, fade_out: float, volume: float, normalize: bool) -> str:
        """Trim music to exact duration"""
        output_path = self.temp_dir / "trimmed_music_processed.mp3"
        
        filters = []
        
        if normalize:
            filters.append("loudnorm=I=-16:LRA=11:TP=-1.5")
        
        if volume != 1.0:
            filters.append(f"volume={volume}")
        
        if fade_in > 0:
            filters.append(f"afade=t=in:st=0:d={fade_in}")
        
        if fade_out > 0:
            filters.append(f"afade=t=out:st={duration - fade_out}:d={fade_out}")
        
        filter_str = ",".join(filters) if filters else "anull"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-t", str(duration),
            "-af", filter_str,
            "-c:a", "libmp3lame",
            "-q:a", "2",
            str(output_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        logger.info(f"Trimmed music processed: {output_path}")
        return str(output_path)
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds"""
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    
    def list_available_music(self) -> List[Dict]:
        """List all music files in the music directory"""
        music_files = []
        for ext in self.SUPPORTED_FORMATS:
            for file_path in self.music_dir.glob(f"*{ext}"):
                music_files.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size_kb": file_path.stat().st_size / 1024,
                    "duration": self._get_audio_duration(str(file_path))
                })
        return music_files
    
    def generate_preview(self, audio_path: str, duration: int = 15) -> str:
        """Generate 15-second preview of music"""
        preview_path = self.temp_dir / "preview.mp3"
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-t", str(duration),
            "-af", "volume=0.5",
            "-c:a", "libmp3lame",
            "-q:a", "8",
            str(preview_path)
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return str(preview_path)
    
    def cleanup(self):
        """Delete temporary files"""
        for file_path in self.downloaded_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass
        
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass


# ============ COMMAND LINE TOOL ============
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Music Manager for Video Generation")
    parser.add_argument("command", choices=["list", "info", "preview", "process"])
    parser.add_argument("--source", help="Music file path or URL")
    parser.add_argument("--mode", default="background", choices=["full", "background", "trim"])
    parser.add_argument("--duration", type=int, default=30, help="Target duration in seconds")
    parser.add_argument("--fade-in", type=float, default=2, help="Fade in duration (seconds)")
    parser.add_argument("--fade-out", type=float, default=2, help="Fade out duration (seconds)")
    parser.add_argument("--volume", type=float, default=0.7, help="Volume multiplier")
    parser.add_argument("--no-normalize", action="store_true", help="Disable normalization")
    
    args = parser.parse_args()
    
    manager = MusicManager()
    
    if args.command == "list":
        files = manager.list_available_music()
        print("\nAvailable Music Files:")
        print("-" * 60)
        for f in files:
            print(f"  📁 {f['name']} ({f['duration']:.1f}s, {f['size_kb']:.0f}KB)")
    
    elif args.command == "info" and args.source:
        audio_path = manager._get_audio_file(args.source)
        if audio_path:
            duration = manager._get_audio_duration(audio_path)
            print(f"\nMusic Info:")
            print(f"  Path: {audio_path}")
            print(f"  Duration: {duration:.1f} seconds")
            print(f"  Size: {Path(audio_path).stat().st_size / 1024:.1f} KB")
    
    elif args.command == "preview" and args.source:
        audio_path = manager._get_audio_file(args.source)
        if audio_path:
            preview = manager.generate_preview(audio_path)
            print(f"Preview generated: {preview}")
    
    elif args.command == "process" and args.source:
        config = {
            "mode": args.mode,
            "duration": args.duration,
            "fade_in": args.fade_in,
            "fade_out": args.fade_out,
            "volume": args.volume,
            "normalize": not args.no_normalize,
        }
        output = manager.load_music(args.source, config)
        if output:
            print(f"Processed music saved to: {output}")