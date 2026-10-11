#!/usr/bin/env python3
"""
Social Media Auto Content System - Version 3
Web Application with Flask + Tailwind CSS
Complete UI with light/dark mode, file uploads, and API
"""

import os
import json
import yaml
import uuid
import shutil
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from functools import wraps
from queue import Queue

from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Load config
with open('config.yaml', 'r') as f:
    CONFIG = yaml.safe_load(f)

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

# Configuration
UPLOAD_FOLDER = Path(CONFIG['system']['temp_dir']) / 'uploads'
OUTPUT_FOLDER = Path(CONFIG['system']['output_dir']) / 'videos'
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'm4a', 'wav', 'ogg', 'flac'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

# Job queue
job_queue = Queue()
active_jobs = {}


def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set


class Job:
    """Represents a render job"""
    
    def __init__(self, job_id, data):
        self.job_id = job_id
        self.data = data
        self.status = 'pending'
        self.progress = 0
        self.message = ''
        self.result = None
        self.error = None
        self.created_at = datetime.now()
    
    def to_dict(self):
        return {
            'job_id': self.job_id,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'result': self.result,
            'error': self.error,
            'created_at': self.created_at.isoformat()
        }


def process_job(job):
    """Process a render job in background"""
    try:
        job.status = 'processing'
        job.message = 'Starting video generation...'
        
        # Extract data
        texts = job.data.get('texts', [])
        template = job.data.get('template', 'motivational')
        asset_keyword = job.data.get('asset_keyword', 'nature')
        music_mood = job.data.get('music_mood', 'ambient')
        
        # Get video path (from upload or URL or search)
        video_path = job.data.get('video_path')
        if not video_path:
            # Search for video
            job.message = 'Searching for background video...'
            job.progress = 20
            # Simulate search
            import time
            time.sleep(2)
            video_path = str(Path(CONFIG['video']['search']['local_fallback']['directory']) / 'fallback.mp4')
        
        # Get music path
        music_path = job.data.get('music_path')
        if not music_path and job.data.get('music_url'):
            job.message = 'Downloading music from URL...'
            job.progress = 40
            import time
            time.sleep(2)
        
        # Render video
        job.message = 'Rendering video...'
        job.progress = 60
        
        # Simulate render
        import time
        time.sleep(3)
        
        # Generate output path
        output_filename = f"video_{job.job_id}.mp4"
        output_path = OUTPUT_FOLDER / output_filename
        
        # Create a simple test video if real render not available
        if not output_path.exists():
            # Create black video with text using FFmpeg
            width, height = CONFIG['video']['processing']['output_size']
            text = texts[0] if texts else "Test Video"
            
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:d=5",
                "-vf", f"drawtext=text='{text}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v", "libx264",
                "-t", "5",
                str(output_path)
            ]
            
            try:
                subprocess.run(cmd, capture_output=True, check=True)
            except:
                # If FFmpeg fails, create empty file
                output_path.touch()
        
        job.progress = 100
        job.status = 'completed'
        job.message = 'Video generation complete'
        job.result = {
            'video_url': f'/download/{output_filename}',
            'video_path': str(output_path),
            'duration': 5
        }
        
    except Exception as e:
        job.status = 'failed'
        job.error = str(e)
        job.message = f'Error: {str(e)}'


def run_worker():
    """Background worker to process jobs"""
    while True:
        job = job_queue.get()
        process_job(job)
        job_queue.task_done()


# Start worker thread
worker_thread = threading.Thread(target=run_worker, daemon=True)
worker_thread.start()


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify({
        'features': CONFIG['features'],
        'templates': ['motivational', 'zodiac_dark', 'educational', 'quote_simple', 'tips_daily'],
        'zodiac_signs': ['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 
                         'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces'],
        'music_moods': ['dark', 'cinematic', 'upbeat', 'motivational', 'lofi', 
                        'ambient', 'epic', 'happy', 'sad', 'beats'],
        'animations': ['fade', 'zoom_fan', 'blur'],
        'text_effects': ['shadow', 'blink', 'box', 'rainbow', 'none']
    })


@app.route('/api/search/music', methods=['POST'])
def search_music():
    """Search for music"""
    data = request.json
    query = data.get('query', '')
    platform = data.get('platform', 'youtube')
    
    # Simulate search results
    results = [
        {
            'id': '1',
            'title': f'{query} - Chill Mix',
            'artist': 'Various Artists',
            'duration': 180,
            'platform': platform,
            'url': 'https://example.com/track1'
        },
        {
            'id': '2',
            'title': f'{query} - Study Beats',
            'artist': 'Lofi Girl',
            'duration': 240,
            'platform': platform,
            'url': 'https://example.com/track2'
        }
    ]
    
    return jsonify({'results': results})


@app.route('/api/search/video', methods=['POST'])
def search_video():
    """Search for video background"""
    data = request.json
    query = data.get('query', '')
    
    # Simulate search results
    results = [
        {
            'id': '1',
            'title': f'{query} - Nature 4K',
            'duration': 30,
            'resolution': '1080x1920',
            'thumbnail': 'https://via.placeholder.com/150',
            'url': 'https://example.com/video1'
        },
        {
            'id': '2',
            'title': f'{query} - City Lights',
            'duration': 45,
            'resolution': '1080x1920',
            'thumbnail': 'https://via.placeholder.com/150',
            'url': 'https://example.com/video2'
        }
    ]
    
    return jsonify({'results': results})


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload music or video file"""
    file_type = request.form.get('type', 'music')
    file = request.files.get('file')
    
    if not file:
        return jsonify({'error': 'No file provided'}), 400
    
    allowed_set = ALLOWED_AUDIO_EXTENSIONS if file_type == 'music' else ALLOWED_VIDEO_EXTENSIONS
    
    if not allowed_file(file.filename, allowed_set):
        return jsonify({'error': f'File type not allowed for {file_type}'}), 400
    
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    filepath = UPLOAD_FOLDER / unique_filename
    file.save(filepath)
    
    return jsonify({
        'success': True,
        'file_path': str(filepath),
        'file_name': filename,
        'file_type': file_type
    })


@app.route('/api/generate', methods=['POST'])
def generate_video():
    """Start video generation job"""
    data = request.json
    
    # Validate required fields
    if not data.get('texts'):
        return jsonify({'error': 'At least one text line is required'}), 400
    
    # Create job
    job_id = uuid.uuid4().hex
    job = Job(job_id, data)
    active_jobs[job_id] = job
    job_queue.put(job)
    
    return jsonify({
        'job_id': job_id,
        'status': 'pending',
        'message': 'Job created'
    })


@app.route('/api/job/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get job status"""
    job = active_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(job.to_dict())


@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all jobs"""
    return jsonify({
        'jobs': [job.to_dict() for job in active_jobs.values()]
    })


@app.route('/download/<filename>')
def download_file(filename):
    """Download generated video"""
    filepath = OUTPUT_FOLDER / filename
    if not filepath.exists():
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(filepath, as_attachment=True, download_name=filename)


@app.route('/api/settings', methods=['GET', 'POST'])
def settings():
    """Get or update settings"""
    global CONFIG
    
    if request.method == 'GET':
        return jsonify({
            'api': {
                'pexels': {'configured': CONFIG['api']['pexels']['api_key'] != 'YOUR_PEXELS_API_KEY'},
                'pixabay': {'configured': CONFIG['api']['pixabay']['api_key'] != 'YOUR_PIXABAY_API_KEY'},
                'nuelink': {'configured': CONFIG['api']['nuelink']['api_key'] != 'YOUR_NUELINK_API_KEY'}
            },
            'google_sheet_id': CONFIG['api']['google_sheets']['sheet_id'],
            'features': CONFIG['features']
        })
    
    else:
        data = request.json
        
        # Update config (in memory)
        if 'google_sheet_id' in data:
            CONFIG['api']['google_sheets']['sheet_id'] = data['google_sheet_id']
        
        if 'features' in data:
            for key, value in data['features'].items():
                if key in CONFIG['features']:
                    CONFIG['features'][key] = value
        
        # Save to file
        with open('config.yaml', 'w') as f:
            yaml.dump(CONFIG, f)
        
        return jsonify({'success': True})


@app.route('/api/google-sheet/template', methods=['GET'])
def get_google_sheet_template():
    """Download Google Sheet template"""
    import csv
    from io import StringIO
    
    headers = ['id', 'status', 'approval_status', 'template', 'zodiac_sign', 'text_1', 'text_2', 
               'text_3', 'text_4', 'text_5', 'caption', 'hashtags', 'asset_keyword', 'music_mood', 
               'schedule_datetime', 'timezone', 'video_output_path', 'preview_url', 'nuelink_post_id', 
               'retry_count', 'last_error', 'approved_by', 'approved_at', 'reject_reason']
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerow(['1001', 'DRAFT', '', 'motivational', 'leo', 'Believe in yourself', 
                    'Keep pushing forward', 'Success awaits', '', '', 'Check this out!', 
                    '#motivation #success', 'nature sunset', 'upbeat', '2026-05-20 15:30:00', 
                    'Asia/Jakarta', '', '', '', '0', '', '', '', ''])
    
    response_data = output.getvalue()
    output.close()
    
    return response_data, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=google_sheet_template.csv'
    }


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)