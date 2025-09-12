#!/usr/bin/env python3
"""
Bottle Drop Tester - Main entry point
"""
import sys
import tkinter as tk

try:
    from ttkthemes import ThemedTk
except ImportError:
    # Fallback in case ttkthemes is not installed
    ThemedTk = tk.Tk

from src.login import show_login
from src.app import BottleTestApp

# ---------- Entry point ----------
if __name__ == "__main__":
    # The login screen must run before the main app's root is created
    if not show_login():
        sys.exit(0)

    # Use a themed window if available
    root = ThemedTk(theme="arc") if 'ThemedTk' in locals() and ThemedTk is not tk.Tk else tk.Tk()
    
    app = BottleTestApp(root)

    # --- Menu Bar ---
    menubar = tk.Menu(root)
    filemenu = tk.Menu(menubar, tearoff=0)
    filemenu.add_command(label="Open Previous Test", command=app.open_previous_test)
    filemenu.add_command(label="Settings", command=app._open_settings_window)
    filemenu.add_separator()
    filemenu.add_command(label="Change Login Credentials", command=app.change_login_credentials)
    filemenu.add_separator()
    filemenu.add_command(label="Exit", command=app.on_closing)
    menubar.add_cascade(label="File", menu=filemenu)

    # Analytics menu
    analytics_menu = tk.Menu(menubar, tearoff=0)
    analytics_menu.add_command(label="Analytics Dashboard", command=app.show_analytics_dashboard)
    analytics_menu.add_command(label="Export Data", command=app.show_export_dialog)
    analytics_menu.add_command(label="Performance Report", command=app.generate_performance_report)
    analytics_menu.add_separator()
    analytics_menu.add_command(label="Video Analyzer", command=app.show_video_analyzer_dialog)
    menubar.add_cascade(label="Analytics", menu=analytics_menu)

    # Optional: Devices menu to rescan cameras at runtime
    devmenu = tk.Menu(menubar, tearoff=0)
    devmenu.add_command(label="Rescan Cameras", command=app._rescan_cameras)
    devmenu.add_command(label="Enhanced Analysis Settings", command=app.show_enhanced_analysis_settings)
    menubar.add_cascade(label="Devices", menu=devmenu)

    root.config(menu=menubar)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()