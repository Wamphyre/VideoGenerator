#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re
import platform
from PIL import Image
import numpy as np
import psutil
import threading
import time
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
from functools import lru_cache
import tempfile
import shutil
import json

# CRITICAL: Hide Python from menu bar on macOS - THIS MUST BE FIRST
if platform.system() == 'Darwin':
    try:
        # Method 1: Use AppKit to hide the application initially
        from AppKit import NSApp, NSApplication, NSApplicationActivationPolicyRegular, NSApplicationActivationPolicyAccessory
        app = NSApplication.sharedApplication()
        # Set as accessory app initially (hides from Dock and menu)
        app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        
        # We'll change this to regular when GUI appears
        def make_app_visible():
            app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
            
    except ImportError:
        def make_app_visible():
            pass
    
    try:
        # Method 2: Change process name to VideoGenerator
        import ctypes
        import ctypes.util
        libc = ctypes.CDLL(ctypes.util.find_library('c'))
        # Set process name (this might help)
        app_name = b'VideoGenerator'
        try:
            # Try Linux-style prctl
            libc.prctl(15, app_name, 0, 0, 0)
        except:
            pass
    except:
        pass
        
    try:
        # Method 3: Override argv[0] to change process name
        sys.argv[0] = 'VideoGenerator'
        if hasattr(sys, '_getframe'):
            # Try to modify the process title
            import setproctitle
            setproctitle.setproctitle('VideoGenerator')
    except:
        pass
        
else:
    def make_app_visible():
        pass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check operating system
IS_MACOS = platform.system() == 'Darwin'

# Get application directory
if getattr(sys, 'frozen', False):
    # If packaged application
    APPLICATION_PATH = os.path.dirname(sys.executable)
else:
    # If normal script
    APPLICATION_PATH = os.path.dirname(os.path.abspath(__file__))

# Path to bundled FFmpeg
FFMPEG_PATH = os.path.join(APPLICATION_PATH, 'ffmpeg')
FFPROBE_PATH = os.path.join(APPLICATION_PATH, 'ffprobe')  # If you also have ffprobe

# Ensure FFmpeg exists and is executable
if os.path.exists(FFMPEG_PATH):
    os.chmod(FFMPEG_PATH, 0o755)  # Ensure execution permissions
else:
    # Look in current directory as fallback
    FFMPEG_PATH = './ffmpeg'
    if os.path.exists(FFMPEG_PATH):
        os.chmod(FFMPEG_PATH, 0o755)

class VideoGenerator:
    """Video generator optimized for macOS with bundled FFmpeg"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix='videogenerator_')
        self.executor = ThreadPoolExecutor(max_workers=multiprocessing.cpu_count())
        self.ffmpeg_path = FFMPEG_PATH
        self.ffprobe_path = FFPROBE_PATH if os.path.exists(FFPROBE_PATH) else self.ffmpeg_path
        
    def __del__(self):
        """Clean up resources"""
        try:
            self.executor.shutdown(wait=False)
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass
    
    def check_ffmpeg(self):
        """Verify bundled FFmpeg"""
        try:
            if not os.path.exists(self.ffmpeg_path):
                return False, False, "FFmpeg not found in application directory"
            
            # Ensure it's executable
            if not os.access(self.ffmpeg_path, os.X_OK):
                os.chmod(self.ffmpeg_path, 0o755)
            
            # Check version
            result = subprocess.run(
                [self.ffmpeg_path, '-version'], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"FFmpeg found: {self.ffmpeg_path}")
                version_info = result.stdout.split('\n')[0]
                logger.info(f"Version: {version_info}")
                
                # Check available codecs
                result = subprocess.run(
                    [self.ffmpeg_path, '-codecs'], 
                    capture_output=True, 
                    text=True
                )
                
                has_videotoolbox = 'videotoolbox' in result.stdout
                
                if has_videotoolbox:
                    logger.info("VideoToolbox available for hardware acceleration")
                
                return True, has_videotoolbox, "FFmpeg ready"
            else:
                return False, False, f"Error executing FFmpeg: {result.stderr}"
                
        except Exception as e:
            return False, False, f"Error verifying FFmpeg: {str(e)}"
    
    @staticmethod
    @lru_cache(maxsize=128)
    def get_track_number(filename):
        """Extract track number from filename (cached)"""
        basename = os.path.splitext(filename)[0]
        
        # Look for number at beginning
        match = re.search(r'^(\d+)', basename)
        if match:
            return int(match.group(1))
        
        # Look for number anywhere
        match = re.search(r'(\d+)', basename)
        if match:
            return int(match.group(1))
        
        return float('inf')
    
    def process_audio_files(self, audio_dir, progress_callback=None):
        """Process audio files optimally"""
        audio_extensions = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma'}
        audio_files = []
        
        # Use pathlib for better path handling
        audio_path = Path(audio_dir)
        for file in audio_path.iterdir():
            if file.suffix.lower() in audio_extensions:
                audio_files.append(str(file))
        
        # Sort by track number
        audio_files.sort(key=lambda x: self.get_track_number(os.path.basename(x)))
        
        logger.info(f"Found {len(audio_files)} audio files")
        return audio_files
    
    def optimize_image(self, image_path, target_size=(1920, 1080)):
        """Optimize image for video using PIL"""
        try:
            img = Image.open(image_path)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Calculate dimensions maintaining aspect ratio
            img_ratio = img.width / img.height
            target_ratio = target_size[0] / target_size[1]
            
            if img_ratio > target_ratio:
                # Image is wider
                new_width = target_size[0]
                new_height = int(target_size[0] / img_ratio)
            else:
                # Image is taller
                new_height = target_size[1]
                new_width = int(target_size[1] * img_ratio)
            
            # Resize with best quality
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Create image with black background
            background = Image.new('RGB', target_size, (0, 0, 0))
            x = (target_size[0] - new_width) // 2
            y = (target_size[1] - new_height) // 2
            background.paste(img, (x, y))
            
            # Save optimized image
            output_path = os.path.join(self.temp_dir, 'optimized_bg.jpg')
            background.save(output_path, 'JPEG', quality=95, optimize=True)
            
            logger.info(f"Image optimized: {new_width}x{new_height} on canvas {target_size[0]}x{target_size[1]}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise
    
    def get_optimal_encoding_params(self, use_hardware=True, quality='high'):
        """Get optimal encoding parameters for macOS"""
        base_params = [
            '-c:a', 'aac',
            '-b:a', '320k',
            '-ar', '48000',
            '-ac', '2'
        ]
        
        quality_presets = {
            'low': {'crf': 28, 'bitrate': '2M'},
            'medium': {'crf': 23, 'bitrate': '5M'},
            'high': {'crf': 18, 'bitrate': '10M'},
            'ultra': {'crf': 15, 'bitrate': '20M'}
        }
        
        preset = quality_presets.get(quality, quality_presets['high'])
        
        if IS_MACOS and use_hardware:
            # Use VideoToolbox on macOS
            video_params = [
                '-c:v', 'h264_videotoolbox',
                '-b:v', preset['bitrate'],
                '-profile:v', 'high',
                '-level', '4.2',
                '-coder', '1',
                '-pix_fmt', 'yuv420p',
                '-color_range', 'tv',
                '-colorspace', 'bt709',
                '-color_trc', 'bt709',
                '-color_primaries', 'bt709'
            ]
        else:
            # Software encoding
            video_params = [
                '-c:v', 'libx264',
                '-crf', str(preset['crf']),
                '-preset', 'medium',
                '-profile:v', 'high',
                '-level', '4.2',
                '-pix_fmt', 'yuv420p'
            ]
        
        return base_params + video_params
    
    def get_audio_duration(self, audio_files):
        """Get total audio duration using FFmpeg"""
        try:
            total_duration = 0
            
            for audio_file in audio_files:
                cmd = [
                    self.ffmpeg_path, '-i', audio_file, '-f', 'null', '-'
                ]
                
                result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
                
                # Parse duration from stderr
                duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', result.stderr)
                if duration_match:
                    hours = int(duration_match.group(1))
                    minutes = int(duration_match.group(2))
                    seconds = int(duration_match.group(3))
                    centiseconds = int(duration_match.group(4))
                    
                    file_duration = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
                    total_duration += file_duration
            
            return total_duration if total_duration > 0 else None
            
        except Exception as e:
            logger.error(f"Error getting duration: {e}")
            return None
    
    def create_video(self, audio_files, image_path, output_path, 
                    use_hardware=True, quality='high', 
                    fade_in=True, fade_out=True,
                    progress_callback=None, log_callback=None):
        """Create video with optimizations for macOS"""
        
        try:
            # Verify FFmpeg first
            ffmpeg_ok, hw_available, msg = self.check_ffmpeg()
            if not ffmpeg_ok:
                raise Exception(f"FFmpeg not available: {msg}")
            
            # If no hardware support, use software
            if not hw_available and use_hardware:
                if log_callback:
                    log_callback("VideoToolbox not available, using software encoding")
                use_hardware = False
            
            # Optimize image
            if log_callback:
                log_callback("Optimizing background image...")
            optimized_image = self.optimize_image(image_path)
            
            # Get total audio duration for fade out
            total_duration = None
            if fade_out:
                if log_callback:
                    log_callback("Calculating total audio duration...")
                total_duration = self.get_audio_duration(audio_files)
                if total_duration:
                    if log_callback:
                        log_callback(f"Total audio duration: {total_duration:.2f} seconds")
                    logger.info(f"Total audio duration: {total_duration:.2f} seconds")
            
            # Create audio list file
            list_file = os.path.join(self.temp_dir, 'audio_list.txt')
            with open(list_file, 'w') as f:
                for audio in audio_files:
                    # Escape single quotes for FFmpeg
                    escaped_path = audio.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")
            
            # Build FFmpeg command
            cmd = [self.ffmpeg_path, '-y']
            
            # Concatenated audio input
            cmd.extend(['-f', 'concat', '-safe', '0', '-i', list_file])
            
            # Image input
            cmd.extend(['-loop', '1', '-framerate', '30', '-i', optimized_image])
            
            # Video duration = audio duration
            cmd.extend(['-shortest'])
            
            # Video filters
            filters = []
            if fade_in:
                filters.append('fade=t=in:st=0:d=2')
            if fade_out and total_duration and total_duration > 4:
                # Start fade out 2 seconds before end
                fade_out_start = total_duration - 2
                filters.append(f'fade=t=out:st={fade_out_start:.2f}:d=2')
            
            if filters:
                cmd.extend(['-vf', ','.join(filters)])
            
            # Optimized encoding parameters
            encoding_params = self.get_optimal_encoding_params(use_hardware, quality)
            cmd.extend(encoding_params)
            
            # Additional optimizations
            cmd.extend([
                '-movflags', '+faststart',  # Optimize for streaming
                '-max_muxing_queue_size', '9999',
                '-threads', '0'  # Use all available cores
            ])
            
            # Output file
            cmd.append(output_path)
            
            # Log command
            if log_callback:
                log_callback(f"Using FFmpeg: {self.ffmpeg_path}")
                log_callback(f"Encoding: {'Hardware (VideoToolbox)' if use_hardware else 'Software'}")
                log_callback("Starting video generation...")
            
            # Execute FFmpeg with progress monitoring
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Monitor progress
            duration_total = total_duration
            for line in process.stderr:
                if log_callback and line.strip():
                    # Filter only relevant lines
                    if any(keyword in line for keyword in ['frame=', 'time=', 'bitrate=', 'speed=']):
                        log_callback(line.strip())
                
                # Look for total duration if we don't have it
                if duration_total is None and "Duration:" in line:
                    match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})', line)
                    if match:
                        h, m, s = map(int, match.groups())
                        duration_total = h * 3600 + m * 60 + s
                
                # Look for progress
                if duration_total and "time=" in line:
                    match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})', line)
                    if match:
                        h, m, s = map(int, match.groups())
                        current_time = h * 3600 + m * 60 + s
                        progress = min(current_time / duration_total, 1.0)
                        if progress_callback:
                            progress_callback(progress)
            
            process.wait()
            
            if process.returncode != 0:
                error_output = process.stderr.read() if process.stderr else "Unknown error"
                raise Exception(f"FFmpeg failed during encoding: {error_output}")
            
            if log_callback:
                log_callback("Video generated successfully!")
                # Get file size
                file_size = os.path.getsize(output_path)
                log_callback(f"File size: {self._format_size(file_size)}")
            
            # Clean up temporary files
            os.unlink(list_file)
            os.unlink(optimized_image)
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating video: {e}")
            raise
    
    def _format_size(self, bytes):
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.1f} TB"

class VideoGeneratorGUI:
    """macOS-optimized graphical interface"""
    
    def __init__(self):
        self.root = tk.Tk()
        
        # CRITICAL: Make app visible and set proper name immediately
        self.root.title("VideoGenerator")
        
        # On macOS, make the app visible now that we have a window
        if IS_MACOS:
            make_app_visible()
            self.root.after(100, self._setup_macos_app)
        
        self.root.geometry("900x750")
        self.root.resizable(False, False)
        
        # Configure dark theme colors
        self.colors = {
            'bg': '#2d2d2d',
            'fg': '#ffffff',
            'select_bg': '#404040',
            'select_fg': '#ffffff',
            'button_bg': '#505050',
            'button_fg': '#ffffff',
            'button_hover': '#606060',
            'button_pressed': '#707070',
            'entry_bg': '#404040',
            'entry_fg': '#ffffff',
            'disabled_fg': '#888888',
            'accent': '#0066CC',
            'accent_hover': '#0080FF',
            'accent_pressed': '#004499',
            'checkbox_hover': '#505050'  # Fixed checkbox hover color
        }
        
        # Configure style for dark theme
        self.style = ttk.Style()
        
        # Configure colors for dark theme
        self.root.configure(bg=self.colors['bg'])
        
        # Configure ttk style for macOS appearance
        self.style.theme_use('default')
        
        # Configure ttk widgets
        self.style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['fg'])
        self.style.configure('TFrame', background=self.colors['bg'])
        self.style.configure('TLabelframe', background=self.colors['bg'], foreground=self.colors['fg'])
        self.style.configure('TLabelframe.Label', background=self.colors['bg'], foreground=self.colors['fg'])
        
        # Configure button style with rounded corners appearance
        self.style.configure('TButton', 
                           background=self.colors['button_bg'],
                           foreground=self.colors['button_fg'],
                           borderwidth=0,
                           focuscolor='none',
                           relief='flat',
                           padding=(15, 8))
        self.style.map('TButton',
                      background=[('active', self.colors['button_hover']),
                                 ('pressed', self.colors['button_pressed']),
                                 ('disabled', '#303030')],
                      foreground=[('disabled', self.colors['disabled_fg'])])
        
        # Accent button style (for primary actions)
        self.style.configure('Accent.TButton', 
                           background=self.colors['accent'],
                           foreground='white',
                           borderwidth=0,
                           focuscolor='none',
                           relief='flat',
                           padding=(20, 8))
        self.style.map('Accent.TButton',
                      background=[('active', self.colors['accent_hover']),
                                 ('pressed', self.colors['accent_pressed']),
                                 ('disabled', '#303030')],
                      foreground=[('disabled', self.colors['disabled_fg'])])
        
        # FIXED: Configure checkbutton style to prevent white hover
        self.style.configure('TCheckbutton', 
                           background=self.colors['bg'], 
                           foreground=self.colors['fg'],
                           focuscolor='none')
        self.style.map('TCheckbutton',
                      background=[('active', self.colors['checkbox_hover']),
                                 ('selected', self.colors['bg']),
                                 ('pressed', self.colors['bg'])],
                      foreground=[('active', self.colors['fg']),
                                 ('selected', self.colors['fg']),
                                 ('pressed', self.colors['fg'])])
        
        # Combobox with better visibility
        self.style.configure('TCombobox', 
                           fieldbackground=self.colors['entry_bg'], 
                           background=self.colors['button_bg'],
                           foreground=self.colors['entry_fg'],
                           borderwidth=0,
                           arrowcolor=self.colors['fg'])
        self.style.map('TCombobox',
                      fieldbackground=[('readonly', self.colors['entry_bg'])],
                      selectbackground=[('readonly', self.colors['select_bg'])],
                      selectforeground=[('readonly', self.colors['select_fg'])])
        
        # Entry style
        self.style.configure('TEntry', 
                           fieldbackground=self.colors['entry_bg'], 
                           foreground=self.colors['entry_fg'],
                           borderwidth=0,
                           insertcolor=self.colors['fg'])
        
        # Progress bar
        self.style.configure('TProgressbar', 
                           background=self.colors['accent'],
                           troughcolor=self.colors['select_bg'],
                           borderwidth=0,
                           lightcolor=self.colors['accent'],
                           darkcolor=self.colors['accent'])
        
        self.video_generator = VideoGenerator()
        self.audio_files = []
        self.image_path = None
        self.output_dir = None
        self.processing = False
        self.output_filename = None  # Store filename for notification
        
        # Saved configuration
        self.config_file = os.path.join(APPLICATION_PATH, 'config.json')
        self.load_config()
        
        self.setup_ui()
        self.check_dependencies()
    
    def _setup_macos_app(self):
        """Setup macOS specific app behavior"""
        if IS_MACOS:
            try:
                # Try to set app name in menu
                from AppKit import NSApp
                NSApp.setMainMenu_(None)  # Clear menu initially
                
                # Set application name
                import Foundation
                bundle = Foundation.NSBundle.mainBundle()
                if bundle:
                    info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
                    if info and info.get('CFBundleName') != 'VideoGenerator':
                        info['CFBundleName'] = 'VideoGenerator'
                        info['CFBundleDisplayName'] = 'VideoGenerator'
                        
            except ImportError:
                pass
            
            try:
                self.root.createcommand('tk::mac::ShowPreferences', self.show_preferences)
                self.root.createcommand('tk::mac::ShowAbout', self.show_about)
            except:
                pass
        
        # Configure icon if exists
        icon_path = os.path.join(APPLICATION_PATH, 'icon.png')
        if os.path.exists(icon_path):
            try:
                self.root.iconphoto(True, tk.PhotoImage(file=icon_path))
            except:
                pass
    
    def load_config(self):
        """Load saved configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = {
                    'quality': 'high',
                    'use_hardware': True,
                    'fade_in': True,
                    'fade_out': True,
                    'last_output_dir': os.path.expanduser('~/Movies')
                }
        except:
            self.config = {}
    
    def save_config(self):
        """Save configuration"""
        try:
            self.config['quality'] = self.quality_var.get()
            self.config['use_hardware'] = self.use_hardware_var.get()
            self.config['fade_in'] = self.fade_in_var.get()
            self.config['fade_out'] = self.fade_out_var.get()
            if self.output_dir:
                self.config['last_output_dir'] = self.output_dir
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except:
            pass
    
    def create_rounded_button(self, parent, text, command, style='TButton'):
        """Create a button with rounded appearance"""
        btn = ttk.Button(parent, text=text, command=command, style=style)
        return btn
    
    def setup_ui(self):
        """Configure user interface"""
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Files Section
        files_frame = ttk.LabelFrame(main_frame, text="Files", padding="15")
        files_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Audio Files
        audio_container = ttk.Frame(files_frame)
        audio_container.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(audio_container, text="Audio Files", font=('System', 12, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        audio_btn_frame = ttk.Frame(audio_container)
        audio_btn_frame.grid(row=1, column=0, sticky=tk.W)
        
        self.create_rounded_button(audio_btn_frame, "Choose Files...", 
                                  self.select_audio_files).pack(side=tk.LEFT)
        self.audio_label = ttk.Label(audio_btn_frame, text="No files selected", foreground=self.colors['disabled_fg'])
        self.audio_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Background Image
        image_container = ttk.Frame(files_frame)
        image_container.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(image_container, text="Background Image", font=('System', 12, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        image_btn_frame = ttk.Frame(image_container)
        image_btn_frame.grid(row=1, column=0, sticky=tk.W)
        
        self.create_rounded_button(image_btn_frame, "Choose Image...", 
                                  self.select_image).pack(side=tk.LEFT)
        self.image_label = ttk.Label(image_btn_frame, text="No image selected", foreground=self.colors['disabled_fg'])
        self.image_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Output Settings
        output_container = ttk.Frame(files_frame)
        output_container.pack(fill=tk.X)
        
        ttk.Label(output_container, text="Output Settings", font=('System', 12, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        output_frame = ttk.Frame(output_container)
        output_frame.grid(row=1, column=0, sticky=tk.W)
        
        self.create_rounded_button(output_frame, "Choose Location...", 
                                  self.select_output_dir).pack(side=tk.LEFT)
        self.output_label = ttk.Label(output_frame, text="No location selected", foreground=self.colors['disabled_fg'])
        self.output_label.pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Label(output_frame, text="Filename:").pack(side=tk.LEFT, padx=(20, 5))
        self.filename_var = tk.StringVar(value="output_video")
        filename_entry = ttk.Entry(output_frame, textvariable=self.filename_var, width=20)
        filename_entry.pack(side=tk.LEFT)
        ttk.Label(output_frame, text=".mp4").pack(side=tk.LEFT)
        
        # Encoding Options Section
        options_frame = ttk.LabelFrame(main_frame, text="Encoding Options", padding="15")
        options_frame.pack(fill=tk.X, pady=(0, 15))
        
        options_row1 = ttk.Frame(options_frame)
        options_row1.pack(fill=tk.X)
        
        # Quality
        ttk.Label(options_row1, text="Quality:").pack(side=tk.LEFT, padx=(0, 5))
        self.quality_var = tk.StringVar(value=self.config.get('quality', 'high'))
        quality_combo = ttk.Combobox(options_row1, textvariable=self.quality_var,
                                    values=["low", "medium", "high", "ultra"],
                                    state="readonly", width=10)
        quality_combo.pack(side=tk.LEFT, padx=(0, 20))
        quality_combo.bind('<<ComboboxSelected>>', lambda e: self.save_config())
        
        # Hardware acceleration
        self.use_hardware_var = tk.BooleanVar(value=self.config.get('use_hardware', True))
        hw_check = ttk.Checkbutton(options_row1, text="Use hardware acceleration",
                                  variable=self.use_hardware_var,
                                  command=self.save_config)
        hw_check.pack(side=tk.LEFT, padx=(0, 20))
        
        # Fade effects
        self.fade_in_var = tk.BooleanVar(value=self.config.get('fade_in', True))
        self.fade_out_var = tk.BooleanVar(value=self.config.get('fade_out', True))
        
        fade_in_check = ttk.Checkbutton(options_row1, text="Fade in",
                                       variable=self.fade_in_var,
                                       command=self.save_config)
        fade_in_check.pack(side=tk.LEFT, padx=(0, 10))
        
        fade_out_check = ttk.Checkbutton(options_row1, text="Fade out",
                                        variable=self.fade_out_var,
                                        command=self.save_config)
        fade_out_check.pack(side=tk.LEFT)
        
        # Progress Section
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.progress_label = ttk.Label(progress_frame, text="Ready")
        self.progress_label.pack(anchor=tk.W)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=1.0, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        
        # Log Section
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Create text widget with scrollbar
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True)
        
        # Configure log text widget with proper colors
        self.log_text = tk.Text(log_container, height=12, wrap=tk.WORD,
                               font=('Monaco', 10), 
                               bg=self.colors['bg'], 
                               fg=self.colors['fg'],
                               selectbackground=self.colors['select_bg'],
                               selectforeground=self.colors['select_fg'],
                               insertbackground=self.colors['fg'])
        
        scrollbar = ttk.Scrollbar(log_container, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons Section - Fixed positioning
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Create a container for better button layout
        button_container = ttk.Frame(button_frame)
        button_container.pack(side=tk.RIGHT)
        
        # Generate Video button (Primary action - make it more prominent)
        self.generate_btn = self.create_rounded_button(button_container, "Generate Video",
                                                      self.generate_video,
                                                      style='Accent.TButton')
        self.generate_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Clear Log button
        self.clear_btn = self.create_rounded_button(button_container, "Clear Log",
                                                    self.clear_log)
        self.clear_btn.pack(side=tk.RIGHT)
    
    def check_dependencies(self):
        """Check dependencies"""
        self.log("Checking FFmpeg...")
        ffmpeg_ok, hw_available, msg = self.video_generator.check_ffmpeg()
        
        if not ffmpeg_ok:
            self.log(f"Error: {msg}")
            # Use after to avoid the modalSession error
            self.root.after(100, lambda: messagebox.showerror(
                "FFmpeg Not Found",
                f"FFmpeg is not available:\n{msg}\n\n"
                "Please ensure the 'ffmpeg' file is in the same directory as this application."
            ))
        else:
            self.log(f"FFmpeg found at: {self.video_generator.ffmpeg_path}")
            
            if IS_MACOS and hw_available:
                self.log("VideoToolbox available for hardware acceleration")
            elif IS_MACOS:
                self.log("VideoToolbox not available - using software encoding")
                self.use_hardware_var.set(False)
            
            # System information
            self.log(f"System: macOS {platform.mac_ver()[0]}")
    
    def log(self, message):
        """Add message to log with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        """Clear the log"""
        self.log_text.delete(1.0, tk.END)
    
    def select_audio_files(self):
        """Select audio files"""
        initialdir = self.config.get('last_audio_dir', os.path.expanduser('~/Music'))
        
        files = filedialog.askopenfilenames(
            title="Select Audio Files",
            initialdir=initialdir,
            filetypes=[
                ("Audio files", "*.mp3 *.wav *.ogg *.flac *.aac *.m4a *.wma"),
                ("All files", "*.*")
            ]
        )
        
        if files:
            # Save directory
            self.config['last_audio_dir'] = os.path.dirname(files[0])
            self.save_config()
            
            self.audio_files = sorted(files, 
                key=lambda x: VideoGenerator.get_track_number(os.path.basename(x)))
            self.audio_label.config(text=f"{len(self.audio_files)} files selected", foreground=self.colors['fg'])
            self.log(f"Selected {len(self.audio_files)} audio files:")
            
            # Show order
            for i, file in enumerate(self.audio_files, 1):
                self.log(f"  {i}. {os.path.basename(file)}")
    
    def select_image(self):
        """Select background image"""
        initialdir = self.config.get('last_image_dir', os.path.expanduser('~/Pictures'))
        
        file = filedialog.askopenfilename(
            title="Select Background Image",
            initialdir=initialdir,
            filetypes=[
                ("Images", "*.jpg *.jpeg *.png *.bmp *.tiff"),
                ("All files", "*.*")
            ]
        )
        
        if file:
            # Save directory
            self.config['last_image_dir'] = os.path.dirname(file)
            self.save_config()
            
            self.image_path = file
            self.image_label.config(text=os.path.basename(file), foreground=self.colors['fg'])
            self.log(f"Selected image: {os.path.basename(file)}")
            
            # Show image information
            try:
                img = Image.open(file)
                self.log(f"  Dimensions: {img.width}x{img.height}")
                self.log(f"  Format: {img.format}")
            except:
                pass
    
    def select_output_dir(self):
        """Select output directory"""
        initialdir = self.config.get('last_output_dir', os.path.expanduser('~/Movies'))
        
        directory = filedialog.askdirectory(
            title="Select Output Location",
            initialdir=initialdir
        )
        
        if directory:
            self.output_dir = directory
            # Show shortened path
            display_path = directory
            if len(display_path) > 40:
                display_path = "..." + display_path[-37:]
            self.output_label.config(text=display_path, foreground=self.colors['fg'])
            self.log(f"Output location: {directory}")
            
            # Save as last directory used
            self.config['last_output_dir'] = directory
            self.save_config()
    
    def generate_video(self):
        """Generate the video"""
        # Validations
        if not self.audio_files:
            self.root.after(100, lambda: messagebox.showerror("Error", "No audio files selected"))
            return
        
        if not self.image_path:
            self.root.after(100, lambda: messagebox.showerror("Error", "No background image selected"))
            return
        
        if not self.output_dir:
            self.root.after(100, lambda: messagebox.showerror("Error", "No output location selected"))
            return
        
        # Prepare output file
        filename = self.filename_var.get().strip()
        if not filename:
            filename = "output_video"
        if not filename.endswith('.mp4'):
            filename += '.mp4'
        
        self.output_filename = filename  # Store for later use
        output_path = os.path.join(self.output_dir, filename)
        
        # Check if exists
        if os.path.exists(output_path):
            result = messagebox.askyesno("File Exists", 
                                      f"The file {filename} already exists. Do you want to overwrite it?")
            if not result:
                return
        
        # Disable controls
        self.processing = True
        self.generate_btn.config(state="disabled")
        self.clear_btn.config(state="disabled")
        self.progress_var.set(0)
        self.progress_label.config(text="Processing...")
        
        # Generate in separate thread
        thread = threading.Thread(
            target=self._generate_video_thread,
            args=(output_path,)
        )
        thread.daemon = True
        thread.start()
    
    def _generate_video_thread(self, output_path):
        """Thread to generate video"""
        try:
            self.log("\n" + "="*60)
            self.log("Starting video generation...")
            self.log(f"Output file: {output_path}")
            self.log(f"Settings:")
            self.log(f"  • Quality: {self.quality_var.get()}")
            self.log(f"  • Codec: {'Hardware (VideoToolbox)' if self.use_hardware_var.get() else 'Software (libx264)'}")
            self.log(f"  • Fade In: {'Yes' if self.fade_in_var.get() else 'No'}")
            self.log(f"  • Fade Out: {'Yes' if self.fade_out_var.get() else 'No'}")
            self.log("="*60 + "\n")
            
            start_time = time.time()
            
            self.video_generator.create_video(
                audio_files=self.audio_files,
                image_path=self.image_path,
                output_path=output_path,
                use_hardware=self.use_hardware_var.get(),
                quality=self.quality_var.get(),
                fade_in=self.fade_in_var.get(),
                fade_out=self.fade_out_var.get(),
                progress_callback=self.update_progress,
                log_callback=self.log
            )
            
            elapsed_time = time.time() - start_time
            self.log(f"\nTotal time: {elapsed_time:.1f} seconds")
            self.log("Video generated successfully!")
            
            # Open in Finder
            if IS_MACOS:
                subprocess.run(['open', '-R', output_path])
                self.log("Opening location in Finder...")
            
            # System notification
            if IS_MACOS and self.output_filename:
                self.send_notification("Video Generated", f"'{self.output_filename}' has been created successfully")
            
            self.root.after(0, lambda: self.show_completion_dialog(output_path, elapsed_time))
            
        except Exception as e:
            self.log(f"\nError: {str(e)}")
            logger.exception("Error generating video")
            self.root.after(0, lambda: messagebox.showerror(
                "Error", 
                f"Error generating video:\n{str(e)}"
            ))
        
        finally:
            self.root.after(0, self._reset_ui)
    
    def show_completion_dialog(self, output_path, elapsed_time):
        """Show completion dialog"""
        messagebox.showinfo(
            "Success", 
            f"Video generated successfully!\n\n"
            f"File: {os.path.basename(output_path)}\n"
            f"Time: {elapsed_time:.1f} seconds\n\n"
            f"The video location has been opened in Finder."
        )
    
    def update_progress(self, value):
        """Update progress bar"""
        def update():
            self.progress_var.set(value)
            percentage = int(value * 100)
            self.progress_label.config(text=f"Processing... {percentage}%")
        
        self.root.after(0, update)
    
    def _reset_ui(self):
        """Reset the interface"""
        self.processing = False
        self.generate_btn.config(state="normal")
        self.clear_btn.config(state="normal")
        self.progress_var.set(0)
        self.progress_label.config(text="Ready")
    
    def send_notification(self, title, message):
        """Send system notification on macOS"""
        try:
            subprocess.run([
                'osascript', '-e',
                f'display notification "{message}" with title "{title}" sound name "Glass"'
            ])
        except:
            pass
    
    def show_preferences(self):
        """Show preferences window"""
        pref_window = tk.Toplevel(self.root)
        pref_window.title("Preferences")
        pref_window.geometry("500x450")
        pref_window.transient(self.root)
        
        # Configure window background
        pref_window.configure(bg=self.colors['bg'])
        
        # Main frame
        pref_frame = ttk.Frame(pref_window, padding="20")
        pref_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(pref_frame, text="Preferences", 
                               font=('System', 18, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # FFmpeg information
        info_frame = ttk.LabelFrame(pref_frame, text="System Information", padding="15")
        info_frame.pack(fill=tk.X, pady=10)
        
        # Create labels with proper spacing
        ffmpeg_name_label = ttk.Label(info_frame, text=f"FFmpeg: {os.path.basename(self.video_generator.ffmpeg_path)}")
        ffmpeg_name_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Use a frame for better path display
        path_frame = ttk.Frame(info_frame)
        path_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(path_frame, text="Location:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Path in a text widget for better display
        path_text = tk.Text(path_frame, height=2, wrap=tk.WORD,
                           font=('Monaco', 9), 
                           bg=self.colors['entry_bg'], 
                           fg=self.colors['entry_fg'])
        path_text.insert(1.0, self.video_generator.ffmpeg_path)
        path_text.config(state='disabled')
        path_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Button to reveal FFmpeg in Finder
        finder_btn = self.create_rounded_button(info_frame, "Show in Finder", 
                                               lambda: subprocess.run(['open', '-R', self.video_generator.ffmpeg_path]))
        finder_btn.pack(pady=(5, 0))
        
        # Default directories
        dirs_frame = ttk.LabelFrame(pref_frame, text="Default Directories", padding="15")
        dirs_frame.pack(fill=tk.X, pady=10)
        
        dirs_label = ttk.Label(dirs_frame, text="Selected directories are remembered automatically",
                              font=('System', 11))
        dirs_label.pack()
        
        # Clean temp files section
        clean_frame = ttk.Frame(pref_frame)
        clean_frame.pack(fill=tk.X, pady=(20, 10))
        
        clean_btn = self.create_rounded_button(clean_frame, "Clean Temporary Files", 
                                              self.clean_temp_files)
        clean_btn.pack()
        
        # Close button
        close_frame = ttk.Frame(pref_frame)
        close_frame.pack(side=tk.BOTTOM, pady=(0))
        
        close_btn = self.create_rounded_button(close_frame, "Close", 
                                              pref_window.destroy)
        close_btn.pack()
    
    def clean_temp_files(self):
        """Clean temporary files"""
        temp_dir = tempfile.gettempdir()
        cleaned = 0
        
        for item in os.listdir(temp_dir):
            if item.startswith('videogenerator_'):
                try:
                    path = os.path.join(temp_dir, item)
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.unlink(path)
                    cleaned += 1
                except:
                    pass
        
        messagebox.showinfo("Cleanup Complete", 
                           f"Removed {cleaned} temporary files/directories")
    
    def show_about(self):
        """Show About window"""
        about_window = tk.Toplevel(self.root)
        about_window.title("About VideoGenerator")
        about_window.geometry("400x500")
        about_window.transient(self.root)
        about_window.resizable(False, False)
        
        # Configure window background
        about_window.configure(bg=self.colors['bg'])
        
        # Main frame
        about_frame = ttk.Frame(about_window, padding="30")
        about_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo/Icon (if exists)
        icon_path = os.path.join(APPLICATION_PATH, 'icon.png')
        if os.path.exists(icon_path):
            try:
                img = Image.open(icon_path)
                img = img.resize((100, 100), Image.Resampling.LANCZOS)
                photo = tk.PhotoImage(img)
                icon_label = ttk.Label(about_frame, image=photo)
                icon_label.pack(pady=(0, 20))
                about_window.photo = photo  # Keep reference
            except:
                pass
        
        # Title
        title_label = ttk.Label(about_frame, text="VideoGenerator", 
                               font=('System', 24, 'bold'))
        title_label.pack()
        
        version_label = ttk.Label(about_frame, text="Version 1.2.0", 
                                 font=('System', 14))
        version_label.pack(pady=(5, 20))
        
        # Description
        desc_text = """Create music videos by combining
audio files with a static image.

Optimized for macOS
Bundled FFmpeg included"""
        
        desc_label = ttk.Label(about_frame, text=desc_text, 
                              justify=tk.CENTER, font=('System', 12))
        desc_label.pack(pady=(0, 20))
        
        # Separator
        separator = ttk.Separator(about_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=10)
        
        # Links
        links_frame = ttk.Frame(about_frame)
        links_frame.pack(pady=10)
        
        github_btn = self.create_rounded_button(links_frame, "GitHub", 
                                               lambda: subprocess.run(['open', 'https://github.com/Wamphyre/VideoGenerator']))
        github_btn.pack(side=tk.LEFT, padx=5)
        
        kofi_btn = self.create_rounded_button(links_frame, "Support on Ko-fi", 
                                             lambda: subprocess.run(['open', 'https://ko-fi.com/wamphyre94078']))
        kofi_btn.pack(side=tk.LEFT, padx=5)
        
        # Copyright
        copyright_label = ttk.Label(about_frame, text="© 2024 Wamphyre", 
                                   font=('System', 11))
        copyright_label.pack(pady=(20, 0))
        
        license_label = ttk.Label(about_frame, text="BSD 3-Clause License", 
                                 font=('System', 10), foreground='gray')
        license_label.pack()
        
        # Close button
        close_btn = self.create_rounded_button(about_frame, "Close", 
                                              about_window.destroy)
        close_btn.pack(pady=(30, 0))
    
    def quit_app(self):
        """Quit the application"""
        if self.processing:
            result = messagebox.askyesno("Confirm Exit", 
                                      "A video is being processed. Do you want to exit anyway?")
            if not result:
                return
        
        self.save_config()
        self.root.quit()
    
    def run(self):
        """Run the application"""
        if IS_MACOS:
            # Configure application menu for macOS
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)
            
            # VideoGenerator menu
            app_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="VideoGenerator", menu=app_menu)
            app_menu.add_command(label="About VideoGenerator", 
                               command=self.show_about)
            app_menu.add_separator()
            app_menu.add_command(label="Preferences...", 
                               command=self.show_preferences, accelerator="Cmd+,")
            app_menu.add_separator()
            app_menu.add_command(label="Quit", command=self.quit_app, 
                               accelerator="Cmd+Q")
            
            # File menu
            file_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="File", menu=file_menu)
            file_menu.add_command(label="Select Audio Files...", 
                                command=self.select_audio_files, accelerator="Cmd+O")
            file_menu.add_command(label="Select Image...", 
                                command=self.select_image, accelerator="Cmd+I")
            file_menu.add_separator()
            file_menu.add_command(label="Generate Video", 
                                command=self.generate_video, accelerator="Cmd+G")
            
            # Edit menu
            edit_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Edit", menu=edit_menu)
            edit_menu.add_command(label="Clear Log", 
                                command=self.clear_log, accelerator="Cmd+L")
            
            # Keyboard shortcuts
            self.root.bind('<Command-o>', lambda e: self.select_audio_files())
            self.root.bind('<Command-i>', lambda e: self.select_image())
            self.root.bind('<Command-g>', lambda e: self.generate_video())
            self.root.bind('<Command-l>', lambda e: self.clear_log())
            self.root.bind('<Command-q>', lambda e: self.quit_app())
            self.root.bind('<Command-comma>', lambda e: self.show_preferences())
        
        # Window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")
        
        self.root.mainloop()

def main():
    """Main function"""
    # Configure for high resolution on macOS
    if IS_MACOS:
        try:
            # Try to configure for Retina
            from tkinter import _tkinter
            try:
                # This may vary depending on Tk version
                # Try to set Retina support
                root = tk.Tk()
                root.withdraw()
                root.tk.call('tk', 'scaling', 2.0)
                root.destroy()
            except:
                pass
        except:
            pass
    
    # Create and run the application
    app = VideoGeneratorGUI()
    app.run()

if __name__ == "__main__":
    main()