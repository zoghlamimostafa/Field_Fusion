#!/usr/bin/env python3
"""
Test the Hugging Face football-specific YOLO model
Model: uisikdag/yolo-v8-football-players-detection
Classes: ball, goalkeeper, player, referee
"""

import cv2
import numpy as np
import os
import torch

def test_football_model():
    """Test the football-specific model on sample frames"""

    print("=" * 60)
    print("Testing Football-Specific YOLO Model")
    print("=" * 60)

    # Load the model with weights_only=False for older checkpoints
    print("\n🔄 Downloading and loading model from Hugging Face")
    print("   Model: uisikdag/yolo-v8-football-players-detection")
    print("   Expected classes: ball, goalkeeper, player, referee")
    print("   Reported mAP@0.5: 0.785")

    try:
        from huggingface_hub import hf_hub_download

        # Download model weights
        model_path = hf_hub_download(
            repo_id="uisikdag/yolo-v8-football-players-detection",
            filename="best.pt"
        )

        print(f"✅ Model downloaded to: {model_path}")

        # Load with ultralytics directly, setting weights_only=False for compatibility
        from ultralytics import YOLO

        # Temporarily allow unsafe loading for trusted HuggingFace model
        original_weights_only = torch.load.__defaults__
        model = YOLO(model_path)

        print("✅ Model loaded successfully!")

        # Set model parameters
        model.overrides['conf'] = 0.25  # NMS confidence threshold
        model.overrides['iou'] = 0.45   # NMS IoU threshold
        model.overrides['agnostic_nms'] = False  # NMS class-agnostic
        model.overrides['max_det'] = 1000  # Maximum number of detections per image

        print(f"\n📊 Model Info:")
        print(f"   Model type: {type(model.model).__name__}")
        print(f"   Classes: {model.model.names}")

    except Exception as e:
        print(f"❌ Error loading model: {e}")
        import traceback
        traceback.print_exc()
        return None

    # Test on video frames
    video_path = 'input_videos/08fd33_4.mp4'

    if not os.path.exists(video_path):
        print(f"\n❌ Video not found: {video_path}")
        return None

    print(f"\n🎥 Testing on video: {video_path}")

    cap = cv2.VideoCapture(video_path)

    # Test on multiple frames throughout the video
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    test_frame_numbers = [0, total_frames//4, total_frames//2, 3*total_frames//4, total_frames-1]

    print(f"\n📹 Video has {total_frames} frames")
    print(f"   Testing frames: {test_frame_numbers}")

    detection_stats = {
        'player': [],
        'goalkeeper': [],
        'referee': [],
        'ball': [],
        'inference_times': []
    }

    output_dir = 'outputs/detections/football_model_test'
    os.makedirs(output_dir, exist_ok=True)

    for frame_num in test_frame_numbers:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()

        if not ret:
            print(f"⚠️  Could not read frame {frame_num}")
            continue

        print(f"\n--- Frame {frame_num} ---")

        # Run inference
        results = model.predict(frame, verbose=False)

        # Extract detections
        detections = results[0]
        boxes = detections.boxes

        # Count by class
        class_counts = {'player': 0, 'goalkeeper': 0, 'referee': 0, 'ball': 0}

        if boxes is not None and len(boxes) > 0:
            classes = boxes.cls.cpu().numpy().astype(int)
            confidences = boxes.conf.cpu().numpy()

            for cls_id, conf in zip(classes, confidences):
                cls_name = model.model.names[cls_id]
                class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

            # Store stats
            for cls_name in ['player', 'goalkeeper', 'referee', 'ball']:
                detection_stats[cls_name].append(class_counts.get(cls_name, 0))

            detection_stats['inference_times'].append(detections.speed['inference'])

            print(f"   Detections: {len(boxes)} total")
            print(f"   - Players: {class_counts.get('player', 0)}")
            print(f"   - Goalkeepers: {class_counts.get('goalkeeper', 0)}")
            print(f"   - Referees: {class_counts.get('referee', 0)}")
            print(f"   - Ball: {class_counts.get('ball', 0)}")
            print(f"   Average confidence: {np.mean(confidences):.3f}")
            print(f"   Inference time: {detections.speed['inference']:.1f}ms")

            # Draw annotated frame
            annotated = detections.plot()
            output_path = f'{output_dir}/frame_{frame_num:05d}.jpg'
            cv2.imwrite(output_path, annotated)
            print(f"   Saved: {output_path}")
        else:
            print(f"   No detections")
            for cls_name in ['player', 'goalkeeper', 'referee', 'ball']:
                detection_stats[cls_name].append(0)

    cap.release()

    # Print summary statistics
    print("\n" + "=" * 60)
    print("📊 DETECTION SUMMARY")
    print("=" * 60)

    for cls_name in ['player', 'goalkeeper', 'referee', 'ball']:
        counts = detection_stats[cls_name]
        if counts:
            print(f"\n{cls_name.upper()}:")
            print(f"   Average per frame: {np.mean(counts):.1f}")
            print(f"   Min: {np.min(counts)} | Max: {np.max(counts)}")
            print(f"   Detection rate: {sum(1 for c in counts if c > 0) / len(counts) * 100:.1f}%")

    if detection_stats['inference_times']:
        print(f"\nINFERENCE PERFORMANCE:")
        print(f"   Average: {np.mean(detection_stats['inference_times']):.1f}ms")
        print(f"   Min: {np.min(detection_stats['inference_times']):.1f}ms")
        print(f"   Max: {np.max(detection_stats['inference_times']):.1f}ms")
        print(f"   Estimated FPS: {1000 / np.mean(detection_stats['inference_times']):.1f}")

    print("\n" + "=" * 60)
    print("✅ Test complete! Check outputs in:", output_dir)
    print("=" * 60)

    return model

if __name__ == '__main__':
    test_football_model()
