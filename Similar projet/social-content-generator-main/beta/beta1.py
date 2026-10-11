#!/usr/bin/env python3
"""
Social Media Auto Content System - BETA 1
Python Desktop UI with Tkinter
No Nuelink required - FIXED VERSION
"""

import os
import sys
import json
import threading
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

# ============ Configuration ============

CONFIG_FILE = Path(__file__).parent / "config.json"

DEFAULT_CONFIG = {
    "app": {
        "name": "Social Media Auto Content",
        "version": "beta1",
        "theme": "dark"
    },
    "features": {
        "video_generation": {
            "enabled": True,
            "max_video_duration": 60,
            "resolution": "1080x1920",
            "fps": 30
        },
        "music": {
            "enabled": True,
            "default_volume": 0.7,
            "fade_in": 2,
            "fade_out": 2
        },
        "background": {
            "enabled": True,
            "auto_search": True
        },
        "text_effects": {
            "enabled": True
        },
        "zodiac_templates": {
            "enabled": True
        },
        "social_media": {
            "enabled": False
        },
        "cleanup": {
            "enabled": True,
            "keep_days": 7
        }
    },
    "paths": {
        "output_dir": "output",
        "assets_dir": "assets",
        "music_dir": "assets/music"
    }
}


class ConfigManager:
    """Manage configuration file"""
    
    def __init__(self, config_file: Path = CONFIG_FILE):
        self.config_file = config_file
        self.config = self.load()
    
    def load(self) -> dict:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()
    
    def save(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get(self, key: str, default=None):
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value
    
    def set(self, key: str, value):
        keys = key.split('.')
        target = self.config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.save()


# ============ Video Generator ============

class VideoGenerator:
    """Generate videos using FFmpeg"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.output_dir = Path(config.get("paths.output_dir", "output"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_zodiac_color(self, zodiac: str) -> str:
        """Get color for zodiac sign"""
        colors = {
            "aries": "red", "taurus": "green", "gemini": "gold",
            "cancer": "lightblue", "leo": "orange", "virgo": "yellowgreen",
            "libra": "pink", "scorpio": "darkred", "sagittarius": "saddlebrown",
            "capricorn": "darkslategray", "aquarius": "deepskyblue", "pisces": "mediumpurple"
        }
        return colors.get(zodiac.lower(), "white")
    
    def generate_video(self, texts: List[str], template: str, zodiac: str = None, 
                       keyword: str = None, music_path: str = None) -> Optional[str]:
        """Generate video from texts"""
        
        if not texts:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"video_{timestamp}.mp4"
        
        # Determine text color
        if template == "zodiac_dark" and zodiac:
            text_color = self.get_zodiac_color(zodiac)
        else:
            text_color = "white"
        
        duration_per_text = 5
        total_duration = len(texts) * duration_per_text
        
        # Create temp directory for segments
        temp_dir = Path(__file__).parent / f"temp_{timestamp}"
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
            return None
            
        except Exception as e:
            print(f"Video generation error: {e}")
            return None
            
        finally:
            # Cleanup temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)


# ============ Beta1App - Main Application ============

class Beta1App:
    """Main Tkinter Application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Social Media Auto Content - Beta 1")
        self.root.geometry("1100x650")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Initialize components
        self.config = ConfigManager()
        self.video_generator = VideoGenerator(self.config)
        
        # Current state
        self.current_video_path = None
        self.is_generating = False
        
        # Setup UI
        self.setup_ui()
        self.load_config_to_ui()
        
        # Create output directory
        output_dir = Path(self.config.get("paths.output_dir", "output"))
        output_dir.mkdir(parents=True, exist_ok=True)
    
    def setup_ui(self):
        """Setup user interface"""
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 1: Content Creator
        self.create_tab_content()
        
        # Tab 2: Settings
        self.create_tab_settings()
        
        # Tab 3: History
        self.create_tab_history()
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                                relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_tab_content(self):
        """Create content creation tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Content Creator")
        
        # Left panel - Input
        left_frame = ttk.Frame(tab)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Template selection
        ttk.Label(left_frame, text="Template:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.template_var = tk.StringVar(value="motivational")
        template_combo = ttk.Combobox(left_frame, textvariable=self.template_var, 
                                       values=["motivational", "zodiac_dark", "educational", "quote_simple"])
        template_combo.grid(row=0, column=1, sticky=tk.W, pady=5)
        template_combo.bind("<<ComboboxSelected>>", self.on_template_change)
        
        # Zodiac sign (for zodiac template)
        ttk.Label(left_frame, text="Zodiac Sign:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.zodiac_var = tk.StringVar(value="leo")
        self.zodiac_combo = ttk.Combobox(left_frame, textvariable=self.zodiac_var,
                                      values=["aries", "taurus", "gemini", "cancer", "leo", "virgo",
                                              "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"])
        self.zodiac_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Text inputs
        ttk.Label(left_frame, text="Text Line 1:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.text1_entry = ttk.Entry(left_frame, width=50)
        self.text1_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        self.text1_entry.insert(0, "Your message here")
        
        ttk.Label(left_frame, text="Text Line 2:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.text2_entry = ttk.Entry(left_frame, width=50)
        self.text2_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(left_frame, text="Text Line 3:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.text3_entry = ttk.Entry(left_frame, width=50)
        self.text3_entry.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(left_frame, text="Text Line 4:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.text4_entry = ttk.Entry(left_frame, width=50)
        self.text4_entry.grid(row=5, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(left_frame, text="Text Line 5:").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.text5_entry = ttk.Entry(left_frame, width=50)
        self.text5_entry.grid(row=6, column=1, sticky=tk.W, pady=5)
        
        # Caption
        ttk.Label(left_frame, text="Caption:").grid(row=7, column=0, sticky=tk.W, pady=5)
        self.caption_entry = ttk.Entry(left_frame, width=50)
        self.caption_entry.grid(row=7, column=1, sticky=tk.W, pady=5)
        
        # Hashtags
        ttk.Label(left_frame, text="Hashtags:").grid(row=8, column=0, sticky=tk.W, pady=5)
        self.hashtags_entry = ttk.Entry(left_frame, width=50)
        self.hashtags_entry.grid(row=8, column=1, sticky=tk.W, pady=5)
        
        # Background keyword
        ttk.Label(left_frame, text="Background Keyword:").grid(row=9, column=0, sticky=tk.W, pady=5)
        self.keyword_entry = ttk.Entry(left_frame, width=50)
        self.keyword_entry.grid(row=9, column=1, sticky=tk.W, pady=5)
        self.keyword_entry.insert(0, "nature beautiful")
        
        # Music file
        ttk.Label(left_frame, text="Music File:").grid(row=10, column=0, sticky=tk.W, pady=5)
        music_frame = ttk.Frame(left_frame)
        music_frame.grid(row=10, column=1, sticky=tk.W, pady=5)
        self.music_path_var = tk.StringVar()
        music_entry = ttk.Entry(music_frame, textvariable=self.music_path_var, width=40)
        music_entry.pack(side=tk.LEFT)
        music_browse_btn = ttk.Button(music_frame, text="Browse", command=self.browse_music)
        music_browse_btn.pack(side=tk.LEFT, padx=5)
        
        # Generate button
        generate_btn = ttk.Button(left_frame, text="Generate Video", command=self.generate_video)
        generate_btn.grid(row=11, column=0, columnspan=2, pady=20)
        
        # Right panel - Preview
        right_frame = ttk.Frame(tab)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(right_frame, text="Preview", font=("Arial", 14, "bold")).pack()
        
        self.preview_text = scrolledtext.ScrolledText(right_frame, height=15, width=50)
        self.preview_text.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Post buttons
        post_frame = ttk.Frame(right_frame)
        post_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(post_frame, text="Post to YouTube Shorts", 
                   command=lambda: self.post_video("youtube")).pack(side=tk.LEFT, padx=5)
        ttk.Button(post_frame, text="Post to Instagram", 
                   command=lambda: self.post_video("instagram")).pack(side=tk.LEFT, padx=5)
        ttk.Button(post_frame, text="Post to Facebook", 
                   command=lambda: self.post_video("facebook")).pack(side=tk.LEFT, padx=5)
        
        # Play button
        ttk.Button(right_frame, text="Play Video", command=self.play_video).pack(pady=10)
        
        # Initial visibility
        self.on_template_change()
    
    def create_tab_settings(self):
        """Create settings/configuration tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Settings")
        
        # Create canvas with scrollbar
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        row = 0
        
        # Features Section
        ttk.Label(scrollable_frame, text="FEATURES", font=("Arial", 12, "bold")).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=10)
        row += 1
        
        # Video Generation
        self.video_gen_var = tk.BooleanVar(value=self.config.get("features.video_generation.enabled", True))
        ttk.Checkbutton(scrollable_frame, text="Enable Video Generation", 
                        variable=self.video_gen_var,
                        command=lambda: self.config.set("features.video_generation.enabled", self.video_gen_var.get())
                        ).grid(row=row, column=0, sticky=tk.W, pady=2)
        row += 1
        
        # Music
        self.music_var = tk.BooleanVar(value=self.config.get("features.music.enabled", True))
        ttk.Checkbutton(scrollable_frame, text="Enable Music", 
                        variable=self.music_var,
                        command=lambda: self.config.set("features.music.enabled", self.music_var.get())
                        ).grid(row=row, column=0, sticky=tk.W, pady=2)
        row += 1
        
        # Zodiac Templates
        self.zodiac_var_set = tk.BooleanVar(value=self.config.get("features.zodiac_templates.enabled", True))
        ttk.Checkbutton(scrollable_frame, text="Enable Zodiac Templates", 
                        variable=self.zodiac_var_set,
                        command=lambda: self.config.set("features.zodiac_templates.enabled", self.zodiac_var_set.get())
                        ).grid(row=row, column=0, sticky=tk.W, pady=2)
        row += 1
        
        # Separator
        ttk.Separator(scrollable_frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1
        
        # Video Settings Section
        ttk.Label(scrollable_frame, text="VIDEO SETTINGS", font=("Arial", 12, "bold")).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=10)
        row += 1
        
        ttk.Label(scrollable_frame, text="Max Duration (seconds):").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.duration_var = tk.IntVar(value=self.config.get("features.video_generation.max_video_duration", 60))
        duration_spin = ttk.Spinbox(scrollable_frame, from_=10, to=120, textvariable=self.duration_var, width=10)
        duration_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        duration_spin.bind("<KeyRelease>", lambda e: self.config.set("features.video_generation.max_video_duration", self.duration_var.get()))
        row += 1
        
        ttk.Label(scrollable_frame, text="Resolution:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.res_var = tk.StringVar(value=self.config.get("features.video_generation.resolution", "1080x1920"))
        res_combo = ttk.Combobox(scrollable_frame, textvariable=self.res_var,
                     values=["1080x1920", "720x1280", "540x960"], width=15)
        res_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        res_combo.bind("<<ComboboxSelected>>", lambda e: self.config.set("features.video_generation.resolution", self.res_var.get()))
        row += 1
        
        ttk.Label(scrollable_frame, text="FPS:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.fps_var = tk.IntVar(value=self.config.get("features.video_generation.fps", 30))
        fps_spin = ttk.Spinbox(scrollable_frame, from_=24, to=60, textvariable=self.fps_var, width=10)
        fps_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        fps_spin.bind("<KeyRelease>", lambda e: self.config.set("features.video_generation.fps", self.fps_var.get()))
        row += 1
        
        # Separator
        ttk.Separator(scrollable_frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1
        
        # Cleanup Settings
        ttk.Label(scrollable_frame, text="CLEANUP SETTINGS", font=("Arial", 12, "bold")).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=10)
        row += 1
        
        self.cleanup_var = tk.BooleanVar(value=self.config.get("features.cleanup.enabled", True))
        ttk.Checkbutton(scrollable_frame, text="Auto Cleanup", 
                        variable=self.cleanup_var,
                        command=lambda: self.config.set("features.cleanup.enabled", self.cleanup_var.get())
                        ).grid(row=row, column=0, sticky=tk.W, pady=2)
        row += 1
        
        ttk.Label(scrollable_frame, text="Keep videos for (days):").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.keep_days_var = tk.IntVar(value=self.config.get("features.cleanup.keep_days", 7))
        keep_spin = ttk.Spinbox(scrollable_frame, from_=1, to=30, textvariable=self.keep_days_var, width=10)
        keep_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        keep_spin.bind("<KeyRelease>", lambda e: self.config.set("features.cleanup.keep_days", self.keep_days_var.get()))
        row += 1
        
        # Save button
        ttk.Button(scrollable_frame, text="Save All Settings", 
                   command=self.save_all_settings).grid(row=row, column=0, pady=20)
        
        # Reset button
        ttk.Button(scrollable_frame, text="Reset to Default", 
                   command=self.reset_settings).grid(row=row, column=1, pady=20)
    
    def create_tab_history(self):
        """Create history tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="History")
        
        # History list
        columns = ("Date", "Template", "Text Preview", "Status")
        self.history_tree = ttk.Treeview(tab, columns=columns, show="headings")
        
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=150)
        
        self.history_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear History", command=self.clear_history).pack(side=tk.LEFT, padx=5)
    
    # ============ UI Event Handlers ============
    
    def on_template_change(self, event=None):
        """Handle template change"""
        if self.template_var.get() == "zodiac_dark":
            self.zodiac_combo.config(state="normal")
        else:
            self.zodiac_combo.config(state="disabled")
    
    def browse_music(self):
        """Browse for music file"""
        filename = filedialog.askopenfilename(
            title="Select Music File",
            filetypes=[("Audio Files", "*.mp3 *.m4a *.wav *.ogg"), ("All Files", "*.*")]
        )
        if filename:
            self.music_path_var.set(filename)
    
    def generate_video(self):
        """Generate video from inputs"""
        if self.is_generating:
            messagebox.showwarning("Warning", "Already generating a video. Please wait.")
            return
        
        # Get texts
        texts = [
            self.text1_entry.get(),
            self.text2_entry.get(),
            self.text3_entry.get(),
            self.text4_entry.get(),
            self.text5_entry.get()
        ]
        texts = [t for t in texts if t and t.strip()]
        
        if not texts:
            messagebox.showwarning("Warning", "Please enter at least one text line")
            return
        
        # Check if FFmpeg is available
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            messagebox.showerror("Error", "FFmpeg not found. Please install FFmpeg and add it to PATH.\n\nDownload from: https://ffmpeg.org/download.html")
            return
        
        self.is_generating = True
        self.status_var.set("Generating video...")
        self.preview_text.insert(tk.END, f"\n[INFO] Generating video at {datetime.now()}\n")
        self.preview_text.see(tk.END)
        
        # Generate in thread to prevent UI freeze
        def generate():
            try:
                template = self.template_var.get()
                zodiac = self.zodiac_var.get() if template == "zodiac_dark" else None
                music_path = self.music_path_var.get() if self.music_path_var.get() else None
                
                video_path = self.video_generator.generate_video(
                    texts=texts,
                    template=template,
                    zodiac=zodiac,
                    keyword=self.keyword_entry.get(),
                    music_path=music_path
                )
                
                self.root.after(0, self.on_generation_complete, video_path, texts[0], template)
            except Exception as e:
                self.root.after(0, self.on_generation_error, str(e))
        
        threading.Thread(target=generate, daemon=True).start()
    
    def on_generation_complete(self, video_path, text_preview, template):
        """Handle generation completion"""
        self.is_generating = False
        
        if video_path:
            self.current_video_path = video_path
            self.status_var.set(f"Video generated: {video_path}")
            self.preview_text.insert(tk.END, f"[SUCCESS] Video saved to: {video_path}\n")
            self.preview_text.insert(tk.END, f"[INFO] You can now play or post the video\n")
            
            # Add to history
            self.add_to_history(video_path, text_preview, template)
            
            messagebox.showinfo("Success", f"Video generated successfully!\n\nSaved to: {video_path}")
        else:
            self.status_var.set("Video generation failed")
            self.preview_text.insert(tk.END, f"[ERROR] Video generation failed\n")
            messagebox.showerror("Error", "Video generation failed.\n\nMake sure FFmpeg is properly installed.")
        
        self.preview_text.see(tk.END)
    
    def on_generation_error(self, error_msg):
        """Handle generation error"""
        self.is_generating = False
        self.status_var.set("Video generation error")
        self.preview_text.insert(tk.END, f"[ERROR] {error_msg}\n")
        messagebox.showerror("Error", f"Video generation error:\n\n{error_msg}")
        self.preview_text.see(tk.END)
    
    def play_video(self):
        """Play generated video"""
        if self.current_video_path and Path(self.current_video_path).exists():
            if sys.platform == "win32":
                os.startfile(self.current_video_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", self.current_video_path])
            else:
                subprocess.run(["xdg-open", self.current_video_path])
        else:
            messagebox.showwarning("Warning", "No video generated yet. Please generate a video first.")
    
    def post_video(self, platform: str):
        """Post video to social media (placeholder)"""
        if not self.current_video_path:
            messagebox.showwarning("Warning", "No video to post. Generate a video first.")
            return
        
        caption = self.caption_entry.get()
        hashtags = self.hashtags_entry.get()
        full_caption = f"{caption}\n\n{hashtags}" if hashtags else caption
        
        messagebox.showinfo("Info", 
            f"Video ready to post to {platform}\n\n"
            f"Video: {self.current_video_path}\n"
            f"Caption: {full_caption}\n\n"
            f"Note: Auto-posting requires additional setup.\n"
            f"Please upload manually to {platform} for now.")
        
        # Open folder for manual upload
        folder_path = Path(self.current_video_path).parent
        if sys.platform == "win32":
            os.startfile(folder_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(folder_path)])
        else:
            subprocess.run(["xdg-open", str(folder_path)])
    
    def add_to_history(self, video_path: str, text_preview: str, template: str):
        """Add item to history"""
        history_file = Path(__file__).parent / "history.json"
        history = []
        
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
            except:
                pass
        
        history.append({
            "date": datetime.now().isoformat(),
            "video_path": video_path,
            "text_preview": text_preview[:50],
            "template": template,
            "status": "generated"
        })
        
        # Keep last 100
        history = history[-100:]
        
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        self.refresh_history()
    
    def refresh_history(self):
        """Refresh history display"""
        # Clear existing
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Load from history file
        history_file = Path(__file__).parent / "history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
                
                for item in reversed(history[-20:]):  # Show last 20
                    self.history_tree.insert("", tk.END, values=(
                        item.get("date", "")[:19],
                        item.get("template", ""),
                        item.get("text_preview", ""),
                        item.get("status", "")
                    ))
            except:
                pass
    
    def clear_history(self):
        """Clear all history"""
        if messagebox.askyesno("Confirm", "Clear all history?"):
            history_file = Path(__file__).parent / "history.json"
            if history_file.exists():
                history_file.unlink()
            self.refresh_history()
            messagebox.showinfo("Success", "History cleared")
    
    def load_config_to_ui(self):
        """Load configuration values to UI elements"""
        # Feature toggles
        if hasattr(self, 'video_gen_var'):
            self.video_gen_var.set(self.config.get("features.video_generation.enabled", True))
        if hasattr(self, 'music_var'):
            self.music_var.set(self.config.get("features.music.enabled", True))
        if hasattr(self, 'zodiac_var_set'):
            self.zodiac_var_set.set(self.config.get("features.zodiac_templates.enabled", True))
        if hasattr(self, 'cleanup_var'):
            self.cleanup_var.set(self.config.get("features.cleanup.enabled", True))
        
        # Video settings
        if hasattr(self, 'duration_var'):
            self.duration_var.set(self.config.get("features.video_generation.max_video_duration", 60))
        if hasattr(self, 'res_var'):
            self.res_var.set(self.config.get("features.video_generation.resolution", "1080x1920"))
        if hasattr(self, 'fps_var'):
            self.fps_var.set(self.config.get("features.video_generation.fps", 30))
        if hasattr(self, 'keep_days_var'):
            self.keep_days_var.set(self.config.get("features.cleanup.keep_days", 7))
    
    def save_all_settings(self):
        """Save all current settings to config"""
        # Feature toggles
        self.config.set("features.video_generation.enabled", self.video_gen_var.get())
        self.config.set("features.music.enabled", self.music_var.get())
        self.config.set("features.zodiac_templates.enabled", self.zodiac_var_set.get())
        self.config.set("features.cleanup.enabled", self.cleanup_var.get())
        
        # Video settings
        self.config.set("features.video_generation.max_video_duration", self.duration_var.get())
        self.config.set("features.video_generation.resolution", self.res_var.get())
        self.config.set("features.video_generation.fps", self.fps_var.get())
        self.config.set("features.cleanup.keep_days", self.keep_days_var.get())
        
        messagebox.showinfo("Success", "All settings saved")
    
    def reset_settings(self):
        """Reset all settings to default"""
        if messagebox.askyesno("Confirm", "Reset all settings to default?"):
            self.config.config = DEFAULT_CONFIG.copy()
            self.config.save()
            self.load_config_to_ui()
            messagebox.showinfo("Success", "Settings reset to default")
    
    def on_closing(self):
        """Handle window closing"""
        self.root.destroy()
    
    def run(self):
        """Run the application"""
        # Initial history load
        self.refresh_history()
        self.root.mainloop()


# ============ Main Entry Point ============

if __name__ == "__main__":
    # Check FFmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("Warning: FFmpeg not found. Please install FFmpeg.")
            print("Download from: https://ffmpeg.org/download.html")
    except FileNotFoundError:
        print("Warning: FFmpeg not found. Please install FFmpeg.")
        print("Download from: https://ffmpeg.org/download.html")
    
    app = Beta1App()
    app.run()
