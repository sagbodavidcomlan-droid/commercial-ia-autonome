#!/usr/bin/env python3
"""
Music Search Module - Search and download from YouTube & SoundCloud
Features:
- Search YouTube for music by keyword
- Search SoundCloud for tracks
- Download audio from both platforms
- Extract BPM and key information
"""

import os
import re
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Try to import yt-dlp for downloads
try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False
    logger.warning("yt-dlp not installed. YouTube/SoundCloud features disabled.")


class MusicSearchEngine:
    """Search and download music from YouTube and SoundCloud"""
    
    def __init__(self, download_dir: Path = None):
        self.download_dir = download_dir or Path("/project/assets/music/downloads")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # SoundCloud API configuration
        self.soundcloud_client_id = os.getenv("SOUNDCLOUD_CLIENT_ID", "")
        self.soundcloud_oauth = os.getenv("SOUNDCLOUD_OAUTH", "")
    
    # ============ YOUTUBE SEARCH & DOWNLOAD ============
    
    def search_youtube(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search YouTube for music tracks
        
        Args:
            query: Search keyword (e.g., "lofi hip hop study beats")
            max_results: Maximum number of results
        
        Returns:
            List of track dictionaries with keys: title, url, duration, channel
        """
        if not YTDLP_AVAILABLE:
            return self._search_youtube_via_scrape(query, max_results)
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_generic_extractor': False,
        }
        
        search_url = f"ytsearch{max_results}:{query}"
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_url, download=False)
                
                results = []
                for entry in info.get('entries', []):
                    if entry:
                        results.append({
                            "title": entry.get('title', 'Unknown'),
                            "url": f"https://youtube.com/watch?v={entry.get('id', '')}",
                            "duration": entry.get('duration', 0),
                            "channel": entry.get('channel', 'Unknown'),
                            "platform": "youtube",
                            "thumbnail": entry.get('thumbnail', '')
                        })
                return results
                
        except Exception as e:
            logger.error(f"YouTube search error: {e}")
            return []
    
    def _search_youtube_via_scrape(self, query: str, max_results: int) -> List[Dict]:
        """Fallback search using yt-dlp's scrape feature"""
        # Simplified - use yt-dlp even if import failed but CLI available
        try:
            cmd = [
                "yt-dlp", f"ytsearch{max_results}:{query}",
                "--flat-playlist", "--dump-json", "--quiet"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            results = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        data = json.loads(line)
                        results.append({
                            "title": data.get('title', 'Unknown'),
                            "url": f"https://youtube.com/watch?v={data.get('id', '')}",
                            "duration": data.get('duration', 0),
                            "channel": data.get('channel', 'Unknown'),
                            "platform": "youtube"
                        })
                    except json.JSONDecodeError:
                        continue
            return results
        except Exception as e:
            logger.error(f"YouTube scrape error: {e}")
            return []
    
    def download_youtube_audio(self, url: str, output_filename: str = None) -> Optional[str]:
        """
        Download audio from YouTube URL
        
        Args:
            url: YouTube video URL
            output_filename: Optional custom filename
        
        Returns:
            Path to downloaded audio file
        """
        if not YTDLP_AVAILABLE:
            return self._download_audio_via_cli(url, output_filename)
        
        output_template = str(self.download_dir / "%(title)s.%(ext)s")
        if output_filename:
            output_template = str(self.download_dir / f"{output_filename}.%(ext)s")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                # Find downloaded file
                for file in self.download_dir.glob(f"*{info.get('title', '')}*.mp3"):
                    return str(file)
                # Fallback
                mp3_files = list(self.download_dir.glob("*.mp3"))
                if mp3_files:
                    return str(mp3_files[-1])
            return None
        except Exception as e:
            logger.error(f"YouTube download error: {e}")
            return None
    
    def _download_audio_via_cli(self, url: str, output_filename: str = None) -> Optional[str]:
        """Fallback download using yt-dlp CLI"""
        output_path = self.download_dir / f"{output_filename or 'download'}.mp3"
        
        cmd = [
            "yt-dlp", "-x", "--audio-format", "mp3",
            "--audio-quality", "2",
            "-o", str(output_path),
            url
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            if output_path.exists():
                return str(output_path)
            
            # Find any new mp3 file
            mp3_files = list(self.download_dir.glob("*.mp3"))
            if mp3_files:
                return str(mp3_files[-1])
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"CLI download error: {e}")
            return None
    
    # ============ SOUNDCLOUD SEARCH & DOWNLOAD ============
    
    def search_soundcloud(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search SoundCloud for tracks
        
        Args:
            query: Search keyword
            limit: Maximum number of results
        
        Returns:
            List of track dictionaries
        """
        tracks = []
        
        # Try API method if client_id is available
        if self.soundcloud_client_id:
            tracks = self._search_soundcloud_api(query, limit)
        
        # Fallback to scraping
        if not tracks:
            tracks = self._search_soundcloud_scrape(query, limit)
        
        return tracks
    
    def _search_soundcloud_api(self, query: str, limit: int) -> List[Dict]:
        """Search using SoundCloud API"""
        import requests
        
        url = "https://api-v2.soundcloud.com/search/tracks"
        params = {
            "q": query,
            "limit": limit,
            "client_id": self.soundcloud_client_id
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            tracks = []
            for track in data.get('collection', []):
                tracks.append({
                    "title": track.get('title', 'Unknown'),
                    "artist": track.get('user', {}).get('username', 'Unknown'),
                    "duration": track.get('duration', 0) / 1000,  # Convert ms to seconds
                    "url": track.get('permalink_url', ''),
                    "stream_url": track.get('stream_url', ''),
                    "platform": "soundcloud",
                    "artwork_url": track.get('artwork_url', '')
                })
            return tracks
        except Exception as e:
            logger.error(f"SoundCloud API error: {e}")
            return []
    
    def _search_soundcloud_scrape(self, query: str, limit: int) -> List[Dict]:
        """Search using yt-dlp (supports SoundCloud)"""
        if not YTDLP_AVAILABLE:
            logger.warning("Cannot search SoundCloud without yt-dlp")
            return []
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        search_url = f"scsearch{limit}:{query}"
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_url, download=False)
                
                tracks = []
                for entry in info.get('entries', []):
                    if entry:
                        tracks.append({
                            "title": entry.get('title', 'Unknown'),
                            "artist": entry.get('uploader', 'Unknown'),
                            "duration": entry.get('duration', 0),
                            "url": entry.get('url', ''),
                            "platform": "soundcloud"
                        })
                return tracks
        except Exception as e:
            logger.error(f"SoundCloud scrape error: {e}")
            return []
    
    def download_soundcloud_audio(self, url: str, output_filename: str = None) -> Optional[str]:
        """
        Download audio from SoundCloud URL
        
        Args:
            url: SoundCloud track URL
            output_filename: Optional custom filename
        
        Returns:
            Path to downloaded audio file
        """
        if not YTDLP_AVAILABLE:
            return self._download_audio_via_cli(url, output_filename)
        
        output_template = str(self.download_dir / "%(title)s.%(ext)s")
        if output_filename:
            output_template = str(self.download_dir / f"{output_filename}.%(ext)s")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                # Find downloaded file
                for file in self.download_dir.glob(f"*{info.get('title', '')}*.mp3"):
                    return str(file)
                mp3_files = list(self.download_dir.glob("*.mp3"))
                if mp3_files:
                    return str(mp3_files[-1])
            return None
        except Exception as e:
            logger.error(f"SoundCloud download error: {e}")
            return None
    
    # ============ SEARCH COMBINED ============
    
    def search_all(self, query: str, limit: int = 5) -> Dict[str, List[Dict]]:
        """
        Search both YouTube and SoundCloud
        
        Args:
            query: Search keyword
            limit: Results per platform
        
        Returns:
            Dictionary with 'youtube' and 'soundcloud' keys
        """
        return {
            "youtube": self.search_youtube(query, limit),
            "soundcloud": self.search_soundcloud(query, limit)
        }
    
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass


# ============ COMMAND LINE TOOL ============
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Music Search Tool")
    parser.add_argument("command", choices=["search", "download"])
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--url", help="URL to download")
    parser.add_argument("--platform", choices=["youtube", "soundcloud", "all"], default="all")
    parser.add_argument("--limit", type=int, default=5)
    
    args = parser.parse_args()
    
    engine = MusicSearchEngine()
    
    if args.command == "search":
        if args.platform == "all":
            results = engine.search_all(args.query, args.limit)
            print("\n=== YOUTUBE RESULTS ===")
            for i, track in enumerate(results['youtube'], 1):
                print(f"  {i}. {track['title']} ({track.get('channel', 'Unknown')})")
                print(f"     {track['url']}")
            
            print("\n=== SOUNDCLOUD RESULTS ===")
            for i, track in enumerate(results['soundcloud'], 1):
                print(f"  {i}. {track['title']} by {track.get('artist', 'Unknown')}")
                print(f"     {track['url']}")
        
        elif args.platform == "youtube":
            results = engine.search_youtube(args.query, args.limit)
            for i, track in enumerate(results, 1):
                print(f"{i}. {track['title']} - {track['channel']}")
                print(f"   {track['url']}")
        
        elif args.platform == "soundcloud":
            results = engine.search_soundcloud(args.query, args.limit)
            for i, track in enumerate(results, 1):
                print(f"{i}. {track['title']} by {track.get('artist', 'Unknown')}")
                print(f"   {track['url']}")
    
    elif args.command == "download" and args.url:
        if "youtube.com" in args.url or "youtu.be" in args.url:
            output = engine.download_youtube_audio(args.url)
        elif "soundcloud.com" in args.url:
            output = engine.download_soundcloud_audio(args.url)
        else:
            output = engine.download_youtube_audio(args.url)
        
        if output:
            print(f"Downloaded: {output}")
        else:
            print("Download failed")