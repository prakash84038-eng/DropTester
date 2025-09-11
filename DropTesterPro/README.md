# DropTesterPro

A Tkinter desktop app to record dual-camera bottle drop tests, auto-analyze outcomes (PASS/FAIL), and generate PDF reports. Optional training pipeline provided for future ML classification.

## Features
- Dual camera recording with automatic side-by-side compositing (demo mode fallback if cameras unavailable)
- Simple rule-based analysis for deformation/shatter/spill
- Manual override + auto-adjusting thresholds and sample capture for training
- PDF report generation with logos and metadata
- Session browser to reopen prior tests
- Login screen + change credentials
- Keyboard shortcuts and clean UI

## Quick start
1. Create a virtual environment and install dependencies
```powershell
python -m venv .venv ; .\.venv\Scripts\Activate.ps1 ; pip install -r requirements.txt
```
2. Run the app
```powershell
python main.py
```
3. Default login
- Username: `admin`
- Password: `1234`

## Data & outputs
- Videos and PDFs saved under the directory chosen in Settings (default Desktop)
- Config files at project root: `analysis_config.json`, `directory.json`, `login.json`, `testing_persons.json`
- Training images saved under `training_data/PASS|FAIL`

## Train the optional model
```powershell
python train_model.py
```
Note: The app currently uses rule-based analysis. The training script is exploratory.

## Known limitations
- Requires two cameras for recording; otherwise runs in demo mode
- Videos saved as AVI (XVID)
- Basic spill/deformation heuristics; ML integration not wired into the app yet

## License
Proprietary. All rights reserved.
