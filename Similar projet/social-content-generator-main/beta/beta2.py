#!/usr/bin/env python3
"""
Social Media Auto Content System - BETA 2
Web Application with Flask
No Nuelink required - FIXED VERSION
"""

import os
import json
import threading
import subprocess
import shutil
import secrets
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from flask import Flask, render_template, request, jsonify, send_file, session
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ============ Configuration ============

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app)

# Paths
BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = BASE_DIR / "output"
ASSETS_FOLDER = BASE_DIR / "assets"
MUSIC_FOLDER = ASSETS_FOLDER / "music"

# Create directories
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, ASSETS_FOLDER, MUSIC_FOLDER]:
    folder.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'mp4', 'ogg'}

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# ============ Global State (using class to avoid nonlocal issues) ============

class AppState:
    """Global application state"""
    def __init__(self):
        self.current_video_path = None
        self.content_queue = []
        self.history = []
        self.is_generating = False
        self.generation_progress = 0
    
    def add_to_history(self, video_path: str, text_preview: str, template: str):
        """Add item to history"""
        self.history.append({
            "date": datetime.now().isoformat(),
            "video_path": video_path,
            "template": template,
            "text_preview": text_preview[:100],
            "status": "generated"
        })
        # Keep last 100
        while len(self.history) > 100:
            self.history.pop(0)
    
    def clear_history(self):
        """Clear all history"""
        self.history = []
    
    def add_to_queue(self, item: dict):
        """Add item to queue"""
        item["created_at"] = datetime.now().isoformat()
        self.content_queue.append(item)
    
    def remove_from_queue(self, index: int):
        """Remove item from queue"""
        if 0 <= index < len(self.content_queue):
            return self.content_queue.pop(index)
        return None
    
    def clear_queue(self):
        """Clear all queue"""
        self.content_queue = []
    
    def get_queue_size(self):
        return len(self.content_queue)
    
    def get_history_size(self):
        return len(self.history)

# Initialize global state
state = AppState()

# ============ Helper Functions ============

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_zodiac_color(zodiac: str) -> str:
    """Get color for zodiac sign"""
    colors = {
        "aries": "red", "taurus": "green", "gemini": "gold",
        "cancer": "lightblue", "leo": "orange", "virgo": "yellowgreen",
        "libra": "pink", "scorpio": "darkred", "sagittarius": "saddlebrown",
        "capricorn": "darkslategray", "aquarius": "deepskyblue", "pisces": "mediumpurple"
    }
    return colors.get(zodiac.lower(), "white")

def generate_video_sync(texts: List[str], template: str, zodiac: str, keyword: str, music_path: str = None) -> Optional[str]:
    """
    Generate video synchronously (blocking)
    Returns path to generated video or None
    """
    if not texts:
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_FOLDER / f"video_{timestamp}.mp4"
    
    # Get text color
    if template == "zodiac_dark" and zodiac:
        text_color = get_zodiac_color(zodiac)
    else:
        text_color = "white"
    
    duration_per_text = 5
    total_duration = len(texts) * duration_per_text
    
    # Create temp directory for segments
    temp_dir = BASE_DIR / f"temp_{timestamp}"
    temp_dir.mkdir(exist_ok=True)
    
    segment_files = []
    success = True
    
    try:
        # Generate each text segment
        for i, text in enumerate(texts):
            if not text or not text.strip():
                continue
            
            segment_path = temp_dir / f"segment_{i}.mp4"
            segment_files.append(segment_path)
            
            # Escape text for FFmpeg
            escaped_text = text.replace("'", "'\\''").replace(":", "\\:").replace("=", "\\=")
            
            # FFmpeg command for single segment
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:d={duration_per_text}",
                "-vf", f"drawtext=text='{escaped_text}':fontcolor={text_color}:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-t", str(duration_per_text),
                str(segment_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0 or not segment_path.exists():
                print(f"Segment {i} failed: {result.stderr}")
                success = False
                break
        
        if success and segment_files:
            # Create concat file
            concat_file = temp_dir / "concat.txt"
            with open(concat_file, "w") as f:
                for seg in segment_files:
                    f.write(f"file '{seg}'\n")
            
            # Concatenate all segments
            concat_cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                str(output_path)
            ]
            
            result = subprocess.run(concat_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Concat failed: {result.stderr}")
                success = False
        
        if success and output_path.exists():
            return str(output_path)
        else:
            return None
            
    except Exception as e:
        print(f"Video generation error: {e}")
        return None
        
    finally:
        # Cleanup temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def generate_video_async(texts: List[str], template: str, zodiac: str, keyword: str, music_path: str = None):
    """Generate video in background thread"""
    global state
    
    state.is_generating = True
    state.generation_progress = 0
    
    try:
        output_path = generate_video_sync(texts, template, zodiac, keyword, music_path)
        
        if output_path:
            state.current_video_path = output_path
            state.add_to_history(output_path, texts[0] if texts else "", template)
            print(f"Video generated: {output_path}")
        else:
            print("Video generation failed")
            
    except Exception as e:
        print(f"Generation error: {e}")
        
    finally:
        state.is_generating = False
        state.generation_progress = 100


# ============ Routes ============

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('beta2_dashboard.html')


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Get or update configuration"""
    config_file = BASE_DIR / "config.json"
    
    if request.method == 'GET':
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            return jsonify(config)
        else:
            # Return default config
            default_config = {
                "features": {
                    "video_generation": {"enabled": True, "max_duration": 60},
                    "music": {"enabled": True, "default_volume": 0.7}
                }
            }
            return jsonify(default_config)
    
    elif request.method == 'POST':
        data = request.json
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)
        return jsonify({"status": "success", "message": "Configuration saved"})


@app.route('/api/generate', methods=['POST'])
def api_generate():
    """Start video generation"""
    global state
    
    if state.is_generating:
        return jsonify({"status": "error", "message": "Already generating a video"}), 409
    
    data = request.json
    texts = [data.get(f'text_{i}', '') for i in range(1, 6)]
    texts = [t for t in texts if t and t.strip()]
    
    if not texts:
        return jsonify({"status": "error", "message": "No text provided"}), 400
    
    template = data.get('template', 'motivational')
    zodiac = data.get('zodiac', 'leo')
    keyword = data.get('keyword', 'nature beautiful')
    music_path = data.get('music_path')
    
    # Start generation in background
    thread = threading.Thread(
        target=generate_video_async,
        args=(texts, template, zodiac, keyword, music_path)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "status": "success",
        "message": "Video generation started"
    })


@app.route('/api/status', methods=['GET'])
def api_status():
    """Get current status"""
    return jsonify({
        "current_video": state.current_video_path,
        "is_generating": state.is_generating,
        "progress": state.generation_progress,
        "queue_size": state.get_queue_size(),
        "history_size": state.get_history_size()
    })


@app.route('/api/preview', methods=['GET'])
def api_preview():
    """Get video preview URL"""
    if state.current_video_path and Path(state.current_video_path).exists():
        filename = Path(state.current_video_path).name
        return jsonify({"video_url": f"/video/{filename}"})
    return jsonify({"error": "No video available"}), 404


@app.route('/video/<filename>')
def serve_video(filename):
    """Serve generated video"""
    video_path = OUTPUT_FOLDER / filename
    if video_path.exists():
        return send_file(video_path, mimetype='video/mp4')
    return "Video not found", 404


@app.route('/api/queue', methods=['GET', 'POST', 'DELETE'])
def api_queue():
    """Manage content queue"""
    global state
    
    if request.method == 'GET':
        return jsonify(state.content_queue)
    
    elif request.method == 'POST':
        item = request.json
        state.add_to_queue(item)
        return jsonify({"status": "success", "queue_size": state.get_queue_size()})
    
    elif request.method == 'DELETE':
        index = request.args.get('index', type=int)
        if index is not None:
            removed = state.remove_from_queue(index)
            if removed:
                return jsonify({"status": "success", "removed": removed})
        return jsonify({"status": "error", "message": "Invalid index"}), 400


@app.route('/api/queue/clear', methods=['POST'])
def api_queue_clear():
    """Clear all queue"""
    global state
    state.clear_queue()
    return jsonify({"status": "success"})


@app.route('/api/queue/process', methods=['POST'])
def api_process_queue():
    """Process all items in queue"""
    global state
    
    if state.is_generating:
        return jsonify({"status": "error", "message": "Already generating"}), 409
    
    def process():
        queue_copy = state.content_queue.copy()
        state.clear_queue()
        
        for item in queue_copy:
            texts = item.get('texts', [])
            texts = [t for t in texts if t and t.strip()]
            if texts:
                generate_video_sync(
                    texts=texts,
                    template=item.get('template', 'motivational'),
                    zodiac=item.get('zodiac', 'leo'),
                    keyword=item.get('keyword', 'nature beautiful'),
                    music_path=item.get('music')
                )
    
    thread = threading.Thread(target=process)
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "success", "message": "Queue processing started"})


@app.route('/api/history', methods=['GET', 'DELETE'])
def api_history():
    """Get or clear history"""
    global state
    
    if request.method == 'GET':
        return jsonify(state.history)
    
    elif request.method == 'DELETE':
        state.clear_history()
        return jsonify({"status": "success"})


@app.route('/api/history/export', methods=['GET'])
def api_history_export():
    """Export history to CSV"""
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Template", "Text Preview", "Status", "Video Path"])
    
    for item in state.history:
        writer.writerow([
            item.get("date", ""),
            item.get("template", ""),
            item.get("text_preview", ""),
            item.get("status", ""),
            item.get("video_path", "")
        ])
    
    response = app.response_class(
        response=output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=history.csv'}
    )
    return response


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Upload music file"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_name = f"{timestamp}_{filename}"
        filepath = UPLOAD_FOLDER / saved_name
        file.save(filepath)
        return jsonify({
            "status": "success",
            "path": str(filepath),
            "filename": saved_name
        })
    
    return jsonify({"error": "File type not allowed"}), 400


@app.route('/api/music/list', methods=['GET'])
def api_music_list():
    """List available music files"""
    music_files = []
    for ext in ['*.mp3', '*.wav', '*.m4a', '*.ogg']:
        for file in MUSIC_FOLDER.glob(ext):
            music_files.append({
                "name": file.name,
                "path": str(file),
                "size_kb": round(file.stat().st_size / 1024, 2)
            })
    return jsonify(music_files)


@app.route('/api/post', methods=['POST'])
def api_post():
    """Post video to social media (placeholder)"""
    data = request.json
    platform = data.get('platform')
    caption = data.get('caption', '')
    hashtags = data.get('hashtags', '')
    
    if not state.current_video_path:
        return jsonify({"error": "No video to post"}), 400
    
    full_caption = f"{caption}\n\n{hashtags}" if hashtags else caption
    
    # Placeholder - actual posting would require browser automation
    return jsonify({
        "status": "success",
        "message": f"Video ready for posting to {platform}",
        "video_path": state.current_video_path,
        "caption": full_caption
    })


@app.route('/api/cleanup', methods=['POST'])
def api_cleanup():
    """Clean up old files"""
    days = request.json.get('days', 7)
    cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
    
    deleted_count = 0
    for video_file in OUTPUT_FOLDER.glob("*.mp4"):
        if video_file.stat().st_mtime < cutoff_date:
            try:
                video_file.unlink()
                deleted_count += 1
            except:
                pass
    
    return jsonify({
        "status": "success",
        "deleted_count": deleted_count,
        "message": f"Deleted {deleted_count} old videos"
    })


@app.route('/api/diagnostics', methods=['GET'])
def api_diagnostics():
    """Run diagnostics"""
    results = {}
    
    # Check FFmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        results["ffmpeg"] = {
            "status": "ok" if result.returncode == 0 else "error",
            "version": result.stdout.split('\n')[0] if result.returncode == 0 else None
        }
    except FileNotFoundError:
        results["ffmpeg"] = {"status": "error", "message": "FFmpeg not found in PATH"}
    
    # Check directories
    results["directories"] = {}
    for name, path in [("output", OUTPUT_FOLDER), ("uploads", UPLOAD_FOLDER), ("assets", ASSETS_FOLDER)]:
        results["directories"][name] = {"exists": path.exists()}
    
    # Check disk space
    try:
        import shutil
        disk_usage = shutil.disk_usage(BASE_DIR)
        results["disk"] = {
            "free_gb": round(disk_usage.free / (1024**3), 2),
            "total_gb": round(disk_usage.total / (1024**3), 2)
        }
    except:
        results["disk"] = {"error": "Could not get disk info"}
    
    return jsonify(results)


# ============ Main Entry Point ============

def create_template_file():
    """Create HTML template if not exists"""
    template_dir = BASE_DIR / "templates"
    template_dir.mkdir(exist_ok=True)
    
    template_file = template_dir / "beta2_dashboard.html"
    
    if not template_file.exists():
        # Create a minimal HTML template
        html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Social Media Auto Content - Beta 2</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; }
        h1 { color: #333; }
        .status-bar { background: #e0e0e0; border-radius: 5px; height: 20px; margin: 10px 0; overflow: hidden; }
        .status-progress { background: #4CAF50; height: 100%; width: 0%; transition: width 0.3s; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .card { background: white; border-radius: 10px; padding: 20px; }
        .card h2 { margin-bottom: 15px; }
        input, select, textarea { width: 100%; padding: 10px; margin: 5px 0 15px; border: 1px solid #ddd; border-radius: 5px; }
        button { background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        button:hover { background: #5a67d8; }
        .video-preview { margin-top: 15px; text-align: center; }
        video { max-width: 100%; border-radius: 10px; }
        .queue-item, .history-item { padding: 10px; border-bottom: 1px solid #eee; }
        .toast { position: fixed; bottom: 20px; right: 20px; background: #333; color: white; padding: 12px 20px; border-radius: 8px; display: none; z-index: 1000; }
        .toast.success { background: #4CAF50; }
        .toast.error { background: #f44336; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Social Media Auto Content - Beta 2</h1>
            <p>Web Application | No Nuelink Required</p>
            <div class="status-bar"><div class="status-progress" id="progressBar"></div></div>
        </div>
        <div class="grid">
            <div class="card">
                <h2>Content Creator</h2>
                <select id="template"><option value="motivational">Motivational</option><option value="zodiac_dark">Zodiac Dark</option><option value="educational">Educational</option></select>
                <select id="zodiac"><option value="leo">Leo</option><option value="aries">Aries</option><option value="taurus">Taurus</option><option value="gemini">Gemini</option><option value="cancer">Cancer</option><option value="virgo">Virgo</option><option value="libra">Libra</option><option value="scorpio">Scorpio</option><option value="sagittarius">Sagittarius</option><option value="capricorn">Capricorn</option><option value="aquarius">Aquarius</option><option value="pisces">Pisces</option></select>
                <input type="text" id="text1" placeholder="Text Line 1">
                <input type="text" id="text2" placeholder="Text Line 2">
                <input type="text" id="text3" placeholder="Text Line 3">
                <input type="text" id="keyword" placeholder="Background keyword" value="nature">
                <button onclick="generateVideo()">Generate Video</button>
                <button onclick="addToQueue()">Add to Queue</button>
            </div>
            <div class="card">
                <h2>Preview</h2>
                <div class="video-preview" id="preview">No video yet</div>
                <button onclick="refreshPreview()">Refresh</button>
                <button onclick="postVideo('youtube')">Post to YouTube</button>
            </div>
        </div>
        <div class="card"><h2>Queue</h2><div id="queueList"></div><button onclick="processQueue()">Process Queue</button></div>
        <div class="card"><h2>History</h2><div id="historyList"></div></div>
    </div>
    <div id="toast" class="toast"></div>
    <script>
        function showToast(msg, type){var t=document.getElementById('toast');t.textContent=msg;t.className='toast '+type;t.style.display='block';setTimeout(()=>t.style.display='none',3000);}
        async function generateVideo(){showToast('Generating...','success');var texts={text1:document.getElementById('text1').value,text2:document.getElementById('text2').value,text3:document.getElementById('text3').value};await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({template:document.getElementById('template').value,zodiac:document.getElementById('zodiac').value,text_1:texts.text1,text_2:texts.text2,text_3:texts.text3,keyword:document.getElementById('keyword').value})});setTimeout(refreshPreview,3000);}
        async function refreshPreview(){var r=await fetch('/api/preview');var d=await r.json();if(d.video_url){document.getElementById('preview').innerHTML='<video width="100%" controls><source src="'+d.video_url+'" type="video/mp4"></video>';showToast('Preview loaded','success');}else{document.getElementById('preview').innerHTML='<p>No video yet</p>';}}
        async function addToQueue(){var texts=[document.getElementById('text1').value,document.getElementById('text2').value,document.getElementById('text3').value].filter(t=>t);if(texts.length===0){showToast('Enter text first','error');return;}await fetch('/api/queue',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({texts:texts,template:document.getElementById('template').value,zodiac:document.getElementById('zodiac').value,keyword:document.getElementById('keyword').value})});showToast('Added to queue','success');loadQueue();}
        async function loadQueue(){var r=await fetch('/api/queue');var q=await r.json();var div=document.getElementById('queueList');if(q.length===0)div.innerHTML='<p>Queue empty</p>';else div.innerHTML=q.map((i,idx)=>'<div class="queue-item">'+i.texts[0]+'<button onclick="removeFromQueue('+idx+')">Remove</button></div>').join('');}
        async function removeFromQueue(idx){await fetch('/api/queue?index='+idx,{method:'DELETE'});loadQueue();showToast('Removed','success');}
        async function processQueue(){await fetch('/api/queue/process',{method:'POST'});showToast('Processing queue...','success');setTimeout(loadQueue,2000);}
        async function loadHistory(){var r=await fetch('/api/history');var h=await r.json();var div=document.getElementById('historyList');if(h.length===0)div.innerHTML='<p>No history</p>';else div.innerHTML=h.slice().reverse().map(i=>'<div class="history-item">'+i.text_preview+'<br><small>'+new Date(i.date).toLocaleString()+'</small></div>').join('');}
        async function postVideo(platform){var r=await fetch('/api/post',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({platform:platform,caption:'',hashtags:''})});var d=await r.json();showToast(d.message,'success');}
        async function updateStatus(){var r=await fetch('/api/status');var d=await r.json();if(d.is_generating)document.getElementById('progressBar').style.width=d.progress+'%';}
        setInterval(updateStatus,1000);setInterval(loadQueue,3000);setInterval(loadHistory,5000);refreshPreview();loadQueue();loadHistory();
    </script>
</body>
</html>'''
        
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Created template: {template_file}")


if __name__ == '__main__':
    create_template_file()
    print("=" * 50)
    print("Social Media Auto Content - Beta 2")
    print("Web Application Started")
    print("=" * 50)
    print(f"Access at: http://localhost:5000")
    print(f"Output folder: {OUTPUT_FOLDER}")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
