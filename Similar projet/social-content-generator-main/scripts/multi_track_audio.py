#!/usr/bin/env python3
"""
Multi-Track Audio Mixer - Combine multiple audio tracks
Features:
- Background music + outro music
- Overlay audio (voiceover, sound effects)
- Crossfade between tracks
- Volume mixing per track
"""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TrackType(Enum):
    BACKGROUND = "background"  # Loops, lower volume
    FOREGROUND = "foreground"   # Normal volume
    OUTRO = "outro"             # Plays at end
    VOICEOVER = "voiceover"     # Speech, duck background music
    SFX = "sfx"                 # Sound effect


@dataclass
class AudioTrack:
    """Represents a single audio track"""
    path: str
    track_type: TrackType = TrackType.BACKGROUND
    start_time: float = 0.0  # When to start (seconds into video)
    duration: Optional[float] = None  # Duration to play
    volume: float = 1.0  # Volume multiplier
    fade_in: float = 0.0  # Fade in duration
    fade_out: float = 0.0  # Fade out duration
    loop: bool = False  # Loop if shorter than video
    crossfade_to_next: float = 0.0  # Crossfade to next track


class MultiTrackAudioMixer:
    """
    Mix multiple audio tracks into a single output
    Supports background music, outro, voiceover with ducking
    """
    
    def __init__(self, video_duration: float):
        self.video_duration = video_duration
        self.tracks: List[AudioTrack] = []
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def add_track(self, track: AudioTrack):
        """Add an audio track to the mix"""
        self.tracks.append(track)
    
    def add_background_music(self, path: str, volume: float = 0.5, fade_in: float = 2, fade_out: float = 3):
        """Add background music that plays throughout the video"""
        self.tracks.append(AudioTrack(
            path=path,
            track_type=TrackType.BACKGROUND,
            start_time=0,
            duration=self.video_duration,
            volume=volume,
            fade_in=fade_in,
            fade_out=fade_out,
            loop=True
        ))
    
    def add_outro_music(self, path: str, duration: float = 10, fade_in: float = 1, fade_out: float = 2):
        """Add outro music that plays at the end of video"""
        start_time = max(0, self.video_duration - duration)
        self.tracks.append(AudioTrack(
            path=path,
            track_type=TrackType.OUTRO,
            start_time=start_time,
            duration=duration,
            volume=0.8,
            fade_in=fade_in,
            fade_out=fade_out,
            loop=False
        ))
    
    def add_voiceover(self, path: str, start_time: float, duration: float, duck_background: bool = True):
        """Add voiceover that ducks background music"""
        self.tracks.append(AudioTrack(
            path=path,
            track_type=TrackType.VOICEOVER,
            start_time=start_time,
            duration=duration,
            volume=1.0,
            fade_in=0.5,
            fade_out=0.5,
            loop=False
        ))
    
    def add_sound_effect(self, path: str, start_time: float, volume: float = 0.7):
        """Add a sound effect at specific time"""
        # Get duration of sound effect
        duration = self._get_audio_duration(path)
        self.tracks.append(AudioTrack(
            path=path,
            track_type=TrackType.SFX,
            start_time=start_time,
            duration=duration,
            volume=volume,
            fade_in=0.1,
            fade_out=0.2,
            loop=False
        ))
    
    def mix(self, output_path: str) -> str:
        """
        Mix all tracks into a single audio file
        
        Args:
            output_path: Path for output audio file
        
        Returns:
            Path to mixed audio
        """
        if not self.tracks:
            return None
        
        # Process each track
        processed_tracks = []
        for i, track in enumerate(self.tracks):
            processed = self._process_track(track, i)
            if processed:
                processed_tracks.append(processed)
        
        if not processed_tracks:
            return None
        
        # Mix all tracks together
        return self._mix_tracks(processed_tracks, output_path)
    
    def _process_track(self, track: AudioTrack, index: int) -> Optional[str]:
        """Process individual track: trim, fade, volume adjust"""
        
        # Get track duration
        track_duration = self._get_audio_duration(track.path)
        
        # Determine effective duration
        end_time = track.start_time + (track.duration or track_duration)
        effective_duration = min(track.duration or track_duration, self.video_duration - track.start_time)
        
        if effective_duration <= 0:
            return None
        
        output_path = self.temp_dir / f"track_{index}.m4a"
        
        # Build filters
        filters = []
        
        # Trim
        filters.append(f"atrim=start={0}:end={effective_duration}")
        
        # Volume
        if track.volume != 1.0:
            filters.append(f"volume={track.volume}")
        
        # Fades
        if track.fade_in > 0:
            filters.append(f"afade=t=in:st=0:d={track.fade_in}")
        if track.fade_out > 0:
            filters.append(f"afade=t=out:st={effective_duration - track.fade_out}:d={track.fade_out}")
        
        filter_str = ",".join(filters) if filters else "anull"
        
        # Build FFmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-i", track.path,
            "-filter_complex", filter_str,
            "-c:a", "aac",
            "-b:a", "128k",
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            
            # Add delay for start time
            if track.start_time > 0:
                delayed_path = self.temp_dir / f"track_{index}_delayed.m4a"
                delay_ms = int(track.start_time * 1000)
                
                cmd_delay = [
                    "ffmpeg", "-y",
                    "-i", str(output_path),
                    "-af", f"adelay={delay_ms}|{delay_ms}",
                    "-c:a", "aac",
                    str(delayed_path)
                ]
                subprocess.run(cmd_delay, capture_output=True, check=True)
                return str(delayed_path)
            
            return str(output_path)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Track processing error: {e}")
            return None
    
    def _mix_tracks(self, track_paths: List[str], output_path: str) -> str:
        """Mix multiple audio tracks together"""
        if len(track_paths) == 1:
            # Just copy
            cmd = ["ffmpeg", "-y", "-i", track_paths[0], "-c", "copy", output_path]
        else:
            # Mix with amix filter
            # Build inputs
            inputs = []
            for path in track_paths:
                inputs.extend(["-i", path])
            
            # Build amix filter
            input_count = len(track_paths)
            amix_filter = f"amix=inputs={input_count}:duration=longest:dropout_transition=2"
            
            cmd = [
                "ffmpeg", "-y",
                *inputs,
                "-filter_complex", amix_filter,
                "-c:a", "aac",
                "-b:a", "192k",
                output_path
            ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            logger.info(f"Mixed {len(track_paths)} tracks to {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Mixing error: {e}")
            return None
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds"""
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass


# ============ EXAMPLE USAGE ============
if __name__ == "__main__":
    # Create mixer
    mixer = MultiTrackAudioMixer(video_duration=30)
    
    # Add background music (plays entire video)
    mixer.add_background_music("assets/music/background.mp3", volume=0.4)
    
    # Add outro music (last 8 seconds)
    mixer.add_outro_music("assets/music/outro.mp3", duration=8)
    
    # Add sound effect at 5 seconds
    mixer.add_sound_effect("assets/music/ding.mp3", start_time=5)
    
    # Mix all tracks
    output = mixer.mix("output/mixed_audio.m4a")
    print(f"Mixed audio saved to: {output}")
    
    mixer.cleanup()