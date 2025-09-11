# AI Development Rules

This document outlines the technology stack and coding conventions for the Bottle Drop Tester application. Adhering to these rules ensures consistency and maintainability.

## Tech Stack

The application is a desktop GUI application built entirely in Python. The key technologies are:

*   **Language:** Python 3.
*   **GUI Framework:** `tkinter` is the core library for the user interface, with `tkinter.ttk` used for modern, themeable widgets. The `ttkthemes` library is optionally used for enhanced styling.
*   **Video & Camera Handling:** OpenCV (`cv2`) is used for all camera detection, video capture, recording, and playback functionalities.
*   **Image Processing:** Pillow (`PIL` fork) is used for loading, resizing, and displaying images within the Tkinter UI.
*   **Numerical Computing:** NumPy is utilized for efficient manipulation of video frame arrays.
*   **PDF Generation:** The `fpdf` library is responsible for creating and saving test reports.
*   **Data Storage:** Simple configuration data (e.g., login credentials, settings) is stored in JSON format using Python's built-in `json` library.
*   **Concurrency:** Python's standard `threading` module is used to run long-running tasks like video recording without freezing the user interface.

## Library Usage Rules

*   **User Interface:**
    *   All UI components must be built using `tkinter` and `tkinter.ttk`.
    *   Prefer `ttk` widgets (e.g., `ttk.Button`, `ttk.Frame`) over standard `tk` widgets for better cross-platform appearance.
    *   UI styling should remain consistent with the established color scheme (e.g., `BIS_BLUE`, `BIS_ORANGE`).

*   **Camera and Video:**
    *   Use **OpenCV (`cv2`)** exclusively for interacting with cameras, reading video files, and writing video files.
    *   Frame manipulation and processing should leverage **NumPy** for performance.

*   **Images:**
    *   Use **Pillow (`PIL`)** for all image-related tasks, such as opening, resizing, and preparing images for display.
    *   Use `ImageTk` from Pillow to integrate images into the Tkinter UI.

*   **Reporting:**
    *   All PDF reports must be generated using the **`fpdf`** library.

*   **Configuration and Data:**
    *   Use the built-in **`json`** module for saving and loading application settings, user lists, and login information. Do not introduce other serialization formats unless necessary.

*   **Asynchronous Operations:**
    *   To prevent the UI from becoming unresponsive, any long-running process (like recording or playing a video) must be executed in a separate thread using the **`threading`** module.
    *   Communication from a background thread to the UI must be done safely using `root.after()`.

*   **File System:**
    *   Use the `os` module for all interactions with the file system (e.g., creating directories, checking paths) to ensure cross-platform compatibility.