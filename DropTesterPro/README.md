# DropTesterPro

A Tkinter desktop app to record dual-camera bottle drop tests, auto-analyze outcomes (PASS/FAIL), and generate PDF reports. Now enhanced with advanced analytics, ML integration, and comprehensive data management.

## Features

### Core Testing Features
- Dual camera recording with automatic side-by-side compositing (demo mode fallback if cameras unavailable)
- Enhanced analysis combining rule-based logic with optional ML predictions
- Confidence scoring and uncertainty analysis for all test results
- Manual override + auto-adjusting thresholds and sample capture for training
- PDF report generation with logos and metadata
- Session browser to reopen prior tests
- Login screen + change credentials
- Keyboard shortcuts and clean UI

### 🆕 Advanced Analytics & Reporting
- **Analytics Dashboard**: Comprehensive statistics and trend analysis
  - Pass/fail rate tracking over time
  - Performance metrics by material type and tester
  - Confidence analysis and method effectiveness
- **Enhanced Data Export**: Multiple export formats (CSV, Excel, JSON, ZIP packages)
- **Performance Reporting**: Automated system performance analysis
- **Failure Pattern Analysis**: Identify common failure modes and trends

### 🆕 Enhanced Analysis Engine
- **Hybrid Analysis**: Combines rule-based and ML approaches with confidence scoring
- **Intelligent Confidence Calibration**: Adaptive confidence thresholds based on analysis type
- **ML Integration**: Optional TensorFlow model integration for improved accuracy
- **Training Data Collection**: Automated collection of samples for model improvement
- **Uncertainty Detection**: Flags low-confidence results for manual review

### 🆕 Advanced Video Analysis Tools
- **Video Analyzer**: Slow-motion replay and frame-by-frame analysis
- **Impact Detection**: Automated and manual impact moment identification
- **Trajectory Tracking**: Object path analysis and measurement tools
- **Deformation Analysis**: Visual measurement and marking tools
- **Export Capabilities**: Export analyzed frames and measurement data

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
- **🆕 Analytics database**: `test_analytics.db` stores all test results and statistics
- **🆕 Enhanced config**: `confidence_calibration.json` for ML and confidence settings

## Enhanced Features Usage

### Analytics Dashboard
Access via **Analytics → Analytics Dashboard** to view:
- Summary statistics and trends
- Material performance breakdown  
- Tester performance metrics
- Failure pattern analysis

### Data Export
Use **Analytics → Export Data** for:
- CSV export with filtering options
- Excel reports with charts and analytics
- JSON data for API integration
- ZIP packages with multiple file formats

### Video Analysis
Access **Analytics → Video Analyzer** to:
- Perform slow-motion replay of test videos
- Mark impact points and deformation areas
- Track object trajectories frame-by-frame
- Export annotated frames and analysis data

### Enhanced Analysis Settings
Configure via **Devices → Enhanced Analysis Settings**:
- ML model usage preferences
- Confidence threshold adjustment
- Analysis method weight tuning
- Training data collection options

## Train the optional model
```powershell
python train_model.py
```
The trained model integrates automatically with the enhanced analysis engine for improved accuracy and confidence scoring.

## Known limitations
- Requires two cameras for recording; otherwise runs in demo mode
- Videos saved as AVI (XVID)
- **🆕 Enhanced**: ML integration now fully operational with confidence scoring
- Video analyzer requires OpenCV for advanced features

## New Dependencies (Optional)
- `openpyxl`: For advanced Excel export features
- `tensorflow`: For ML model integration
- `scikit-learn`: For model training and validation

## License
Proprietary. All rights reserved.
