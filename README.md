# VideoGenerator

A professional macOS application for creating music videos by combining audio files with static background images. Built with Python and optimized for macOS with native integration and hardware acceleration support.

![VideoGenerator](https://img.shields.io/badge/macOS-10.14+-blue.svg)
![Python](https://img.shields.io/badge/Python-3.8+-green.svg)
![License](https://img.shields.io/badge/License-BSD%203--Clause-orange.svg)

## 🎥 What is VideoGenerator?

VideoGenerator is a specialized tool designed for content creators, musicians, and video producers who need to quickly create professional music videos. It combines multiple audio files into a single video with a static background image, perfect for:

- **Music albums** - Create videos for entire albums or playlists
- **Podcast episodes** - Add visual elements to audio content  
- **Social media** - Generate engaging video content from audio
- **YouTube uploads** - Convert audio-only content to video format
- **Lyric videos** - Use custom background images with your music

## ✨ Key Features

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
- **Finder integration** - Opens output location automatically
- **Retina display support** - Optimized for high-DPI screens
- **Keyboard shortcuts** - Power user friendly

## 📋 System Requirements

- **macOS**: 10.14 (Mojave) or later
- **Architecture**: Intel and Apple Silicon (Universal Binary)
- **Python**: 3.8+ (bundled with dependencies)
- **Storage**: ~100MB for application and dependencies

## 🚀 Installation

### Option 1: Download Release (Recommended)
1. Download the latest `VideoGenerator-X.X.X.dmg` from [Releases](https://github.com/Wamphyre/VideoGenerator/releases)
2. Double-click the DMG file to mount it
3. Drag `VideoGenerator.app` to your Applications folder
4. Launch from Applications or Spotlight

### Option 2: Build from Source
```bash
# Clone the repository
git clone https://github.com/Wamphyre/VideoGenerator.git
cd VideoGenerator

# Install Python dependencies
pip3 install -r requirements.txt

# Build native app (requires Xcode Command Line Tools)
chmod +x build_with_platypus.sh
./build_with_platypus.sh

# Install the built app
cp -r dist/VideoGenerator.app /Applications/
```

## 🎯 How to Use

### Basic Workflow
1. **Select Audio Files** - Choose one or more audio files to combine
2. **Choose Background Image** - Select a static image for the video background  
3. **Set Output Location** - Choose where to save the generated video
4. **Configure Options** - Adjust quality, effects, and encoding settings
5. **Generate Video** - Click the blue "Generate Video" button

### Interface Overview

#### Files Section
- **Audio Files**: Select multiple audio files (automatically ordered by filename)
- **Background Image**: Choose a single image for the video background
- **Output Settings**: Set save location and filename

#### Encoding Options
- **Quality**: Choose from Low, Medium, High, or Ultra presets
- **Hardware Acceleration**: Enable VideoToolbox for faster encoding (macOS only)
- **Fade Effects**: Toggle fade in/out effects (2-second duration)

#### Progress & Logging
- **Real-time progress bar** with percentage completion
- **Detailed activity log** with timestamps
- **FFmpeg output** for troubleshooting

### Pro Tips
- **File naming**: Number your audio files (01, 02, 03...) for proper ordering
- **Image resolution**: Use high-resolution images (1920x1080 or higher) for best quality
- **Hardware acceleration**: Enable for 2-3x faster encoding on supported Macs
- **Quality settings**: Use "High" for most purposes, "Ultra" for archival quality

## ⚙️ Technical Details

### Architecture
- **Frontend**: Python/Tkinter with native macOS styling
- **Backend**: FFmpeg for video processing and encoding
- **Launcher**: Native C executable to eliminate Python branding
- **Packaging**: macOS app bundle with embedded dependencies

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
├── build_with_platypus.sh     # Build script for native app
├── requirements.txt           # Python dependencies
├── ffmpeg                     # Bundled FFmpeg binary
├── icon.png                   # Application icon
└── dist/                      # Build output directory
    ├── VideoGenerator.app     # Native macOS application
    └── VideoGenerator-X.X.X.dmg # Distribution package
```

### Dependencies
- **tkinter**: GUI framework (built into Python)
- **Pillow**: Image processing and optimization
- **numpy**: Numerical operations for image handling
- **psutil**: System information and process management
- **FFmpeg**: Video encoding and processing (bundled)

### Building
The build process creates a native macOS application that:
1. Compiles a C launcher to eliminate Python branding
2. Bundles all Python dependencies
3. Includes FFmpeg binary for video processing
4. Creates proper macOS app bundle structure
5. Generates DMG for easy distribution

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

### Development Setup
```bash
git clone https://github.com/Wamphyre/VideoGenerator.git
cd VideoGenerator
pip3 install -r requirements.txt
python3 videogenerator.py  # Run in development mode
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