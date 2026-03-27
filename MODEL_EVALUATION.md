# Football Model Evaluation Report

## Overview

This document compares the **generic YOLOv8n** model (currently in use) with the **football-specific YOLOv8** model from Hugging Face for the Tunisia Football AI SaaS project.

---

## Model Comparison

### 1. Generic YOLOv8n (Current System)

**Model:** `yolov8n.pt` (pretrained COCO)
**Size:** 6.3 MB
**Source:** Ultralytics official

**Detected Classes:**
- `person` (mapped to `player`)
- `sports ball` (mapped to `ball`)
- 78 other COCO classes (car, chair, truck, etc.)

**Performance on Demo Video:**
- **Average detections per frame:** 28-35 persons
- **Ball detection rate:** ~40% (intermittent)
- **Inference time:** 35-60ms per frame (~17-28 FPS on CPU)
- **Issues:**
  - No goalkeeper/referee distinction
  - Detects irrelevant objects (cars, chairs, benches)
  - Ball detection is unreliable
  - Manual class mapping required

---

### 2. Football-Specific YOLOv8 (Hugging Face)

**Model:** `uisikdag/yolo-v8-football-players-detection`
**Reported mAP@0.5:** 0.785
**Source:** [Hugging Face](https://huggingface.co/uisikdag/yolo-v8-football-players-detection)

**Detected Classes:**
- `player` (0)
- `goalkeeper` (1)
- `referee` (2)
- `ball` (3)

**Performance on Demo Video (5 frames tested):**
- **Players:** 19.8 avg per frame (100% detection rate)
- **Goalkeepers:** 0.8 avg per frame (80% detection rate)
- **Referees:** 2.8 avg per frame (100% detection rate)
- **Ball:** 0.2 avg per frame (20% detection rate)
- **Average confidence:** 0.82
- **Inference time:** 105-193ms per frame (~5-10 FPS on CPU)
- **Total detections:** 22-25 per frame

**Advantages:**
- ✅ Direct football-specific detection
- ✅ Distinguishes goalkeepers from field players
- ✅ Identifies referees separately
- ✅ Higher detection confidence (0.82 avg)
- ✅ Fewer false positives (no cars, chairs, etc.)
- ✅ No class mapping needed

**Disadvantages:**
- ❌ Slower inference (2-3x slower than generic model)
- ❌ Ball detection still unreliable (20% vs 40%)
- ❌ Older model architecture (requires PyTorch workarounds)
- ❌ Not optimized for Tunisia-specific footage

---

## Test Results Summary

### Frame-by-Frame Analysis

| Frame | Players | Goalkeepers | Referees | Ball | Confidence | Inference (ms) |
|-------|---------|-------------|----------|------|------------|----------------|
| 0     | 20      | 1           | 3        | 1    | 0.817      | 192.8          |
| 187   | 20      | 1           | 2        | 0    | 0.801      | 121.1          |
| 375   | 19      | 0           | 3        | 0    | 0.822      | 104.6          |
| 562   | 20      | 1           | 3        | 0    | 0.827      | 107.8          |
| 749   | 20      | 1           | 3        | 0    | 0.821      | 116.4          |
| **Avg** | **19.8** | **0.8** | **2.8** | **0.2** | **0.822** | **128.5** |

---

## Recommendations

### Phase 1 Decision: Which Model to Use for MVP?

**Option A: Keep Generic YOLOv8n**
- ✅ Faster (2-3x)
- ✅ Works with current codebase
- ✅ Better ball detection
- ❌ No goalkeeper/referee distinction
- ❌ More false positives

**Option B: Switch to Football-Specific Model**
- ✅ Better semantic understanding
- ✅ Clean detections (no irrelevant objects)
- ✅ Referee/goalkeeper separation
- ❌ Slower performance
- ❌ Still poor ball detection

**Option C: Hybrid Approach** ⭐ **RECOMMENDED**
- Use **football-specific model** for player/goalkeeper/referee detection
- Add a **specialized ball detector** (lighter, focused model)
- This gives you:
  - Clean, football-specific detections
  - Goalkeeper distinction (critical for analytics)
  - Better ball tracking with dedicated detector

### Immediate Next Steps

Based on your roadmap **Phase 1-2**, here's what to do:

1. ✅ **COMPLETED:** Test football-specific model *(done)*

2. **Integrate football-specific model into existing pipeline** *(next)*
   - Update `trackers/tracker.py` to use the new model
   - Remove class mapping logic (player/goalkeeper/referee are native)
   - Keep ByteTrack tracking (already working)

3. **Address ball detection weakness**
   - Option 1: Train custom ball detector on football footage
   - Option 2: Use optical flow + motion detection for ball
   - Option 3: Ensemble approach (multiple detectors)

4. **Pitch calibration** (Phase 5 from roadmap)
   - This is more important than perfect ball detection
   - Enables real distance/speed metrics
   - Required for heatmaps and tactical analysis

5. **Tunisia dataset collection** (Phase 7 from roadmap)
   - Collect 10-20 Tunisian match videos
   - Label with football-specific classes
   - Fine-tune the Hugging Face model
   - This will be your competitive advantage

---

## Performance Analysis

### Generic YOLOv8n
```
Inference: 35-60ms → 17-28 FPS
Pros: Fast enough for real-time
Cons: Low semantic accuracy
```

### Football-Specific YOLOv8
```
Inference: 105-193ms → 5-10 FPS
Pros: High semantic accuracy
Cons: Too slow for smooth real-time (need optimization)
```

### Speed Optimization Strategies

If you choose the football-specific model:

1. **Model quantization** (INT8)
   - Can achieve 2-3x speedup
   - Target: ~50-70ms inference

2. **GPU acceleration**
   - Your system has CUDA capability
   - Update NVIDIA drivers (currently too old)
   - Expected: 10-20ms inference on GPU

3. **TensorRT optimization**
   - Export to TensorRT engine
   - Can achieve 5-10x speedup on NVIDIA GPUs

4. **Frame skipping for non-critical objects**
   - Detect players every frame
   - Detect referee every 5 frames
   - Reduces computational load

---

## Critical Issue: Ball Detection

**Both models struggle with ball detection:**

| Model | Ball Detection Rate |
|-------|---------------------|
| Generic YOLOv8n | ~40% |
| Football-Specific | ~20% |

**Why ball detection is hard:**
- Small object (low pixel count)
- Fast movement (motion blur)
- Occlusion by players
- Similar color to pitch markings

**Solutions (in order of priority):**

1. **Temporal consistency** (use tracking)
   - Even if detected 20% of frames, tracking can interpolate
   - ByteTrack already handles this

2. **Custom ball detector**
   - Train YOLOv8-nano on just ball detection
   - Use higher resolution input (1280 vs 640)
   - Focus on center field (where ball spends most time)

3. **Motion-based ball detection**
   - Use optical flow to detect fast-moving objects
   - Combine with size/shape filters
   - Fallback when ML detection fails

4. **Multi-model ensemble**
   - Run 2-3 different ball detectors
   - Vote/average results
   - Increases reliability

---

## Next Steps for Tunisia SaaS

### Week 1: Model Integration
- [ ] Integrate football-specific model into `trackers/tracker.py`
- [ ] Test on full video (not just 5 frames)
- [ ] Measure end-to-end performance
- [ ] Update Gradio interface to show goalkeeper/referee stats

### Week 2: Performance Optimization
- [ ] Update NVIDIA drivers for GPU acceleration
- [ ] Export model to ONNX/TensorRT
- [ ] Benchmark GPU vs CPU performance
- [ ] Optimize inference pipeline

### Week 3: Pitch Calibration
- [ ] Implement pitch line detection
- [ ] Build homography estimation
- [ ] Map player positions to top-down view
- [ ] Enable distance/speed calculations

### Week 4: Tunisia Dataset
- [ ] Collect 10 Tunisian match videos
- [ ] Extract and label 1000 frames
- [ ] Fine-tune football model on Tunisia data
- [ ] Evaluate improvement

---

## Conclusion

The **football-specific YOLOv8 model is a significant upgrade** for semantic understanding, despite being slower. For a Tunisia-focused SaaS:

1. **Use the football-specific model** as your baseline
2. **Optimize for speed** (GPU, quantization, TensorRT)
3. **Fine-tune on Tunisia footage** for local advantage
4. **Add specialized ball detector** to solve detection weakness
5. **Implement pitch calibration** to unlock real metrics

This approach follows your roadmap and positions the product for Tunisia market differentiation.

---

## Files Generated

- **Test script:** `test_football_model_v3.py`
- **Detection outputs:** `outputs/detections/football_model_test/frame_*.jpg`
- **Model cache:** `~/.cache/huggingface/hub/models--uisikdag--yolo-v8-football-players-detection/`

---

**Date:** 2026-03-26
**Tested by:** Claude Code
**Model Source:** [Hugging Face - uisikdag/yolo-v8-football-players-detection](https://huggingface.co/uisikdag/yolo-v8-football-players-detection)
