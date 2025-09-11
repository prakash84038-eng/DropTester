import os
import sys
import platform
import subprocess
import time
import threading
import json
from datetime import datetime

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from PIL import Image, ImageTk

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF = None
    FPDF_AVAILABLE = False
    print("Warning: fpdf not available. PDF generation will fail unless installed.")

try:
    import cv2
except ImportError:
    # This is handled by CV2_AVAILABLE, but we need a placeholder for type hints if needed
    pass

from .camera import DualCameraRecorder, CV2_AVAILABLE, NUMPY_AVAILABLE
from . import constants
from . import utils
from . import analysis

class BottleTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bottle Drop Tester")
        self.root.geometry("1400x800")
        self.root.minsize(1200, 720)

        # --- Theme / Colors ---
        self.BIS_BLUE = "#003366"
        self.BIS_ORANGE = "#FF9933"
        self.BIS_GREEN = "#138808"
        self.BIS_RED = "#DC3545"
        self.LIGHT_BG = "#F8F9FA"
        self.SETTINGS_BG = "#EAF2F8"  # Soft light blue for settings
        self.WHITE_TEXT = "#FFFFFF"
        self.PRIMARY_BLUE = "#007BFF"
        self.SECONDARY_GRAY = "#6C757D"

        self.root.configure(bg=self.LIGHT_BG)

        self.style = ttk.Style(self.root)
        
        # --- Global Style Configuration ---
        self.style.configure(".", background=self.LIGHT_BG, foreground="black")
        self.style.configure("TFrame", background=self.LIGHT_BG)
        self.style.configure("TLabel", background=self.LIGHT_BG, foreground="black")
        self.style.configure("TLabelFrame", background=self.LIGHT_BG)
        self.style.configure("TLabelFrame.Label", background=self.LIGHT_BG, foreground="black")
        self.style.configure("TButton", foreground="black")
        self.style.configure("TEntry", fieldbackground="white", foreground="black")
        self.style.configure("TCombobox", fieldbackground="white", foreground="black")

        # --- Specific Named Styles (override defaults) ---
        self.style.configure("Card.TFrame", background="white", relief="solid", borderwidth=1)
        self.style.configure("Header.TFrame", background=self.BIS_BLUE)
        self.style.configure("Header.TLabel", background=self.BIS_BLUE, foreground=self.WHITE_TEXT, font=("Arial", 10))
        self.style.configure("Footer.TFrame", background=self.BIS_BLUE)
        self.style.configure("Footer.TLabel", background=self.BIS_BLUE, foreground=self.WHITE_TEXT, font=("Arial", 9))
        self.style.configure("Clock.TLabel", background=self.BIS_BLUE, foreground=self.BIS_ORANGE, font=("Arial", 9, "bold"))

        # state
        self.testing_persons = utils.load_testing_persons()
        self.current_parent_dir = utils.load_directory()

        self.sample_code_var = tk.StringVar()
        self.is_number_var = tk.StringVar(value="15410")
        self.parameter_var = tk.StringVar(value="Drop Impact test")
        self.department_var = tk.StringVar(value="Mechanical")
        self.material_var = tk.StringVar(value="Plastic")
        self.testing_person_var = tk.StringVar(value=self.testing_persons[0] if self.testing_persons else "Default User")
        self.date_var = tk.StringVar(value=datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
        self.result_var = tk.StringVar(value="")
        self.countdown_var = tk.StringVar(value="")

        self.bottle_video_paths = [None] * constants.BOTTLE_COUNT
        self.bottle_analysis_results = [None] * constants.BOTTLE_COUNT
        self.bottle_recording = [False] * constants.BOTTLE_COUNT
        self.bottle_indicators = []
        self.progress_status_labels = []
        self.progress_result_labels = []
        self.current_bottle_index = 0
        self.current_pdf_path = None
        self.read_only = False
        self.playing_video = False
        self.recording_start_time = 0

        self.recorder = DualCameraRecorder()

        # Initialize recorder with saved resolution
        width, height = utils.load_video_settings()
        self.cameras_ready = self.recorder.initialize(width, height)

        if self.recorder.demo_mode:
            messagebox.showinfo(
                "Demo Mode",
                "No cameras detected or OpenCV is missing. Running in DEMO MODE where recording is simulated.",
                parent=self.root,
            )

        self._build_ui()
        self._setup_keyboard_shortcuts()
        self.update_time_loop()

    def _build_ui(self):
        # Configure main window grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)  # Make the preview area row expandable

        self._build_header()
        self._build_preview_area()
        self._build_controls()
        self._build_status_bar()
        self._update_ui_for_bottle()

    def _build_header(self):
        header = ttk.Frame(self.root, padding=10, style="Header.TFrame")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        header.bind("<Button-1>", self._clear_focus)
        for i in range(8):
            header.grid_columnconfigure(i, weight=1)
        header.grid_columnconfigure(8, weight=0)  # Logo column

        ttk.Label(header, text="Sample Code:", style="Header.TLabel").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="e")
        self.sample_code_entry = ttk.Entry(header, textvariable=self.sample_code_var)
        self.sample_code_entry.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.sample_code_var.trace("w", lambda *a: self._on_sample_code_change())

        ttk.Label(header, text="IS Number:", style="Header.TLabel").grid(row=0, column=2, padx=(0, 5), pady=5, sticky="e")
        self.is_number_entry = ttk.Entry(header, textvariable=self.is_number_var)
        self.is_number_entry.grid(row=0, column=3, padx=(0, 10), pady=5, sticky="ew")

        ttk.Label(header, text="Parameter:", style="Header.TLabel").grid(row=0, column=4, padx=(0, 5), pady=5, sticky="e")
        self.parameter_entry = ttk.Entry(header, textvariable=self.parameter_var)
        self.parameter_entry.grid(row=0, column=5, padx=(0, 10), pady=5, sticky="ew")

        ttk.Label(header, text="Department:", style="Header.TLabel").grid(row=0, column=6, padx=(0, 5), pady=5, sticky="e")
        self.department_entry = ttk.Entry(header, textvariable=self.department_var, state="readonly")
        self.department_entry.grid(row=0, column=7, pady=5, sticky="ew")

        ttk.Label(header, text="Testing Person:", style="Header.TLabel").grid(row=1, column=0, padx=(0, 5), pady=5, sticky="e")
        self.testing_person_menu = ttk.Combobox(header, textvariable=self.testing_person_var,
                                                values=self.testing_persons, state="readonly")
        self.testing_person_menu.grid(row=1, column=1, padx=(0, 10), pady=5, sticky="ew")

        ttk.Label(header, text="Bottle Material:", style="Header.TLabel").grid(row=1, column=2, padx=(0, 5), pady=5, sticky="e")
        self.material_menu = ttk.Combobox(header, textvariable=self.material_var,
                                          values=["Plastic", "Steel"], state="readonly")
        self.material_menu.grid(row=1, column=3, padx=(0, 10), pady=5, sticky="ew")

        ttk.Label(header, text="Date & Time:", style="Header.TLabel").grid(row=1, column=4, padx=(0, 5), pady=5, sticky="e")
        ttk.Entry(header, textvariable=self.date_var, state="readonly").grid(row=1, column=5, pady=5, sticky="ew")

        try:
            if hasattr(constants, 'HEADER_LOGO_FILE') and os.path.exists(constants.HEADER_LOGO_FILE):
                original_img = Image.open(constants.HEADER_LOGO_FILE).convert("RGBA")
                
                target_height = 50
                w, h = original_img.size
                aspect_ratio = w / h
                target_width = int(target_height * aspect_ratio)

                logo_img = original_img.resize((target_width, target_height), Image.LANCZOS)
                self.header_logo = ImageTk.PhotoImage(logo_img)
                logo_label = ttk.Label(header, image=self.header_logo, style="Header.TLabel")
                logo_label.grid(row=0, column=8, rowspan=2, padx=(20, 10))
        except Exception as e:
            print(f"Header logo error: {e}")

    def _on_sample_code_change(self, *args):
        self._update_ui_for_bottle()

    def _build_preview_area(self):
        # Main container for preview and progress panel
        container = ttk.Frame(self.root)
        container.grid(row=1, column=0, sticky="nsew", padx=10, pady=6)
        container.columnconfigure(0, weight=1)  # Preview area expands
        container.columnconfigure(1, weight=0)  # Progress panel is fixed width
        container.rowconfigure(0, weight=1)
        container.bind("<Button-1>", self._clear_focus)

        # --- Left Panel (Indicators and Video) ---
        left_panel = ttk.Frame(container)
        left_panel.grid(row=0, column=0, sticky="nsew")
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(1, weight=1) # Make the preview row expandable
        left_panel.bind("<Button-1>", self._clear_focus)

        # Visual bottle selector
        indicator_frame = ttk.Frame(left_panel)
        indicator_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        indicator_frame.columnconfigure(0, weight=1)  # Center the inner frame
        indicator_frame.bind("<Button-1>", self._clear_focus)

        inner_indicator_frame = ttk.Frame(indicator_frame)
        inner_indicator_frame.grid(row=0, column=0)
        inner_indicator_frame.bind("<Button-1>", self._clear_focus)

        for i in range(constants.BOTTLE_COUNT):
            btn = ttk.Button(inner_indicator_frame, text=f"Bottle {i+1}",
                             command=lambda i=i: self._switch_bottle_to(i), style="Indicator.TButton")
            btn.pack(side="left", padx=5)
            self.bottle_indicators.append(btn)

        # Video Preview Frame
        preview_frame = ttk.Frame(left_panel, style="Card.TFrame")
        preview_frame.grid(row=1, column=0, sticky="nsew", pady=8)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.bind("<Button-1>", self._clear_focus)

        self.preview_label = ttk.Label(preview_frame, background="black")
        self.preview_label.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.preview_label.bind("<Button-1>", self._clear_focus)

        # --- Right Panel (Progress & Override) ---
        right_panel = ttk.Frame(container)
        right_panel.grid(row=0, column=1, sticky="ns", padx=(10, 0), pady=8)
        self._build_progress_panel(right_panel)
        self._build_override_panel(right_panel)

        self._fill_black_preview()

    def _build_progress_panel(self, parent):
        progress_frame = ttk.LabelFrame(parent, text="Test Progress", padding=15)
        progress_frame.pack(fill="x", expand=False)

        for i in range(constants.BOTTLE_COUNT):
            name_label = ttk.Label(progress_frame, text=f"Bottle {i+1}:", font=("Arial", 11))
            name_label.grid(row=i, column=0, sticky="w", pady=4)

            status_label = ttk.Label(progress_frame, text="Pending", font=("Arial", 11, "normal"), foreground=self.SECONDARY_GRAY)
            status_label.grid(row=i, column=1, sticky="w", padx=(10, 0))
            
            result_label = ttk.Label(progress_frame, text="-", font=("Arial", 11, "bold"))
            result_label.grid(row=i, column=2, sticky="w", padx=(10, 0))

            self.progress_status_labels.append({'name': name_label, 'status': status_label})
            self.progress_result_labels.append(result_label)

    def _build_override_panel(self, parent):
        self.override_frame = ttk.LabelFrame(parent, text="Analysis Correction", padding=15)
        # This frame will be packed later by `_update_ui_for_bottle`
        
        ttk.Label(self.override_frame, text="Is the result correct?", justify="center").pack(pady=(0, 10))
        
        btn_container = ttk.Frame(self.override_frame)
        btn_container.pack(pady=5)

        self.override_pass_btn = tk.Button(btn_container, text="Mark as PASS", command=lambda: self._override_analysis("PASS"),
                                           font=("Arial", 10, "bold"), bg=self.BIS_GREEN, fg=self.WHITE_TEXT, bd=0, relief="flat")
        self.override_pass_btn.pack(side="left", padx=5, ipady=4)

        self.override_fail_btn = tk.Button(btn_container, text="Mark as FAIL", command=lambda: self._override_analysis("FAIL"),
                                           font=("Arial", 10, "bold"), bg=self.BIS_RED, fg=self.WHITE_TEXT, bd=0, relief="flat")
        self.override_fail_btn.pack(side="left", padx=5, ipady=4)

    def _build_controls(self):
        controls = ttk.Frame(self.root, padding=(0, 10))
        controls.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))
        for i in range(7):
            controls.columnconfigure(i, weight=1)

        button_font = ("Arial", 10, "bold")

        self.record_btn = tk.Button(controls, text="● Record (Space)", command=self._start_recording,
                                    font=button_font, bg=self.BIS_GREEN, fg=self.WHITE_TEXT, bd=0, relief="flat")
        self.stop_btn = tk.Button(controls, text="■ Stop (Esc)", command=self._stop_activity,
                                  font=button_font, bg=self.BIS_RED, fg=self.WHITE_TEXT, bd=0, relief="flat")
        self.play_btn = tk.Button(controls, text="▶ Play (Enter)", command=self._play_current,
                                  font=button_font, bg=self.PRIMARY_BLUE, fg=self.WHITE_TEXT, bd=0, relief="flat")
        self.analyze_btn = tk.Button(controls, text="🔬 Re-Analyze (F3)", command=self._run_auto_detection,
                                     font=button_font, bg=self.PRIMARY_BLUE, fg=self.WHITE_TEXT, bd=0, relief="flat")
        self.finalize_btn = tk.Button(controls, text="✓ Finalize Report (F1)", command=self._finish_test,
                                  font=button_font, bg=self.BIS_GREEN, fg=self.WHITE_TEXT, bd=0, relief="flat")
        self.view_report_btn = tk.Button(controls, text="📄 View Report (Ctrl+V)", command=self._view_report,
                                         font=button_font, bg=self.SECONDARY_GRAY, fg=self.WHITE_TEXT, bd=0, relief="flat")
        self.new_test_btn = tk.Button(controls, text="✨ New Test (Ctrl+N)", command=self._start_new_test,
                                      font=button_font, bg=self.BIS_ORANGE, fg=self.WHITE_TEXT, bd=0, relief="flat")

        self.record_btn.grid(row=0, column=0, sticky="ew", padx=4, ipady=5)
        self.stop_btn.grid(row=0, column=1, sticky="ew", padx=4, ipady=5)
        self.play_btn.grid(row=0, column=2, sticky="ew", padx=4, ipady=5)
        self.analyze_btn.grid(row=0, column=3, sticky="ew", padx=4, ipady=5)
        self.finalize_btn.grid(row=0, column=4, sticky="ew", padx=4, ipady=5)
        self.view_report_btn.grid(row=0, column=5, sticky="ew", padx=4, ipady=5)
        self.new_test_btn.grid(row=0, column=6, sticky="ew", padx=4, ipady=5)

    def _build_status_bar(self):
        bar = ttk.Frame(self.root, padding=5, style="Footer.TFrame")
        bar.grid(row=3, column=0, sticky="ew", padx=10, pady=(6, 10))
        bar.bind("<Button-1>", self._clear_focus)

        # Column 1 will take up all available space, pushing other elements to the right
        bar.columnconfigure(1, weight=1)

        # Column 0: Result info
        ttk.Label(bar, text="Status:", style="Footer.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Entry(bar, textvariable=self.result_var, width=25, style="Footer.TEntry", state="readonly").grid(row=0, column=1, sticky="w")

        # Column 2: Progress bar
        self.progress_bar = ttk.Progressbar(bar, orient="horizontal", length=200, mode="determinate")
        self.progress_bar.grid(row=0, column=2, padx=(20, 10), sticky="e")

        # Column 3: Countdown timer
        ttk.Label(bar, textvariable=self.countdown_var, style="Footer.TLabel", font=("Arial", 10, "bold")).grid(row=0, column=3, sticky="e")

        # Column 4: Date and time
        ttk.Label(bar, textvariable=self.date_var, style="Clock.TLabel").grid(row=0, column=4, sticky="e", padx=(20, 0))

    def _clear_focus(self, event=None):
        """Remove focus from any input widget to enable global keyboard shortcuts."""
        self.root.focus_set()

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for common operations."""
        self.root.focus_set()
        
        # Record operations
        self.root.bind_all('<Control-r>', self._on_record_shortcut)
        self.root.bind_all('<space>', self._on_record_shortcut)
        
        # Stop operations  
        self.root.bind_all('<Escape>', self._on_stop_shortcut)
        self.root.bind_all('<Control-s>', self._on_stop_shortcut)
        
        # Play current video
        self.root.bind_all('<Control-p>', self._on_play_shortcut)
        self.root.bind_all('<Return>', self._on_play_shortcut)
        
        # Test results
        self.root.bind_all('<F1>', self._on_finalize_shortcut)
        self.root.bind_all('<F3>', self._on_analyze_shortcut)
        
        # File operations
        self.root.bind_all('<Control-n>', self._on_new_test_shortcut)
        self.root.bind_all('<Control-o>', self._on_open_test_shortcut)
        self.root.bind_all('<Control-v>', self._on_view_report_shortcut)
        
        # Settings and utilities
        self.root.bind_all('<Control-comma>', self._on_settings_shortcut)
        self.root.bind_all('<F5>', self._on_rescan_cameras_shortcut)
        
        # Help
        self.root.bind_all('<Control-h>', self._on_help_shortcut)

    def _is_typing_in_field(self, event):
        """Check if user is currently typing in an input field."""
        focused_widget = self.root.focus_get()
        return isinstance(focused_widget, (tk.Entry, ttk.Entry, ttk.Combobox))

    def _on_record_shortcut(self, event):
        if self._is_typing_in_field(event): return
        if self.record_btn['state'] == 'normal':
            self._start_recording()
        return "break"

    def _on_stop_shortcut(self, event):
        if self.stop_btn['state'] == 'normal':
            self._stop_activity()
        return "break"

    def _on_play_shortcut(self, event):
        if self._is_typing_in_field(event): return
        if self.play_btn['state'] == 'normal':
            self._play_current()
        return "break"

    def _on_analyze_shortcut(self, event):
        if self.analyze_btn['state'] == 'normal':
            self._run_auto_detection()
        return "break"

    def _on_finalize_shortcut(self, event):
        if self.finalize_btn['state'] == 'normal':
            self._finish_test()
        return "break"

    def _on_new_test_shortcut(self, event):
        if self.new_test_btn['state'] == 'normal':
            self._start_new_test()
        return "break"

    def _on_open_test_shortcut(self, event):
        self.open_previous_test()
        return "break"

    def _on_view_report_shortcut(self, event):
        if self.view_report_btn['state'] == 'normal':
            self._view_report()
        return "break"

    def _on_settings_shortcut(self, event):
        self._open_settings_window()
        return "break"

    def _on_rescan_cameras_shortcut(self, event):
        self._rescan_cameras()
        return "break"

    def _on_help_shortcut(self, event):
        self._show_keyboard_shortcuts_help()
        return "break"

    def _show_keyboard_shortcuts_help(self):
        """Display keyboard shortcuts help dialog."""
        help_window = tk.Toplevel(self.root)
        help_window.title("Keyboard Shortcuts")
        help_window.geometry("600x480")
        help_window.resizable(False, False)
        help_window.transient(self.root)
        help_window.grab_set()
        
        main_frame = ttk.Frame(help_window, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame, text="Keyboard Shortcuts", font=("Arial", 16, "bold")).pack(pady=(0, 20))
        
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True)
        
        text_widget = tk.Text(text_frame, wrap="word", font=("Consolas", 10), 
                              bg="white", fg="black", relief="solid", bd=1, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        shortcuts_text = """RECORDING & PLAYBACK
  Spacebar, Ctrl+R      Start recording
  Escape, Ctrl+S        Stop recording or playback
  Enter, Ctrl+P         Play video for current bottle

TEST RESULTS
  F1                    Finalize the test and generate a report
  F3                    Re-run analysis on the current bottle's video

FILE & UTILITIES
  Ctrl+N                Start a new test
  Ctrl+O                Open a previous test
  Ctrl+V                View the generated PDF report
  Ctrl+,                Open the Settings window
  F5                    Rescan for connected cameras
  Ctrl+H                Show this help dialog

TIPS
  • Shortcuts do not work when typing in text fields.
  • Click on the main window if shortcuts are unresponsive.
"""
        
        text_widget.insert("1.0", shortcuts_text)
        text_widget.config(state="disabled")
        
        close_btn = ttk.Button(main_frame, text="Close", command=help_window.destroy)
        close_btn.pack(pady=(15, 0))
        
        help_window.bind('<KeyPress-Escape>', lambda e: help_window.destroy())

    def _switch_bottle_to(self, index):
        if self.playing_video:
            self.playing_video = False
        self.current_bottle_index = index
        self._update_ui_for_bottle()

    def _update_ui_for_bottle(self):
        idx = self.current_bottle_index
        is_any_recording = any(self.bottle_recording)

        for i, btn in enumerate(self.bottle_indicators):
            if is_any_recording:
                btn.config(state="disabled")
                continue

            btn.config(state="normal")
            is_recorded = self.bottle_video_paths[i] is not None
            is_selected = i == idx
            if is_selected:
                btn.config(style="Indicator.Selected.TButton")
            elif is_recorded:
                btn.config(style="Indicator.Recorded.TButton")
            else:
                btn.config(style="Indicator.TButton")

        has_video = self.bottle_video_paths[idx] is not None
        self.play_btn.config(state="normal" if has_video and not self.playing_video else "disabled")
        self.analyze_btn.config(state="normal" if has_video else "disabled")

        code = self.sample_code_var.get().strip()
        can_record = (not self.read_only) and code and (not has_video) and (self.cameras_ready or self.recorder.demo_mode) and (not self.recorder.recording)
        self.record_btn.config(state="normal" if can_record else "disabled")

        can_stop = self.recorder.recording or self.playing_video
        self.stop_btn.config(state="normal" if can_stop else "disabled")

        recorded_indices = [i for i, path in enumerate(self.bottle_video_paths) if path is not None]
        all_recorded_are_analyzed = True
        for i in recorded_indices:
            if self.bottle_analysis_results[i] is None:
                all_recorded_are_analyzed = False
                break
        
        can_finish = len(recorded_indices) > 0 and all_recorded_are_analyzed and not self.read_only
        self.finalize_btn.config(state="normal" if can_finish else "disabled")

        has_report = self.current_pdf_path and os.path.exists(self.current_pdf_path)
        self.view_report_btn.config(state="normal" if has_report else "disabled")

        # Show or hide the override panel
        analysis_res = self.bottle_analysis_results[idx]
        if analysis_res and 'result' in analysis_res and analysis_res['result'] in ('PASS', 'FAIL') and not self.read_only:
            self.override_frame.pack(fill="x", expand=False, pady=(20, 0))
        else:
            self.override_frame.pack_forget()

        if not has_video:
            self._fill_black_preview()
        
        self._update_progress_panel()

    def _update_progress_panel(self):
        idx = self.current_bottle_index
        for i, labels in enumerate(self.progress_status_labels):
            is_recorded = self.bottle_video_paths[i] is not None
            is_selected = i == idx

            status_text = "Recorded" if is_recorded else "Pending"
            status_color = self.BIS_GREEN if is_recorded else self.SECONDARY_GRAY
            font_weight = "bold" if is_selected else "normal"

            labels['name'].config(font=("Arial", 11, font_weight))
            labels['status'].config(text=status_text, foreground=status_color, font=("Arial", 11, font_weight))

            # Update analysis result label
            result_label = self.progress_result_labels[i]
            analysis_result = self.bottle_analysis_results[i]
            if analysis_result:
                res_text = analysis_result['result']
                res_color = self.BIS_GREEN if res_text == "PASS" else self.BIS_RED
                result_label.config(text=res_text, foreground=res_color)
            else:
                result_label.config(text="-", foreground="black")


    def _start_recording(self):
        self.record_btn.config(state="disabled")
        self._begin_actual_recording()

    def _begin_actual_recording(self):
        idx = self.current_bottle_index
        sample_code = self.sample_code_var.get().strip() or f"sample_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        sample_folder = os.path.join(self.current_parent_dir, sample_code)
        os.makedirs(sample_folder, exist_ok=True)

        out_path = os.path.join(sample_folder, f"bottle{idx+1}.avi")
        self.result_var.set(f"Recording Bottle {idx+1}...")
        self.bottle_recording[idx] = True
        self.bottle_analysis_results[idx] = None # Reset previous analysis

        recorder_thread = self.recorder.start(out_path)
        if not recorder_thread:
            messagebox.showerror("Error", "Failed to start recorder.")
            self.bottle_recording[idx] = False
            self._update_ui_for_bottle()
            return

        self._update_ui_for_bottle()

        self.recording_start_time = time.time()
        self._update_recording_ui()

    def _update_recording_ui(self):
        """
        This method runs on the main UI thread and updates the preview,
        progress bar, and countdown at a controlled rate.
        """
        if not self.recorder.recording:
            recorder_thread = self.recorder.get_thread()
            if recorder_thread and recorder_thread.is_alive():
                self.root.after(100, self._update_recording_ui)
                return

            idx = self.current_bottle_index
            self.bottle_recording[idx] = False
            self.bottle_video_paths[idx] = self.recorder.get_output_path()

            self.result_var.set(f"Saved: {os.path.basename(self.recorder.get_output_path())}")
            self.progress_bar.config(value=0)
            self.countdown_var.set("")
            self.playing_video = False
            self._update_ui_for_bottle()
            self._run_auto_detection(bottle_index=idx)
            return

        frame = self.recorder.get_preview()
        if frame is not None:
            self._render_preview(frame)

        elapsed = time.time() - self.recording_start_time
        progress = min(100, (elapsed / constants.MAX_RECORD_SECONDS) * 100)
        remaining = max(0, constants.MAX_RECORD_SECONDS - elapsed)
        countdown_text = f"Time Left: {int(remaining):02d}s"
        
        self.progress_bar.config(value=progress)
        self.countdown_var.set(countdown_text)

        self.root.after(66, self._update_recording_ui)

    def _stop_activity(self):
        if self.recorder.recording:
            self.recorder.stop()
            self.result_var.set("Stopping recording...")
        if self.playing_video:
            self.playing_video = False
            self.result_var.set("Playback stopped.")
        self._update_ui_for_bottle()

    def _play_current(self):
        if self.playing_video:
            return

        idx = self.current_bottle_index
        path = self.bottle_video_paths[idx]
        if not path or not os.path.exists(path):
            messagebox.showerror("Playback Error", "Video file not found. It may have been moved or deleted.")
            self.bottle_video_paths[idx] = None
            self._update_ui_for_bottle()
            return

        if not CV2_AVAILABLE:
            messagebox.showerror("Error", "Cannot play video because OpenCV is not available.")
            return

        self.playing_video = True
        self._update_ui_for_bottle()

        def play_loop():
            cap = None
            try:
                if CV2_AVAILABLE:
                    cap = cv2.VideoCapture(path)
                    if not cap.isOpened():
                        messagebox.showerror("Error", f"Could not open video file:\n{path}")
                        return

                    fps = cap.get(cv2.CAP_PROP_FPS)
                    delay_sec = 1.0 / float(fps if fps and fps > 1 else 30)

                    while self.playing_video:
                        ret, frame = cap.read()
                        if not ret:
                            break
                        try:
                            self.root.after(0, self._render_preview, frame)
                        except Exception:
                            pass
                        time.sleep(delay_sec)
            finally:
                if cap:
                    cap.release()
                self.playing_video = False
                try:
                    self.root.after(0, self._update_ui_for_bottle)
                except Exception:
                    pass

        threading.Thread(target=play_loop, daemon=True).start()

    def _run_auto_detection(self, bottle_index=None):
        if not CV2_AVAILABLE:
            messagebox.showerror("Error", "Cannot run analysis because OpenCV is not available.", parent=self.root)
            return

        idx = bottle_index if bottle_index is not None else self.current_bottle_index
        path = self.bottle_video_paths[idx]
        if not path or not os.path.exists(path):
            messagebox.showerror("Analysis Error", "Video file not found.", parent=self.root)
            return

        self.result_var.set(f"Analyzing Bottle {idx+1}...")
        self.root.config(cursor="watch")
        self.root.update_idletasks()

        def analysis_thread():
            frame_before, frame_after = None, None
            # 1) Try motion-based impact picker
            try:
                frame_before, frame_after = analysis.pick_impact_frames(path)
            except Exception as e:
                # 2) Fallback: first + ~80% frame (original behavior)
                cap = None
                try:
                    cap = cv2.VideoCapture(path)
                    if not cap.isOpened():
                        raise IOError("Cannot open video file")
                    ret, frame_before = cap.read()
                    if not ret:
                        raise ValueError("Cannot read the first frame")
                    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    target_frame_index = int(total_frames * 0.8)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_index)
                    ret, frame_after = cap.read()
                    if not ret:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 2)
                        ret, frame_after = cap.read()
                        if not ret:
                            raise ValueError("Cannot read a frame from the end of the video")
                except Exception as e2:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Analysis Error", f"Failed to read video frames: {e2}", parent=self.root))
                    self.root.after(0, self.root.config, {"cursor": ""})
                    if cap:
                        cap.release()
                    return
                finally:
                    if cap:
                        cap.release()

            # Run the analysis with the selected material type
            material = self.material_var.get()
            result = analysis.analyze_bottle(frame_before, frame_after, material_type=material)
            
            def _update_on_main_thread():
                self.bottle_analysis_results[idx] = result
                self.result_var.set(f"Bottle {idx+1} Analysis: {result.get('result', 'ERROR')}")
                self._update_progress_panel()
                self._update_ui_for_bottle()
                self.root.config(cursor="")

                # If analysis returns an error, show a popup message
                if result.get('result') == 'ERROR':
                    messagebox.showerror("Analysis Error", result.get('reason', 'An unknown error occurred.'), parent=self.root)

                # Check if all bottles are tested and analyzed
                recorded_and_analyzed_count = 0
                for i in range(constants.BOTTLE_COUNT):
                    if self.bottle_video_paths[i] is not None and self.bottle_analysis_results[i] is not None:
                        recorded_and_analyzed_count += 1
                
                if recorded_and_analyzed_count == constants.BOTTLE_COUNT:
                    self.root.after(100, self._prompt_for_finalization)

            self.root.after(0, _update_on_main_thread)

        threading.Thread(target=analysis_thread, daemon=True).start()

    def _prompt_for_finalization(self):
        """Asks the user if they want to finalize the report."""
        if self.read_only:
            return

        if messagebox.askyesno(
            "Finalize Report?",
            "All bottles have been analyzed. Do you want to generate the final report now?\n\n"
            "Select 'No' to review or correct the analysis before finalizing.",
            parent=self.root
        ):
            self._finish_test()

    def _save_frames_for_training(self, bottle_index: int, final_result: str):
        """Extracts and saves before/after frames from a video for AI training."""
        if not CV2_AVAILABLE:
            return

        video_path = self.bottle_video_paths[bottle_index]
        if not video_path or not os.path.exists(video_path):
            return

        cap = None
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened(): return

            # Get the first frame
            ret_before, frame_before = cap.read()

            # Get a frame from near the end
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            target_frame_index = int(total_frames * 0.8)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_index)
            ret_after, frame_after = cap.read()
            if not ret_after:
                cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 2)
                ret_after, frame_after = cap.read()

            if ret_before and ret_after:
                # Create directories
                base_training_dir = os.path.join(constants.BASE_DIR, "training_data")
                result_dir = os.path.join(base_training_dir, final_result.upper())
                os.makedirs(result_dir, exist_ok=True)

                # Create a unique filename
                sample_code = self.sample_code_var.get().strip() or "unknown_sample"
                timestamp = int(time.time())
                base_filename = f"{sample_code}_bottle{bottle_index+1}_{timestamp}"

                # Save individual images
                cv2.imwrite(os.path.join(result_dir, f"{base_filename}_before.png"), frame_before)
                cv2.imwrite(os.path.join(result_dir, f"{base_filename}_after.png"), frame_after)

                # Also save a combined side-by-side image for the training script
                try:
                    h = min(frame_before.shape[0], frame_after.shape[0])
                    w = min(frame_before.shape[1], frame_after.shape[1])
                    fb = cv2.resize(frame_before, (w, h))
                    fa = cv2.resize(frame_after, (w, h))
                    combined = cv2.hconcat([fb, fa])
                    cv2.imwrite(os.path.join(result_dir, f"{base_filename}_combo.png"), combined)
                except Exception as e:
                    print(f"Error saving combined training image: {e}")
                print(f"Saved training images for bottle {bottle_index+1} to {result_dir}")

        except Exception as e:
            print(f"Error saving training frames: {e}")
        finally:
            if cap:
                cap.release()

    def _override_analysis(self, correct_result: str):
        """Corrects an analysis result, adjusts thresholds, and saves training data."""
        idx = self.current_bottle_index
        current_analysis = self.bottle_analysis_results[idx]

        if not current_analysis:
            return

        # --- Save data for AI training ---
        # We do this first, regardless of whether the result is changing.
        self._save_frames_for_training(idx, correct_result)

        if current_analysis.get('result') == correct_result:
            self.result_var.set(f"Result for Bottle {idx+1} confirmed as {correct_result}.")
            return

        # --- The "Learning" Logic ---
        config = utils.load_analysis_config()
        metric = current_analysis.get('metric')
        value = current_analysis.get('value')
        
        if metric and value is not None:
            adjustment_made = False
            # If user corrects FAIL to PASS, the threshold was too sensitive (too low). Increase it.
            if current_analysis.get('result') == 'FAIL' and correct_result == 'PASS':
                if metric == 'deformation':
                    config['deformation_threshold'] = value * 1.1
                    adjustment_made = True
                elif metric == 'spill_area':
                    config['spill_min_area'] = value * 1.1
                    adjustment_made = True
                elif metric == 'shatter_ratio':
                    config['shatter_contour_increase_ratio'] = value * 1.1
                    adjustment_made = True

            # If user corrects PASS to FAIL, the threshold was too lenient (too high). Decrease it.
            elif current_analysis.get('result') == 'PASS' and correct_result == 'FAIL':
                if metric == 'deformation':
                    config['deformation_threshold'] = value * 0.9
                    adjustment_made = True
                elif metric == 'spill_area':
                    config['spill_min_area'] = value * 0.9
                    adjustment_made = True
                elif metric == 'shatter_ratio':
                    config['shatter_contour_increase_ratio'] = value * 0.9
                    adjustment_made = True
            
            if adjustment_made:
                utils.save_analysis_config(config)
                self.result_var.set(f"Thresholds adjusted. Training data saved.")

        # Update the result for the current bottle
        self.bottle_analysis_results[idx]['result'] = correct_result
        self.bottle_analysis_results[idx]['reason'] = f"Manually overridden to {correct_result}"
        
        self._update_progress_panel()
        self._update_ui_for_bottle()

    def _fill_black_preview(self):
        if not NUMPY_AVAILABLE:
            try:
                ph, pw = self.preview_label.winfo_height(), self.preview_label.winfo_width()
                if pw > 2 and ph > 2:
                    img = Image.new("RGB", (pw, ph), (0, 0, 0))
                    photo = ImageTk.PhotoImage(img)
                    self.preview_label.configure(image=photo)
                    self.preview_label.image = photo
            except Exception:
                pass
            return
        
        import numpy as np
        width = self.recorder.width * 2 if self.recorder.width > 0 else 1280
        height = self.recorder.height if self.recorder.height > 0 else 480
        canvas = np.zeros((height, width, 3), dtype=np.uint8)
        self._render_preview(canvas)

    def _render_preview(self, frame_bgr):
        try:
            if frame_bgr is None: return
            
            ph, pw = self.preview_label.winfo_height(), self.preview_label.winfo_width()
            if ph < 2 or pw < 2: return

            if NUMPY_AVAILABLE and isinstance(frame_bgr, sys.modules['numpy'].ndarray):
                h, w, _ = frame_bgr.shape
                scale = min(pw / w, ph / h)
                nw, nh = int(w * scale), int(h * scale)
                if CV2_AVAILABLE:
                    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                else:
                    frame_rgb = frame_bgr
                img = Image.fromarray(frame_rgb).resize((nw, nh), Image.LANCZOS)
            else:
                img = frame_bgr.resize((pw, ph), Image.LANCZOS)

            photo = ImageTk.PhotoImage(img)
            self.preview_label.configure(image=photo)
            self.preview_label.image = photo
        except Exception:
            pass

    def _finish_test(self):
        recorded_indices = [i for i, path in enumerate(self.bottle_video_paths) if path is not None]
        if not recorded_indices:
            messagebox.showwarning("Finalize Error", "No bottles have been recorded yet.", parent=self.root)
            return

        # Determine final result based on individual analyses
        final_result = "PASS"
        for i in recorded_indices:
            analysis_res = self.bottle_analysis_results[i]
            if not analysis_res:
                messagebox.showerror("Finalize Error", f"Bottle {i+1} has not been analyzed yet.", parent=self.root)
                return
            if analysis_res.get('result') == 'FAIL':
                final_result = "FAIL"
                break  # One failure is enough to fail the entire test

        self.date_var.set(datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
        self.result_var.set(final_result)
        try:
            out = self._generate_pdf_report()
            self.current_pdf_path = out
            self.read_only = True
            self._update_ui_for_bottle()
            messagebox.showinfo("Report", f"PDF report generated successfully!\nClick 'View Report' to open.", parent=self.root)
        except Exception as e:
            messagebox.showerror("PDF Error", f"Failed to generate PDF: {e}", parent=self.root)

    def _generate_pdf_report(self):
        if not FPDF_AVAILABLE:
            raise RuntimeError("FPDF library not available.")

        sample_code = self.sample_code_var.get().strip() or f"sample_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        sample_folder = os.path.join(self.current_parent_dir, sample_code)
        os.makedirs(sample_folder, exist_ok=True)

        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        pdf.set_fill_color(0, 51, 102)
        pdf.rect(0, 0, 210, 35, 'F')

        try:
            if hasattr(constants, 'REPORT_LOGO_FILE') and os.path.exists(constants.REPORT_LOGO_FILE):
                pdf.image(constants.REPORT_LOGO_FILE, x=15, y=8, w=30, h=20)
        except Exception as e:
            print(f"Logo embedding error: {e}")

        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 20)
        pdf.set_xy(50, 12)
        pdf.cell(0, 10, "BOTTLE DROP TEST REPORT", ln=False)

        pdf.set_xy(10, 45)
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(240, 248, 255)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Test Details", ln=True, align="L", fill=True)
        pdf.ln(2)

        fields = {
            "Sample Code": self.sample_code_var.get(),
            "IS Number": self.is_number_var.get(),
            "Parameter": self.parameter_var.get(),
            "Department": self.department_var.get(),
            "Bottle Material": self.material_var.get(),
            "Testing Person": self.testing_person_var.get(),
            "Date/Time": self.date_var.get(),
            "Result": self.result_var.get(),
        }

        try:
            metadata_path = os.path.join(sample_folder, "metadata.json")
            with open(metadata_path, "w") as f:
                json.dump(fields, f, indent=2)
        except Exception as e:
            print(f"Could not save metadata.json: {e}")

        for i, (name, value) in enumerate(fields.items()):
            pdf.set_fill_color(248, 249, 250) if i % 2 == 0 else pdf.set_fill_color(255, 255, 255)

            pdf.set_font("Arial", "B", 11)
            pdf.set_text_color(0, 51, 102)
            pdf.cell(50, 10, name + ":", border=1, ln=0, fill=True)

            pdf.set_font("Arial", "", 11)
            if name == "Result":
                rv = str(value).strip().upper()
                if rv == "PASS": pdf.set_text_color(0, 128, 0)
                elif rv == "FAIL": pdf.set_text_color(220, 20, 60)
                else: pdf.set_text_color(0, 0, 0)
                if rv in ("PASS", "FAIL"): pdf.set_font("Arial", "B", 11)
            else:
                pdf.set_text_color(0, 0, 0)

            pdf.cell(0, 10, str(value), border=1, ln=1, fill=True)

        pdf.ln(15)
        pdf.set_font("Arial", "I", 9)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 5, f"Report generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}", ln=True, align="C")
        pdf.set_draw_color(0, 51, 102)
        y = pdf.get_y() + 2
        pdf.line(10, y, 200, y)

        out_path = os.path.join(sample_folder, f"{sample_code}.pdf")
        pdf.output(out_path)
        return out_path

    def _start_new_test(self):
        self.sample_code_var.set("")
        self.result_var.set("")
        self.countdown_var.set("")
        self.progress_bar.config(value=0)
        self.bottle_video_paths = [None] * constants.BOTTLE_COUNT
        self.bottle_analysis_results = [None] * constants.BOTTLE_COUNT
        self.current_bottle_index = 0
        self.current_pdf_path = None
        self.read_only = False
        self.playing_video = False

        for entry in [self.sample_code_entry, self.is_number_entry, self.parameter_entry]:
            entry.config(state="normal")
        self.testing_person_menu.config(state="readonly")
        self.material_menu.config(state="readonly")

        self._update_ui_for_bottle()

    def _view_report(self):
        if not self.current_pdf_path or not os.path.exists(self.current_pdf_path):
            messagebox.showerror("Error", "No report found to view.")
            return
        try:
            sysname = platform.system().lower()
            if sysname == "windows": os.startfile(self.current_pdf_path)
            elif sysname == "darwin": subprocess.run(["open", self.current_pdf_path], check=False)
            else: subprocess.run(["xdg-open", self.current_pdf_path], check=False)
        except Exception:
            messagebox.showinfo("Report Location", f"Report saved at:\n{self.current_pdf_path}")

    def _rescan_cameras(self):
        self.recorder.release()
        w, h = utils.load_video_settings()
        self.cameras_ready = self.recorder.initialize(w, h)
        self._update_ui_for_bottle()
        messagebox.showinfo("Devices", "Cameras have been rescanned.", parent=self.root)

    def _open_settings_window(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("600x400")  # Increased height
        win.resizable(False, True) # Allow vertical resizing
        win.configure(bg=self.SETTINGS_BG)
        win.transient(self.root)
        win.grab_set()

        main_frame = tk.Frame(win, padx=20, pady=20, bg=self.SETTINGS_BG)
        main_frame.pack(fill="both", expand=True)
        main_frame.rowconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)

        dir_frame = tk.LabelFrame(main_frame, text="Save Directory", padx=10, pady=10, bg=self.SETTINGS_BG, fg="black")
        dir_frame.pack(fill="x", pady=(0, 15))

        settings_dir_var = tk.StringVar(value=self.current_parent_dir)
        dir_entry = ttk.Entry(dir_frame, textvariable=settings_dir_var, state="readonly")
        dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        def browse_dir():
            path = filedialog.askdirectory(initialdir=settings_dir_var.get(), parent=win)
            if path:
                settings_dir_var.set(path)

        ttk.Button(dir_frame, text="Browse...", command=browse_dir).pack(side="left")

        # Video settings
        video_frame = tk.LabelFrame(main_frame, text="Video Settings", padx=10, pady=10, bg=self.SETTINGS_BG, fg="black")
        video_frame.pack(fill="x", pady=(0, 15))

        vw, vh = utils.load_video_settings()
        res_var = tk.StringVar(value=f"{vw}x{vh}")

        ttk.Label(video_frame, text="Resolution:", background=self.SETTINGS_BG).pack(side="left")
        res_combo = ttk.Combobox(video_frame, textvariable=res_var, state="readonly",
                                 values=["640x480", "1280x720"])  # can add 1920x1080 later
        res_combo.pack(side="left", padx=10)

        def apply_video_settings():
            sel = res_var.get()
            try:
                sw, sh = sel.split("x")
                w, h = int(sw), int(sh)
                utils.save_video_settings(w, h)
                # Reinitialize cameras with the new resolution immediately
                self._rescan_cameras()
                messagebox.showinfo("Video Settings", f"Resolution set to {w}x{h}.")
            except Exception as e:
                messagebox.showerror("Video Settings", f"Invalid resolution: {sel}")

        ttk.Button(video_frame, text="Apply", command=apply_video_settings).pack(side="left", padx=10)

        persons_frame = tk.LabelFrame(main_frame, text="Testing Persons", padx=10, pady=10, bg=self.SETTINGS_BG, fg="black")
        persons_frame.pack(fill="both", expand=True)
        persons_frame.rowconfigure(0, weight=1)
        persons_frame.columnconfigure(0, weight=1)

        list_frame = tk.Frame(persons_frame, bg=self.SETTINGS_BG)
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        # Changed selectmode to "extended" to allow multiple selections
        listbox = tk.Listbox(list_frame, selectmode="extended", bg="white", fg="black", bd=0, highlightthickness=0)
        for person in self.testing_persons:
            listbox.insert("end", person)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        listbox.config(yscrollcommand=scrollbar.set)
        listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        btn_frame = tk.Frame(persons_frame, bg=self.SETTINGS_BG)
        btn_frame.grid(row=0, column=1, sticky="ns", padx=(10, 0))

        def add_person():
            # Allow adding multiple people at once, separated by commas
            names_str = simpledialog.askstring("Add Person(s)", 
                                               "Enter one or more names, separated by commas:", 
                                               parent=win)
            if names_str:
                names = [name.strip() for name in names_str.split(',') if name.strip()]
                for name in names:
                    listbox.insert("end", name)

        def remove_person():
            # Correctly remove selected items, handling multiple selections
            selected_indices = listbox.curselection()
            if not selected_indices:
                return
            # Iterate backwards to avoid index shifting issues when deleting
            for i in sorted(selected_indices, reverse=True):
                listbox.delete(i)

        ttk.Button(btn_frame, text="Add", command=add_person).pack(pady=2, fill="x")
        ttk.Button(btn_frame, text="Remove", command=remove_person).pack(pady=2, fill="x")

        action_frame = tk.Frame(main_frame, pady=15, bg=self.SETTINGS_BG)
        action_frame.pack(fill="x")

        def save_settings():
            new_dir = settings_dir_var.get()
            if new_dir != self.current_parent_dir:
                self.current_parent_dir = new_dir
                utils.save_directory(new_dir)

            new_persons = list(listbox.get(0, "end"))
            self.testing_persons = new_persons
            utils.save_testing_persons(new_persons)
            self.testing_person_menu['values'] = self.testing_persons
            if self.testing_person_var.get() not in new_persons:
                self.testing_person_var.set(new_persons[0] if new_persons else "")

            win.destroy()

        ttk.Button(action_frame, text="Save & Close", command=save_settings, style="Accent.TButton").pack(side="right", padx=5)
        ttk.Button(action_frame, text="Cancel", command=win.destroy).pack(side="right")

    def open_previous_test(self):
        open_win = tk.Toplevel(self.root)
        open_win.title("Open Previous Test")
        open_win.geometry("900x560")

        search_frame = ttk.Frame(open_win, padding=10)
        search_frame.pack(fill='x')
        ttk.Label(search_frame, text="Search Sample Code:").pack(side='left', padx=5)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side='left', padx=5)

        tree_frame = ttk.Frame(open_win)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        columns = ('Sample Code', 'Date/Time', 'Videos Count', 'Result')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=160)

        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(fill='both', expand=True)

        def load_test_data():
            for item in tree.get_children(): tree.delete(item)
            search_text = search_var.get().lower()
            try:
                for item in os.listdir(self.current_parent_dir):
                    item_path = os.path.join(self.current_parent_dir, item)
                    if not os.path.isdir(item_path): continue
                    if search_text and search_text not in item.lower(): continue
                    
                    # Only include folders created by the app (identified by session markers)
                    marker_files = ("metadata.json", "analysis.json", "report.pdf")
                    if not any(os.path.exists(os.path.join(item_path, m)) for m in marker_files):
                        continue
                    # For display purposes, still count videos and PDFs
                    avis = [f for f in os.listdir(item_path) if f.lower().endswith('.avi')]
                    pdfs = [f for f in os.listdir(item_path) if f.lower().endswith('.pdf')]
                    
                    # Use the modification time of the folder if no videos/PDFs are found
                    if pdfs or avis:
                        any_file = os.path.join(item_path, (pdfs or avis)[0])
                        dt = datetime.fromtimestamp(os.path.getctime(any_file)).strftime('%Y-%m-%d %H:%M')
                    else:
                        dt = datetime.fromtimestamp(os.path.getmtime(item_path)).strftime('%Y-%m-%d %H:%M')
                    result = "Completed" if pdfs else "In Progress"
                    tree.insert('', 'end', values=(item, dt, f"{len(avis)} video(s)", result))
            except Exception as e:
                messagebox.showerror("Error", f"Error loading tests: {str(e)}")

        def open_selected_test():
            if not tree.selection(): return
            sel = tree.selection()[0]
            sample_code = str(tree.item(sel)['values'][0])
            sample_folder = os.path.join(self.current_parent_dir, sample_code)

            if self.recorder.recording: self.recorder.stop()

            self.sample_code_var.set("")
            self.is_number_var.set("")
            self.parameter_var.set("")
            self.result_var.set("")
            self.bottle_video_paths = [None] * constants.BOTTLE_COUNT
            self.bottle_analysis_results = [None] * constants.BOTTLE_COUNT
            self.current_pdf_path = None

            metadata_path = os.path.join(sample_folder, "metadata.json")
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, "r") as f: metadata = json.load(f)
                    self.sample_code_var.set(metadata.get("Sample Code", sample_code))
                    self.is_number_var.set(metadata.get("IS Number", ""))
                    self.parameter_var.set(metadata.get("Parameter", ""))
                    self.department_var.set(metadata.get("Department", "Mechanical"))
                    self.material_var.set(metadata.get("Bottle Material", "Plastic"))
                    self.testing_person_var.set(metadata.get("Testing Person", ""))
                    self.date_var.set(metadata.get("Date/Time", ""))
                    self.result_var.set(metadata.get("Result", "Completed"))
                except Exception as e:
                    print(f"Error loading metadata: {e}")
                    self.sample_code_var.set(sample_code)
                    self.result_var.set("Completed (metadata error)")
            else:
                self.sample_code_var.set(sample_code)
                self.result_var.set("Completed (legacy format)")
                pdfs = [f for f in os.listdir(sample_folder) if f.lower().endswith('.pdf')]
                if pdfs:
                    pdf_path = os.path.join(sample_folder, pdfs[0])
                    self.date_var.set(datetime.fromtimestamp(os.path.getctime(pdf_path)).strftime("%d-%m-%Y %H:%M:%S"))

            for entry in [self.sample_code_entry, self.is_number_entry, self.parameter_entry, self.department_entry]:
                entry.config(state="disabled")
            self.testing_person_menu.config(state="disabled")
            self.material_menu.config(state="disabled")

            for i in range(constants.BOTTLE_COUNT):
                avi = os.path.join(sample_folder, f"bottle{i+1}.avi")
                if os.path.exists(avi): self.bottle_video_paths[i] = avi

            pdfs = [f for f in os.listdir(sample_folder) if f.lower().endswith('.pdf')]
            if pdfs: self.current_pdf_path = os.path.join(sample_folder, pdfs[0])

            open_win.destroy()
            self.read_only = True
            try:
                self.current_bottle_index = next(i for i, v in enumerate(self.bottle_video_paths) if v)
            except StopIteration:
                self.current_bottle_index = 0
            self._update_ui_for_bottle()

        btn_frame = ttk.Frame(open_win, padding=10)
        btn_frame.pack(fill='x')
        search_btn = ttk.Button(btn_frame, text="Search", command=load_test_data)
        search_btn.pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Open Selected", command=open_selected_test, style="Accent.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=open_win.destroy).pack(side="right", padx=5)
        
        search_entry.bind("<Return>", lambda e: load_test_data())
        tree.bind("<Double-1>", lambda e: open_selected_test())
        load_test_data()

    def update_time_loop(self):
        if not self.read_only:
            self.date_var.set(datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
        self.root.after(1000, self.update_time_loop)

    def change_login_credentials(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Change Login Credentials")
        dialog.geometry("450x350")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        main_frame = ttk.Frame(dialog, padding=30)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Change Login Credentials", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20))

        ttk.Label(main_frame, text="Current Password:").grid(row=3, column=0, sticky="w", pady=5)
        current_password_var = tk.StringVar()
        current_password_entry = ttk.Entry(main_frame, textvariable=current_password_var, show="*")
        current_password_entry.grid(row=3, column=1, sticky="ew", pady=5)

        ttk.Label(main_frame, text="New Username:").grid(row=2, column=0, sticky="w", pady=5)
        new_username_var = tk.StringVar(value=utils.load_login_data().get("username", "admin"))
        ttk.Entry(main_frame, textvariable=new_username_var).grid(row=2, column=1, sticky="ew", pady=5)

        ttk.Label(main_frame, text="New Password:").grid(row=4, column=0, sticky="w", pady=5)
        new_password_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=new_password_var, show="*").grid(row=4, column=1, sticky="ew", pady=5)

        def save_credentials():
            current_pw = current_password_var.get().strip()
            new_username = new_username_var.get().strip()
            new_password = new_password_var.get().strip()
            current_data = utils.load_login_data()

            if utils.hash_password(current_pw) != current_data["password_hash"]:
                messagebox.showerror("Error", "Current password is incorrect!", parent=dialog)
                return

            if not new_username or len(new_password) < 4:
                messagebox.showerror("Error", "Username cannot be empty and password must be at least 4 characters.", parent=dialog)
                return

            utils.save_login_data(new_username, new_password)
            messagebox.showinfo("Success", "Login credentials updated successfully!", parent=dialog)
            dialog.destroy()

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=20)
        ttk.Button(btn_frame, text="Update Credentials", command=save_credentials, style="Accent.TButton").pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="left", padx=10)
        current_password_entry.focus_set()

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
            try:
                self.playing_video = False
                self.recorder.release()
            except Exception:
                pass
            try:
                self.root.quit()
                self.root.destroy()
            except Exception:
                pass
            sys.exit(0)