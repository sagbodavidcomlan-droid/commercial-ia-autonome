#!/usr/bin/env python3
"""
Beat Detection and Text Sync Module
Features:
- Detect BPM from audio file
- Sync text appearance with beats
- Generate timed text overlays based on beat positions
"""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import librosa for BPM detection
try:
    import librosa
    import numpy as np
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("librosa not installed. Beat detection features disabled.")


@dataclass
class BeatInfo:
    """Information about detected beats"""
    bpm: float
    beat_times: List[float]  # Timestamps of each beat
    confidence: float
    method: str  # librosa, madmom, or estimated


class BeatDetector:
    """
    Detect beats in audio and generate beat-synced text overlays
    """
    
    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def detect_bpm(self, audio_path: str, use_madmom: bool = False) -> Optional[BeatInfo]:
        """
        Detect BPM and beat positions from audio file
        
        Args:
            audio_path: Path to audio file
            use_madmom: Use madmom for better accuracy (slower)
        
        Returns:
            BeatInfo object with BPM and beat timestamps
        """
        if not LIBROSA_AVAILABLE:
            return self._estimate_bpm_ffmpeg(audio_path)
        
        try:
            # Load audio
            y, sr = librosa.load(audio_path, duration=60)  # Load first 60 seconds
            
            if use_madmom:
                # Try madmom if available
                return self._detect_with_madmom(audio_path)
            
            # Use librosa for tempo detection
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            
            # Filter beats within audio duration
            duration = self._get_audio_duration(audio_path)
            beat_times = [t for t in beat_times if t <= duration]
            
            return BeatInfo(
                bpm=float(tempo),
                beat_times=beat_times.tolist() if hasattr(beat_times, 'tolist') else beat_times,
                confidence=0.8,
                method="librosa"
            )
            
        except Exception as e:
            logger.error(f"BPM detection error: {e}")
            return self._estimate_bpm_ffmpeg(audio_path)
    
    def _detect_with_madmom(self, audio_path: str) -> Optional[BeatInfo]:
        """Detect beats using madmom (more accurate)"""
        try:
            import madmom
            proc = madmom.features.beats.RNNBeatProcessor()(audio_path)
            beats = madmom.features.beats.DBNBeatTrackingProcessor()(proc)
            beat_times = [float(beat) for beat in beats]
            
            # Calculate BPM from beat intervals
            if len(beat_times) > 1:
                intervals = [beat_times[i+1] - beat_times[i] for i in range(len(beat_times)-1)]
                avg_interval = sum(intervals) / len(intervals)
                bpm = 60 / avg_interval
            else:
                bpm = 120
            
            return BeatInfo(
                bpm=bpm,
                beat_times=beat_times,
                confidence=0.9,
                method="madmom"
            )
        except ImportError:
            return None
        except Exception as e:
            logger.error(f"Madmom error: {e}")
            return None
    
    def _estimate_bpm_ffmpeg(self, audio_path: str) -> Optional[BeatInfo]:
        """Fallback BPM estimation using FFmpeg (rough)"""
        # Generate a spectrogram and try to detect tempo
        # This is a rough approximation
        
        # Use ffmpeg to get audio features
        temp_wav = self.temp_dir / "temp_audio.wav"
        cmd = [
            "ffmpeg", "-y", "-i", audio_path,
            "-t", "30", "-ar", "22050", "-ac", "1",
            str(temp_wav)
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            
            # Load with librosa if available
            if LIBROSA_AVAILABLE:
                y, sr = librosa.load(str(temp_wav), duration=30)
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                
                # Generate estimated beat times
                beat_interval = 60 / tempo
                beat_times = [i * beat_interval for i in range(int(30 / beat_interval))]
                
                return BeatInfo(
                    bpm=float(tempo),
                    beat_times=beat_times,
                    confidence=0.6,
                    method="ffmpeg+librosa"
                )
        except Exception as e:
            logger.error(f"FFmpeg BPM estimation error: {e}")
        
        # Default fallback
        return BeatInfo(
            bpm=120,
            beat_times=[i * 0.5 for i in range(60)],  # 120 BPM = 2 beats per second
            confidence=0.3,
            method="default"
        )
    
    def get_beat_sync_timings(self, beat_info: BeatInfo, text_count: int, duration: float) -> List[Dict]:
        """
        Generate timing for text overlays synchronized with beats
        
        Args:
            beat_info: BeatInfo from detect_bpm()
            text_count: Number of text segments
            duration: Total video duration
        
        Returns:
            List of dicts with 'start' and 'end' times for each text
        """
        beats = beat_info.beat_times
        bpm = beat_info.bpm
        
        if not beats:
            # Fallback to even distribution
            segment_duration = duration / text_count
            return [
                {"start": i * segment_duration, "end": (i + 1) * segment_duration}
                for i in range(text_count)
            ]
        
        # Calculate beats per text segment
        beats_per_text = max(1, len(beats) // text_count)
        
        timings = []
        for i in range(text_count):
            start_idx = i * beats_per_text
            end_idx = min((i + 1) * beats_per_text, len(beats) - 1)
            
            if start_idx < len(beats):
                start_time = beats[start_idx]
                end_time = beats[end_idx] if end_idx < len(beats) else duration
                timings.append({"start": start_time, "end": end_time})
            else:
                # Distribute remaining
                remaining = duration - (timings[-1]['end'] if timings else 0)
                timings.append({"start": timings[-1]['end'] if timings else 0, "end": duration})
        
        return timings
    
    def generate_beat_sync_text_animation(self, text: str, beat_info: BeatInfo, beat_offset: int = 0) -> str:
        """
        Generate FFmpeg filter for beat-synced text animation
        
        Args:
            text: Text to display
            beat_info: BeatInfo from detect_bpm()
            beat_offset: Which beat to sync with (0 = first beat)
        
        Returns:
            FFmpeg drawtext filter string with beat-synced animation
        """
        beats = beat_info.beat_times
        bpm = beat_info.bpm
        
        if not beats or len(beats) <= beat_offset:
            # No beat data, return basic text
            return f"drawtext=text='{text}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2"
        
        target_beat = beats[beat_offset]
        beat_interval = 60 / bpm if bpm > 0 else 0.5
        
        # Create animation that pulses on beat
        # Using expression to scale text size based on time since last beat
        animation = f"fontsize='48 + 10*abs(sin(2*PI*({beat_interval}*floor((t-{target_beat})/{beat_interval}) - (t-{target_beat}))))'"
        
        return f"drawtext=text='{text}':{animation}:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2"
    
    def create_beat_visualizer(self, audio_path: str, output_path: str, width: int = 1080, height: int = 200) -> str:
        """
        Create a beat visualization bar that pulses with music
        
        Args:
            audio_path: Path to audio file
            output_path: Output video path for visualizer
            width: Width of visualizer
            height: Height of visualizer
        
        Returns:
            Path to generated visualizer video
        """
        beat_info = self.detect_bpm(audio_path)
        
        if not beat_info:
            return None
        
        # Generate visualization using showwaves filter
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        # Create waveform visualization
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-filter_complex", 
            f"showwavespic=s={width}x{height}:colors=0x00FF00|0x0000FF",
            "-frames:v", "1",
            str(output)
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return str(output)
        except subprocess.CalledProcessError as e:
            logger.error(f"Visualizer error: {e}")
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


# ============ COMMAND LINE TOOL ============
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Beat Detection Tool")
    parser.add_argument("audio_path", help="Path to audio file")
    parser.add_argument("--madmom", action="store_true", help="Use madmom for better accuracy")
    
    args = parser.parse_args()
    
    detector = BeatDetector()
    beat_info = detector.detect_bpm(args.audio_path, use_madmom=args.madmom)
    
    if beat_info:
        print(f"\n=== BEAT DETECTION RESULTS ===")
        print(f"BPM: {beat_info.bpm:.1f}")
        print(f"Method: {beat_info.method}")
        print(f"Confidence: {beat_info.confidence:.0%}")
        print(f"Beats detected: {len(beat_info.beat_times)}")
        print(f"First 10 beats: {[f'{t:.2f}' for t in beat_info.beat_times[:10]]}")
        
        # Generate sync timings for 5 text segments
        timings = detector.get_beat_sync_timings(beat_info, 5, 30)
        print(f"\nText sync timings (5 segments, 30s video):")
        for i, timing in enumerate(timings):
            print(f"  Text {i+1}: {timing['start']:.2f}s - {timing['end']:.2f}s")
    
    detector.cleanup()