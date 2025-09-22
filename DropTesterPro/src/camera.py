import platform
import threading
import time
import queue

# Try to import cv2 and numpy with fallback
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("Warning: OpenCV (cv2) not available. Camera functionality will be disabled.")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("Warning: NumPy not available. Some functionality may be limited.")

from .constants import MAX_RECORD_SECONDS

# ---------- Camera detection & recorder ----------
def detect_cameras(max_check: int = 12):
    if not CV2_AVAILABLE:
        print("Camera detection skipped: OpenCV not available")
        return []

    available = []
    sysname = platform.system().lower()

    # Preferred backend order per OS
    backend_orders = []
    try:
        if sysname.startswith("windows"):
            backend_orders = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        elif sysname == "darwin":
            backend_orders = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
        else:
            backend_orders = [cv2.CAP_V4L2, cv2.CAP_ANY]
    except Exception:
        backend_orders = [cv2.CAP_ANY]

    print(f"[Detect] Backends to probe: {backend_orders}")
    for i in range(max_check):
        opened = False
        for backend in backend_orders:
            cap = None
            try:
                cap = cv2.VideoCapture(i, backend)
            except Exception as e:
                cap = None
            if cap is not None and cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    available.append(i)
                    opened = True
                cap.release()
                if opened:
                    break
        if not opened:
            # continue probing
            pass
    print(f"[Detect] Total cameras detected: {len(available)} -> {available}")
    return available


class CameraWorker(threading.Thread):
    """
    A worker thread that continuously reads frames from a camera and puts them in a queue.
    Handles frame dropping when queue is full to prevent memory bloat and lag.
    """
    
    def __init__(self, camera, target_width, target_height, queue_maxsize=8, name="CameraWorker"):
        """
        Initialize the camera worker.
        
        Args:
            camera: OpenCV VideoCapture object
            target_width: Target frame width for resizing
            target_height: Target frame height for resizing
            queue_maxsize: Maximum number of frames to keep in queue
            name: Thread name for debugging
        """
        super().__init__(daemon=True, name=name)
        self.camera = camera
        self.target_width = target_width
        self.target_height = target_height
        self.frame_queue = queue.Queue(maxsize=queue_maxsize)
        self._stop_event = threading.Event()
        self._error_event = threading.Event()
        self._last_error = None
        
    def run(self):
        """
        Main worker loop: continuously capture frames and put them in queue.
        Drops oldest frame if queue is full to prevent blocking.
        """
        while not self._stop_event.is_set():
            try:
                # Check if camera is still valid
                if not self.camera or not self.camera.isOpened():
                    self._last_error = "Camera disconnected or not opened"
                    self._error_event.set()
                    break
                
                # Capture frame using grab/retrieve for better performance
                try:
                    self.camera.grab()
                    ret, frame = self.camera.retrieve()
                except Exception:
                    # Fallback to read() if grab/retrieve not supported
                    ret, frame = self.camera.read()
                
                if not ret or frame is None:
                    # Skip this frame but don't exit - camera might recover
                    time.sleep(0.001)  # Small delay to prevent busy waiting
                    continue
                
                # Resize frame if necessary
                if frame.shape[1] != self.target_width or frame.shape[0] != self.target_height:
                    frame = cv2.resize(frame, (self.target_width, self.target_height))
                
                # Try to put frame in queue, drop oldest if full
                try:
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    # Queue is full, drop the oldest frame to make space
                    try:
                        self.frame_queue.get_nowait()  # Remove oldest
                        self.frame_queue.put_nowait(frame)  # Add new
                    except queue.Empty:
                        # Race condition, queue emptied between checks
                        try:
                            self.frame_queue.put_nowait(frame)
                        except queue.Full:
                            pass  # Still full, drop this frame
                            
            except Exception as e:
                self._last_error = f"Frame capture error: {e}"
                self._error_event.set()
                break
        
        # Clear queue on exit
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break
    
    def get_frame(self):
        """
        Get the latest frame from queue without blocking.
        Returns None if no frame available.
        """
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None
    
    def has_frames(self):
        """Check if frames are available in queue."""
        return not self.frame_queue.empty()
    
    def stop(self):
        """Signal the worker to stop."""
        self._stop_event.set()
    
    def has_error(self):
        """Check if worker encountered an error."""
        return self._error_event.is_set()
    
    def get_last_error(self):
        """Get the last error message."""
        return self._last_error

class DualCameraRecorder:
    def __init__(self):
        self.cap1, self.cap2 = None, None
        self.recording = False
        self.frame_preview = None
        self._t = None
        self._lock = threading.Lock()
        self._out_path = None
        self._stop_requested = False
        self.demo_mode = False
        self.width = 0
        self.height = 0
        
        # Camera worker threads for threaded frame capture
        self.camera_worker1 = None
        self.camera_worker2 = None
        
        # Last captured frames for handling queue empty situations
        self._last_frame1 = None
        self._last_frame2 = None

    def initialize(self, width=640, height=480):
        self.width = width
        self.height = height

        if not CV2_AVAILABLE:
            print("[Init] OpenCV not available. Demo mode enabled.")
            self.demo_mode = True
            return True

        cams = detect_cameras(12)
        if len(cams) < 2:
            print("[Init] Less than 2 cameras found. Demo mode enabled.")
            self.demo_mode = True
            return True

        sysname = platform.system().lower()
        if sysname.startswith("windows"):
            pref = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        elif sysname == "darwin":
            pref = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
        else:
            pref = [cv2.CAP_V4L2, cv2.CAP_ANY]

        def open_with_pref(idx):
            for backend in pref:
                try:
                    cap = cv2.VideoCapture(idx, backend)
                    if cap.isOpened():
                        return cap
                    cap.release()
                except Exception:
                    pass
            return None

        try:
            self.cap1 = open_with_pref(cams[0])
            self.cap2 = open_with_pref(cams[1])
            if not self.cap1 or not self.cap2 or not self.cap1.isOpened() or not self.cap2.isOpened():
                self.release()
                self.demo_mode = True
                print("[Init] Falling back to demo mode (could not open two cameras).")
                return True

            for c in (self.cap1, self.cap2):
                try:
                    # Request MJPG at higher res for better throughput
                    if self.height >= 720:
                        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
                        c.set(cv2.CAP_PROP_FOURCC, fourcc)
                    # Reduce camera internal buffering to lower latency
                    try:
                        c.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    except Exception:
                        pass
                    c.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    c.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    c.set(cv2.CAP_PROP_FPS, 30)
                except Exception:
                    pass
                    
            # Create camera worker threads for independent frame capture
            self.camera_worker1 = CameraWorker(
                self.cap1, self.width, self.height, 
                queue_maxsize=8, name="CameraWorker1"
            )
            self.camera_worker2 = CameraWorker(
                self.cap2, self.width, self.height, 
                queue_maxsize=8, name="CameraWorker2"
            )
            
            return True
        except Exception as e:
            print(f"[Init] Camera initialization error: {e}")
            self.release()
            self.demo_mode = True
            return True

    def start(self, out_path: str):
        self._out_path = out_path
        self.recording = True
        self._stop_requested = False
        self.frame_preview = None
        
        # Start camera worker threads if not in demo mode
        if not self.demo_mode and self.camera_worker1 and self.camera_worker2:
            self.camera_worker1.start()
            self.camera_worker2.start()
        
        # Start the main recording thread
        self._t = threading.Thread(target=self._loop, daemon=True)
        self._t.start()
        return self._t

    def get_thread(self):
        return self._t

    def get_output_path(self):
        return self._out_path

    def _loop(self):
        """
        Main recording loop that processes frames from camera worker queues.
        This method now acts as a consumer, combining frames from both cameras,
        writing to disk, and updating preview without blocking on camera capture.
        """
        frames = []
        start_time = time.time()

        combo_width = self.width * 2
        combo_height = self.height
        target_fps = 30  # Use a fixed, standard FPS for consistent playback speed

        if self.demo_mode:
            # Demo mode remains unchanged
            while self.recording and not self._stop_requested and (time.time() - start_time) <= MAX_RECORD_SECONDS:
                if NUMPY_AVAILABLE:
                    frame = np.zeros((combo_height, combo_width, 3), dtype=np.uint8)
                    elapsed = time.time() - start_time
                    pattern_val = int((elapsed * 50) % 255)
                    frame[:, :, 0] = pattern_val
                    frames.append(frame)
                    with self._lock:
                        self.frame_preview = frame
                    time.sleep(1 / target_fps)  # Sleep according to target FPS in demo mode
                else:
                    time.sleep(0.1)
                    continue
        else:
            # Real camera mode using worker threads
            # Determine writer FPS from camera if available
            writer_fps = target_fps
            try:
                fps1 = self.cap1.get(cv2.CAP_PROP_FPS) if self.cap1 else 0
                fps2 = self.cap2.get(cv2.CAP_PROP_FPS) if self.cap2 else 0
                fps_candidates = [f for f in [fps1, fps2] if f and f > 1]
                if fps_candidates:
                    writer_fps = max(5.0, min(60.0, float(min(fps_candidates))))
            except Exception:
                pass

            # Prefer MJPG for high res
            prefer_mjpg = combo_width * combo_height >= (1920 * 1080) or self.height >= 720
            try_codecs = ["MJPG", "XVID"] if prefer_mjpg else ["XVID", "MJPG"]
            out = None
            last_err = None
            for c in try_codecs:
                try:
                    fourcc = cv2.VideoWriter_fourcc(*c)
                    out_try = cv2.VideoWriter(self._out_path, fourcc, writer_fps, (combo_width, combo_height))
                    if out_try is not None and out_try.isOpened():
                        out = out_try
                        break
                except Exception as e:
                    last_err = e
                    out = None

            # If writer cannot be opened, we'll buffer frames as a fallback
            buffering_fallback = out is None
            if out is None:
                print(f"[Loop] Warning: Could not open VideoWriter (last error: {last_err}). Falling back to buffering.")

            preview_throttle = 3 if self.height >= 720 else 1
            frame_counter = 0
            # Keep playback in real time by writing duplicates or dropping frames based on elapsed time
            last_t = time.time()
            write_accum = 0.0
            total_written = 0

            # Main processing loop - now consumes from camera worker queues
            while self.recording and not self._stop_requested and (time.time() - start_time) <= MAX_RECORD_SECONDS:
                
                # Check for camera worker errors
                if (self.camera_worker1 and self.camera_worker1.has_error() or
                    self.camera_worker2 and self.camera_worker2.has_error()):
                    error1 = self.camera_worker1.get_last_error() if self.camera_worker1 else None
                    error2 = self.camera_worker2.get_last_error() if self.camera_worker2 else None
                    print(f"[Loop] Camera worker error - Worker1: {error1}, Worker2: {error2}")
                    break

                # Get frames from camera worker queues
                f1 = None
                f2 = None
                
                if self.camera_worker1:
                    f1 = self.camera_worker1.get_frame()
                    if f1 is not None:
                        self._last_frame1 = f1  # Store for fallback
                    elif self._last_frame1 is not None:
                        f1 = self._last_frame1  # Use last available frame
                
                if self.camera_worker2:
                    f2 = self.camera_worker2.get_frame()
                    if f2 is not None:
                        self._last_frame2 = f2  # Store for fallback
                    elif self._last_frame2 is not None:
                        f2 = self._last_frame2  # Use last available frame

                # Skip if we don't have frames from both cameras yet
                if f1 is None or f2 is None:
                    time.sleep(0.001)  # Short sleep to prevent busy waiting
                    continue

                try:
                    # Frames are already resized by camera workers, just combine them
                    combo = np.hstack((f1, f2))

                    # Handle video writing or buffering
                    if buffering_fallback:
                        frames.append(combo)
                    else:
                        now_t = time.time()
                        dt = max(0.0, now_t - last_t)
                        last_t = now_t
                        write_accum += writer_fps * dt
                        count = int(write_accum)
                        if total_written == 0 and count == 0:
                            # Ensure we write at least one frame so the file isn't empty
                            count = 1
                        if count > 0:
                            for _ in range(count):
                                out.write(combo)
                            write_accum -= count
                            total_written += count

                    # Update preview (throttled for performance)
                    if frame_counter % preview_throttle == 0:
                        with self._lock:
                            self.frame_preview = combo
                    frame_counter += 1
                    
                except Exception as e:
                    print(f"[Loop] Frame processing error: {e}")
                    break

            # Release writer if we streamed frames
            if out is not None:
                try:
                    out.release()
                except Exception:
                    pass

        self.recording = False

        # Save frames to a real video when OpenCV is available (even in demo mode),
        # otherwise fall back to a tiny text file to indicate the recording occurred.
        if frames and self._out_path and CV2_AVAILABLE:
            try:
                # Measure actual FPS to avoid "fast playback" when capture is slower than target
                elapsed = max(0.001, time.time() - start_time)
                actual_fps = max(1.0, min(60.0, len(frames) / elapsed))

                # Prefer MJPG at higher resolutions for lower CPU use; fallback to XVID
                prefer_mjpg = combo_width * combo_height >= (1920 * 1080) or self.height >= 720
                try_codecs = ["MJPG", "XVID"] if prefer_mjpg else ["XVID", "MJPG"]
                out = None
                last_err = None
                for c in try_codecs:
                    try:
                        fourcc = cv2.VideoWriter_fourcc(*c)
                        out_try = cv2.VideoWriter(self._out_path, fourcc, actual_fps, (combo_width, combo_height))
                        if out_try is not None and out_try.isOpened():
                            out = out_try
                            break
                    except Exception as e:
                        last_err = e
                        out = None
                if out is None:
                    raise RuntimeError(f"Could not open VideoWriter. Last error: {last_err}")

                for frame in frames:
                    out.write(frame)
                out.release()

                print(f"[Loop] Video saved: {self._out_path} ({len(frames)} frames @ ~{actual_fps:.1f} fps)")
            except Exception as e:
                print(f"[Loop] Error saving video: {e}")
        elif frames and self._out_path:
            try:
                with open(self._out_path, 'w') as f:
                    f.write(f"Demo recording completed at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                print(f"[Loop] Demo file created: {self._out_path}")
            except Exception as e:
                print(f"[Loop] Error writing demo file: {e}")

    def get_preview(self):
        with self._lock:
            if self.frame_preview is None:
                return None
            try:
                return self.frame_preview.copy()
            except Exception:
                return self.frame_preview

    def stop(self):
        """Stop recording and signal camera workers to stop."""
        self._stop_requested = True
        self.recording = False
        
        # Stop camera workers if they exist
        if self.camera_worker1:
            self.camera_worker1.stop()
        if self.camera_worker2:
            self.camera_worker2.stop()

    def release(self):
        """Release all resources including cameras and worker threads."""
        self.stop()
        
        # Wait for camera workers to finish and clean up
        if self.camera_worker1:
            try:
                self.camera_worker1.join(timeout=2.0)  # Wait up to 2 seconds
            except Exception:
                pass
            self.camera_worker1 = None
            
        if self.camera_worker2:
            try:
                self.camera_worker2.join(timeout=2.0)  # Wait up to 2 seconds
            except Exception:
                pass
            self.camera_worker2 = None
        
        # Release camera resources
        try:
            if self.cap1:
                self.cap1.release()
        except Exception:
            pass
        try:
            if self.cap2:
                self.cap2.release()
        except Exception:
            pass
        self.cap1 = self.cap2 = None
        self.frame_preview = None
        self._last_frame1 = None
        self._last_frame2 = None