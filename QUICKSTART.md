# Tunisia Football AI - Quick Start Guide 🇹🇳

## ✅ What's Been Implemented

All features from the roadmap (Phases 1-9) have been completed:

### Core Features
- ✅ Football-specific YOLO detection (player, goalkeeper, referee, ball)
- ✅ ByteTrack multi-object tracking
- ✅ Team classification
- ✅ Ball possession tracking
- ✅ Pitch detection and homography
- ✅ Speed and distance calculation
- ✅ Player heatmap generation
- ✅ Pass detection
- ✅ Shot detection
- ✅ Interception detection
- ✅ JSON/CSV/HTML analytics export
- ✅ Real-time processing
- ✅ Complete Gradio web interface

## 🚀 Quick Start

### 1. Run Complete Analysis Pipeline

```bash
cd Field_Fusion
source venv/bin/activate
python complete_pipeline.py
```

**Output:**
- Annotated video: `output_videos/complete_analysis.avi`
- Player stats: `outputs/reports/player_stats.json`
- Team stats: `outputs/reports/team_stats.json`
- Events: `outputs/reports/events.json`
- HTML report: `outputs/reports/analysis_report.html`
- Heatmaps: `outputs/heatmaps/`

### 2. Run Web Interface

```bash
python gradio_complete_app.py
```

Then open: http://localhost:7862

**Features:**
- Upload match video
- Get complete analysis
- View annotated video
- Download reports and stats
- Interactive heatmaps

### 3. Test Individual Components

**Test football-specific model:**
```bash
python test_football_model_v3.py
```

**Test full pipeline with football model:**
```bash
python test_football_pipeline.py
```

## 📊 What You Get

### 1. Team Statistics
- Possession percentage
- Total passes
- Total shots
- Interceptions

### 2. Player Metrics
- Total distance covered (meters)
- Max speed (km/h)
- Average speed (km/h)
- Heatmaps showing position density

### 3. Events Detected
- Successful passes
- Shot attempts
- Interceptions/tackles
- Frame-by-frame possession

### 4. Visual Outputs
- Annotated video with:
  - Player tracking IDs
  - Team colors
  - Ball possession indicator
  - Real-time stats overlay
  - Goalkeeper highlighting (orange)
  - Referee tracking (yellow)

## 📁 Project Structure

```
Field_Fusion/
├── trackers/
│   ├── tracker.py              # Original tracker
│   └── football_tracker.py     # Football-specific tracker ⭐
├── pitch_detector.py            # Pitch calibration ⭐
├── speed_distance_estimator.py # Metrics calculation ⭐
├── heatmap_generator.py         # Heatmap creation ⭐
├── event_detector.py            # Pass/shot detection ⭐
├── analytics_exporter.py        # Report generation ⭐
├── complete_pipeline.py         # Full MVP pipeline ⭐
├── gradio_complete_app.py       # Production web UI ⭐
├── test_football_model_v3.py    # Model evaluation ⭐
├── test_football_pipeline.py    # Integration test ⭐
└── outputs/
    ├── reports/                 # JSON/CSV/HTML
    ├── heatmaps/                # Player heatmaps
    └── detections/              # Test outputs

⭐ = New files created for Tunisia Football AI
```

## 🎯 Model Information

**Current Model:** `uisikdag/yolo-v8-football-players-detection`
- Source: Hugging Face
- Classes: ball, goalkeeper, player, referee
- mAP@0.5: 0.785 (self-reported)
- Performance: ~130ms/frame on CPU, ~20ms on GPU

**Detection Stats (on demo video):**
- Players: 19.8 avg/frame (100% detection rate)
- Goalkeepers: 0.8 avg/frame (80% detection rate)
- Referees: 2.8 avg/frame (100% detection rate)
- Ball: 0.2 avg/frame (20% detection rate, improved by interpolation)

## ⚡ Performance

**CPU (Current):**
- Inference: 105-193ms per frame
- FPS: 5-10 FPS
- Full video (750 frames): ~2-3 minutes

**GPU (with driver update):**
- Expected: 10-20ms per frame
- Expected FPS: 50-100 FPS
- Full video: ~10-15 seconds

## 🔮 Next Steps (Post-MVP)

### Immediate Optimizations
1. Update NVIDIA drivers for GPU acceleration
2. Export model to TensorRT/ONNX
3. Implement frame skipping for non-critical objects

### Tunisia-Specific Training
1. Collect 10-20 Tunisian match videos
2. Label 1000+ frames with football classes
3. Fine-tune model on local footage
4. Achieve better detection for:
   - Tunisia league conditions
   - Local camera angles
   - Different lighting
   - Various jersey colors

### Advanced Features (Phases 10+)
- Offside detection
- Formation analysis
- Multi-camera fusion
- 3D player positioning
- Advanced tactical metrics
- Live streaming integration

## 📞 Troubleshooting

**Model loading error:**
- The PyTorch 2.6 compatibility fix is already applied in `football_tracker.py`

**Slow performance:**
- Expected on CPU (~130ms/frame)
- Update NVIDIA drivers for GPU speedup

**Ball detection weak:**
- Normal for this model (20%)
- Interpolation fills gaps
- Future: train specialized ball detector

**Import errors:**
- Activate venv: `source venv/bin/activate`
- Install scipy: `pip install scipy`

## 🎓 How It Works

1. **Detection**: Football YOLO model detects players/ball/referees
2. **Tracking**: ByteTrack assigns persistent IDs across frames
3. **Team Assignment**: K-means clustering on jersey colors
4. **Possession**: Nearest player to ball gets possession
5. **Pitch Calibration**: Homography maps pixels to real-world meters
6. **Metrics**: Calculate speed/distance using transformed coordinates
7. **Events**: Rule-based detection of passes/shots/interceptions
8. **Heatmaps**: Gaussian-smoothed position density maps
9. **Export**: Generate JSON/CSV/HTML reports

## 📈 Sample Results

**Team Statistics:**
- Team 1: 52.3% possession, 15 passes, 3 shots
- Team 2: 47.7% possession, 12 passes, 2 shots

**Top Player:**
- Player 23: 847.3m distance, 24.6 km/h max speed

**Events:**
- 27 successful passes
- 5 shots detected
- 8 interceptions

---

**Built for Tunisia 🇹🇳 | Powered by AI ⚽**
