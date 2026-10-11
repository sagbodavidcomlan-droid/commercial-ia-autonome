#!/usr/bin/env python3
"""
Debugging System - Test all components
Run: python scripts/debug_system.py
"""

import os
import sys
import json
import subprocess
import requests
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_test(name, status, message=""):
    """Print test result"""
    symbol = f"{GREEN}✓{RESET}" if status else f"{RED}✗{RESET}"
    print(f"  {symbol} {name}")
    if message and not status:
        print(f"    {RED}→ {message}{RESET}")

def run_test():
    """Run all debug tests"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}🔍 SOCIAL MEDIA AUTO CONTENT - DEBUG SYSTEM{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    results = []
    
    # Test 1: Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    python_ok = sys.version_info.major >= 3 and sys.version_info.minor >= 8
    print_test(f"Python {python_version}", python_ok, "Need Python 3.8+")
    results.append(python_ok)
    
    # Test 2: FFmpeg
    try:
        ffmpeg_result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        ffmpeg_ok = ffmpeg_result.returncode == 0
        if ffmpeg_ok:
            version_line = ffmpeg_result.stdout.split('\n')[0][:50]
            print_test(f"FFmpeg: {version_line}", True)
        else:
            print_test("FFmpeg", False, "Install: sudo apt install ffmpeg")
    except FileNotFoundError:
        print_test("FFmpeg", False, "Install: sudo apt install ffmpeg")
        ffmpeg_ok = False
    results.append(ffmpeg_ok)
    
    # Test 3: Required packages
    required_packages = ["moviepy", "requests", "Pillow", "numpy"]
    missing_packages = []
    for pkg in required_packages:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing_packages.append(pkg)
    
    packages_ok = len(missing_packages) == 0
    print_test("Python packages", packages_ok, f"Missing: {', '.join(missing_packages)}" if missing_packages else "")
    results.append(packages_ok)
    
    # Test 4: Environment variables
    env_vars = ["PEXELS_API_KEY", "PIXABAY_API_KEY", "NUELINK_API_KEY"]
    env_status = {}
    for var in env_vars:
        value = os.getenv(var)
        env_status[var] = value and value != "your_xxx_api_key_here"
        print_test(f"ENV: {var}", env_status[var], "Not set or still default" if not env_status[var] else "")
    results.append(all(env_status.values()))
    
    # Test 5: Folder structure
    required_folders = [
        "assets/videos", "assets/images", "assets/music",
        "assets_cache", "output/videos", "output/logs",
        "templates", "scripts"
    ]
    missing_folders = []
    for folder in required_folders:
        if not Path(folder).exists():
            missing_folders.append(folder)
    
    folders_ok = len(missing_folders) == 0
    print_test("Folder structure", folders_ok, f"Missing: {', '.join(missing_folders)}" if missing_folders else "")
    results.append(folders_ok)
    
    # Test 6: API connectivity
    api_tests = []
    
    # Pexels API test
    pexels_key = os.getenv("PEXELS_API_KEY")
    if pexels_key and pexels_key != "your_pexels_api_key_here":
        try:
            response = requests.get(
                "https://api.pexels.com/videos/search?query=nature&per_page=1",
                headers={"Authorization": pexels_key},
                timeout=5
            )
            pexels_ok = response.status_code == 200
            print_test("Pexels API", pexels_ok, f"HTTP {response.status_code}" if not pexels_ok else "")
            api_tests.append(pexels_ok)
        except Exception as e:
            print_test("Pexels API", False, str(e)[:50])
            api_tests.append(False)
    else:
        print_test("Pexels API", False, "API key not configured")
        api_tests.append(False)
    
    # Pixabay API test
    pixabay_key = os.getenv("PIXABAY_API_KEY")
    if pixabay_key and pixabay_key != "your_pixabay_api_key_here":
        try:
            response = requests.get(
                f"https://pixabay.com/api/v2/music/search/?key={pixabay_key}&q=upbeat&limit=1",
                timeout=5
            )
            pixabay_ok = response.status_code == 200
            print_test("Pixabay API", pixabay_ok, f"HTTP {response.status_code}" if not pixabay_ok else "")
            api_tests.append(pixabay_ok)
        except Exception as e:
            print_test("Pixabay API", False, str(e)[:50])
            api_tests.append(False)
    else:
        print_test("Pixabay API", False, "API key not configured")
        api_tests.append(False)
    
    results.append(all(api_tests) if api_tests else False)
    
    # Test 7: FFmpeg drawtext capability
    try:
        test_cmd = [
            "ffmpeg", "-f", "lavfi", "-i", "color=c=black:s=100x100:d=1",
            "-vf", "drawtext=text='Test':fontsize=20",
            "-f", "null", "-"
        ]
        ffmpeg_drawtext = subprocess.run(test_cmd, capture_output=True, timeout=5)
        drawtext_ok = ffmpeg_drawtext.returncode == 0
        print_test("FFmpeg drawtext", drawtext_ok, "FFmpeg may need fontconfig" if not drawtext_ok else "")
    except Exception:
        drawtext_ok = False
        print_test("FFmpeg drawtext", False, "Test failed")
    results.append(drawtext_ok)
    
    # Test 8: Disk space
    import shutil
    disk_usage = shutil.disk_usage("/")
    free_gb = disk_usage.free / (1024**3)
    disk_ok = free_gb > 5
    print_test(f"Disk space: {free_gb:.1f} GB free", disk_ok, "Need at least 5GB free" if not disk_ok else "")
    results.append(disk_ok)
    
    # Test 9: Memory
    try:
        with open("/proc/meminfo", "r") as f:
            meminfo = f.read()
        for line in meminfo.split("\n"):
            if "MemAvailable:" in line:
                mem_available = int(line.split()[1]) / (1024**2)
                mem_ok = mem_available > 1
                print_test(f"Memory: {mem_available:.1f} GB available", mem_ok, "Need at least 1GB free" if not mem_ok else "")
                results.append(mem_ok)
                break
    except:
        results.append(True)  # Skip on non-Linux
    
    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"{GREEN}✅ ALL TESTS PASSED! System is ready.{RESET}")
        print(f"\n{YELLOW}Next steps:{RESET}")
        print("  1. Run: python test_local.py")
        print("  2. Start: docker-compose up -d")
        print("  3. Access n8n at http://localhost:5678")
    else:
        print(f"{RED}❌ {total - passed} test(s) failed.{RESET}")
        print(f"\n{YELLOW}To fix:{RESET}")
        if not ffmpeg_ok:
            print("  • Install FFmpeg: sudo apt install ffmpeg")
        if missing_packages:
            print(f"  • Install packages: pip install {' '.join(missing_packages)}")
        if not all(env_status.values()):
            print("  • Configure .env file with API keys")
        if not folders_ok:
            print(f"  • Create missing folders: mkdir -p {' '.join(missing_folders)}")
        if not drawtext_ok:
            print("  • Install fonts: sudo apt install fonts-liberation")
    
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    return passed == total

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
