#!/usr/bin/env python3
"""
Dual Camera Stream Merger

A Python script that merges two live camera streams (each set to 720p resolution) 
in real-time into a single 1280x720 video output.

Features:
1. Capture video from two cameras at 720p resolution
2. Downscale each camera's frame to 640x720
3. Merge both frames horizontally to form a single 1280x720 frame
4. Display the merged stream in real-time
5. Optional video recording to file

Requirements:
- OpenCV (cv2)
- NumPy
- Two connected cameras

Usage:
    python dual_camera_merger.py [options]

Options:
    --camera1 INDEX     Camera index for left camera (default: 0)
    --camera2 INDEX     Camera index for right camera (default: 1)
    --record PATH       Save merged video to file (optional)
    --fps FPS           Target FPS for recording (default: 30)
    --no-display       Don't show real-time display window
    --list-cameras     List available cameras and exit
    --help             Show this help message

Controls (when display is enabled):
    'q' or ESC         Quit the application
    'r'                Start/stop recording (if --record specified)
    's'                Save current frame as image
    SPACE              Pause/resume display

Author: Auto-generated for DropTester repository
"""

import argparse
import cv2
import numpy as np
import platform
import sys
import time
import os
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any


class DualCameraMerger:
    """
    Handles merging of two live camera streams into a single output.
    """
    
    def __init__(self, camera1_idx: int = 0, camera2_idx: int = 1, demo_mode: bool = False):
        """
        Initialize the dual camera merger.
        
        Args:
            camera1_idx: Index of the first camera (left side)
            camera2_idx: Index of the second camera (right side)
            demo_mode: If True, generate synthetic frames instead of using real cameras
        """
        self.camera1_idx = camera1_idx
        self.camera2_idx = camera2_idx
        self.cap1: Optional[cv2.VideoCapture] = None
        self.cap2: Optional[cv2.VideoCapture] = None
        self.demo_mode = demo_mode
        
        # Video settings
        self.source_width = 1280
        self.source_height = 720
        self.target_width = 640
        self.target_height = 720
        self.merged_width = 1280
        self.merged_height = 720
        self.target_fps = 30
        
        # Recording settings
        self.is_recording = False
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.record_path: Optional[str] = None
        
        # Display settings
        self.show_display = True
        self.is_paused = False
        
        # Statistics
        self.frame_count = 0
        self.start_time = 0
        self.fps_counter = 0
        self.last_fps_time = 0
        
        print(f"Dual Camera Merger initialized:")
        print(f"  Camera 1 index: {camera1_idx}")
        print(f"  Camera 2 index: {camera2_idx}")
        print(f"  Demo mode: {demo_mode}")
        print(f"  Source resolution: {self.source_width}x{self.source_height}")
        print(f"  Target merged resolution: {self.merged_width}x{self.merged_height}")

    def generate_demo_frame(self, camera_idx: int, frame_count: int) -> np.ndarray:
        """
        Generate a synthetic demo frame for testing without real cameras.
        
        Args:
            camera_idx: Camera index (for visual differentiation)
            frame_count: Current frame number
            
        Returns:
            Synthetic frame of source resolution
        """
        # Create base frame
        frame = np.zeros((self.source_height, self.source_width, 3), dtype=np.uint8)
        
        # Different patterns for each camera
        if camera_idx == self.camera1_idx:
            # Camera 1: Blue gradient with moving circle
            frame[:, :, 2] = 100  # Blue background
            center_x = int(self.source_width // 2 + 200 * np.sin(frame_count * 0.05))
            center_y = int(self.source_height // 2 + 100 * np.cos(frame_count * 0.03))
            cv2.circle(frame, (center_x, center_y), 50, (255, 255, 0), -1)  # Yellow circle
        else:
            # Camera 2: Green gradient with moving rectangle
            frame[:, :, 1] = 100  # Green background
            rect_x = int(200 + 150 * np.sin(frame_count * 0.04))
            rect_y = int(150 + 100 * np.cos(frame_count * 0.06))
            cv2.rectangle(frame, (rect_x, rect_y), (rect_x + 100, rect_y + 80), (255, 0, 255), -1)  # Magenta rectangle
        
        # Add frame counter and camera label
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, f"DEMO CAM {camera_idx}", (10, 30), font, 1, (255, 255, 255), 2)
        cv2.putText(frame, f"Frame: {frame_count}", (10, 70), font, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"{self.source_width}x{self.source_height}", (10, self.source_height - 20), font, 0.6, (255, 255, 255), 2)
        
        return frame

    def get_preferred_backends(self) -> List[int]:
        """
        Get preferred camera backends based on the operating system.
        
        Returns:
            List of OpenCV backend constants in order of preference
        """
        system = platform.system().lower()
        
        if system.startswith("windows"):
            return [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        elif system == "darwin":  # macOS
            return [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
        else:  # Linux and others
            return [cv2.CAP_V4L2, cv2.CAP_ANY]

    def open_camera_with_backends(self, camera_idx: int) -> Optional[cv2.VideoCapture]:
        """
        Open a camera using preferred backends.
        
        Args:
            camera_idx: Camera index to open
            
        Returns:
            VideoCapture object if successful, None otherwise
        """
        backends = self.get_preferred_backends()
        
        for backend in backends:
            try:
                cap = cv2.VideoCapture(camera_idx, backend)
                if cap is not None and cap.isOpened():
                    # Test if we can read a frame
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        print(f"  Opened camera {camera_idx} with backend {backend}")
                        return cap
                    cap.release()
            except Exception as e:
                print(f"  Failed to open camera {camera_idx} with backend {backend}: {e}")
                
        return None

    def configure_camera(self, cap: cv2.VideoCapture, camera_name: str) -> bool:
        """
        Configure camera settings for optimal performance.
        
        Args:
            cap: VideoCapture object to configure
            camera_name: Human-readable camera name for logging
            
        Returns:
            True if configuration successful, False otherwise
        """
        try:
            # Set MJPEG format for better performance at high resolution
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            cap.set(cv2.CAP_PROP_FOURCC, fourcc)
            
            # Set resolution
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.source_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.source_height)
            
            # Set FPS
            cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            
            # Reduce buffer size for lower latency
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except:
                pass  # Not all backends support this
            
            # Verify settings
            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = cap.get(cv2.CAP_PROP_FPS)
            
            print(f"  {camera_name} configured:")
            print(f"    Requested: {self.source_width}x{self.source_height} @ {self.target_fps} FPS")
            print(f"    Actual: {actual_width}x{actual_height} @ {actual_fps:.1f} FPS")
            
            return True
            
        except Exception as e:
            print(f"  Failed to configure {camera_name}: {e}")
            return False

    def initialize_cameras(self) -> bool:
        """
        Initialize both cameras with proper configuration.
        
        Returns:
            True if both cameras initialized successfully, False otherwise
        """
        print("Initializing cameras...")
        
        if self.demo_mode:
            print("✓ Demo mode enabled - using synthetic frames")
            return True
        
        # Open camera 1
        self.cap1 = self.open_camera_with_backends(self.camera1_idx)
        if self.cap1 is None:
            print(f"ERROR: Could not open camera {self.camera1_idx}")
            print("TIP: Try --demo mode for testing without real cameras")
            return False
            
        if not self.configure_camera(self.cap1, f"Camera {self.camera1_idx}"):
            print(f"ERROR: Could not configure camera {self.camera1_idx}")
            self.cap1.release()
            return False
        
        # Open camera 2
        self.cap2 = self.open_camera_with_backends(self.camera2_idx)
        if self.cap2 is None:
            print(f"ERROR: Could not open camera {self.camera2_idx}")
            self.cap1.release()
            print("TIP: Try --demo mode for testing without real cameras")
            return False
            
        if not self.configure_camera(self.cap2, f"Camera {self.camera2_idx}"):
            print(f"ERROR: Could not configure camera {self.camera2_idx}")
            self.cap1.release()
            self.cap2.release()
            return False
        
        print("✓ Both cameras initialized successfully")
        return True

    def capture_frames(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Capture frames from both cameras simultaneously.
        
        Returns:
            Tuple of (frame1, frame2) or (None, None) if capture failed
        """
        if self.demo_mode:
            # Generate synthetic frames
            frame1 = self.generate_demo_frame(self.camera1_idx, self.frame_count)
            frame2 = self.generate_demo_frame(self.camera2_idx, self.frame_count)
            return frame1, frame2
            
        if not self.cap1 or not self.cap2:
            return None, None
            
        try:
            # Use grab() and retrieve() for better synchronization
            success1 = self.cap1.grab()
            success2 = self.cap2.grab()
            
            if success1 and success2:
                ret1, frame1 = self.cap1.retrieve()
                ret2, frame2 = self.cap2.retrieve()
                
                if ret1 and ret2 and frame1 is not None and frame2 is not None:
                    return frame1, frame2
                    
        except Exception as e:
            print(f"Frame capture error: {e}")
            
        return None, None

    def process_frame(self, frame1: np.ndarray, frame2: np.ndarray) -> np.ndarray:
        """
        Process and merge two frames into a single output frame.
        
        Args:
            frame1: First camera frame
            frame2: Second camera frame
            
        Returns:
            Merged frame of size 1280x720
        """
        # Resize frames to target dimensions (640x720 each)
        if frame1.shape[:2] != (self.target_height, self.target_width):
            frame1 = cv2.resize(frame1, (self.target_width, self.target_height))
            
        if frame2.shape[:2] != (self.target_height, self.target_width):
            frame2 = cv2.resize(frame2, (self.target_width, self.target_height))
        
        # Merge frames horizontally
        merged_frame = np.hstack((frame1, frame2))
        
        # Add overlay information
        merged_frame = self.add_overlay_info(merged_frame)
        
        return merged_frame

    def add_overlay_info(self, frame: np.ndarray) -> np.ndarray:
        """
        Add overlay information to the frame.
        
        Args:
            frame: Input frame
            
        Returns:
            Frame with overlay information
        """
        # Calculate FPS
        current_time = time.time()
        if self.last_fps_time == 0:
            self.last_fps_time = current_time
            
        self.fps_counter += 1
        if current_time - self.last_fps_time >= 1.0:
            fps = self.fps_counter / (current_time - self.last_fps_time)
            self.current_fps = fps
            self.fps_counter = 0
            self.last_fps_time = current_time
        
        # Add text overlays
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        color = (0, 255, 0)  # Green
        thickness = 2
        
        # FPS counter
        if hasattr(self, 'current_fps'):
            fps_text = f"FPS: {self.current_fps:.1f}"
            cv2.putText(frame, fps_text, (10, 30), font, font_scale, color, thickness)
        
        # Frame counter
        frame_text = f"Frame: {self.frame_count}"
        cv2.putText(frame, frame_text, (10, 60), font, font_scale, color, thickness)
        
        # Recording indicator
        if self.is_recording:
            rec_text = "● REC"
            cv2.putText(frame, rec_text, (frame.shape[1] - 100, 30), font, font_scale, (0, 0, 255), thickness)
        
        # Camera labels
        cv2.putText(frame, f"Camera {self.camera1_idx}", (10, frame.shape[0] - 20), 
                   font, font_scale * 0.8, (255, 255, 255), thickness)
        cv2.putText(frame, f"Camera {self.camera2_idx}", (frame.shape[1]//2 + 10, frame.shape[0] - 20), 
                   font, font_scale * 0.8, (255, 255, 255), thickness)
        
        # Pause indicator
        if self.is_paused:
            pause_text = "PAUSED"
            text_size = cv2.getTextSize(pause_text, font, font_scale * 2, thickness * 2)[0]
            text_x = (frame.shape[1] - text_size[0]) // 2
            text_y = (frame.shape[0] + text_size[1]) // 2
            cv2.putText(frame, pause_text, (text_x, text_y), font, font_scale * 2, (0, 255, 255), thickness * 2)
        
        return frame

    def start_recording(self, output_path: str) -> bool:
        """
        Start recording merged video to file.
        
        Args:
            output_path: Path to save the video file
            
        Returns:
            True if recording started successfully, False otherwise
        """
        if self.is_recording:
            print("Recording is already active")
            return False
            
        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:  # Only create directory if path has a directory component
                os.makedirs(output_dir, exist_ok=True)
            
            # Try different codecs in order of preference
            codecs = ['mp4v', 'XVID', 'MJPG']
            
            for codec in codecs:
                try:
                    fourcc = cv2.VideoWriter_fourcc(*codec)
                    self.video_writer = cv2.VideoWriter(
                        output_path, fourcc, self.target_fps, 
                        (self.merged_width, self.merged_height)
                    )
                    
                    if self.video_writer and self.video_writer.isOpened():
                        self.is_recording = True
                        self.record_path = output_path
                        print(f"✓ Recording started: {output_path} (codec: {codec})")
                        return True
                    
                    if self.video_writer:
                        self.video_writer.release()
                        
                except Exception as e:
                    print(f"Failed to start recording with codec {codec}: {e}")
                    
            print("ERROR: Could not initialize video writer with any codec")
            return False
            
        except Exception as e:
            print(f"ERROR: Could not start recording: {e}")
            return False

    def stop_recording(self):
        """Stop video recording."""
        if self.is_recording and self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            self.is_recording = False
            print(f"✓ Recording stopped: {self.record_path}")
            self.record_path = None

    def save_frame(self, frame: np.ndarray):
        """
        Save current frame as an image.
        
        Args:
            frame: Frame to save
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"frame_{timestamp}.png"
        
        try:
            cv2.imwrite(filename, frame)
            print(f"✓ Frame saved: {filename}")
        except Exception as e:
            print(f"ERROR: Could not save frame: {e}")

    def handle_key_input(self, key: int, frame: np.ndarray) -> bool:
        """
        Handle keyboard input for controls.
        
        Args:
            key: Key code from cv2.waitKey()
            frame: Current frame (for saving)
            
        Returns:
            True to continue, False to quit
        """
        if key == ord('q') or key == 27:  # 'q' or ESC
            return False
        elif key == ord('r'):  # Toggle recording
            if self.record_path:
                if self.is_recording:
                    self.stop_recording()
                else:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    new_path = f"{self.record_path.rsplit('.', 1)[0]}_{timestamp}.{self.record_path.rsplit('.', 1)[1]}"
                    self.start_recording(new_path)
        elif key == ord('s'):  # Save frame
            self.save_frame(frame)
        elif key == ord(' '):  # Pause/resume
            self.is_paused = not self.is_paused
            print("PAUSED" if self.is_paused else "RESUMED")
            
        return True

    def run(self, record_path: Optional[str] = None, show_display: bool = True) -> bool:
        """
        Main loop for capturing, processing, and displaying merged camera streams.
        
        Args:
            record_path: Optional path to save video recording
            show_display: Whether to show the real-time display window
            
        Returns:
            True if successful, False if error occurred
        """
        if not self.initialize_cameras():
            return False
            
        self.show_display = show_display
        self.record_path = record_path
        
        if record_path:
            if not self.start_recording(record_path):
                print("Warning: Could not start recording, continuing with display only")
        
        if show_display:
            cv2.namedWindow('Dual Camera Merger', cv2.WINDOW_RESIZABLE)
            print("\nControls:")
            print("  'q' or ESC - Quit")
            print("  'r' - Toggle recording (if record path specified)")
            print("  's' - Save current frame")
            print("  SPACE - Pause/resume")
            print()
        
        self.start_time = time.time()
        self.frame_count = 0
        
        try:
            while True:
                if not self.is_paused:
                    # Capture frames
                    frame1, frame2 = self.capture_frames()
                    
                    if frame1 is None or frame2 is None:
                        print("Warning: Failed to capture frames from both cameras")
                        time.sleep(0.1)
                        continue
                    
                    # Process and merge frames
                    merged_frame = self.process_frame(frame1, frame2)
                    self.frame_count += 1
                    
                    # Record if enabled
                    if self.is_recording and self.video_writer:
                        self.video_writer.write(merged_frame)
                    
                    # Display if enabled
                    if show_display:
                        cv2.imshow('Dual Camera Merger', merged_frame)
                
                # Handle keyboard input
                if show_display:
                    key = cv2.waitKey(1) & 0xFF
                    if key != 255:  # Key was pressed
                        if not self.handle_key_input(key, merged_frame if not self.is_paused else None):
                            break
                else:
                    # If no display, add a small delay to prevent 100% CPU usage
                    time.sleep(1.0 / self.target_fps)
                    
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        except Exception as e:
            print(f"ERROR: Runtime error: {e}")
            return False
        finally:
            self.cleanup()
            
        # Print statistics
        total_time = time.time() - self.start_time
        avg_fps = self.frame_count / total_time if total_time > 0 else 0
        print(f"\nSession statistics:")
        print(f"  Total frames: {self.frame_count}")
        print(f"  Total time: {total_time:.1f}s")
        print(f"  Average FPS: {avg_fps:.1f}")
        
        return True

    def cleanup(self):
        """Clean up resources."""
        if self.is_recording:
            self.stop_recording()
            
        if self.cap1 and not self.demo_mode:
            self.cap1.release()
            self.cap1 = None
            
        if self.cap2 and not self.demo_mode:
            self.cap2.release()
            self.cap2 = None
            
        if self.show_display:
            cv2.destroyAllWindows()
            
        print("✓ Cleanup completed")


def list_available_cameras(max_check: int = 10) -> List[int]:
    """
    List available cameras on the system.
    
    Args:
        max_check: Maximum number of camera indices to check
        
    Returns:
        List of available camera indices
    """
    print("Scanning for available cameras...")
    
    available = []
    system = platform.system().lower()
    
    # Get preferred backends
    if system.startswith("windows"):
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    elif system == "darwin":
        backends = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
    else:
        backends = [cv2.CAP_V4L2, cv2.CAP_ANY]
    
    for i in range(max_check):
        found = False
        for backend in backends:
            try:
                cap = cv2.VideoCapture(i, backend)
                if cap is not None and cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        # Get camera properties
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        
                        available.append(i)
                        print(f"  Camera {i}: {width}x{height} @ {fps:.1f}fps (backend: {backend})")
                        found = True
                        
                cap.release()
                if found:
                    break
                    
            except Exception as e:
                if cap:
                    cap.release()
                continue
    
    if not available:
        print("  No cameras found")
    else:
        print(f"\nFound {len(available)} camera(s): {available}")
        
    return available


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Dual Camera Stream Merger - Merge two live camera streams in real-time",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dual_camera_merger.py
    # Use cameras 0 and 1 with live display only

  python dual_camera_merger.py --demo
    # Run in demo mode with synthetic frames (no cameras needed)

  python dual_camera_merger.py --camera1 0 --camera2 2 --record output.mp4
    # Use cameras 0 and 2, save to output.mp4

  python dual_camera_merger.py --list-cameras
    # List all available cameras

  python dual_camera_merger.py --demo --record demo.mp4 --no-display
    # Demo mode recording without display window

Controls (when display is enabled):
  'q' or ESC     Quit the application
  'r'            Start/stop recording (if --record specified)
  's'            Save current frame as image
  SPACE          Pause/resume display
        """
    )
    
    parser.add_argument('--camera1', type=int, default=0, 
                       help='Camera index for left camera (default: 0)')
    parser.add_argument('--camera2', type=int, default=1,
                       help='Camera index for right camera (default: 1)')
    parser.add_argument('--record', type=str,
                       help='Save merged video to file (optional)')
    parser.add_argument('--fps', type=int, default=30,
                       help='Target FPS for recording (default: 30)')
    parser.add_argument('--no-display', action='store_true',
                       help="Don't show real-time display window")
    parser.add_argument('--list-cameras', action='store_true',
                       help='List available cameras and exit')
    parser.add_argument('--demo', action='store_true',
                       help='Run in demo mode with synthetic frames (for testing without cameras)')
    
    args = parser.parse_args()
    
    # Check if OpenCV is available
    try:
        import cv2
        import numpy as np
        print(f"OpenCV version: {cv2.__version__}")
        print(f"NumPy version: {np.__version__}")
    except ImportError as e:
        print(f"ERROR: Required dependencies not available: {e}")
        print("Please install OpenCV and NumPy:")
        print("  pip install opencv-python numpy")
        return 1
    
    # List cameras if requested
    if args.list_cameras:
        list_available_cameras()
        return 0
    
    # Validate arguments
    if args.camera1 == args.camera2:
        print("ERROR: Camera indices must be different")
        return 1
        
    if args.fps <= 0 or args.fps > 60:
        print("ERROR: FPS must be between 1 and 60")
        return 1
    
    # Create and run merger
    merger = DualCameraMerger(args.camera1, args.camera2, demo_mode=args.demo)
    merger.target_fps = args.fps
    
    show_display = not args.no_display
    success = merger.run(args.record, show_display)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())