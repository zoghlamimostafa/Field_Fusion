# 🎯 Video Upload Dashboard - Complete Guide

## ✨ NEW FEATURE: Upload & Analyze Dashboard

I've created a beautiful input form dashboard where you can upload new match videos and start AI analysis with just a few clicks!

---

## 🚀 Quick Start

### Launch the Upload Dashboard:

```bash
cd "/media/sda2/coding projet/football/Field_Fusion"
python3 upload_server.py
```

**Access at:** http://localhost:5000

---

## 📊 What You Can Do

### 1. **Upload Match Videos**
- Drag & drop or click to browse
- Supported formats: MP4, AVI, MOV, MKV
- Max file size: 500MB
- Real-time file validation

### 2. **Configure Match Details**
- Match name (e.g., "Elite United vs Club Africain")
- Match date
- Team 1 name (with green color)
- Team 2 name (with blue color)

### 3. **Select Analysis Options**
Choose what you want to analyze:
- ✅ Formation Detection
- ✅ Player Fatigue Analysis
- ✅ Pass Network Analysis
- ✅ Pressing & Defensive Metrics
- ✅ Match Events Detection
- ✅ Player Heatmaps

### 4. **Track Progress**
Real-time progress tracking with 4 steps:
1. Video Processing
2. Player & Ball Tracking
3. Tactical Analysis
4. Generating Reports

### 5. **View Results**
Once complete, navigate to the dashboard to see:
- All statistics and metrics
- Interactive visualizations
- Download PDF reports
- Watch annotated video

---

## 🎨 Dashboard Features

### Upload Zone
- **Drag & Drop:** Simply drag your video file into the upload area
- **Click to Browse:** Or click to select from your files
- **Live Preview:** See file name and size before uploading
- **Validation:** Automatic format and size checking

### Match Details Form
```
┌─────────────────────────────────────────┐
│ Match Name:  [Elite United vs...]       │
│ Match Date:  [2026-03-28]              │
│                                          │
│ Team 1: [Home Team]  (Green)           │
│ Team 2: [Away Team]  (Blue)            │
└─────────────────────────────────────────┘
```

### Analysis Options (All Checked by Default)
- Formation Detection
- Player Fatigue Analysis
- Pass Network Analysis
- Pressing & Defensive Metrics
- Match Events Detection
- Player Heatmaps

### Progress Tracking
```
╔══════════════════════════════════════╗
║  Analysis in Progress                ║
╠══════════════════════════════════════╣
║  1. Video Processing       [████████] 100% ✓ Complete   ║
║  2. Player Tracking        [████████] 100% ✓ Complete   ║
║  3. Tactical Analysis      [█████···] 65%  Processing...║
║  4. Generating Reports     [········] 0%   Waiting...   ║
╚══════════════════════════════════════╝
```

### Console Output
Real-time log display:
```
> Initializing analysis...
> Processing Video Processing...
> ✓ Video Processing complete
> Processing Player & Ball Tracking...
```

---

## 🔗 Integration with Main Dashboard

### Navigation
The upload dashboard and main dashboard are linked:

**Upload Dashboard → Main Dashboard:**
- "View Dashboard" button in top nav
- "View Dashboard" button after analysis completes

**Main Dashboard → Upload Dashboard:**
- "Upload Video" button in top nav

### Workflow
```
1. Upload Video (dashboard_upload.html)
         ↓
2. Configure & Start Analysis
         ↓
3. Track Progress (real-time)
         ↓
4. Analysis Complete → Generate PDFs
         ↓
5. View Results (coach_dashboard_full.html)
```

---

## 🛠️ Technical Details

### Backend Server (upload_server.py)

**Framework:** Flask with CORS support

**API Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/upload` | POST | Upload video file |
| `/api/analyze` | POST | Start analysis pipeline |
| `/api/status/<pid>` | GET | Check analysis status |
| `/api/recent` | GET | Get recent analyses |
| `/api/generate-pdfs` | POST | Generate PDF reports |

**File Structure:**
```
Field_Fusion/
├── dashboard_upload.html       ← Upload interface
├── upload_server.py           ← Backend API
├── input_videos/              ← Uploaded videos
│   ├── 20260328_120000_match.mp4
│   └── 20260328_120000_metadata.json
└── outputs/                   ← Analysis results
    ├── gradio_reports/
    └── *.pdf
```

**Metadata Format:**
```json
{
  "match_name": "Elite United vs Club Africain",
  "match_date": "2026-03-28",
  "team1_name": "Elite United",
  "team2_name": "Club Africain",
  "video_file": "20260328_120000_match.mp4",
  "upload_time": "20260328_120000",
  "options": {
    "formation": true,
    "fatigue": true,
    "passing": true,
    "pressing": true,
    "events": true,
    "heatmap": true
  }
}
```

---

## 📋 File Upload Process

### Step-by-Step:

1. **User selects video file**
   - Validates format (MP4, AVI, MOV, MKV)
   - Validates size (< 500MB)
   - Shows file info

2. **User fills match details**
   - Match name
   - Date
   - Team names

3. **User selects analysis options**
   - All checked by default
   - Can uncheck to skip certain analyses

4. **User clicks "Start AI Analysis"**
   - File uploads to `input_videos/`
   - Metadata saves as JSON
   - Analysis pipeline starts

5. **Progress tracking**
   - 4-step visual progress bars
   - Console output log
   - Real-time status updates

6. **Analysis completes**
   - Success message displays
   - "View Dashboard" button appears
   - Generated files listed

7. **User views results**
   - Navigate to main dashboard
   - All data automatically loaded
   - PDF reports available for download

---

## 🎯 Use Cases

### Pre-Season Analysis
1. Upload training match footage
2. Analyze player performance
3. Identify formation patterns
4. Review fatigue levels

### Match Day Preparation
1. Upload opponent's previous match
2. Analyze their tactics
3. Study pressing patterns
4. Prepare counter-strategies

### Post-Match Review
1. Upload match video
2. Complete analysis
3. Generate PDF reports
4. Share with coaching staff

### Player Development
1. Upload specific player footage
2. Track performance over time
3. Monitor fatigue and workload
4. Plan training adjustments

---

## 💡 Features Highlights

### User Experience
- ✅ Drag & drop file upload
- ✅ Real-time validation
- ✅ Progress tracking with animations
- ✅ Console output display
- ✅ Success confirmation
- ✅ Recent analyses list

### Visual Design
- ✅ Dark theme with football colors
- ✅ Green/Blue team color coding
- ✅ Smooth animations
- ✅ Material Design icons
- ✅ Responsive layout
- ✅ Professional typography

### Functionality
- ✅ File format validation
- ✅ Size limit enforcement
- ✅ Metadata storage
- ✅ Analysis options
- ✅ Background processing
- ✅ Status monitoring

---

## 🔄 Complete Workflow Example

### Upload New Match:

```bash
# 1. Start upload server
python3 upload_server.py

# 2. Open browser
http://localhost:5000

# 3. Upload video
- Drag "match_video.mp4" to upload zone
- Fill: Match Name = "Tunisia vs Algeria"
- Fill: Date = "2026-03-28"
- Fill: Team 1 = "Tunisia"
- Fill: Team 2 = "Algeria"
- Select analysis options
- Click "Start AI Analysis"

# 4. Wait for completion (shown in progress bars)

# 5. Generate PDFs
# (Automatically done or click generate)

# 6. View dashboard
http://localhost:8081

# 7. Download reports
- Click PDF download buttons
```

---

## 🚀 Launch Instructions

### Option 1: Upload Dashboard + Main Dashboard

**Terminal 1:**
```bash
cd "/media/sda2/coding projet/football/Field_Fusion"
python3 upload_server.py
# Access upload at: http://localhost:5000
```

**Terminal 2:**
```bash
cd "/media/sda2/coding projet/football/Field_Fusion"
python3 launch_dashboard.py
# Access dashboard at: http://localhost:8081
```

### Option 2: Upload Only
```bash
python3 upload_server.py
# Upload + analysis at: http://localhost:5000
```

---

## 📦 Dependencies

The upload server requires:
```bash
pip install flask flask-cors psutil
```

Already installed in your venv:
- ✅ Flask (web framework)
- ✅ Flask-CORS (cross-origin requests)
- ✅ PSutil (process monitoring)

---

## 🎨 Color Scheme

| Element | Color | Usage |
|---------|-------|-------|
| Primary | #6dfe9c (Green) | Team 1, Success, CTA buttons |
| Secondary | #7799ff (Blue) | Team 2, Info |
| Tertiary | #ffb148 (Orange) | Processing, Warnings |
| Error | #ff716c (Red) | Errors, Cancel |
| Surface | #0e0e0e (Dark) | Background |

---

## ✅ Features Checklist

- [x] Drag & drop file upload
- [x] File format validation
- [x] File size validation
- [x] Match details form
- [x] Team name inputs
- [x] Analysis options checkboxes
- [x] Start analysis button
- [x] Progress tracking (4 steps)
- [x] Console output display
- [x] Success screen
- [x] Recent analyses list
- [x] Navigation to main dashboard
- [x] Backend API server
- [x] File upload handling
- [x] Metadata storage
- [x] Analysis pipeline trigger
- [x] PDF generation
- [x] Status monitoring

**Total: 17/17 Features ✅**

---

## 🎉 Summary

**YES - The Input Form Dashboard is Complete!**

✅ Beautiful upload interface
✅ Drag & drop file handling
✅ Match details configuration
✅ Analysis options selection
✅ Real-time progress tracking
✅ Backend API server
✅ Integration with main dashboard
✅ Automated pipeline execution
✅ PDF report generation
✅ Recent analyses tracking

**Files Created:**
- `dashboard_upload.html` - Frontend upload interface
- `upload_server.py` - Backend API server
- Navigation links in main dashboard

**Access:**
- Upload: http://localhost:5000
- Dashboard: http://localhost:8081

🚀 **Ready to upload and analyze new matches!**
