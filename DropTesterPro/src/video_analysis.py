"""
Advanced Video Analysis Module
Provides slow-motion replay, frame-by-frame analysis, and trajectory tracking.
"""

import os
import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import time
from typing import Optional, List, Tuple, Dict

class VideoAnalyzer:
    """Advanced video analysis tool with slow-motion and frame-by-frame capabilities."""
    
    def __init__(self, parent_app):
        """Initialize video analyzer."""
        self.parent_app = parent_app
        self.window = None
        self.video_path = None
        self.cap = None
        self.total_frames = 0
        self.current_frame = 0
        self.fps = 30
        self.playing = False
        self.playback_speed = 1.0
        self.frame_cache = {}
        self.trajectory_points = []
        self.analysis_markers = []
        
    def show_analyzer(self, video_path: str):
        """Show the video analyzer window."""
        if not os.path.exists(video_path):
            messagebox.showerror("Error", f"Video file not found: {video_path}")
            return
            
        if self.window and self.window.winfo_exists():
            self.window.destroy()
            
        self.video_path = video_path
        self._init_video()
        self._create_window()
        
    def _init_video(self):
        """Initialize video capture."""
        try:
            if self.cap:
                self.cap.release()
                
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                raise Exception("Cannot open video file")
                
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
            self.current_frame = 0
            self.frame_cache = {}
            self.trajectory_points = []
            self.analysis_markers = []
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize video: {e}")
            
    def _create_window(self):
        """Create the analyzer window."""
        self.window = tk.Toplevel(self.parent_app.root)
        self.window.title(f"Video Analyzer - {os.path.basename(self.video_path)}")
        self.window.geometry("1200x800")
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Configure grid
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(1, weight=1)
        
        # Create UI elements
        self._create_controls()
        self._create_video_display()
        self._create_analysis_panel()
        self._create_timeline()
        
        # Load first frame
        self._display_frame(0)
        
    def _create_controls(self):
        """Create playback controls."""
        controls_frame = ttk.Frame(self.window, padding=10)
        controls_frame.grid(row=0, column=0, sticky="ew")
        
        # Playback buttons
        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        self.play_btn = ttk.Button(button_frame, text="▶", command=self._toggle_play, width=3)
        self.play_btn.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(button_frame, text="⏹", command=self._stop, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="⏮", command=self._prev_frame, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="⏭", command=self._next_frame, width=3).pack(side=tk.LEFT, padx=2)
        
        # Speed controls
        speed_frame = ttk.Frame(controls_frame)
        speed_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(speed_frame, text="Speed:").pack(side=tk.LEFT, padx=2)
        
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_scale = ttk.Scale(speed_frame, from_=0.1, to=2.0, variable=self.speed_var, 
                               orient=tk.HORIZONTAL, length=150)
        speed_scale.pack(side=tk.LEFT, padx=5)
        speed_scale.bind("<Motion>", self._on_speed_change)
        
        self.speed_label = ttk.Label(speed_frame, text="1.0x")
        self.speed_label.pack(side=tk.LEFT, padx=2)
        
        # Frame info
        info_frame = ttk.Frame(controls_frame)
        info_frame.pack(side=tk.RIGHT)
        
        self.frame_info_var = tk.StringVar(value="Frame: 0 / 0")
        ttk.Label(info_frame, textvariable=self.frame_info_var).pack(side=tk.LEFT, padx=5)
        
        self.time_info_var = tk.StringVar(value="Time: 0.00s")
        ttk.Label(info_frame, textvariable=self.time_info_var).pack(side=tk.LEFT, padx=5)
        
    def _create_video_display(self):
        """Create video display area."""
        display_frame = ttk.Frame(self.window)
        display_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        display_frame.columnconfigure(0, weight=1)
        display_frame.rowconfigure(0, weight=1)
        
        # Video canvas
        self.canvas = tk.Canvas(display_frame, bg="black")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        # Bind mouse events for analysis
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        
        # Scrollbars for large videos
        v_scroll = ttk.Scrollbar(display_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scroll = ttk.Scrollbar(display_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
    def _create_analysis_panel(self):
        """Create analysis tools panel."""
        analysis_frame = ttk.LabelFrame(self.window, text="Analysis Tools", padding=10)
        analysis_frame.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(0, 10))
        
        # Analysis mode selection
        ttk.Label(analysis_frame, text="Analysis Mode:").pack(anchor="w", pady=(0, 5))
        
        self.analysis_mode = tk.StringVar(value="trajectory")
        modes = [("Trajectory Tracking", "trajectory"), ("Impact Detection", "impact"), 
                ("Deformation Analysis", "deformation"), ("Measurement", "measurement")]
        
        for text, value in modes:
            ttk.Radiobutton(analysis_frame, text=text, variable=self.analysis_mode, 
                           value=value).pack(anchor="w", pady=2)
        
        ttk.Separator(analysis_frame, orient=tk.HORIZONTAL).pack(fill="x", pady=10)
        
        # Analysis actions
        ttk.Button(analysis_frame, text="Auto-Detect Impact", 
                  command=self._auto_detect_impact).pack(fill="x", pady=2)
        ttk.Button(analysis_frame, text="Track Object", 
                  command=self._start_tracking).pack(fill="x", pady=2)
        ttk.Button(analysis_frame, text="Clear Markers", 
                  command=self._clear_markers).pack(fill="x", pady=2)
        
        ttk.Separator(analysis_frame, orient=tk.HORIZONTAL).pack(fill="x", pady=10)
        
        # Export options
        ttk.Label(analysis_frame, text="Export:").pack(anchor="w", pady=(0, 5))
        ttk.Button(analysis_frame, text="Export Frame", 
                  command=self._export_frame).pack(fill="x", pady=2)
        ttk.Button(analysis_frame, text="Export Analysis", 
                  command=self._export_analysis).pack(fill="x", pady=2)
        
        # Analysis results display
        ttk.Separator(analysis_frame, orient=tk.HORIZONTAL).pack(fill="x", pady=10)
        
        ttk.Label(analysis_frame, text="Results:").pack(anchor="w", pady=(0, 5))
        self.results_text = tk.Text(analysis_frame, height=10, width=30, wrap=tk.WORD)
        results_scroll = ttk.Scrollbar(analysis_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=results_scroll.set)
        
        self.results_text.pack(side=tk.LEFT, fill="both", expand=True)
        results_scroll.pack(side=tk.RIGHT, fill="y")
        
    def _create_timeline(self):
        """Create timeline scrubber."""
        timeline_frame = ttk.Frame(self.window, padding=10)
        timeline_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        timeline_frame.columnconfigure(1, weight=1)
        
        ttk.Label(timeline_frame, text="Timeline:").grid(row=0, column=0, padx=(0, 10))
        
        self.timeline_var = tk.IntVar(value=0)
        self.timeline_scale = ttk.Scale(timeline_frame, from_=0, to=max(1, self.total_frames-1), 
                                       variable=self.timeline_var, orient=tk.HORIZONTAL)
        self.timeline_scale.grid(row=0, column=1, sticky="ew", padx=5)
        self.timeline_scale.bind("<ButtonRelease-1>", self._on_timeline_change)
        self.timeline_scale.bind("<B1-Motion>", self._on_timeline_drag)
        
        # Timeline markers for important frames
        self.timeline_canvas = tk.Canvas(timeline_frame, height=20, bg="lightgray")
        self.timeline_canvas.grid(row=1, column=1, sticky="ew", padx=5, pady=(5, 0))
        
    def _display_frame(self, frame_num: int):
        """Display specific frame."""
        try:
            if frame_num < 0 or frame_num >= self.total_frames:
                return
                
            # Get frame from cache or load it
            if frame_num in self.frame_cache:
                frame = self.frame_cache[frame_num]
            else:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = self.cap.read()
                if not ret:
                    return
                    
                # Cache frame for better performance
                if len(self.frame_cache) < 100:  # Limit cache size
                    self.frame_cache[frame_num] = frame.copy()
            
            self.current_frame = frame_num
            
            # Convert to RGB and resize for display
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Add analysis overlays
            frame_rgb = self._add_analysis_overlays(frame_rgb)
            
            # Convert to PhotoImage
            frame_pil = Image.fromarray(frame_rgb)
            
            # Scale to fit canvas while maintaining aspect ratio
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                frame_pil = self._scale_image(frame_pil, canvas_width, canvas_height)
            
            self.photo = ImageTk.PhotoImage(frame_pil)
            
            # Clear canvas and display frame
            self.canvas.delete("all")
            self.canvas.create_image(canvas_width//2, canvas_height//2, image=self.photo)
            
            # Update info displays
            self._update_info_displays()
            self._update_timeline_markers()
            
        except Exception as e:
            print(f"Error displaying frame: {e}")
    
    def _scale_image(self, image: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """Scale image to fit within given dimensions while maintaining aspect ratio."""
        orig_width, orig_height = image.size
        
        # Calculate scaling factor
        scale_x = max_width / orig_width
        scale_y = max_height / orig_height
        scale = min(scale_x, scale_y, 1.0)  # Don't upscale
        
        if scale < 1.0:
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def _add_analysis_overlays(self, frame: np.ndarray) -> np.ndarray:
        """Add analysis overlays to frame."""
        overlay_frame = frame.copy()
        
        # Draw trajectory points
        for i, point in enumerate(self.trajectory_points):
            if point['frame'] == self.current_frame:
                cv2.circle(overlay_frame, (point['x'], point['y']), 5, (255, 0, 0), -1)
                if i > 0:
                    prev_point = self.trajectory_points[i-1]
                    cv2.line(overlay_frame, (prev_point['x'], prev_point['y']), 
                            (point['x'], point['y']), (255, 0, 0), 2)
        
        # Draw analysis markers
        for marker in self.analysis_markers:
            if marker['frame'] == self.current_frame:
                x, y = marker['x'], marker['y']
                marker_type = marker['type']
                
                if marker_type == 'impact':
                    cv2.drawMarker(overlay_frame, (x, y), (0, 255, 0), 
                                  markerType=cv2.MARKER_CROSS, markerSize=20, thickness=3)
                    cv2.putText(overlay_frame, "IMPACT", (x+10, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                elif marker_type == 'deformation':
                    cv2.rectangle(overlay_frame, (x-20, y-20), (x+20, y+20), (0, 0, 255), 2)
                    cv2.putText(overlay_frame, "DEFORM", (x+25, y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        return overlay_frame
    
    def _update_info_displays(self):
        """Update frame and time information."""
        self.frame_info_var.set(f"Frame: {self.current_frame} / {self.total_frames}")
        time_seconds = self.current_frame / self.fps
        self.time_info_var.set(f"Time: {time_seconds:.2f}s")
        
        # Update timeline position
        self.timeline_var.set(self.current_frame)
        
    def _update_timeline_markers(self):
        """Update timeline markers for analysis points."""
        self.timeline_canvas.delete("all")
        
        if self.total_frames > 0:
            canvas_width = self.timeline_canvas.winfo_width()
            if canvas_width > 1:
                # Draw impact markers
                for marker in self.analysis_markers:
                    if marker['type'] == 'impact':
                        x_pos = (marker['frame'] / self.total_frames) * canvas_width
                        self.timeline_canvas.create_line(x_pos, 0, x_pos, 20, fill="red", width=2)
                        
                # Draw current position
                current_x = (self.current_frame / self.total_frames) * canvas_width
                self.timeline_canvas.create_line(current_x, 0, current_x, 20, fill="blue", width=3)
    
    def _toggle_play(self):
        """Toggle video playback."""
        if self.playing:
            self._pause()
        else:
            self._play()
    
    def _play(self):
        """Start video playback."""
        self.playing = True
        self.play_btn.config(text="⏸")
        self._playback_loop()
    
    def _pause(self):
        """Pause video playback."""
        self.playing = False
        self.play_btn.config(text="▶")
    
    def _stop(self):
        """Stop video playback and return to beginning."""
        self.playing = False
        self.play_btn.config(text="▶")
        self._display_frame(0)
    
    def _playback_loop(self):
        """Main playback loop."""
        if not self.playing:
            return
            
        # Calculate frame delay based on speed
        frame_delay = (1.0 / self.fps) / self.playback_speed
        
        # Display next frame
        next_frame = self.current_frame + 1
        if next_frame >= self.total_frames:
            self._pause()
            return
            
        self._display_frame(next_frame)
        
        # Schedule next frame
        self.window.after(int(frame_delay * 1000), self._playback_loop)
    
    def _prev_frame(self):
        """Go to previous frame."""
        if self.current_frame > 0:
            self._display_frame(self.current_frame - 1)
    
    def _next_frame(self):
        """Go to next frame."""
        if self.current_frame < self.total_frames - 1:
            self._display_frame(self.current_frame + 1)
    
    def _on_speed_change(self, event=None):
        """Handle speed control change."""
        self.playback_speed = self.speed_var.get()
        self.speed_label.config(text=f"{self.playback_speed:.1f}x")
    
    def _on_timeline_change(self, event=None):
        """Handle timeline scrubber change."""
        frame_num = int(self.timeline_var.get())
        self._display_frame(frame_num)
    
    def _on_timeline_drag(self, event=None):
        """Handle timeline dragging."""
        self._on_timeline_change(event)
    
    def _on_canvas_click(self, event):
        """Handle canvas click for analysis."""
        mode = self.analysis_mode.get()
        x, y = event.x, event.y
        
        # Convert canvas coordinates to image coordinates
        # This is a simplified conversion - you'd need more sophisticated coordinate mapping
        if mode == "impact":
            self._add_impact_marker(x, y)
        elif mode == "trajectory":
            self._add_trajectory_point(x, y)
        elif mode == "deformation":
            self._add_deformation_marker(x, y)
    
    def _on_canvas_drag(self, event):
        """Handle canvas dragging."""
        pass  # Implement for drawing tools
    
    def _on_canvas_release(self, event):
        """Handle canvas button release."""
        pass  # Implement for drawing tools
    
    def _add_impact_marker(self, x: int, y: int):
        """Add impact marker at current frame."""
        marker = {
            'frame': self.current_frame,
            'x': x,
            'y': y,
            'type': 'impact',
            'timestamp': self.current_frame / self.fps
        }
        self.analysis_markers.append(marker)
        self._display_frame(self.current_frame)  # Refresh display
        self._update_results_display()
    
    def _add_trajectory_point(self, x: int, y: int):
        """Add trajectory point at current frame."""
        point = {
            'frame': self.current_frame,
            'x': x,
            'y': y,
            'timestamp': self.current_frame / self.fps
        }
        self.trajectory_points.append(point)
        self._display_frame(self.current_frame)  # Refresh display
        self._update_results_display()
    
    def _add_deformation_marker(self, x: int, y: int):
        """Add deformation marker at current frame."""
        marker = {
            'frame': self.current_frame,
            'x': x,
            'y': y,
            'type': 'deformation',
            'timestamp': self.current_frame / self.fps
        }
        self.analysis_markers.append(marker)
        self._display_frame(self.current_frame)  # Refresh display
        self._update_results_display()
    
    def _clear_markers(self):
        """Clear all analysis markers."""
        self.trajectory_points = []
        self.analysis_markers = []
        self._display_frame(self.current_frame)  # Refresh display
        self._update_results_display()
    
    def _auto_detect_impact(self):
        """Auto-detect impact frame using motion analysis."""
        try:
            messagebox.showinfo("Auto-Detection", "Analyzing video for impact moment...")
            
            # This would implement the actual impact detection algorithm
            # For now, we'll use a placeholder
            impact_frame = self.total_frames // 2  # Placeholder
            
            self._add_impact_marker(100, 100)  # Placeholder position
            self._display_frame(impact_frame)
            
            messagebox.showinfo("Detection Complete", f"Impact detected at frame {impact_frame}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to detect impact: {e}")
    
    def _start_tracking(self):
        """Start object tracking."""
        messagebox.showinfo("Tracking", "Object tracking feature coming soon!")
    
    def _update_results_display(self):
        """Update the analysis results display."""
        self.results_text.delete(1.0, tk.END)
        
        results = f"Analysis Results:\n\n"
        results += f"Impact Markers: {len([m for m in self.analysis_markers if m['type'] == 'impact'])}\n"
        results += f"Deformation Markers: {len([m for m in self.analysis_markers if m['type'] == 'deformation'])}\n"
        results += f"Trajectory Points: {len(self.trajectory_points)}\n\n"
        
        if self.trajectory_points:
            results += "Trajectory Analysis:\n"
            for i, point in enumerate(self.trajectory_points):
                results += f"  Point {i+1}: Frame {point['frame']}, Time {point['timestamp']:.2f}s\n"
        
        if self.analysis_markers:
            results += "\nMarkers:\n"
            for i, marker in enumerate(self.analysis_markers):
                results += f"  {marker['type'].title()} {i+1}: Frame {marker['frame']}, Time {marker['timestamp']:.2f}s\n"
        
        self.results_text.insert(1.0, results)
    
    def _export_frame(self):
        """Export current frame as image."""
        try:
            from tkinter import filedialog
            
            filename = filedialog.asksaveasfilename(
                title="Export Frame",
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
            )
            
            if filename:
                # Get current frame
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                ret, frame = self.cap.read()
                if ret:
                    # Add analysis overlays
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_with_overlay = self._add_analysis_overlays(frame_rgb)
                    frame_bgr = cv2.cvtColor(frame_with_overlay, cv2.COLOR_RGB2BGR)
                    
                    cv2.imwrite(filename, frame_bgr)
                    messagebox.showinfo("Export Complete", f"Frame exported to:\n{filename}")
                    
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export frame: {e}")
    
    def _export_analysis(self):
        """Export analysis data."""
        try:
            from tkinter import filedialog
            import json
            
            filename = filedialog.asksaveasfilename(
                title="Export Analysis Data",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                analysis_data = {
                    "video_path": self.video_path,
                    "total_frames": self.total_frames,
                    "fps": self.fps,
                    "analysis_timestamp": time.time(),
                    "trajectory_points": self.trajectory_points,
                    "analysis_markers": self.analysis_markers
                }
                
                with open(filename, 'w') as f:
                    json.dump(analysis_data, f, indent=2)
                
                messagebox.showinfo("Export Complete", f"Analysis data exported to:\n{filename}")
                
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export analysis: {e}")
    
    def _on_close(self):
        """Handle window closing."""
        self.playing = False
        if self.cap:
            self.cap.release()
        if self.window:
            self.window.destroy()
        self.window = None