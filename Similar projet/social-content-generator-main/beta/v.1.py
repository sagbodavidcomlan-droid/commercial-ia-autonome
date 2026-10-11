#!/usr/bin/env python3
"""
Social Media Auto Content System - Version 1
Full Automatic Mode - No UI Required
Complete automation with interactive music & video search/download
"""

import os
import sys
import json
import yaml
import time
import logging
import subprocess
import requests
import tempfile
import shutil
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

# Import libraries
try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False
    print("Warning: yt-dlp not installed. YouTube features disabled.")

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    print("Warning: Google libraries not installed. Google Sheets features disabled.")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class MediaItem:
    """Represents a media item (video or music)"""
    url: str
    title: str
    duration: int
    platform: str
    quality: str
    download_path: Optional[str] = None
    thumbnail: Optional[str] = None
    tags: List[str] = None


class MediaSearchEngine:
    """Interactive media search and download engine"""
    
    def __init__(self, config: dict):
        self.config = config
        self.download_dir = Path(config['system']['temp_dir']) / 'downloads'
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
    def search_video(self, keyword: str, platform: str = "pexels") -> List[MediaItem]:
        """
        Search for videos from various platforms
        
        Args:
            keyword: Search keyword
            platform: pexels, pixabay, youtube
            
        Returns:
            List of MediaItem objects
        """
        results = []
        
        if platform == "pexels":
            results = self._search_pexels_video(keyword)
        elif platform == "pixabay":
            results = self._search_pixabay_video(keyword)
        elif platform == "youtube":
            results = self._search_youtube_video(keyword)
        else:
            # Search all enabled platforms
            if self.config['video']['search']['pexels']['enabled']:
                results.extend(self._search_pexels_video(keyword))
            if self.config['video']['search']['pixabay']['enabled']:
                results.extend(self._search_pixabay_video(keyword))
            if self.config['video']['search'].get('youtube', {}).get('enabled', False):
                results.extend(self._search_youtube_video(keyword))
        
        # Sort by relevance and duration
        results.sort(key=lambda x: x.duration)
        return results
    
    def search_music(self, keyword: str, mood: str = "", platform: str = "all") -> List[MediaItem]:
        """
        Search for music from various platforms
        
        Args:
            keyword: Search keyword
            mood: Music mood (upbeat, chill, epic, etc.)
            platform: youtube, soundcloud, pixabay
            
        Returns:
            List of MediaItem objects
        """
        results = []
        
        # Build search query
        query = keyword
        if mood:
            query = f"{mood} {keyword}"
        
        if platform == "youtube":
            results = self._search_youtube_music(query)
        elif platform == "soundcloud":
            results = self._search_soundcloud_music(query)
        elif platform == "pixabay":
            results = self._search_pixabay_music(query)
        else:
            if self.config['music']['search']['youtube']['enabled']:
                results.extend(self._search_youtube_music(query))
            if self.config['music']['search']['soundcloud']['enabled']:
                results.extend(self._search_soundcloud_music(query))
            if self.config['music']['search'].get('pixabay', {}).get('enabled', False):
                results.extend(self._search_pixabay_music(query))
        
        return results
    
    def download_video(self, media_item: MediaItem) -> Optional[str]:
        """
        Download video from URL
        
        Args:
            media_item: MediaItem object with URL
            
        Returns:
            Path to downloaded file or None
        """
        if media_item.platform == "pexels":
            return self._download_pexels_video(media_item)
        elif media_item.platform == "pixabay":
            return self._download_pixabay_video(media_item)
        elif media_item.platform == "youtube":
            return self._download_youtube_video(media_item)
        return None
    
    def download_music(self, media_item: MediaItem) -> Optional[str]:
        """
        Download music from URL
        
        Args:
            media_item: MediaItem object with URL
            
        Returns:
            Path to downloaded file or None
        """
        if media_item.platform == "youtube":
            return self._download_youtube_audio(media_item)
        elif media_item.platform == "soundcloud":
            return self._download_soundcloud_audio(media_item)
        elif media_item.platform == "pixabay":
            return self._download_pixabay_audio(media_item)
        return None
    
    def _search_pexels_video(self, keyword: str) -> List[MediaItem]:
        """Search Pexels for videos"""
        results = []
        api_key = self.config['api']['pexels']['api_key']
        
        if not api_key or api_key == "YOUR_PEXELS_API_KEY":
            logger.warning("Pexels API key not configured")
            return results
        
        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": api_key}
        params = {
            "query": keyword,
            "per_page": self.config['video']['search']['pexels']['per_page'],
            "orientation": self.config['video']['search']['pexels']['orientation']
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            for video in data.get('videos', []):
                # Get best quality video file
                best_file = None
                best_quality = 0
                
                for video_file in video.get('video_files', []):
                    quality = video_file.get('height', 0)
                    if quality >= best_quality and quality >= 1080:
                        best_quality = quality
                        best_file = video_file
                
                if best_file:
                    results.append(MediaItem(
                        url=best_file['link'],
                        title=video.get('url', keyword),
                        duration=video.get('duration', 0),
                        platform="pexels",
                        quality=f"{best_file.get('width', 0)}x{best_file.get('height', 0)}",
                        thumbnail=video.get('image', ''),
                        tags=video.get('tags', [])
                    ))
            
            logger.info(f"Found {len(results)} videos from Pexels for '{keyword}'")
            
        except Exception as e:
            logger.error(f"Pexels search error: {e}")
        
        return results
    
    def _search_pixabay_video(self, keyword: str) -> List[MediaItem]:
        """Search Pixabay for videos"""
        results = []
        api_key = self.config['api']['pixabay']['api_key']
        
        if not api_key or api_key == "YOUR_PIXABAY_API_KEY":
            logger.warning("Pixabay API key not configured")
            return results
        
        url = "https://pixabay.com/api/videos/"
        params = {
            "key": api_key,
            "q": keyword,
            "per_page": self.config['video']['search']['pixabay']['per_page'],
            "orientation": self.config['video']['search']['pixabay']['orientation']
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            for video in data.get('hits', []):
                # Get best quality video
                videos = video.get('videos', {})
                best_key = 'large' if 'large' in videos else 'medium' if 'medium' in videos else 'small'
                
                if best_key in videos:
                    video_info = videos[best_key]
                    results.append(MediaItem(
                        url=video_info['url'],
                        title=video.get('tags', keyword),
                        duration=video.get('duration', 0),
                        platform="pixabay",
                        quality=best_key,
                        thumbnail=video.get('thumbnail', ''),
                        tags=video.get('tags', '').split(',')
                    ))
            
            logger.info(f"Found {len(results)} videos from Pixabay for '{keyword}'")
            
        except Exception as e:
            logger.error(f"Pixabay search error: {e}")
        
        return results
    
    def _search_youtube_video(self, keyword: str) -> List[MediaItem]:
        """Search YouTube for videos"""
        results = []
        
        if not YTDLP_AVAILABLE:
            logger.warning("yt-dlp not available for YouTube search")
            return results
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'format': 'bestvideo[height<=1080]',
        }
        
        search_url = f"ytsearch10:{keyword}"
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_url, download=False)
                
                for entry in info.get('entries', []):
                    if entry:
                        duration = entry.get('duration', 0)
                        if duration < self.config['video']['search']['pexels']['min_duration']:
                            continue
                        if duration > self.config['video']['search']['pexels']['max_duration']:
                            continue
                        
                        results.append(MediaItem(
                            url=f"https://youtube.com/watch?v={entry.get('id', '')}",
                            title=entry.get('title', keyword),
                            duration=duration,
                            platform="youtube",
                            quality="1080p",
                            thumbnail=entry.get('thumbnail', ''),
                            tags=[]
                        ))
            
            logger.info(f"Found {len(results)} videos from YouTube for '{keyword}'")
            
        except Exception as e:
            logger.error(f"YouTube search error: {e}")
        
        return results
    
    def _search_youtube_music(self, query: str) -> List[MediaItem]:
        """Search YouTube for music"""
        results = []
        
        if not YTDLP_AVAILABLE:
            return results
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'format': 'bestaudio/best',
        }
        
        # Add filter for instrumental if needed
        if not self.config['music']['search']['youtube']['allow_vocals']:
            query = f"{query} instrumental"
        
        search_url = f"ytsearch{self.config['music']['search']['youtube']['max_results']}:{query}"
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_url, download=False)
                
                for entry in info.get('entries', []):
                    if entry:
                        duration = entry.get('duration', 0)
                        min_dur = self.config['music']['search']['youtube']['min_duration']
                        max_dur = self.config['music']['search']['youtube']['max_duration']
                        
                        if duration < min_dur or duration > max_dur:
                            continue
                        
                        results.append(MediaItem(
                            url=f"https://youtube.com/watch?v={entry.get('id', '')}",
                            title=entry.get('title', query),
                            duration=duration,
                            platform="youtube",
                            quality="192k",
                            thumbnail=entry.get('thumbnail', ''),
                            tags=[]
                        ))
            
            logger.info(f"Found {len(results)} music tracks from YouTube for '{query}'")
            
        except Exception as e:
            logger.error(f"YouTube music search error: {e}")
        
        return results
    
    def _search_soundcloud_music(self, query: str) -> List[MediaItem]:
        """Search SoundCloud for music"""
        results = []
        
        if not YTDLP_AVAILABLE:
            return results
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        search_url = f"scsearch{self.config['music']['search']['soundcloud']['max_results']}:{query}"
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_url, download=False)
                
                for entry in info.get('entries', []):
                    if entry:
                        duration = entry.get('duration', 0)
                        min_dur = self.config['music']['search']['soundcloud']['min_duration']
                        max_dur = self.config['music']['search']['soundcloud']['max_duration']
                        
                        if duration < min_dur or duration > max_dur:
                            continue
                        
                        results.append(MediaItem(
                            url=entry.get('url', ''),
                            title=entry.get('title', query),
                            duration=duration,
                            platform="soundcloud",
                            quality="128k",
                            thumbnail=entry.get('thumbnail', ''),
                            tags=[]
                        ))
            
            logger.info(f"Found {len(results)} music tracks from SoundCloud for '{query}'")
            
        except Exception as e:
            logger.error(f"SoundCloud search error: {e}")
        
        return results
    
    def _search_pixabay_music(self, query: str) -> List[MediaItem]:
        """Search Pixabay for music"""
        results = []
        api_key = self.config['api']['pixabay']['api_key']
        
        if not api_key or api_key == "YOUR_PIXABAY_API_KEY":
            return results
        
        url = "https://pixabay.com/api/v2/music/search/"
        params = {
            "key": api_key,
            "q": query,
            "limit": self.config['music']['search'].get('pixabay', {}).get('max_results', 10),
            "instrumental": 1 if not self.config['music']['search']['youtube'].get('allow_vocals', False) else 0
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            for track in data.get('hits', []):
                duration = track.get('duration', 0)
                results.append(MediaItem(
                    url=track.get('audio_file_url', track.get('url', '')),
                    title=track.get('title', query),
                    duration=duration,
                    platform="pixabay",
                    quality="192k",
                    thumbnail=track.get('thumbnail', ''),
                    tags=[tag.get('name', '') for tag in track.get('tags', [])]
                ))
            
            logger.info(f"Found {len(results)} music tracks from Pixabay for '{query}'")
            
        except Exception as e:
            logger.error(f"Pixabay music search error: {e}")
        
        return results
    
    def _download_pexels_video(self, media_item: MediaItem) -> Optional[str]:
        """Download video from Pexels URL"""
        output_path = self.download_dir / f"pexels_{int(time.time())}.mp4"
        
        try:
            response = requests.get(media_item.url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded video: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Pexels download error: {e}")
            return None
    
    def _download_pixabay_video(self, media_item: MediaItem) -> Optional[str]:
        """Download video from Pixabay URL"""
        return self._download_pexels_video(media_item)  # Same method
    
    def _download_youtube_video(self, media_item: MediaItem) -> Optional[str]:
        """Download video from YouTube"""
        if not YTDLP_AVAILABLE:
            return None
        
        output_path = self.download_dir / f"youtube_video_{int(time.time())}.mp4"
        
        ydl_opts = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]',
            'outtmpl': str(output_path).replace('.mp4', '.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([media_item.url])
                
                # Find downloaded file
                for f in self.download_dir.glob("youtube_video_*"):
                    if f.suffix in ['.mp4', '.webm', '.mkv']:
                        # Convert to mp4 if needed
                        if f.suffix != '.mp4':
                            mp4_path = f.with_suffix('.mp4')
                            subprocess.run([
                                'ffmpeg', '-i', str(f), '-c', 'copy', str(mp4_path)
                            ], capture_output=True)
                            f.unlink()
                            return str(mp4_path)
                        return str(f)
            
            return None
            
        except Exception as e:
            logger.error(f"YouTube download error: {e}")
            return None
    
    def _download_youtube_audio(self, media_item: MediaItem) -> Optional[str]:
        """Download audio from YouTube"""
        if not YTDLP_AVAILABLE:
            return None
        
        output_path = self.download_dir / f"youtube_audio_{int(time.time())}.mp3"
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': self.config['music']['search']['youtube']['preferred_quality'],
            }],
            'outtmpl': str(output_path).replace('.mp3', '.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([media_item.url])
                
                # Find downloaded file
                for f in self.download_dir.glob("youtube_audio_*.mp3"):
                    return str(f)
            
            return None
            
        except Exception as e:
            logger.error(f"YouTube audio download error: {e}")
            return None
    
    def _download_soundcloud_audio(self, media_item: MediaItem) -> Optional[str]:
        """Download audio from SoundCloud"""
        if not YTDLP_AVAILABLE:
            return None
        
        output_path = self.download_dir / f"soundcloud_{int(time.time())}.mp3"
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192k',
            }],
            'outtmpl': str(output_path).replace('.mp3', '.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([media_item.url])
                
                for f in self.download_dir.glob("soundcloud_*.mp3"):
                    return str(f)
            
            return None
            
        except Exception as e:
            logger.error(f"SoundCloud download error: {e}")
            return None
    
    def _download_pixabay_audio(self, media_item: MediaItem) -> Optional[str]:
        """Download audio from Pixabay URL"""
        output_path = self.download_dir / f"pixabay_{int(time.time())}.mp3"
        
        try:
            response = requests.get(media_item.url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Pixabay audio download error: {e}")
            return None


class VideoRenderer:
    """Video rendering engine with FFmpeg"""
    
    def __init__(self, config: dict):
        self.config = config
        
    def render(self, texts: List[str], video_path: str, music_path: str = None, 
               output_path: str = None, template: str = "motivational") -> str:
        """
        Render video with text overlays
        
        Args:
            texts: List of text lines
            video_path: Path to background video
            music_path: Path to background music (optional)
            output_path: Output path for rendered video
            template: Template name
            
        Returns:
            Path to rendered video
        """
        if output_path is None:
            output_dir = Path(self.config['system']['output_dir']) / 'videos'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"video_{int(time.time())}.mp4"
        
        output_path = Path(output_path)
        duration_per_text = 5
        total_duration = len(texts) * duration_per_text
        total_duration = min(total_duration, self.config['rendering']['max_duration'])
        
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Process background video
            processed_bg = self._process_background(video_path, total_duration, temp_dir)
            
            # Build text filters
            text_filters = self._build_text_filters(texts, duration_per_text, template)
            
            # Build FFmpeg command
            filter_complex = f"[0:v]{processed_bg}"
            for text_filter in text_filters:
                filter_complex += f",{text_filter}"
            filter_complex += "[v]"
            
            cmd = [
                "ffmpeg", "-y",
                "-i", processed_bg,
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-b:v", self.config['video']['processing']['video_bitrate'],
                "-pix_fmt", "yuv420p",
                "-r", str(self.config['video']['processing']['fps']),
            ]
            
            # Add audio if provided
            if music_path and Path(music_path).exists():
                processed_audio = self._process_audio(music_path, total_duration, temp_dir)
                cmd.extend(["-i", processed_audio])
                cmd.extend(["-c:a", "aac", "-b:a", "128k", "-shortest"])
            else:
                cmd.append("-an")
            
            cmd.append(str(output_path))
            
            # Execute render
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg error: {result.stderr[:500]}")
            
            logger.info(f"Video rendered: {output_path}")
            return str(output_path)
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _process_background(self, video_path: str, duration: int, temp_dir: Path) -> str:
        """Process background video (loop, resize)"""
        output_path = temp_dir / "background.mp4"
        
        # Get video duration
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ], capture_output=True, text=True)
        video_duration = float(probe.stdout.strip())
        
        if video_duration < duration:
            # Loop video
            concat_file = temp_dir / "concat.txt"
            loops = int(duration / video_duration) + 1
            with open(concat_file, "w") as f:
                for _ in range(loops):
                    f.write(f"file '{video_path}'\n")
            
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_file), "-c", "copy", "-t", str(duration),
                str(output_path)
            ], capture_output=True, check=True)
        else:
            subprocess.run([
                "ffmpeg", "-y", "-i", video_path, "-t", str(duration),
                "-c", "copy", str(output_path)
            ], capture_output=True, check=True)
        
        # Resize to target resolution
        width, height = self.config['video']['processing']['output_size']
        processed = temp_dir / "processed_bg.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(output_path),
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=1,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-preset", "fast",
            str(processed)
        ], capture_output=True, check=True)
        
        return str(processed)
    
    def _process_audio(self, audio_path: str, duration: int, temp_dir: Path) -> str:
        """Process audio (loop, normalize)"""
        output_path = temp_dir / "audio_processed.m4a"
        
        # Get audio duration
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_path
        ], capture_output=True, text=True)
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
        volume = self.config['music']['processing']['default_volume']
        normalized = temp_dir / "audio_normalized.m4a"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(output_path),
            "-af", f"volume={volume},loudnorm=I=-16:LRA=11:TP=-1.5",
            "-c:a", "aac", str(normalized)
        ], capture_output=True, check=True)
        
        return str(normalized)
    
    def _build_text_filters(self, texts: List[str], duration_per_text: int, template: str) -> List[str]:
        """Build FFmpeg drawtext filters for text overlays"""
        filters = []
        
        # Template styles
        styles = {
            "motivational": {"color": "#FFD700", "size": 52, "shadow": True},
            "zodiac_dark": {"color": "#FFFFFF", "size": 48, "shadow": True},
            "educational": {"color": "#00FF88", "size": 40, "shadow": False},
            "quote_simple": {"color": "#F5F5F5", "size": 44, "shadow": True}
        }
        
        style = styles.get(template, styles["motivational"])
        
        for i, text in enumerate(texts):
            if not text.strip():
                continue
            
            start_time = i * duration_per_text
            escaped_text = text.replace("'", "\\'").replace(":", "\\:")
            
            filter_parts = [
                f"drawtext=text='{escaped_text}'",
                f"fontfile=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                f"fontsize={style['size']}",
                f"fontcolor={style['color']}",
                f"x=(w-text_w)/2",
                f"y=(h-text_h)/2",
                f"enable='between(t,{start_time},{start_time + duration_per_text})'",
                "bordercolor=black:borderw=2"
            ]
            
            if style['shadow']:
                filter_parts.append("shadowcolor=black@0.5:shadowx=3:shadowy=3")
            
            # Add fade animation
            filter_parts.append(f"alpha='if(lt(t-{start_time},0.5), (t-{start_time})/0.5, if(gt({start_time + duration_per_text}-t,0.5), 1, ({start_time + duration_per_text}-t)/0.5))'")
            
            filters.append(":".join(filter_parts))
        
        return filters


class GoogleSheetsManager:
    """Manage Google Sheets operations"""
    
    def __init__(self, config: dict):
        self.config = config
        self.service = None
        self._init_service()
    
    def _init_service(self):
        """Initialize Google Sheets service"""
        if not GOOGLE_AVAILABLE:
            logger.warning("Google libraries not available")
            return
        
        creds_path = self.config['api']['google_sheets']['credentials_file']
        
        if not Path(creds_path).exists():
            logger.warning(f"Credentials file not found: {creds_path}")
            return
        
        try:
            with open(creds_path, 'r') as f:
                creds_json = json.load(f)
            
            credentials = service_account.Credentials.from_service_account_info(
                creds_json,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("Google Sheets service initialized")
            
        except Exception as e:
            logger.error(f"Google Sheets init error: {e}")
    
    def read_pending_rows(self) -> List[Dict]:
        """Read rows with status DRAFT or READY_RENDER"""
        if not self.service:
            return []
        
        sheet_id = self.config['api']['google_sheets']['sheet_id']
        sheet_name = self.config['api']['google_sheets']['sheet_name']
        range_name = f"{sheet_name}!A:Z"
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return []
            
            headers = values[0]
            rows = []
            
            for row in values[1:]:
                row_dict = dict(zip(headers, row))
                status = row_dict.get('status', '')
                
                if status in ['DRAFT', 'READY_RENDER', 'ERROR']:
                    # Convert to dict with proper keys
                    row_data = {}
                    for i, header in enumerate(headers):
                        if i < len(row):
                            row_data[header] = row[i]
                        else:
                            row_data[header] = ''
                    
                    # Add row number
                    row_data['row_index'] = values.index(row) + 1
                    rows.append(row_data)
            
            logger.info(f"Found {len(rows)} pending rows")
            return rows
            
        except Exception as e:
            logger.error(f"Read sheet error: {e}")
            return []
    
    def update_row(self, row_index: int, updates: Dict):
        """Update specific row in sheet"""
        if not self.service:
            return
        
        sheet_id = self.config['api']['google_sheets']['sheet_id']
        sheet_name = self.config['api']['google_sheets']['sheet_name']
        
        # Get headers
        range_name = f"{sheet_name}!A1:Z1"
        result = self.service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        
        headers = result.get('values', [[]])[0]
        
        # Build update request
        update_range = f"{sheet_name}!A{row_index}:Z{row_index}"
        
        # Get current row values
        current = self.service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=update_range
        ).execute()
        
        current_values = current.get('values', [[]])[0] if current.get('values') else []
        
        # Apply updates
        for i, header in enumerate(headers):
            if header in updates:
                while len(current_values) <= i:
                    current_values.append('')
                current_values[i] = str(updates[header])
        
        # Update sheet
        body = {
            'values': [current_values]
        }
        
        try:
            self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=update_range,
                valueInputOption='RAW',
                body=body
            ).execute()
            logger.info(f"Updated row {row_index}: {updates}")
            
        except Exception as e:
            logger.error(f"Update row error: {e}")


class NuelinkAPI:
    """Nuelink API integration"""
    
    def __init__(self, config: dict):
        self.config = config
        self.api_key = config['api']['nuelink']['api_key']
        self.base_url = config['api']['nuelink']['base_url']
    
    def upload_media(self, video_path: str, caption: str) -> Optional[str]:
        """Upload video to Nuelink"""
        if not self.api_key or self.api_key == "YOUR_NUELINK_API_KEY":
            logger.warning("Nuelink API key not configured")
            return None
        
        url = f"{self.base_url}/media/upload"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            with open(video_path, 'rb') as f:
                files = {'file': f}
                data = {'caption': caption}
                
                response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
                response.raise_for_status()
                
                result = response.json()
                media_id = result.get('media_id') or result.get('id')
                logger.info(f"Uploaded to Nuelink: {media_id}")
                return media_id
                
        except Exception as e:
            logger.error(f"Nuelink upload error: {e}")
            return None
    
    def schedule_post(self, media_id: str, scheduled_time: str, timezone: str) -> Optional[str]:
        """Schedule post on Nuelink"""
        url = f"{self.base_url}/posts/schedule"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        
        platforms = self.config['posting']['platforms']
        
        body = {
            "media_id": media_id,
            "scheduled_time": scheduled_time,
            "timezone": timezone,
            "platforms": platforms
        }
        
        try:
            response = requests.post(url, headers=headers, json=body, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            post_id = result.get('post_id') or result.get('id')
            logger.info(f"Scheduled post: {post_id} at {scheduled_time}")
            return post_id
            
        except Exception as e:
            logger.error(f"Nuelink schedule error: {e}")
            return None


class ContentProcessor:
    """Main content processing engine"""
    
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize components
        self.media_search = MediaSearchEngine(self.config)
        self.video_renderer = VideoRenderer(self.config)
        self.sheets_manager = GoogleSheetsManager(self.config)
        self.nuelink = NuelinkAPI(self.config)
        
        # Create directories
        for dir_name in ['system/temp_dir', 'system/output_dir', 'system/data_dir']:
            path = Path(self.config['system'].get(dir_name.split('/')[-1], ''))
            if path:
                path.mkdir(parents=True, exist_ok=True)
        
        logger.info("Content Processor initialized")
    
    def process_row(self, row: Dict) -> Dict:
        """Process a single row from Google Sheets"""
        row_id = row.get('id', row.get('row_index', 'unknown'))
        logger.info(f"Processing row {row_id}")
        
        result = {
            'row_id': row_id,
            'status': 'error',
            'error_message': ''
        }
        
        try:
            # Update status to RENDERING
            self.sheets_manager.update_row(row['row_index'], {'status': 'RENDERING'})
            
            # Extract texts
            texts = []
            for i in range(1, 6):
                text = row.get(f'text_{i}', '')
                if text and text.strip():
                    texts.append(text.strip())
            
            if not texts:
                raise ValueError("No text content provided")
            
            template = row.get('template', 'motivational')
            asset_keyword = row.get('asset_keyword', 'nature')
            music_mood = row.get('music_mood', 'ambient')
            
            # Search and download video
            if self.config['features']['auto_search_video']:
                videos = self.media_search.search_video(asset_keyword)
                if videos:
                    video_item = videos[0]
                    video_path = self.media_search.download_video(video_item)
                else:
                    video_path = str(Path(self.config['video']['search']['local_fallback']['directory']) / 'fallback.mp4')
            else:
                video_path = str(Path(self.config['video']['search']['local_fallback']['directory']) / 'fallback.mp4')
            
            if not video_path or not Path(video_path).exists():
                video_path = self._create_fallback_video()
            
            # Search and download music
            music_path = None
            if self.config['features']['auto_search_music']:
                music_tracks = self.media_search.search_music(asset_keyword, music_mood)
                if music_tracks:
                    music_item = music_tracks[0]
                    music_path = self.media_search.download_music(music_item)
            
            # Render video
            output_path = self.video_renderer.render(
                texts=texts,
                video_path=video_path,
                music_path=music_path,
                template=template
            )
            
            # Generate preview URL
            preview_url = f"http://localhost:8080/{Path(output_path).name}"
            
            # Update sheet with preview
            self.sheets_manager.update_row(row['row_index'], {
                'status': 'WAITING_APPROVAL',
                'approval_status': 'WAITING_APPROVAL',
                'video_output_path': output_path,
                'preview_url': preview_url
            })
            
            # Check if auto-approve or wait for manual
            if not self.config['approval']['required']:
                # Auto approve
                self.sheets_manager.update_row(row['row_index'], {
                    'approval_status': 'APPROVED',
                    'approved_by': 'system',
                    'approved_at': datetime.now().isoformat()
                })
                
                # Post to Nuelink
                if self.config['features']['auto_post']:
                    caption = row.get('caption', '')
                    hashtags = row.get('hashtags', '')
                    full_caption = f"{caption} {hashtags}".strip()
                    
                    media_id = self.nuelink.upload_media(output_path, full_caption)
                    
                    if media_id:
                        schedule_time = row.get('schedule_datetime', datetime.now().isoformat())
                        timezone = row.get('timezone', self.config['posting']['default_timezone'])
                        
                        post_id = self.nuelink.schedule_post(media_id, schedule_time, timezone)
                        
                        self.sheets_manager.update_row(row['row_index'], {
                            'status': 'SENT_TO_NUELINK',
                            'nuelink_post_id': post_id
                        })
            
            result['status'] = 'success'
            result['video_path'] = output_path
            result['preview_url'] = preview_url
            
        except Exception as e:
            logger.exception(f"Row {row_id} processing failed")
            error_msg = str(e)
            
            result['error_message'] = error_msg
            
            # Update error in sheet
            retry_count = int(row.get('retry_count', 0)) + 1
            max_retries = self.config['error_handling']['retry_count']
            
            if retry_count >= max_retries:
                self.sheets_manager.update_row(row['row_index'], {
                    'status': 'ERROR',
                    'last_error': error_msg,
                    'retry_count': retry_count
                })
            else:
                self.sheets_manager.update_row(row['row_index'], {
                    'status': 'READY_RENDER',
                    'last_error': f"Retry {retry_count}/{max_retries}: {error_msg}",
                    'retry_count': retry_count
                })
        
        return result
    
    def _create_fallback_video(self) -> str:
        """Create a fallback black video"""
        output_path = Path(self.config['system']['temp_dir']) / 'fallback_video.mp4'
        
        width, height = self.config['video']['processing']['output_size']
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:d=60",
            "-c:v", "libx264", "-t", "60",
            str(output_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        return str(output_path)
    
    def run(self):
        """Main run loop"""
        logger.info("Starting Content Processor - Version 1 (Full Automatic)")
        
        while True:
            try:
                # Read pending rows
                rows = self.sheets_manager.read_pending_rows()
                
                # Process each row
                for row in rows:
                    result = self.process_row(row)
                    
                    if result['status'] == 'success':
                        logger.info(f"Row {result['row_id']} processed successfully")
                    else:
                        logger.error(f"Row {result['row_id']} failed: {result['error_message']}")
                
                # Wait before next iteration
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.exception(f"Run loop error: {e}")
                time.sleep(60)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Social Media Auto Content System V1")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()
    
    processor = ContentProcessor(args.config)
    
    if args.once:
        # Run once
        rows = processor.sheets_manager.read_pending_rows()
        for row in rows:
            processor.process_row(row)
    else:
        # Run continuously
        processor.run()


if __name__ == "__main__":
    main()