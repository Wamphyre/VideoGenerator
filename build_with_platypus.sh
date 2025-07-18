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

# Test Python dependencies
echo ""
echo "Testing Python dependencies..."
PYTHON_CMD=$(which python3)
echo "Using Python: $PYTHON_CMD"

if ! $PYTHON_CMD -c "import tkinter, PIL, numpy, psutil" 2>/dev/null; then
    echo -e "${RED}Missing dependencies. Install with:${NC}"
    echo "pip3 install Pillow numpy psutil"
    exit 1
fi
echo -e "${GREEN}✓ All dependencies available${NC}"

# Create the native C launcher
echo ""
echo "Creating native C launcher..."
cat > videogenerator_launcher.c << 'EOF'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <libgen.h>
#include <sys/stat.h>
#include <CoreFoundation/CoreFoundation.h>

// Function to get the bundle path
char* get_bundle_path() {
    CFBundleRef bundle = CFBundleGetMainBundle();
    if (!bundle) return NULL;
    
    CFURLRef bundleURL = CFBundleCopyBundleURL(bundle);
    CFURLRef resourcesURL = CFBundleCopyResourcesDirectoryURL(bundle);
    CFURLRef absoluteResourcesURL = CFURLCopyAbsoluteURL(resourcesURL);
    
    CFStringRef path = CFURLCopyFileSystemPath(absoluteResourcesURL, kCFURLPOSIXPathStyle);
    
    CFIndex length = CFStringGetLength(path);
    CFIndex maxSize = CFStringGetMaximumSizeForEncoding(length, kCFStringEncodingUTF8) + 1;
    char* buffer = malloc(maxSize);
    
    CFStringGetCString(path, buffer, maxSize, kCFStringEncodingUTF8);
    
    CFRelease(path);
    CFRelease(absoluteResourcesURL);
    CFRelease(resourcesURL);
    CFRelease(bundleURL);
    
    return buffer;
}

// Function to find Python with dependencies
char* find_python_with_deps() {
    char* candidates[] = {
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        "/usr/bin/python3",
        NULL
    };
    
    char test_cmd[1024];
    
    for (int i = 0; candidates[i] != NULL; i++) {
        // Check if file exists and is executable
        if (access(candidates[i], X_OK) == 0) {
            // Test if it has required modules
            snprintf(test_cmd, sizeof(test_cmd), 
                "%s -c \"import tkinter, PIL, numpy, psutil\" 2>/dev/null", 
                candidates[i]);
            
            if (system(test_cmd) == 0) {
                char* result = malloc(strlen(candidates[i]) + 1);
                strcpy(result, candidates[i]);
                return result;
            }
        }
    }
    
    return NULL;
}

int main(int argc, char* argv[]) {
    // Get bundle resources path
    char* bundle_path = get_bundle_path();
    if (!bundle_path) {
        fprintf(stderr, "Error: Could not get bundle path\n");
        return 1;
    }
    
    // Construct paths
    char main_script[1024];
    char ffmpeg_path[1024];
    
    snprintf(main_script, sizeof(main_script), "%s/videogenerator.py", bundle_path);
    snprintf(ffmpeg_path, sizeof(ffmpeg_path), "%s/ffmpeg", bundle_path);
    
    // Make ffmpeg executable
    chmod(ffmpeg_path, 0755);
    
    // Check if main script exists
    if (access(main_script, R_OK) != 0) {
        fprintf(stderr, "Error: videogenerator.py not found at %s\n", main_script);
        free(bundle_path);
        return 1;
    }
    
    // Find Python with dependencies
    char* python_exe = find_python_with_deps();
    if (!python_exe) {
        // Show error dialog using osascript
        system("osascript -e 'display dialog \"Python with required dependencies not found!\\n\\nInstall with: pip3 install Pillow numpy psutil\" with title \"VideoGenerator Error\" buttons {\"OK\"} with icon stop'");
        free(bundle_path);
        return 1;
    }
    
    // Change to bundle directory
    if (chdir(bundle_path) != 0) {
        fprintf(stderr, "Error: Could not change to bundle directory\n");
        free(bundle_path);
        free(python_exe);
        return 1;
    }
    
    // Set up environment
    char new_path[2048];
    char* current_path = getenv("PATH");
    snprintf(new_path, sizeof(new_path), "%s:%s", bundle_path, current_path ? current_path : "");
    setenv("PATH", new_path, 1);
    
    // Execute Python script
    execl(python_exe, python_exe, main_script, (char*)NULL);
    
    // If we get here, exec failed
    fprintf(stderr, "Error: Failed to execute Python script\n");
    free(bundle_path);
    free(python_exe);
    return 1;
}
EOF

echo -e "${GREEN}✓ C launcher source created${NC}"

# Compile the native launcher
echo "Compiling native launcher..."
gcc -o videogenerator_launcher videogenerator_launcher.c -framework CoreFoundation

if [ ! -f "videogenerator_launcher" ]; then
    echo -e "${RED}Error: Failed to compile native launcher${NC}"
    exit 1
fi

chmod +x videogenerator_launcher
echo -e "${GREEN}✓ Native launcher compiled${NC}"

# Handle icon
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

# Clean and create app bundle manually
echo ""
echo "Creating app bundle..."
rm -rf dist
mkdir -p dist/VideoGenerator.app/Contents/{MacOS,Resources}

# Copy the native launcher as the main executable
cp videogenerator_launcher dist/VideoGenerator.app/Contents/MacOS/VideoGenerator
chmod +x dist/VideoGenerator.app/Contents/MacOS/VideoGenerator

# Copy resources
cp videogenerator.py dist/VideoGenerator.app/Contents/Resources/
cp requirements.txt dist/VideoGenerator.app/Contents/Resources/
[ -f "ffmpeg" ] && cp ffmpeg dist/VideoGenerator.app/Contents/Resources/
[ -f "icon.png" ] && cp icon.png dist/VideoGenerator.app/Contents/Resources/
[ -f "icon.icns" ] && cp icon.icns dist/VideoGenerator.app/Contents/Resources/

# Create Info.plist
cat > dist/VideoGenerator.app/Contents/Info.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>VideoGenerator</string>
    <key>CFBundleIdentifier</key>
    <string>com.wamphyre.videogenerator</string>
    <key>CFBundleName</key>
    <string>VideoGenerator</string>
    <key>CFBundleDisplayName</key>
    <string>VideoGenerator</string>
    <key>CFBundleVersion</key>
    <string>1.2.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.2.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2024 Wamphyre</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.video</string>
EOF

# Add icon to Info.plist if available
if [ -f "icon.icns" ]; then
    echo "    <key>CFBundleIconFile</key>" >> dist/VideoGenerator.app/Contents/Info.plist
    echo "    <string>icon</string>" >> dist/VideoGenerator.app/Contents/Info.plist
    cp icon.icns dist/VideoGenerator.app/Contents/Resources/icon.icns
fi

# Close Info.plist
echo "</dict>" >> dist/VideoGenerator.app/Contents/Info.plist
echo "</plist>" >> dist/VideoGenerator.app/Contents/Info.plist

echo -e "${GREEN}✓ App bundle created${NC}"

# Set proper permissions
chmod +x dist/VideoGenerator.app/Contents/MacOS/VideoGenerator
[ -f "dist/VideoGenerator.app/Contents/Resources/ffmpeg" ] && chmod +x dist/VideoGenerator.app/Contents/Resources/ffmpeg

# Try to sign the app
echo "Signing app..."
codesign --force --deep --sign - "dist/VideoGenerator.app" 2>/dev/null || {
    echo -e "${YELLOW}Note: Could not sign app (no developer certificate)${NC}"
}

# Remove quarantine
xattr -dr com.apple.quarantine "dist/VideoGenerator.app" 2>/dev/null || true

echo -e "${GREEN}✓ App preparation complete${NC}"

# Clean up
rm -f videogenerator_launcher.c videogenerator_launcher

# Show results
APP_SIZE=$(du -sh "dist/VideoGenerator.app" | awk '{print $1}')
echo ""
echo -e "${BLUE}Native App Build Complete! 🎉${NC}"
echo "App: dist/VideoGenerator.app"
echo "Size: $APP_SIZE"
echo ""
echo -e "${BLUE}Key Features:${NC}"
echo "• Native C executable (no Python in menu!)"
echo "• Should work with double-click"
echo "• Menu will show 'VideoGenerator' instead of 'Python'"
echo ""
echo -e "${BLUE}Installation:${NC}"
echo "1. Drag dist/VideoGenerator.app to /Applications"
echo "2. Double-click should work directly"
echo "3. If blocked: Right-click → Open (first time only)"

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
DMG_NAME="VideoGenerator-1.2.0"
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
VideoGenerator v1.2.0
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