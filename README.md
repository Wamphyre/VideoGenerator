# VideoGenerator

A professional macOS application for creating music videos by combining audio files with static background images. **Completely standalone** - no Python installation required!

![VideoGenerator](https://img.shields.io/badge/macOS-10.14+-blue.svg)
![Version](https://img.shields.io/badge/Version-1.3.0-green.svg)
![License](https://img.shields.io/badge/License-BSD%203--Clause-orange.svg)
![Standalone](https://img.shields.io/badge/Standalone-No%20Dependencies-brightgreen.svg)

## 🎥 What is VideoGenerator?

VideoGenerator is a specialized tool designed for content creators, musicians, and video producers who need to quickly create professional music videos. It combines multiple audio files into a single video with a static background image, perfect for:

- **Music albums** - Create videos for entire albums or playlists
- **Podcast episodes** - Add visual elements to audio content  
- **Social media** - Generate engaging video content from audio
- **YouTube uploads** - Convert audio-only content to video format
- **Lyric videos** - Use custom background images with your music

## ✨ Key Features

### 🆕 What's New in v1.3.0
- **Completely Standalone** - No Python installation required on target machines
- **Modern Interface** - Redesigned with CustomTkinter for better UX
- **Clean Menu Bar** - Shows "VideoGenerator" instead of "Python"
- **Enhanced System Info** - Displays GPU model and hardware acceleration status
- **Improved Logging** - Better formatted activity log with timestamps
- **Compact Design** - More efficient use of screen space
- **Auto-contained FFmpeg** - Bundled and automatically detected

### 🎵 Audio Processing
- **Multiple format support**: MP3, WAV, OGG, FLAC, AAC, M4A, WMA
- **Automatic track ordering** by filename numbers
- **Seamless concatenation** of multiple audio files
- **High-quality audio encoding** (320k AAC)

### 🖼️ Image Processing  
- **Format support**: JPG, JPEG, PNG, BMP, TIFF
- **Automatic optimization** for video output (1920x1080)
- **Aspect ratio preservation** with letterboxing
- **Background centering** with black bars if needed

### 🎬 Video Generation
- **Quality presets**: Low, Medium, High, Ultra
- **Hardware acceleration**: VideoToolbox support on macOS
- **Fade effects**: Customizable fade in/out (2 seconds)
- **Optimized encoding** for streaming and playback

### 🍎 macOS Integration
- **Native app bundle** - No Python menu, shows "VideoGenerator"
- **Finder integration** - Opens output location automatically
- **Retina display support** - Optimized for high-DPI screens
- **Keyboard shortcuts** - Power user friendly
- **System notifications** - Completion alerts with sound
- **Completely standalone** - No external dependencies required

## 📋 System Requirements

- **macOS**: 10.14 (Mojave) or later
- **Architecture**: Intel and Apple Silicon compatible
- **Dependencies**: None! Everything is bundled
- **Storage**: ~200MB for standalone application
- **Memory**: 4GB RAM recommended for video processing

## 🚀 Installation

### Option 1: Download Release (Recommended)
1. Download the latest `VideoGenerator-1.3.0.dmg` from [Releases](https://github.com/Wamphyre/VideoGenerator/releases)
2. Double-click the DMG file to mount it
3. Drag `VideoGenerator.app` to your Applications folder
4. Launch from Applications or Spotlight
5. **That's it!** No Python or dependencies needed

### Option 2: Build from Source
```bash
# Clone the repository
git clone https://github.com/Wamphyre/VideoGenerator.git
cd VideoGenerator

# Install Python dependencies (for building only)
pip3 install -r requirements.txt

# Build standalone app (requires Xcode Command Line Tools)
chmod +x build_app.sh
./build_app.sh

# Install the built app
cp -r dist/VideoGenerator.app /Applications/
```

> **Note**: The built app is completely standalone and includes Python + all dependencies. Users don't need Python installed!

## 🎯 How to Use

### Basic Workflow
1. **Select Audio Files** - Choose one or more audio files to combine
2. **Choose Background Image** - Select a static image for the video background  
3. **Set Output Location** - Choose where to save the generated video
4. **Configure Options** - Adjust quality, effects, and encoding settings
5. **Generate Video** - Click the blue "Generate Video" button

### Interface Overview

#### Files Section
- **Audio Files**: Browse and select multiple audio files (automatically ordered by filename)
- **Background Image**: Choose a single image for the video background
- **Output Settings**: Set save location and custom filename

#### Settings Section
- **Quality**: Choose from Low, Medium, High, or Ultra presets
- **Hardware Acceleration**: Enable VideoToolbox for faster encoding (automatically detected)
- **Fade Effects**: Toggle fade in/out effects (2-second duration)

#### Progress & Generation
- **Real-time progress bar** with percentage completion
- **Generate Video**: Large, prominent button to start processing
- **Activity Log**: Detailed log with timestamps and system information
- **Utility Buttons**: Clear log and access settings

### Pro Tips
- **File naming**: Number your audio files (01, 02, 03...) for proper ordering
- **Image resolution**: Use high-resolution images (1920x1080 or higher) for best quality
- **Hardware acceleration**: Automatically detected and enabled on supported Macs
- **Quality settings**: Use "High" for most purposes, "Ultra" for archival quality
- **System info**: Check the activity log to see your GPU model and acceleration status
- **Standalone**: Share the app with others - no installation required!

## ⚙️ Technical Details

### Architecture
- **Frontend**: CustomTkinter with modern dark theme
- **Backend**: FFmpeg for video processing and encoding
- **Launcher**: Bash wrapper with process name masking
- **Packaging**: PyInstaller with complete Python runtime bundled
- **Distribution**: Standalone macOS app bundle (no dependencies)

### Video Specifications
- **Resolution**: 1920x1080 (Full HD)
- **Frame Rate**: 30 FPS
- **Video Codec**: H.264 (hardware accelerated when available)
- **Audio Codec**: AAC 320kbps, 48kHz stereo
- **Container**: MP4 with fast-start optimization

### Performance
- **Hardware Encoding**: Uses VideoToolbox on supported Macs
- **Multi-threading**: Utilizes all available CPU cores
- **Memory Efficient**: Processes large files without excessive RAM usage
- **Optimized I/O**: Minimizes disk operations during encoding

## 🛠️ Development

### Project Structure
```
VideoGenerator/
├── videogenerator.py          # Main application code
├── build_app.sh              # Build script for standalone app
├── requirements.txt           # Python dependencies (for building)
├── ffmpeg                     # Bundled FFmpeg binary
├── icon.png                   # Application icon
├── LICENSE                    # BSD-3 License
└── dist/                      # Build output directory
    ├── VideoGenerator.app     # Standalone macOS application
    └── VideoGenerator-1.3.0.dmg # Distribution package
```

### Dependencies (All Bundled)
- **CustomTkinter**: Modern GUI framework with dark theme
- **Pillow**: Image processing and optimization
- **numpy**: Numerical operations for image handling
- **psutil**: System information and process management
- **Python 3.13**: Complete runtime bundled
- **FFmpeg**: Video encoding and processing (bundled)

### Building
The build process creates a completely standalone macOS application that:
1. Uses PyInstaller to bundle Python runtime and all dependencies
2. Creates a bash wrapper to mask the process name as "VideoGenerator"
3. Includes FFmpeg binary for video processing
4. Bundles all required libraries and frameworks
5. Creates proper macOS app bundle structure with custom Info.plist
6. Generates DMG for easy distribution
7. Results in a ~200MB standalone app that works on any Mac

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

### Development Setup
```bash
git clone https://github.com/Wamphyre/VideoGenerator.git
cd VideoGenerator

# Install dependencies for development
pip3 install -r requirements.txt

# Run in development mode
python3 videogenerator.py

# Build standalone app
chmod +x build_app.sh
./build_app.sh
```

### Reporting Issues
When reporting bugs, please include:
- macOS version
- Python version
- Error messages from the activity log
- Steps to reproduce the issue

## 📄 License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details.

## 💖 Support

If you find VideoGenerator useful, consider supporting the project:

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20Development-red.svg)](https://ko-fi.com/wamphyre94078)

## 🔗 Links

- **GitHub Repository**: https://github.com/Wamphyre/VideoGenerator
- **Releases**: https://github.com/Wamphyre/VideoGenerator/releases
- **Support**: https://ko-fi.com/wamphyre94078

---

**Made with ❤️ for the macOS community**

*VideoGenerator - Transform your audio into engaging video content*