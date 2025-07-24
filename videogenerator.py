#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
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

def set_process_name():
    """Set process name before creating the app to change menu bar name"""
    try:
        # Check if running from native app bundle
        is_native_app = os.environ.get('VIDEOGENERATOR_APP') == '1'
        
        # Method 1: Set sys.argv[0] early
        sys.argv[0] = "VideoGenerator"
        
        # Method 2: macOS specific - set process name using Foundation (most effective)
        try:
            import objc
            from Foundation import NSProcessInfo, NSBundle
            
            # Set process name
            NSProcessInfo.processInfo().setProcessName_("VideoGenerator")
            
            # If running as native app, also set bundle info
            if is_native_app:
                bundle = NSBundle.mainBundle()
                if bundle:
                    info = bundle.infoDictionary()
                    if info:
                        info['CFBundleName'] = 'VideoGenerator'
                        info['CFBundleDisplayName'] = 'VideoGenerator'
            
            print("Process name set using Foundation framework")
            
        except ImportError:
            # Foundation not available, try ctypes approach
            try:
                import ctypes
                import ctypes.util
                
                # Load Foundation framework
                foundation_lib = ctypes.util.find_library("Foundation")
                if foundation_lib:
                    objc_lib = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
                    
                    # Set up function signatures
                    objc_lib.objc_getClass.restype = ctypes.c_void_p
                    objc_lib.objc_getClass.argtypes = [ctypes.c_char_p]
                    objc_lib.sel_registerName.restype = ctypes.c_void_p
                    objc_lib.sel_registerName.argtypes = [ctypes.c_char_p]
                    objc_lib.objc_msgSend.restype = ctypes.c_void_p
                    objc_lib.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
                    
                    # Get NSProcessInfo and set process name
                    NSProcessInfo = objc_lib.objc_getClass(b"NSProcessInfo")
                    processInfo = objc_lib.objc_msgSend(NSProcessInfo, objc_lib.sel_registerName(b"processInfo"))
                    
                    # Create NSString for "VideoGenerator"
                    objc_lib.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
                    NSString = objc_lib.objc_getClass(b"NSString")
                    app_name = objc_lib.objc_msgSend(NSString, objc_lib.sel_registerName(b"stringWithUTF8String:"), b"VideoGenerator")
                    objc_lib.objc_msgSend(processInfo, objc_lib.sel_registerName(b"setProcessName:"), app_name)
                    
                    print("Process name set using ctypes Foundation framework")
                    
            except Exception as e:
                print(f"Failed to set process name with ctypes: {e}")
                
    except Exception as e:
        print(f"Failed to set process name: {e}")

# Set process name early on macOS
if platform.system() == 'Darwin':
    set_process_name()

# macOS initialization - simplified to avoid compatibility issues
if platform.system() == 'Darwin':
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyRegular
        def make_app_visible():
            try:
                app = NSApplication.sharedApplication()
                app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
            except:
                pass
    except ImportError:
        def make_app_visible():
            pass
else:
    def make_app_visible():
        pass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check operating system
IS_MACOS = platform.system() == 'Darwin'

# Get application directory and FFmpeg path
def get_application_path():
    """Get the correct application path for both development and packaged versions"""
    if getattr(sys, 'frozen', False):
        # If packaged with PyInstaller
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller temporary directory
            return sys._MEIPASS
        else:
            # Other packaged application
            return os.path.dirname(sys.executable)
    else:
        # If normal script
        return os.path.dirname(os.path.abspath(__file__))

def find_ffmpeg():
    """Find FFmpeg in various possible locations"""
    base_path = get_application_path()
    
    # Possible FFmpeg locations
    possible_paths = [
        os.path.join(base_path, 'ffmpeg'),  # Same directory as script/executable
        os.path.join(base_path, '..', 'Resources', 'ffmpeg'),  # macOS app bundle Resources
        os.path.join(base_path, 'Resources', 'ffmpeg'),  # Alternative Resources location
        './ffmpeg',  # Current directory fallback
    ]
    
    for ffmpeg_path in possible_paths:
        if os.path.exists(ffmpeg_path):
            os.chmod(ffmpeg_path, 0o755)  # Ensure execution permissions
            return ffmpeg_path
    
    return None

APPLICATION_PATH = get_application_path()
FFMPEG_PATH = find_ffmpeg()
FFPROBE_PATH = os.path.join(APPLICATION_PATH, 'ffprobe') if FFMPEG_PATH else None

class VideoGenerator:
    """Video generator optimized for macOS with bundled FFmpeg"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix='videogenerator_')
        self.executor = ThreadPoolExecutor(max_workers=multiprocessing.cpu_count())
        self.ffmpeg_path = find_ffmpeg()
        self.ffprobe_path = self.ffmpeg_path  # Use same path for both
        
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
    """Interfaz gráfica moderna con CustomTkinter"""
    
    def __init__(self):
        # Configurar tema y apariencia de CustomTkinter
        ctk.set_appearance_mode("dark")  # Modo oscuro por defecto
        ctk.set_default_color_theme("blue")  # Tema azul
        
        # Crear ventana principal compacta
        self.root = ctk.CTk()
        self.root.title("VideoGenerator")
        # La geometría se establece en setup_ui() para mejor control
        
        # Configurar icono de la aplicación
        self._setup_app_icon()
        
        # On macOS, setup immediately to prevent default menu creation
        if IS_MACOS:
            make_app_visible()
            # Call immediately, not after delay, to prevent default menu
            self._setup_macos_app()
        
        # Variables de la aplicación
        self.video_generator = VideoGenerator()
        self.audio_files = []
        self.image_path = None
        self.output_dir = None
        self.processing = False
        self.output_filename = None
        
        # Configuración guardada
        self.config_file = os.path.join(APPLICATION_PATH, 'config.json')
        self.load_config()
        
        # Configurar la interfaz
        self.setup_ui()
        self.check_dependencies()
    
    def _setup_app_icon(self):
        """Setup application icon"""
        icon_path = os.path.join(APPLICATION_PATH, 'icon.png')
        if os.path.exists(icon_path):
            try:
                # For CustomTkinter, we need to use the underlying tkinter window
                icon_image = tk.PhotoImage(file=icon_path)
                self.root.wm_iconphoto(True, icon_image)
                # Keep a reference to prevent garbage collection
                self.root.icon_image = icon_image
            except Exception as e:
                logger.warning(f"Could not set application icon: {e}")
    
    def _setup_macos_app(self):
        """Setup macOS specific app behavior"""
        if IS_MACOS:
            try:
                # Create our custom menu bar
                self._create_custom_menubar()
                
                # Setup macOS commands to override default behavior
                self.root.createcommand('tk::mac::ShowPreferences', self.show_preferences)
                self.root.createcommand('tk::mac::ShowAbout', self.show_about)
                self.root.createcommand('tk::mac::Quit', self.quit_app)
                
                # Keyboard shortcuts
                self.root.bind('<Command-o>', lambda e: self.select_audio_files())
                self.root.bind('<Command-i>', lambda e: self.select_image())
                self.root.bind('<Command-g>', lambda e: self.generate_video())
                self.root.bind('<Command-l>', lambda e: self.clear_log())
                self.root.bind('<Command-q>', lambda e: self.quit_app())
                self.root.bind('<Command-comma>', lambda e: self.show_preferences())
                
            except Exception as e:
                print(f"Could not setup macOS menu: {e}")
    
    def _create_custom_menubar(self):
        """Create custom menu bar without duplicating app name"""
        try:
            # Create empty menu bar first
            menubar = tk.Menu(self.root)
            
            # File menu (first menu, no app menu to avoid duplication)
            file_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="File", menu=file_menu)
            file_menu.add_command(label="Select Audio Files...", command=self.select_audio_files, accelerator="Cmd+O")
            file_menu.add_command(label="Select Background Image...", command=self.select_image, accelerator="Cmd+I")
            file_menu.add_separator()
            file_menu.add_command(label="Generate Video", command=self.generate_video, accelerator="Cmd+G")
            file_menu.add_separator()
            file_menu.add_command(label="Preferences...", command=self.show_preferences, accelerator="Cmd+,")
            file_menu.add_separator()
            file_menu.add_command(label="Quit VideoGenerator", command=self.quit_app, accelerator="Cmd+Q")
            
            # Edit menu
            edit_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Edit", menu=edit_menu)
            edit_menu.add_command(label="Clear Log", command=self.clear_log, accelerator="Cmd+L")
            
            # Help menu
            help_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Help", menu=help_menu)
            help_menu.add_command(label="About VideoGenerator", command=self.show_about)
            
            # Set the menu bar - this should replace the default one
            self.root.config(menu=menubar)
            
        except Exception as e:
            print(f"Could not create custom menu bar: {e}")
    
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
    

    
    def setup_ui(self):
        """Setup clean and minimal interface"""
        # Configure window - taller for better log visibility
        self.root.geometry("650x700")
        self.root.minsize(600, 650)
        
        # Main container without frame borders
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        main_container = ctk.CTkFrame(self.root, corner_radius=0, fg_color="transparent")
        main_container.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(3, weight=1)
        
        # Section 1: File Selection - cleaner without frame
        files_section = ctk.CTkFrame(main_container, corner_radius=8)
        files_section.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        files_section.grid_columnconfigure(1, weight=1)
        
        # Audio files
        ctk.CTkLabel(files_section, text="Audio Files:", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, padx=15, pady=(15, 8), sticky="w"
        )
        
        audio_container = ctk.CTkFrame(files_section, fg_color="transparent")
        audio_container.grid(row=0, column=1, sticky="ew", padx=(5, 15), pady=(15, 8))
        audio_container.grid_columnconfigure(1, weight=1)
        
        self.audio_btn = ctk.CTkButton(
            audio_container, text="Browse", command=self.select_audio_files, width=80, height=30
        )
        self.audio_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.audio_label = ctk.CTkLabel(
            audio_container, text="No files selected", text_color="gray60", font=ctk.CTkFont(size=12)
        )
        self.audio_label.grid(row=0, column=1, sticky="w")
        
        # Background image
        ctk.CTkLabel(files_section, text="Background:", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=1, column=0, padx=15, pady=6, sticky="w"
        )
        
        image_container = ctk.CTkFrame(files_section, fg_color="transparent")
        image_container.grid(row=1, column=1, sticky="ew", padx=(5, 15), pady=6)
        image_container.grid_columnconfigure(1, weight=1)
        
        self.image_btn = ctk.CTkButton(
            image_container, text="Browse", command=self.select_image, width=80, height=30
        )
        self.image_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.image_label = ctk.CTkLabel(
            image_container, text="No image selected", text_color="gray60", font=ctk.CTkFont(size=12)
        )
        self.image_label.grid(row=0, column=1, sticky="w")
        
        # Output location
        ctk.CTkLabel(files_section, text="Output:", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=2, column=0, padx=15, pady=6, sticky="w"
        )
        
        output_container = ctk.CTkFrame(files_section, fg_color="transparent")
        output_container.grid(row=2, column=1, sticky="ew", padx=(5, 15), pady=6)
        output_container.grid_columnconfigure(1, weight=1)
        
        self.output_btn = ctk.CTkButton(
            output_container, text="Browse", command=self.select_output_dir, width=80, height=30
        )
        self.output_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.output_label = ctk.CTkLabel(
            output_container, text="No location selected", text_color="gray60", font=ctk.CTkFont(size=12)
        )
        self.output_label.grid(row=0, column=1, sticky="w")
        
        # Filename
        filename_container = ctk.CTkFrame(files_section, fg_color="transparent")
        filename_container.grid(row=3, column=0, columnspan=2, sticky="ew", padx=15, pady=(6, 15))
        filename_container.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(filename_container, text="Filename:", font=ctk.CTkFont(size=12)).grid(
            row=0, column=0, padx=(0, 10), sticky="w"
        )
        
        self.filename_var = tk.StringVar(value="output_video")
        self.filename_entry = ctk.CTkEntry(filename_container, textvariable=self.filename_var, height=30)
        self.filename_entry.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        
        ctk.CTkLabel(filename_container, text=".mp4", font=ctk.CTkFont(size=12)).grid(row=0, column=2)
        
        # Section 2: Settings - horizontal layout
        settings_section = ctk.CTkFrame(main_container, corner_radius=8)
        settings_section.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        settings_section.grid_columnconfigure((1, 2, 3, 4), weight=1)
        
        ctk.CTkLabel(settings_section, text="Settings:", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, padx=15, pady=15, sticky="w"
        )
        
        # Quality
        quality_container = ctk.CTkFrame(settings_section, fg_color="transparent")
        quality_container.grid(row=0, column=1, padx=10, pady=15)
        
        ctk.CTkLabel(quality_container, text="Quality", font=ctk.CTkFont(size=11)).grid(row=0, column=0, pady=(0, 4))
        
        self.quality_var = tk.StringVar(value=self.config.get('quality', 'high'))
        self.quality_combo = ctk.CTkComboBox(
            quality_container,
            values=["low", "medium", "high", "ultra"],
            variable=self.quality_var,
            command=lambda x: self.save_config(),
            width=85,
            height=28
        )
        self.quality_combo.grid(row=1, column=0)
        
        # Checkboxes
        self.use_hardware_var = tk.BooleanVar(value=self.config.get('use_hardware', True))
        self.hw_check = ctk.CTkCheckBox(
            settings_section,
            text="Hardware\nAcceleration",
            variable=self.use_hardware_var,
            command=self.save_config,
            font=ctk.CTkFont(size=11)
        )
        self.hw_check.grid(row=0, column=2, padx=10, pady=15)
        
        self.fade_in_var = tk.BooleanVar(value=self.config.get('fade_in', True))
        self.fade_in_check = ctk.CTkCheckBox(
            settings_section,
            text="Fade In",
            variable=self.fade_in_var,
            command=self.save_config,
            font=ctk.CTkFont(size=11)
        )
        self.fade_in_check.grid(row=0, column=3, padx=10, pady=15)
        
        self.fade_out_var = tk.BooleanVar(value=self.config.get('fade_out', True))
        self.fade_out_check = ctk.CTkCheckBox(
            settings_section,
            text="Fade Out",
            variable=self.fade_out_var,
            command=self.save_config,
            font=ctk.CTkFont(size=11)
        )
        self.fade_out_check.grid(row=0, column=4, padx=(10, 15), pady=15)
        
        # Section 3: Progress and Generate - compact
        action_section = ctk.CTkFrame(main_container, corner_radius=8)
        action_section.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        action_section.grid_columnconfigure(1, weight=1)
        
        # Progress
        progress_container = ctk.CTkFrame(action_section, fg_color="transparent")
        progress_container.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        progress_container.grid_columnconfigure(0, weight=1)
        
        self.progress_label = ctk.CTkLabel(
            progress_container, text="Ready", font=ctk.CTkFont(size=12, weight="bold")
        )
        self.progress_label.grid(row=0, column=0, sticky="w", pady=(0, 6))
        
        self.progress_bar = ctk.CTkProgressBar(progress_container, height=14)
        self.progress_bar.grid(row=1, column=0, sticky="ew")
        self.progress_bar.set(0)
        
        # Generate button
        self.generate_btn = ctk.CTkButton(
            action_section,
            text="Generate Video",
            command=self.generate_video,
            width=130,
            height=42,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.generate_btn.grid(row=0, column=1, padx=(15, 10), pady=15)
        
        # Utility buttons
        utils_container = ctk.CTkFrame(action_section, fg_color="transparent")
        utils_container.grid(row=0, column=2, padx=(0, 15), pady=15)
        
        self.clear_btn = ctk.CTkButton(
            utils_container,
            text="Clear Log",
            command=self.clear_log,
            width=75,
            height=30,
            fg_color="gray40",
            hover_color="gray50",
            font=ctk.CTkFont(size=11)
        )
        self.clear_btn.grid(row=0, column=0, pady=(0, 6))
        
        self.prefs_btn = ctk.CTkButton(
            utils_container,
            text="Settings",
            command=self.show_preferences,
            width=75,
            height=30,
            fg_color="gray40",
            hover_color="gray50",
            font=ctk.CTkFont(size=11)
        )
        self.prefs_btn.grid(row=1, column=0)
        
        # Section 4: Activity Log - much more space
        log_section = ctk.CTkFrame(main_container, corner_radius=8)
        log_section.grid(row=3, column=0, sticky="nsew", pady=(0, 0))
        log_section.grid_columnconfigure(0, weight=1)
        log_section.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(log_section, text="Activity Log:", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, padx=15, pady=(15, 8), sticky="w"
        )
        
        self.log_text = ctk.CTkTextbox(
            log_section,
            font=ctk.CTkFont(family="Monaco", size=10),
            wrap="word"
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
    
    def check_dependencies(self):
        """Check dependencies"""
        ffmpeg_ok, hw_available, msg = self.video_generator.check_ffmpeg()
        
        if not ffmpeg_ok:
            self.log(f"❌ Error: {msg}")
            # Use after to avoid modalSession error
            self.root.after(100, lambda: messagebox.showerror(
                "FFmpeg Not Found",
                f"FFmpeg is not available:\n{msg}\n\n"
                "Please ensure the 'ffmpeg' file is in the same directory as this application."
            ))
        else:
            self.log(f"✅ FFmpeg ready")
            
            # System information (only once)
            self.log(f"💻 System: macOS {platform.mac_ver()[0]}")
            
            # GPU information
            try:
                import subprocess
                gpu_info = subprocess.run(['system_profiler', 'SPDisplaysDataType'], 
                                        capture_output=True, text=True)
                if gpu_info.returncode == 0:
                    # Extract GPU model from system_profiler output
                    lines = gpu_info.stdout.split('\n')
                    for line in lines:
                        if 'Chipset Model:' in line or 'Graphics:' in line:
                            gpu_model = line.split(':')[-1].strip()
                            self.log(f"🎮 GPU: {gpu_model}")
                            break
                    else:
                        self.log("🎮 GPU: Unknown")
                else:
                    self.log("🎮 GPU: Unknown")
            except:
                self.log("🎮 GPU: Unknown")
            
            # Hardware acceleration status
            if IS_MACOS and hw_available:
                self.log("✅ Hardware acceleration: Available (VideoToolbox)")
            elif IS_MACOS:
                self.log("⚠️ Hardware acceleration: Not available - using software encoding")
                self.use_hardware_var.set(False)
            else:
                self.log("⚠️ Hardware acceleration: Not available on this platform")
    
    def log(self, message):
        """Add message to log with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.root.update_idletasks()
    
    def clear_log(self):
        """Clear the log"""
        self.log_text.delete("0.0", "end")
    
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
            self.audio_label.configure(text=f"{len(self.audio_files)} files selected", text_color="green")
            self.log(f"✓ Selected {len(self.audio_files)} audio files")
            
            # Show only first 3 to avoid log clutter
            for i, file in enumerate(self.audio_files[:3], 1):
                self.log(f"  {i}. {os.path.basename(file)}")
            if len(self.audio_files) > 3:
                self.log(f"  ... and {len(self.audio_files) - 3} more")
    
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
            filename = os.path.basename(file)
            if len(filename) > 30:
                filename = filename[:27] + "..."
            self.image_label.configure(text=f"{filename}", text_color="green")
            self.log(f"✓ Image: {os.path.basename(file)}")
            
            # Show image information
            try:
                img = Image.open(file)
                self.log(f"  {img.width}x{img.height} • {img.format}")
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
            # Show shortened path for compact interface
            display_path = os.path.basename(directory)
            if not display_path:
                display_path = directory.split('/')[-2] if '/' in directory else directory
            self.output_label.configure(text=f"{display_path}", text_color="green")
            self.log(f"✓ Output: {directory}")
            
            # Save as last used directory
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
        self.generate_btn.configure(state="disabled", text="Processing...")
        self.clear_btn.configure(state="disabled")
        self.prefs_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Starting...")
        
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
            self.progress_bar.set(value)
            percentage = int(value * 100)
            self.progress_label.configure(text=f"Processing {percentage}%")
        
        self.root.after(0, update)
    
    def _reset_ui(self):
        """Reset interface"""
        self.processing = False
        self.generate_btn.configure(state="normal", text="Generate Video")
        self.clear_btn.configure(state="normal")
        self.prefs_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Ready")
    
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
        pref_window = ctk.CTkToplevel(self.root)
        pref_window.title("Settings")
        pref_window.geometry("550x450")
        pref_window.transient(self.root)
        pref_window.grab_set()  # Make modal
        
        # Configure grid
        pref_window.grid_columnconfigure(0, weight=1)
        pref_window.grid_rowconfigure(0, weight=1)
        
        # Main frame with scroll
        main_frame = ctk.CTkScrollableFrame(pref_window)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame, 
            text="Settings", 
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 25))
        
        # System information
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        info_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            info_frame, 
            text="System Information", 
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 15))
        
        # FFmpeg info
        ffmpeg_info = f"FFmpeg: {os.path.basename(self.video_generator.ffmpeg_path)}"
        ctk.CTkLabel(info_frame, text=ffmpeg_info, font=ctk.CTkFont(size=12)).grid(row=1, column=0, sticky="w", padx=20, pady=5)
        
        # Location
        location_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        location_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        location_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(location_frame, text="Location:", font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w", padx=(0, 10))
        
        path_text = ctk.CTkTextbox(location_frame, height=50, font=ctk.CTkFont(family="Monaco", size=9))
        path_text.grid(row=0, column=1, sticky="ew")
        path_text.insert("0.0", self.video_generator.ffmpeg_path)
        path_text.configure(state="disabled")
        
        # Show in Finder button
        finder_btn = ctk.CTkButton(
            info_frame,
            text="Show in Finder",
            command=lambda: subprocess.run(['open', '-R', self.video_generator.ffmpeg_path]),
            width=130,
            height=32
        )
        finder_btn.grid(row=3, column=0, padx=20, pady=(10, 20))
        
        # Default directories
        dirs_frame = ctk.CTkFrame(main_frame)
        dirs_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        
        ctk.CTkLabel(
            dirs_frame, 
            text="Default Directories", 
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            dirs_frame, 
            text="Selected directories are remembered automatically",
            text_color="gray60",
            font=ctk.CTkFont(size=11)
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 20))
        
        # Clean temporary files
        clean_frame = ctk.CTkFrame(main_frame)
        clean_frame.grid(row=3, column=0, sticky="ew", pady=(0, 20))
        
        ctk.CTkLabel(
            clean_frame, 
            text="Maintenance", 
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))
        
        clean_btn = ctk.CTkButton(
            clean_frame,
            text="Clean Temporary Files",
            command=self.clean_temp_files,
            width=180,
            height=32
        )
        clean_btn.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # Close button
        close_btn = ctk.CTkButton(
            main_frame,
            text="Close",
            command=pref_window.destroy,
            width=100,
            height=35
        )
        close_btn.grid(row=4, column=0, pady=20)
    
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
        about_window = ctk.CTkToplevel(self.root)
        about_window.title("About VideoGenerator")
        about_window.geometry("400x550")
        about_window.transient(self.root)
        about_window.resizable(False, False)
        about_window.grab_set()  # Make modal
        
        # Configure grid
        about_window.grid_columnconfigure(0, weight=1)
        about_window.grid_rowconfigure(0, weight=1)
        
        # Main frame
        main_frame = ctk.CTkFrame(about_window)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Logo/Icon (if exists)
        icon_path = os.path.join(APPLICATION_PATH, 'icon.png')
        if os.path.exists(icon_path):
            try:
                img = Image.open(icon_path)
                img = img.resize((70, 70), Image.Resampling.LANCZOS)
                # Convert to CTkImage
                icon_image = ctk.CTkImage(light_image=img, dark_image=img, size=(70, 70))
                icon_label = ctk.CTkLabel(main_frame, image=icon_image, text="")
                icon_label.grid(row=0, column=0, pady=(25, 15))
            except:
                pass
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame, 
            text="VideoGenerator", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=1, column=0, pady=(0, 8))
        
        version_label = ctk.CTkLabel(
            main_frame, 
            text="Version 1.3.0", 
            font=ctk.CTkFont(size=14),
            text_color="gray60"
        )
        version_label.grid(row=2, column=0, pady=(0, 25))
        
        # Description
        desc_text = """Create music videos by combining
audio files with a static image.

✨ Optimized for macOS
🚀 FFmpeg included
🎨 Modern interface with CustomTkinter"""
        
        desc_label = ctk.CTkLabel(
            main_frame, 
            text=desc_text, 
            font=ctk.CTkFont(size=13),
            justify="center"
        )
        desc_label.grid(row=3, column=0, pady=(0, 25))
        
        # Links
        links_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        links_frame.grid(row=4, column=0, pady=(0, 25))
        
        github_btn = ctk.CTkButton(
            links_frame,
            text="GitHub",
            command=lambda: subprocess.run(['open', 'https://github.com/Wamphyre/VideoGenerator']),
            width=100,
            height=32
        )
        github_btn.grid(row=0, column=0, padx=8)
        
        kofi_btn = ctk.CTkButton(
            links_frame,
            text="Support",
            command=lambda: subprocess.run(['open', 'https://ko-fi.com/wamphyre94078']),
            width=100,
            height=32,
            fg_color="#FF5E5B",
            hover_color="#FF4444"
        )
        kofi_btn.grid(row=0, column=1, padx=8)
        
        # Copyright
        copyright_label = ctk.CTkLabel(
            main_frame, 
            text="© 2024 Wamphyre", 
            font=ctk.CTkFont(size=11),
            text_color="gray60"
        )
        copyright_label.grid(row=5, column=0, pady=(0, 5))
        
        license_label = ctk.CTkLabel(
            main_frame, 
            text="BSD 3-Clause License", 
            font=ctk.CTkFont(size=10),
            text_color="gray50"
        )
        license_label.grid(row=6, column=0, pady=(0, 25))
        
        # Close button
        close_btn = ctk.CTkButton(
            main_frame,
            text="Close",
            command=about_window.destroy,
            width=100,
            height=35
        )
        close_btn.grid(row=7, column=0, pady=(0, 25))
    
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
        # Configure window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")
        
        # Start main loop
        self.root.mainloop()

def main():
    """Main function"""
    # Set process name before creating the app
    if platform.system() == 'Darwin':
        set_process_name()
    
    # Create and run the application
    app = VideoGeneratorGUI()
    app.run()

if __name__ == "__main__":
    main()