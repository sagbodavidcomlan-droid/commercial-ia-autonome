#!/usr/bin/env python3
"""
Test all music features:
- Local file
- URL download
- Fade in/out
- Full vs background mode
"""

import json
import subprocess
import sys
from pathlib import Path

def test_local_music():
    """Test loading music from local folder"""
    print("\n--- Test 1: Local Music File ---")
    
    # Create a test music file if not exists
    music_dir = Path("project/assets/music")
    music_dir.mkdir(parents=True, exist_ok=True)
    
    test_music = music_dir / "test_music.mp3"
    if not test_music.exists():
        # Generate a simple test tone
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", 
            "sine=frequency=440:duration=10", "-c:a", "libmp3lame",
            str(test_music)
        ], capture_output=True)
    
    test_input = {
        "id": "music_test_1",
        "template": "motivational",
        "text_1": "Testing Local Music",
        "text_2": "With fade in/out effects",
        "music_source": "test_music.mp3",
        "music_mode": "full",
        "music_fade_in": 2,
        "music_fade_out": 2,
        "music_volume": 0.8
    }
    
    result = subprocess.run([
        sys.executable, "scripts/advanced_render_v2.py", json.dumps(test_input)
    ], capture_output=True, text=True)
    
    print(f"Exit code: {result.returncode}")
    print(f"Output: {result.stdout[:200] if result.stdout else 'None'}")
    return result.returncode == 0

def test_url_music():
    """Test downloading music from URL"""
    print("\n--- Test 2: URL Music Download ---")
    
    test_input = {
        "id": "music_test_2",
        "template": "motivational",
        "text_1": "Testing URL Music",
        "text_2": "Downloaded from web",
        "music_source": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        "music_mode": "background",
        "music_fade_in": 1,
        "music_fade_out": 3,
        "music_volume": 0.5
    }
    
    result = subprocess.run([
        sys.executable, "scripts/advanced_render_v2.py", json.dumps(test_input)
    ], capture_output=True, text=True)
    
    print(f"Exit code: {result.returncode}")
    print(f"Output: {result.stdout[:200] if result.stdout else 'None'}")
    return result.returncode == 0

def test_music_modes():
    """Test all music modes"""
    modes = ["background", "full", "trim"]
    results = []
    
    for mode in modes:
        print(f"\n--- Test Mode: {mode} ---")
        test_input = {
            "id": f"music_test_mode_{mode}",
            "template": "motivational",
            "text_1": f"Testing {mode} mode",
            "music_source": "test_music.mp3",
            "music_mode": mode,
            "music_fade_in": 1,
            "music_fade_out": 1
        }
        
        result = subprocess.run([
            sys.executable, "scripts/advanced_render_v2.py", json.dumps(test_input)
        ], capture_output=True, text=True)
        
        success = result.returncode == 0
        results.append(success)
        print(f"{'✅' if success else '❌'} {mode}")
    
    return all(results)

def list_available_music():
    """List all music in folder"""
    print("\n--- Available Music Files ---")
    music_dir = Path("project/assets/music")
    if music_dir.exists():
        for f in music_dir.glob("*"):
            if f.suffix in ['.mp3', '.m4a', '.wav', '.ogg']:
                print(f"  📁 {f.name}")
    else:
        print("  No music folder found")

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING MUSIC FEATURES")
    print("=" * 60)
    
    list_available_music()
    
    # Run tests
    test1 = test_local_music()
    test2 = test_url_music()
    test3 = test_music_modes()
    
    print("\n" + "=" * 60)
    print("MUSIC FEATURES SUMMARY")
    print("=" * 60)
    print(f"Local music:    {'✅' if test1 else '❌'}")
    print(f"URL download:   {'✅' if test2 else '❌'}")
    print(f"Music modes:    {'✅' if test3 else '❌'}")
    print("=" * 60)