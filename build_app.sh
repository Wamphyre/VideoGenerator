#!/bin/bash

# VideoGenerator Native Launcher Build
# Creates a native C executable to completely eliminate Python menu

echo "VideoGenerator Native Launcher Build"
echo "===================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if we have required tools
echo "Checking build tools..."
if ! command -v gcc >/dev/null 2>&1; then
    echo -e "${RED}Error: gcc not found. Install Xcode Command Line Tools:${NC}"
    echo "xcode-select --install"
    exit 1
fi
echo -e "${GREEN}✓ gcc found${NC}"

# Check required files
echo "Checking files..."
for file in videogenerator.py requirements.txt; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}Error: $file not found!${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ $file found${NC}"
done

if [ -f "ffmpeg" ]; then
    chmod +x ffmpeg
    echo -e "${GREEN}✓ FFmpeg found${NC}"
fi

# Test Python dependencies and PyInstaller
echo ""
echo "Testing Python dependencies and PyInstaller..."
PYTHON_CMD=$(which python3)
echo "Using Python: $PYTHON_CMD"

# Check if PyInstaller is installed
if ! $PYTHON_CMD -c "import PyInstaller" 2>/dev/null; then
    echo -e "${YELLOW}PyInstaller not found. Installing...${NC}"
    $PYTHON_CMD -m pip install pyinstaller
fi

# Check all required dependencies
REQUIRED_MODULES="tkinter PIL numpy psutil customtkinter PyInstaller"
for module in $REQUIRED_MODULES; do
    if ! $PYTHON_CMD -c "import $module" 2>/dev/null; then
        echo -e "${RED}Missing dependency: $module${NC}"
        echo "Installing $module..."
        if [ "$module" = "PIL" ]; then
            $PYTHON_CMD -m pip install Pillow
        else
            $PYTHON_CMD -m pip install $module
        fi
    fi
done

echo -e "${GREEN}✓ All dependencies available${NC}"

# Create icon for PyInstaller
if [ -f "icon.png" ] && [ ! -f "icon.icns" ]; then
    echo "Creating icon..."
    mkdir -p icon.iconset
    
    # Create all required icon sizes
    for size in 16 32 128 256 512; do
        sips -z $size $size icon.png --out icon.iconset/icon_${size}x${size}.png >/dev/null 2>&1
        if [ $size -ne 512 ]; then
            sips -z $((size*2)) $((size*2)) icon.png --out icon.iconset/icon_${size}x${size}@2x.png >/dev/null 2>&1
        fi
    done
    sips -z 1024 1024 icon.png --out icon.iconset/icon_512x512@2x.png >/dev/null 2>&1
    
    iconutil -c icns icon.iconset >/dev/null 2>&1
    rm -rf icon.iconset
    echo -e "${GREEN}✓ Icon created${NC}"
fi

# Create PyInstaller spec file for better control
echo ""
echo "Creating PyInstaller spec file..."
cat > videogenerator.spec << 'SPEC_EOF'
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Get current directory
current_dir = os.getcwd()

# Define data files to include
datas = []

# Add FFmpeg if it exists (include in root of bundle)
ffmpeg_path = os.path.join(current_dir, 'ffmpeg')
if os.path.exists(ffmpeg_path):
    datas.append((ffmpeg_path, '.'))
    # Also add to Resources folder for macOS app bundle compatibility
    datas.append((ffmpeg_path, 'Resources'))

# Add icon if it exists
icon_path = os.path.join(current_dir, 'icon.png')
if os.path.exists(icon_path):
    datas.append((icon_path, '.'))

# Add requirements.txt
requirements_path = os.path.join(current_dir, 'requirements.txt')
if os.path.exists(requirements_path):
    datas.append((requirements_path, '.'))

a = Analysis(
    ['videogenerator.py'],
    pathex=[current_dir],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'customtkinter',
        'PIL',
        'PIL.Image',
        'numpy',
        'psutil',
        'threading',
        'subprocess',
        'json',
        'tempfile',
        'shutil',
        'platform',
        'logging',
        'time',
        'os',
        'sys',
        're',
        'pathlib',
        'concurrent.futures',
        'multiprocessing',
        'functools'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VideoGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VideoGenerator',
)

app = BUNDLE(
    coll,
    name='VideoGenerator.app',
    icon='icon.icns' if os.path.exists('icon.icns') else None,
    bundle_identifier='com.wamphyre.videogenerator',
    version='1.3.0',
    info_plist={
        'CFBundleName': 'VideoGenerator',
        'CFBundleDisplayName': 'VideoGenerator',
        'CFBundleVersion': '1.3.0',
        'CFBundleShortVersionString': '1.3.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.14',
        'LSApplicationCategoryType': 'public.app-category.video',
        'NSHumanReadableCopyright': 'Copyright © 2024 Wamphyre',
    },
)
SPEC_EOF

echo -e "${GREEN}✓ PyInstaller spec file created${NC}"

# Build with PyInstaller
echo ""
echo "Building standalone app with PyInstaller..."
echo "This may take several minutes..."

# Clean previous builds
rm -rf build dist

# Run PyInstaller
$PYTHON_CMD -m PyInstaller videogenerator.spec --clean --noconfirm

if [ ! -d "dist/VideoGenerator.app" ]; then
    echo -e "${RED}Error: PyInstaller failed to create app bundle${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Standalone app created with PyInstaller${NC}"

# Make sure FFmpeg is executable
if [ -f "dist/VideoGenerator.app/Contents/MacOS/ffmpeg" ]; then
    chmod +x "dist/VideoGenerator.app/Contents/MacOS/ffmpeg"
elif [ -f "dist/VideoGenerator.app/Contents/Resources/ffmpeg" ]; then
    chmod +x "dist/VideoGenerator.app/Contents/Resources/ffmpeg"
fi

# Create the process name wrapper
echo ""
echo "Creating process name wrapper..."
mv "dist/VideoGenerator.app/Contents/MacOS/VideoGenerator" "dist/VideoGenerator.app/Contents/MacOS/VideoGenerator_real"

cat > "dist/VideoGenerator.app/Contents/MacOS/VideoGenerator" << 'WRAPPER_EOF'
#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set environment variable to indicate native app
export VIDEOGENERATOR_APP=1

# Execute the real app with VideoGenerator as process name
exec -a "VideoGenerator" "$SCRIPT_DIR/VideoGenerator_real" "$@"
WRAPPER_EOF

chmod +x "dist/VideoGenerator.app/Contents/MacOS/VideoGenerator"

echo -e "${GREEN}✓ Process name wrapper created${NC}"

# Try to sign the app
echo "Signing app..."
codesign --force --deep --sign - "dist/VideoGenerator.app" 2>/dev/null || {
    echo -e "${YELLOW}Note: Could not sign app (no developer certificate)${NC}"
}

# Remove quarantine
xattr -dr com.apple.quarantine "dist/VideoGenerator.app" 2>/dev/null || true

echo -e "${GREEN}✓ App preparation complete${NC}"

# Clean up PyInstaller files
rm -f videogenerator.spec
rm -rf build

# Show results
APP_SIZE=$(du -sh "dist/VideoGenerator.app" | awk '{print $1}')
echo ""
echo -e "${BLUE}Native App Build Complete! 🎉${NC}"
echo "App: dist/VideoGenerator.app"
echo "Size: $APP_SIZE"
echo ""
echo -e "${BLUE}Key Features:${NC}"
echo "• Completely standalone (no external dependencies!)"
echo "• Python and all modules bundled inside"
echo "• Should work on any macOS 10.14+ system"
echo "• Menu shows 'VideoGenerator' instead of 'Python'"
echo ""
echo -e "${BLUE}Installation:${NC}"
echo "1. Drag dist/VideoGenerator.app to /Applications"
echo "2. Double-click should work directly (no Python needed!)"
echo "3. If blocked: Right-click → Open (first time only)"
echo "4. Works on any Mac without installing anything"

# Test the app
echo ""
read -p "Test the native app now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Testing native VideoGenerator..."
    
    # Remove quarantine again
    xattr -dr com.apple.quarantine "dist/VideoGenerator.app" 2>/dev/null || true
    
    # Open the app
    open "dist/VideoGenerator.app"
    
    sleep 3
    if pgrep -f "videogenerator.py" >/dev/null; then
        echo -e "${GREEN}✓ Native app launched successfully!${NC}"
        echo "Check the menu bar - it should show 'VideoGenerator' NOT 'Python'!"
    else
        echo -e "${YELLOW}App may have launched. Check if GUI appeared.${NC}"
    fi
fi

echo ""
echo -e "${BLUE}Creating DMG for distribution...${NC}"

# Create DMG
DMG_NAME="VideoGenerator-1.3.0"
DMG_PATH="dist/${DMG_NAME}.dmg"

# Remove existing DMG if it exists
rm -f "$DMG_PATH"

# Create temporary directory for DMG contents
DMG_TEMP_DIR=$(mktemp -d)
echo "Using temp directory: $DMG_TEMP_DIR"

# Copy app to temp directory
cp -R "dist/VideoGenerator.app" "$DMG_TEMP_DIR/"

# Create Applications symlink for easy installation
ln -s /Applications "$DMG_TEMP_DIR/Applications"

# Add README file with installation instructions
cat > "$DMG_TEMP_DIR/README.txt" << 'EOF'
VideoGenerator v1.3.0
====================

Installation:
1. Drag VideoGenerator.app to the Applications folder
2. Double-click to launch
3. If blocked by security: Right-click → Open (first time only)

Requirements:
- macOS 10.14 (Mojave) or later
- Python dependencies are bundled

Features:
- Create music videos from audio files and images
- Hardware acceleration support (VideoToolbox)
- Multiple audio format support
- Fade in/out effects
- Native macOS integration

Support:
- GitHub: https://github.com/Wamphyre/VideoGenerator
- Ko-fi: https://ko-fi.com/wamphyre94078

© 2024 Wamphyre - BSD 3-Clause License
EOF

# Create DMG with proper settings
echo "Creating DMG file..."
hdiutil create -volname "VideoGenerator" \
    -srcfolder "$DMG_TEMP_DIR" \
    -ov -format UDZO \
    -fs HFS+ \
    -fsargs "-c c=64,a=16,e=16" \
    "$DMG_PATH"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ DMG created successfully${NC}"
    
    # Get DMG size
    DMG_SIZE=$(du -sh "$DMG_PATH" | awk '{print $1}')
    echo "DMG: $DMG_PATH"
    echo "Size: $DMG_SIZE"
    
    # Clean up temp directory
    rm -rf "$DMG_TEMP_DIR"
    
    # Optional: Open DMG to verify
    echo ""
    read -p "Open DMG to verify? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open "$DMG_PATH"
    fi
    
else
    echo -e "${RED}Error: Failed to create DMG${NC}"
    rm -rf "$DMG_TEMP_DIR"
fi

echo ""
echo -e "${BLUE}Build Complete! 🎉${NC}"
echo "Files created:"
echo "• App: dist/VideoGenerator.app"
echo "• DMG: $DMG_PATH"
echo ""
echo -e "${BLUE}Distribution:${NC}"
echo "• Share the DMG file for easy installation"
echo "• Users just drag the app to Applications folder"
echo "• Compatible with macOS 10.14 and later"
echo ""
echo -e "${GREEN}Done! This should finally eliminate the Python menu! 🎉${NC}"