#!/usr/bin/env python3
"""
Local test script - run this first to verify video rendering works
"""

import json
import subprocess
import sys
from pathlib import Path

def test_ffmpeg():
    """Check FFmpeg is installed"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("✅ FFmpeg found")
        return True
    except:
        print("❌ FFmpeg not found. Install with: sudo apt install ffmpeg")
        return False

def test_render():
    """Test render with sample data"""
    test_input = {
        "id": "test_001",
        "template": "motivational",
        "text_1": "Believe in yourself",
        "text_2": "Keep pushing forward",
        "text_3": "Success awaits",
        "text_4": "",
        "text_5": "",
        "asset_keyword": "sunset ocean",
        "music_mood": "upbeat"
    }
    
    print("\n--- Testing Render ---")
    print(f"Input: {json.dumps(test_input, indent=2)}")
    
    # Run render script
    result = subprocess.run(
        [sys.executable, "scripts/render_video.py", json.dumps(test_input)],
        capture_output=True,
        text=True,
        cwd="project"
    )
    
    print(f"Exit code: {result.returncode}")
    print(f"Stdout: {result.stdout}")
    
    if result.stderr:
        print(f"Stderr: {result.stderr[:500]}")
    
    # Parse output
    try:
        output = json.loads(result.stdout)
        if output.get("status") == "success":
            print(f"\n✅ Render SUCCESS!")
            print(f"   Video path: {output['video_path']}")
            print(f"   Preview URL: {output['preview_url']}")
            return True
        else:
            print(f"\n❌ Render FAILED: {output.get('error_message')}")
            return False
    except json.JSONDecodeError:
        print("\n❌ Failed to parse output")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Social Media Auto Content - Local Test")
    print("=" * 50)
    
    if not test_ffmpeg():
        sys.exit(1)
    
    success = test_render()
    sys.exit(0 if success else 1)