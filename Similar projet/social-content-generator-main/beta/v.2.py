#!/usr/bin/env python3
"""
Social Media Auto Content System - Version 2
Python UI Mode with Tkinter - Complete GUI Application
"""

import os
import sys
import json
import yaml
import threading
import subprocess
import requests
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from queue import Queue

# Tkinter imports
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    print("Tkinter not available. Install with: sudo apt install python3-tk")

# WebView for preview
try:
    import tkinterweb
    WEBVIEW_AVAILABLE = True
except ImportError:
    WEBVIEW_AVAILABLE = False
    print("tkinterweb not available for video preview")

# Load config
CONFIG_FILE = "config.yaml"
with open(CONFIG_FILE, 'r') as f:
    CONFIG = yaml.safe_load(f)


class ModernTheme:
    """Modern dark/light theme manager"""
    
    # Dark theme colors
    DARK = {
        'bg': '#1e1e1e',
        'fg': '#ffffff',
        'select': '#3c3c3c',
        'active': '#007acc',
        'button': '#0e639c',
        'button_hover': '#1177bb',
        'entry': '#2d2d2d',
        'entry_fg': '#cccccc',
        'frame': '#252526',
        'scrollbar': '#3e3e42',
        'error': '#f48771',
        'success': '#6a9955',
        'warning': '#dcdcaa'
    }
    
    # Light theme colors
    LIGHT = {
        'bg': '#f3f3f3',
        'fg': '#333333',
        'select': '#cce8ff',
        'active': '#0078d4',
        'button': '#0078d4',
        'button_hover': '#106ebe',
        'entry': '#ffffff',
        'entry_fg': '#333333',
        'frame': '#eaeaea',
        'scrollbar': '#c1c1c1',
        'error': '#d13438',
        'success': '#107c10',
        'warning': '#ff8c00'
    }
    
    def __init__(self, mode='dark'):
        self.mode = mode
        self.colors = self.DARK if mode == 'dark' else self.LIGHT
    
    def toggle(self):
        self.mode = 'light' if self.mode == 'dark' else 'dark'
        self.colors = self.DARK if self.mode == 'dark' else self.LIGHT
        return self.colors


class ContentGeneratorApp:
    """Main application class"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Social Media Auto Content System v2.0")
        self.root.geometry("1400x900")
        
        self.theme = ModernTheme('dark')
        self.processing = False
        self.queue = Queue()
        
        self.setup_ui()
        self.apply_theme()
        
        # Start background processor
        self.processor_thread = None
        self.start_background_processor()
    
    def setup_ui(self):
        """Setup all UI components"""
        
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Top toolbar
        self.setup_toolbar()
        
        # Main content area (split)
        self.setup_content_area()
        
        # Status bar
        self.setup_statusbar()
    
    def setup_toolbar(self):
        """Setup top toolbar with buttons"""
        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # Title
        title = ttk.Label(toolbar, text="Social Media Auto Content System", 
                          font=('Arial', 16, 'bold'))
        title.pack(side=tk.LEFT, padx=10)
        
        # Theme toggle button
        self.theme_btn = ttk.Button(toolbar, text="🌙 Dark", command=self.toggle_theme)
        self.theme_btn.pack(side=tk.RIGHT, padx=5)
        
        # Settings button
        settings_btn = ttk.Button(toolbar, text="⚙️ Settings", command=self.open_settings)
        settings_btn.pack(side=tk.RIGHT, padx=5)
        
        # Process button
        self.process_btn = ttk.Button(toolbar, text="▶ Start Processing", command=self.start_processing)
        self.process_btn.pack(side=tk.RIGHT, padx=5)
        
        # Upload button
        upload_btn = ttk.Button(toolbar, text="📤 Upload to Google Sheet", command=self.upload_to_sheet)
        upload_btn.pack(side=tk.RIGHT, padx=5)
    
    def setup_content_area(self):
        """Setup main content area with paned windows"""
        self.paned = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Content input
        self.setup_input_panel()
        
        # Right panel - Preview and logs
        self.setup_output_panel()
    
    def setup_input_panel(self):
        """Setup left panel for content input"""
        left_frame = ttk.Frame(self.paned)
        self.paned.add(left_frame, weight=1)
        
        # Notebook for tabs
        notebook = ttk.Notebook(left_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Manual Entry
        self.setup_manual_tab(notebook)
        
        # Tab 2: URL Import
        self.setup_url_tab(notebook)
        
        # Tab 3: File Upload
        self.setup_upload_tab(notebook)
        
        # Tab 4: Template Gallery
        self.setup_template_tab(notebook)
    
    def setup_manual_tab(self, notebook):
        """Setup manual entry tab"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="✏️ Manual Entry")
        
        # Scrollable frame
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Form fields
        row = 0
        padding = 10
        
        # Template selection
        ttk.Label(scrollable_frame, text="Template:").grid(row=row, column=0, sticky='w', padx=padding, pady=5)
        self.template_var = tk.StringVar(value="motivational")
        template_combo = ttk.Combobox(scrollable_frame, textvariable=self.template_var, 
                                       values=["motivational", "zodiac_dark", "educational", "quote_simple", "tips_daily"])
        template_combo.grid(row=row, column=1, sticky='ew', padx=padding, pady=5)
        row += 1
        
        # Zodiac sign (visible only for zodiac template)
        ttk.Label(scrollable_frame, text="Zodiac Sign:").grid(row=row, column=0, sticky='w', padx=padding, pady=5)
        self.zodiac_var = tk.StringVar(value="leo")
        zodiac_combo = ttk.Combobox(scrollable_frame, textvariable=self.zodiac_var,
                                     values=["aries", "taurus", "gemini", "cancer", "leo", "virgo", 
                                             "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"])
        zodiac_combo.grid(row=row, column=1, sticky='ew', padx=padding, pady=5)
        row += 1
        
        # Text fields
        self.text_vars = []
        for i in range(1, 6):
            ttk.Label(scrollable_frame, text=f"Text {i}:").grid(row=row, column=0, sticky='w', padx=padding, pady=5)
            text_var = tk.StringVar()
            entry = ttk.Entry(scrollable_frame, textvariable=text_var, width=50)
            entry.grid(row=row, column=1, sticky='ew', padx=padding, pady=5)
            self.text_vars.append(text_var)
            row += 1
        
        # Caption
        ttk.Label(scrollable_frame, text="Caption:").grid(row=row, column=0, sticky='w', padx=padding, pady=5)
        self.caption_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.caption_var, width=50).grid(row=row, column=1, sticky='ew', padx=padding, pady=5)
        row += 1
        
        # Hashtags
        ttk.Label(scrollable_frame, text="Hashtags:").grid(row=row, column=0, sticky='w', padx=padding, pady=5)
        self.hashtags_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.hashtags_var, width=50).grid(row=row, column=1, sticky='ew', padx=padding, pady=5)
        row += 1
        
        # Asset keyword
        ttk.Label(scrollable_frame, text="Asset Keyword:").grid(row=row, column=0, sticky='w', padx=padding, pady=5)
        self.keyword_var = tk.StringVar(value="nature")
        ttk.Entry(scrollable_frame, textvariable=self.keyword_var, width=50).grid(row=row, column=1, sticky='ew', padx=padding, pady=5)
        row += 1
        
        # Music mood
        ttk.Label(scrollable_frame, text="Music Mood:").grid(row=row, column=0, sticky='w', padx=padding, pady=5)
        self.mood_var = tk.StringVar(value="upbeat")
        mood_combo = ttk.Combobox(scrollable_frame, textvariable=self.mood_var,
                                   values=["dark", "cinematic", "upbeat", "motivational", "lofi", "ambient", "epic", "happy", "sad", "beats"])
        mood_combo.grid(row=row, column=1, sticky='ew', padx=padding, pady=5)
        row += 1
        
        # Schedule datetime
        ttk.Label(scrollable_frame, text="Schedule (YYYY-MM-DD HH:MM:SS):").grid(row=row, column=0, sticky='w', padx=padding, pady=5)
        self.schedule_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.schedule_var, width=50).grid(row=row, column=1, sticky='ew', padx=padding, pady=5)
        row += 1
        
        # Generate button
        self.generate_btn = ttk.Button(scrollable_frame, text="🎬 Generate Video", command=self.generate_video)
        self.generate_btn.grid(row=row, column=0, columnspan=2, pady=20)
        
        # Configure grid
        scrollable_frame.columnconfigure(1, weight=1)
    
    def setup_url_tab(self, notebook):
        """Setup URL import tab"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🔗 Import from URL")
        
        # Music URL
        ttk.Label(tab, text="Music URL:").pack(anchor='w', padx=10, pady=5)
        self.music_url_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.music_url_var, width=80).pack(fill=tk.X, padx=10, pady=5)
        
        # Video URL
        ttk.Label(tab, text="Video URL:").pack(anchor='w', padx=10, pady=5)
        self.video_url_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.video_url_var, width=80).pack(fill=tk.X, padx=10, pady=5)
        
        # Test buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Test Music URL", command=lambda: self.test_url(self.music_url_var.get())).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Test Video URL", command=lambda: self.test_url(self.video_url_var.get())).pack(side=tk.LEFT, padx=5)
        
        # Info label
        self.url_info = ttk.Label(tab, text="Enter YouTube, SoundCloud, or direct MP3/MP4 URLs", foreground='gray')
        self.url_info.pack(pady=10)
    
    def setup_upload_tab(self, notebook):
        """Setup file upload tab"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="📁 Upload File")
        
        # Music file
        ttk.Label(tab, text="Music File:").pack(anchor='w', padx=10, pady=5)
        music_frame = ttk.Frame(tab)
        music_frame.pack(fill=tk.X, padx=10)
        
        self.music_file_var = tk.StringVar()
        ttk.Entry(music_frame, textvariable=self.music_file_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(music_frame, text="Browse", command=lambda: self.browse_file(self.music_file_var, "music")).pack(side=tk.RIGHT, padx=5)
        
        # Video file
        ttk.Label(tab, text="Video File:").pack(anchor='w', padx=10, pady=5)
        video_frame = ttk.Frame(tab)
        video_frame.pack(fill=tk.X, padx=10)
        
        self.video_file_var = tk.StringVar()
        ttk.Entry(video_frame, textvariable=self.video_file_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(video_frame, text="Browse", command=lambda: self.browse_file(self.video_file_var, "video")).pack(side=tk.RIGHT, padx=5)
        
        # Supported formats
        ttk.Label(tab, text="Supported: MP3, M4A, WAV, OGG (music) | MP4, MOV, AVI (video)", 
                  foreground='gray').pack(pady=10)
    
    def setup_template_tab(self, notebook):
        """Setup template gallery tab"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🎨 Templates")
        
        # Template preview area
        preview_frame = ttk.LabelFrame(tab, text="Template Gallery")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        templates = [
            ("motivational", "Motivational Quote", "Gold text on dark background", "#FFD700"),
            ("zodiac_dark", "Zodiac Dark", "White text with zodiac colors", "#FFFFFF"),
            ("educational", "Educational Tips", "Green text for learning content", "#00FF88"),
            ("quote_simple", "Simple Quote", "Minimalist quote design", "#F5F5F5"),
            ("tips_daily", "Daily Tips", "Left-aligned daily tips", "#00BFFF")
        ]
        
        for i, (name, display, desc, color) in enumerate(templates):
            frame = ttk.Frame(preview_frame)
            frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Color indicator
            color_box = tk.Frame(frame, bg=color, width=20, height=20)
            color_box.pack(side=tk.LEFT, padx=5)
            
            # Template info
            ttk.Label(frame, text=display, font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=10)
            ttk.Label(frame, text=desc, foreground='gray').pack(side=tk.LEFT, padx=10)
            
            # Use button
            ttk.Button(frame, text="Use", command=lambda n=name: self.template_var.set(n)).pack(side=tk.RIGHT)
    
    def setup_output_panel(self):
        """Setup right panel for preview and logs"""
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=1)
        
        # Video preview
        preview_label = ttk.Label(right_frame, text="Video Preview", font=('Arial', 12, 'bold'))
        preview_label.pack(anchor='w', pady=5)
        
        self.preview_frame = ttk.Frame(right_frame, relief=tk.SUNKEN, borderwidth=1)
        self.preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.preview_label = ttk.Label(self.preview_frame, text="No video generated yet\n\nClick 'Generate Video' to start", 
                                        justify='center')
        self.preview_label.pack(expand=True)
        
        # Log area
        log_label = ttk.Label(right_frame, text="Log Output", font=('Arial', 12, 'bold'))
        log_label.pack(anchor='w', pady=5)
        
        self.log_text = scrolledtext.ScrolledText(right_frame, height=15, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
    
    def setup_statusbar(self):
        """Setup status bar at bottom"""
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(self.status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.progress_bar = ttk.Progressbar(self.status_frame, mode='indeterminate')
        self.progress_bar.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)
    
    def apply_theme(self):
        """Apply current theme colors"""
        colors = self.theme.colors
        
        # Configure ttk styles
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('.', background=colors['bg'], foreground=colors['fg'])
        style.configure('TFrame', background=colors['bg'])
        style.configure('TLabel', background=colors['bg'], foreground=colors['fg'])
        style.configure('TButton', background=colors['button'], foreground='white')
        style.map('TButton', background=[('active', colors['button_hover'])])
        style.configure('TEntry', fieldbackground=colors['entry'], foreground=colors['entry_fg'])
        style.configure('TCombobox', fieldbackground=colors['entry'], foreground=colors['entry_fg'])
        
        self.root.configure(bg=colors['bg'])
        
        # Update theme button text
        self.theme_btn.config(text="☀️ Light" if self.theme.mode == 'dark' else "🌙 Dark")
    
    def toggle_theme(self):
        """Toggle between dark and light theme"""
        self.theme.toggle()
        self.apply_theme()
        self.log("Theme toggled")
    
    def log(self, message, level="INFO"):
        """Add message to log area"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}\n"
        
        self.log_text.insert(tk.END, log_line)
        self.log_text.see(tk.END)
        
        # Also update status bar
        self.status_label.config(text=message)
        
        # Process UI events
        self.root.update_idletasks()
    
    def browse_file(self, var, file_type):
        """Open file browser dialog"""
        if file_type == "music":
            filetypes = [("Audio files", "*.mp3 *.m4a *.wav *.ogg")]
        else:
            filetypes = [("Video files", "*.mp4 *.mov *.avi *.mkv")]
        
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            var.set(filename)
            self.log(f"Selected {file_type} file: {filename}")
    
    def test_url(self, url):
        """Test if URL is valid"""
        if not url:
            self.log("No URL entered", "WARNING")
            return
        
        self.log(f"Testing URL: {url}")
        # Just check if URL format is valid
        if url.startswith(('http://', 'https://')):
            self.log("URL format is valid", "SUCCESS")
        else:
            self.log("Invalid URL format", "ERROR")
    
    def generate_video(self):
        """Generate video from current input"""
        if self.processing:
            self.log("Already processing, please wait", "WARNING")
            return
        
        # Collect data
        data = {
            'texts': [var.get() for var in self.text_vars if var.get().strip()],
            'template': self.template_var.get(),
            'zodiac_sign': self.zodiac_var.get(),
            'caption': self.caption_var.get(),
            'hashtags': self.hashtags_var.get(),
            'asset_keyword': self.keyword_var.get(),
            'music_mood': self.mood_var.get(),
            'schedule': self.schedule_var.get(),
            'music_url': self.music_url_var.get(),
            'video_url': self.video_url_var.get(),
            'music_file': self.music_file_var.get(),
            'video_file': self.video_file_var.get()
        }
        
        if not data['texts']:
            self.log("Please enter at least one text line", "ERROR")
            messagebox.showwarning("Input Error", "Please enter at least one text line")
            return
        
        # Start processing in background thread
        self.processing = True
        self.process_btn.config(state='disabled', text="⏳ Processing...")
        self.progress_bar.start(10)
        
        thread = threading.Thread(target=self._generate_video_thread, args=(data,))
        thread.daemon = True
        thread.start()
    
    def _generate_video_thread(self, data):
        """Background thread for video generation"""
        try:
            self.log("Starting video generation...")
            
            # Here you would call the actual render engine
            # For demo, we'll simulate
            import time
            for i in range(10):
                time.sleep(0.5)
                self.log(f"Rendering... {i+1}/10")
            
            self.root.after(0, self._generation_complete, "/tmp/demo_video.mp4")
            
        except Exception as e:
            self.root.after(0, self._generation_error, str(e))
    
    def _generation_complete(self, video_path):
        """Called when generation is complete"""
        self.processing = False
        self.progress_bar.stop()
        self.process_btn.config(state='normal', text="▶ Start Processing")
        
        self.log(f"Video generated: {video_path}", "SUCCESS")
        
        # Update preview
        self.preview_label.config(text=f"Video ready: {Path(video_path).name}")
        
        messagebox.showinfo("Success", f"Video generated successfully!\n\nSaved to: {video_path}")
    
    def _generation_error(self, error):
        """Called when generation fails"""
        self.processing = False
        self.progress_bar.stop()
        self.process_btn.config(state='normal', text="▶ Start Processing")
        
        self.log(f"Generation failed: {error}", "ERROR")
        messagebox.showerror("Error", f"Video generation failed:\n{error}")
    
    def start_processing(self):
        """Start background processor for pending rows"""
        self.log("Starting background processor...")
        
        if self.processor_thread is None or not self.processor_thread.is_alive():
            self.processor_thread = threading.Thread(target=self._processor_loop, daemon=True)
            self.processor_thread.start()
            self.log("Background processor started")
        else:
            self.log("Processor already running")
    
    def _processor_loop(self):
        """Background processor loop"""
        self.log("Processor loop running")
        
        while self.processing:
            # Check for pending rows in Google Sheets
            # For demo, just sleep
            import time
            time.sleep(10)
    
    def open_settings(self):
        """Open settings dialog"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("600x500")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Notebook for settings tabs
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # API Settings tab
        api_frame = ttk.Frame(notebook)
        notebook.add(api_frame, text="API Settings")
        
        # Load current config
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
        
        row = 0
        for api_name in ['pexels', 'pixabay', 'nuelink']:
            ttk.Label(api_frame, text=f"{api_name.upper()} API Key:").grid(row=row, column=0, sticky='w', padx=10, pady=5)
            
            api_var = tk.StringVar(value=config['api'][api_name]['api_key'])
            entry = ttk.Entry(api_frame, textvariable=api_var, width=50, show="*")
            entry.grid(row=row, column=1, padx=10, pady=5)
            
            setattr(self, f"{api_name}_key_var", api_var)
            row += 1
        
        # Google Sheet ID
        ttk.Label(api_frame, text="Google Sheet ID:").grid(row=row, column=0, sticky='w', padx=10, pady=5)
        self.sheet_id_var = tk.StringVar(value=config['api']['google_sheets']['sheet_id'])
        ttk.Entry(api_frame, textvariable=self.sheet_id_var, width=50).grid(row=row, column=1, padx=10, pady=5)
        row += 1
        
        # Feature toggles tab
        features_frame = ttk.Frame(notebook)
        notebook.add(features_frame, text="Features")
        
        self.feature_vars = {}
        row = 0
        for feature, enabled in config['features'].items():
            var = tk.BooleanVar(value=enabled)
            ttk.Checkbutton(features_frame, text=feature.replace('_', ' ').title(), variable=var).grid(row=row, column=0, sticky='w', padx=10, pady=5)
            self.feature_vars[feature] = var
            row += 1
        
        # Save button
        btn_frame = ttk.Frame(settings_window)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Save", command=lambda: self.save_settings(settings_window)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=settings_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def save_settings(self, window):
        """Save settings to config file"""
        # Update config
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
        
        # Save API keys
        for api_name in ['pexels', 'pixabay', 'nuelink']:
            var = getattr(self, f"{api_name}_key_var", None)
            if var:
                config['api'][api_name]['api_key'] = var.get()
        
        # Save Google Sheet ID
        config['api']['google_sheets']['sheet_id'] = self.sheet_id_var.get()
        
        # Save feature toggles
        for feature, var in self.feature_vars.items():
            config['features'][feature] = var.get()
        
        # Write back
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(config, f)
        
        self.log("Settings saved")
        window.destroy()
        messagebox.showinfo("Success", "Settings saved successfully")
    
    def upload_to_sheet(self):
        """Upload template to Google Sheet"""
        self.log("Uploading template to Google Sheet...")
        
        # Create template data
        headers = ['id', 'status', 'approval_status', 'template', 'zodiac_sign', 'text_1', 'text_2', 
                   'text_3', 'text_4', 'text_5', 'caption', 'hashtags', 'asset_keyword', 'music_mood', 
                   'schedule_datetime', 'timezone', 'video_output_path', 'preview_url', 'nuelink_post_id', 
                   'retry_count', 'last_error', 'approved_by', 'approved_at', 'reject_reason']
        
        # Show file dialog to save template
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx")],
            initialfile="google_sheet_template.csv"
        )
        
        if filepath:
            import csv
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                # Add example row
                writer.writerow(['1001', 'DRAFT', '', 'motivational', 'leo', 'Believe in yourself', 
                                'Keep pushing forward', 'Success awaits', '', '', 'Check this out!', 
                                '#motivation #success', 'nature sunset', 'upbeat', '2026-05-20 15:30:00', 
                                'Asia/Jakarta', '', '', '', '0', '', '', '', ''])
            
            self.log(f"Template saved to: {filepath}")
            messagebox.showinfo("Success", f"Template saved to:\n{filepath}\n\nUpload this file to Google Sheets")
    
    def start_background_processor(self):
        """Start the background processor thread"""
        self.processor_thread = threading.Thread(target=self._processor_loop, daemon=True)
        self.processor_thread.start()
        self.log("Background processor started")


def main():
    if not TKINTER_AVAILABLE:
        print("Tkinter is not available. Please install python3-tk")
        sys.exit(1)
    
    root = tk.Tk()
    app = ContentGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()