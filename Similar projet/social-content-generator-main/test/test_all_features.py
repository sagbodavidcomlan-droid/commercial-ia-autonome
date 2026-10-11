#!/usr/bin/env python3
"""
Test all features of the advanced renderer
"""

import json
import subprocess
import sys
from pathlib import Path

def test_zodiac_template(zodiac_sign):
    """Test a specific zodiac template"""
    test_input = {
        "id": f"test_{zodiac_sign}",
        "template": "motivational",
        "zodiac_sign": zodiac_sign,
        "text_1": f"{zodiac_sign.upper()} Zodiac",
        "text_2": "Today's Energy Is High",
        "text_3": "Success Is Coming Your Way",
        "text_4": "Stay Positive",
        "text_5": f"✨ #{zodiac_sign}",
        "animation": "zoom_fan",
        "text_effect": "rainbow",
        "transition": "center",
        "watermark_enabled": True,
        "watermark_text": f"♈ {zodiac_sign}",
        "watermark_position": "bottom_center",
        "logo_enabled": True,
        "logo_text": "@zodiacdaily",
        "logo_position": "top_right"
    }
    
    print(f"\n--- Testing {zodiac_sign.upper()} ---")
    result = subprocess.run(
        [sys.executable, "scripts/advanced_render.py", json.dumps(test_input)],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        output = json.loads(result.stdout)
        print(f"✅ SUCCESS: {output['video_path']}")
        return True
    else:
        print(f"❌ FAILED: {result.stderr[:200]}")
        return False

def test_all_features():
    """Test each feature individually"""
    features = [
        {"name": "Fade animation", "animation": "fade"},
        {"name": "Zoom fan animation", "animation": "zoom_fan"},
        {"name": "Blur animation", "animation": "blur"},
        {"name": "Rainbow effect", "text_effect": "rainbow"},
        {"name": "Shadow effect", "text_effect": "shadow"},
        {"name": "Blink effect", "text_effect": "blink"},
        {"name": "Box effect", "text_effect": "box"},
        {"name": "Scrolling left", "scrolling": True, "scrolling_direction": "left"},
        {"name": "Scrolling right", "scrolling": True, "scrolling_direction": "right"},
        {"name": "Scrolling up", "scrolling": True, "scrolling_direction": "up"},
        {"name": "Scrolling down", "scrolling": True, "scrolling_direction": "down"},
    ]
    
    results = []
    for feature in features:
        test_input = {
            "id": f"test_feature",
            "template": "motivational",
            "text_1": f"Testing: {feature['name']}",
            "text_2": "This is a test of the feature",
            **{k: v for k, v in feature.items() if k != "name"}
        }
        
        print(f"\n--- Testing {feature['name']} ---")
        result = subprocess.run(
            [sys.executable, "scripts/advanced_render.py", json.dumps(test_input)],
            capture_output=True, text=True
        )
        
        success = result.returncode == 0
        results.append(success)
        print(f"{'✅' if success else '❌'} {feature['name']}")
    
    return all(results)

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING ALL FEATURES")
    print("=" * 60)
    
    # Test all zodiacs
    zodiacs = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", 
               "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]
    
    zodiac_results = []
    for zodiac in zodiacs:
        zodiac_results.append(test_zodiac_template(zodiac))
    
    # Test all features
    features_ok = test_all_features()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Zodiac templates: {sum(zodiac_results)}/{len(zodiacs)} passed")
    print(f"Features: {'✅ PASSED' if features_ok else '❌ FAILED'}")
    print("=" * 60)