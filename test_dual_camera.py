#!/usr/bin/env python3
"""
Test script for the Dual Camera Merger functionality.

This script validates the core functionality of the dual camera merger
without requiring physical cameras.
"""

import numpy as np
import cv2
import os
import sys
import tempfile
from dual_camera_merger import DualCameraMerger


def test_demo_mode():
    """Test that demo mode generates proper synthetic frames."""
    print("Testing demo mode frame generation...")
    
    merger = DualCameraMerger(0, 1, demo_mode=True)
    
    # Generate a few demo frames
    for i in range(5):
        frame1 = merger.generate_demo_frame(0, i)
        frame2 = merger.generate_demo_frame(1, i)
        
        # Verify frame properties
        assert frame1.shape == (720, 1280, 3), f"Frame 1 shape incorrect: {frame1.shape}"
        assert frame2.shape == (720, 1280, 3), f"Frame 2 shape incorrect: {frame2.shape}"
        assert frame1.dtype == np.uint8, f"Frame 1 dtype incorrect: {frame1.dtype}"
        assert frame2.dtype == np.uint8, f"Frame 2 dtype incorrect: {frame2.dtype}"
        
        # Frames should be different (not all zeros)
        assert np.sum(frame1) > 0, "Frame 1 is all zeros"
        assert np.sum(frame2) > 0, "Frame 2 is all zeros"
        
        # Frames from different cameras should be different
        assert not np.array_equal(frame1, frame2), "Frames from different cameras should be different"
    
    print("✓ Demo mode frame generation test passed")


def test_frame_processing():
    """Test frame processing and merging functionality."""
    print("Testing frame processing...")
    
    merger = DualCameraMerger(0, 1, demo_mode=True)
    
    # Create test frames
    frame1 = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    frame2 = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    
    # Process frames
    merged = merger.process_frame(frame1, frame2)
    
    # Verify merged frame properties
    assert merged.shape == (720, 1280, 3), f"Merged frame shape incorrect: {merged.shape}"
    assert merged.dtype == np.uint8, f"Merged frame dtype incorrect: {merged.dtype}"
    
    # Check that both halves exist (approximate check)
    left_half = merged[:, :640]
    right_half = merged[:, 640:]
    
    assert left_half.shape == (720, 640, 3), f"Left half shape incorrect: {left_half.shape}"
    assert right_half.shape == (720, 640, 3), f"Right half shape incorrect: {right_half.shape}"
    
    print("✓ Frame processing test passed")


def test_recording():
    """Test video recording functionality."""
    print("Testing recording functionality...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, "test_recording.mp4")
        
        merger = DualCameraMerger(0, 1, demo_mode=True)
        
        # Test recording start
        success = merger.start_recording(output_path)
        assert success, "Recording should start successfully"
        assert merger.is_recording, "Merger should be in recording state"
        
        # Generate and record a few frames
        for i in range(10):
            frame1 = merger.generate_demo_frame(0, i)
            frame2 = merger.generate_demo_frame(1, i)
            merged = merger.process_frame(frame1, frame2)
            
            if merger.video_writer:
                merger.video_writer.write(merged)
        
        # Stop recording
        merger.stop_recording()
        assert not merger.is_recording, "Merger should not be in recording state after stop"
        
        # Verify file was created
        assert os.path.exists(output_path), f"Recording file should exist: {output_path}"
        assert os.path.getsize(output_path) > 0, "Recording file should not be empty"
    
    print("✓ Recording test passed")


def test_camera_initialization():
    """Test camera initialization in demo mode."""
    print("Testing camera initialization...")
    
    merger = DualCameraMerger(0, 1, demo_mode=True)
    
    # Initialize cameras
    success = merger.initialize_cameras()
    assert success, "Camera initialization should succeed in demo mode"
    
    # Test frame capture
    frame1, frame2 = merger.capture_frames()
    assert frame1 is not None, "Frame 1 should not be None"
    assert frame2 is not None, "Frame 2 should not be None"
    assert frame1.shape == (720, 1280, 3), f"Frame 1 shape incorrect: {frame1.shape}"
    assert frame2.shape == (720, 1280, 3), f"Frame 2 shape incorrect: {frame2.shape}"
    
    # Cleanup
    merger.cleanup()
    
    print("✓ Camera initialization test passed")


def run_all_tests():
    """Run all tests."""
    print("Running Dual Camera Merger tests...\n")
    
    try:
        test_demo_mode()
        test_frame_processing()
        test_camera_initialization()
        test_recording()
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)