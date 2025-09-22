# Dual Camera Stream Merger

A Python script that merges two live camera streams (each set to 720p resolution) in real-time into a single 1280x720 video output.

## Features

1. **Dual Camera Capture**: Simultaneously captures video from two cameras at 720p resolution
2. **Real-time Processing**: Downscales each camera's frame to 640x720 and merges horizontally
3. **Live Display**: Shows the merged 1280x720 stream in real-time
4. **Video Recording**: Optional recording of the merged stream to various video formats
5. **Cross-platform**: Works on Windows, macOS, and Linux with automatic backend selection
6. **Interactive Controls**: Keyboard controls for recording, pausing, and saving frames
7. **Performance Monitoring**: Real-time FPS display and session statistics

## Requirements

- Python 3.6+
- OpenCV (cv2)
- NumPy
- Two connected cameras (webcams, USB cameras, etc.)

## Installation

1. Install the required dependencies:
```bash
pip install opencv-python numpy
```

2. Ensure you have two cameras connected to your system

## Usage

### Basic Usage

```bash
# Use default cameras (0 and 1) with live display
python dual_camera_merger.py

# Use specific camera indices
python dual_camera_merger.py --camera1 0 --camera2 2

# Record to a video file
python dual_camera_merger.py --record output.mp4

# Record without displaying the live view
python dual_camera_merger.py --record output.avi --no-display
```

### Command Line Options

- `--camera1 INDEX`: Camera index for left camera (default: 0)
- `--camera2 INDEX`: Camera index for right camera (default: 1)
- `--record PATH`: Save merged video to file (optional)
- `--fps FPS`: Target FPS for recording (default: 30)
- `--no-display`: Don't show real-time display window
- `--list-cameras`: List available cameras and exit
- `--help`: Show detailed help message

### Interactive Controls

When the display window is active, you can use these keyboard controls:

- **'q' or ESC**: Quit the application
- **'r'**: Start/stop recording (if `--record` specified)
- **'s'**: Save current frame as PNG image
- **SPACE**: Pause/resume display

### Examples

```bash
# List all available cameras
python dual_camera_merger.py --list-cameras

# Use cameras 0 and 2, record at 60 FPS
python dual_camera_merger.py --camera1 0 --camera2 2 --record recording.mp4 --fps 60

# Headless recording (no display window)
python dual_camera_merger.py --record background_recording.avi --no-display

# Save with different video formats
python dual_camera_merger.py --record output.mov    # QuickTime
python dual_camera_merger.py --record output.avi    # AVI
python dual_camera_merger.py --record output.mp4    # MP4
```

## Technical Details

### Resolution Handling

- **Source Resolution**: Each camera is configured for 1280x720 (720p)
- **Processing Resolution**: Each frame is downscaled to 640x720
- **Output Resolution**: Final merged frame is 1280x720 (two 640x720 frames side by side)

### Camera Backend Selection

The script automatically selects the best camera backend for your operating system:

- **Windows**: DirectShow (DSHOW) → Media Foundation (MSMF) → Any
- **macOS**: AVFoundation → Any
- **Linux**: Video4Linux2 (V4L2) → Any

### Video Codec Selection

For recording, the script tries codecs in this order of preference:
1. MP4V (H.264 compatible)
2. XVID (widely compatible)
3. MJPG (high quality, larger files)

### Performance Optimization

- Uses MJPEG format for camera capture at high resolution
- Implements `grab()` and `retrieve()` for better frame synchronization
- Minimizes camera buffer size to reduce latency
- Efficient numpy operations for frame processing

## Troubleshooting

### No Cameras Found
```bash
# Check available cameras
python dual_camera_merger.py --list-cameras

# Check if cameras are being used by other applications
lsof /dev/video*  # Linux
```

### Recording Issues
- Ensure output directory exists and is writable
- Try different video codecs by changing file extension (.mp4, .avi, .mov)
- Check available disk space

### Performance Issues
- Lower the target FPS: `--fps 15`
- Close other applications using cameras
- Use `--no-display` for better recording performance

### Permission Issues (Linux)
```bash
# Add user to video group
sudo usermod -a -G video $USER
# Log out and log back in
```

## Integration with DropTester

This script is designed to complement the existing DropTester application. It can be used as:

1. **Standalone Tool**: For general dual-camera applications
2. **Testing Setup**: To verify camera functionality before using DropTester
3. **Recording Tool**: For capturing dual-camera footage for analysis
4. **Development Reference**: Code can be adapted for integration into the main DropTester application

## File Structure

```
dual_camera_merger.py          # Main script
README_DualCamera.md          # This documentation
frame_YYYYMMDD_HHMMSS.png     # Saved frames (when 's' is pressed)
output.mp4                    # Recorded videos (when --record is used)
```

## Contributing

When contributing to this script:

1. Maintain compatibility with the existing DropTester codebase
2. Follow the same coding style and error handling patterns
3. Test on multiple operating systems when possible
4. Update this documentation for any new features

## License

This script is part of the DropTester project and follows the same license terms.