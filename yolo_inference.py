"""
YOLO Inference Module
Simple script to test YOLO model on video input with proper error handling
"""
import os
import sys
from pathlib import Path
from ultralytics import YOLO


def run_yolo_inference(model_path='models/best.pt', video_path='input_videos/08fd33_4.mp4', save_results=True):
    """
    Run YOLO inference on a video file with comprehensive error handling

    Args:
        model_path (str): Path to the YOLO model file
        video_path (str): Path to the input video
        save_results (bool): Whether to save prediction results

    Returns:
        results: YOLO prediction results, or None if error occurred
    """
    try:
        # Validate model file exists
        if not os.path.exists(model_path):
            print(f"Error: Model file not found at '{model_path}'")
            print("Please ensure the model file exists or provide correct path")
            return None

        # Validate video file exists
        if not os.path.exists(video_path):
            print(f"Error: Video file not found at '{video_path}'")
            print("Please ensure the video file exists or provide correct path")
            return None

        # Load YOLO model
        print(f"Loading YOLO model from: {model_path}")
        model = YOLO(model_path)

        # Run inference
        print(f"Running inference on: {video_path}")
        results = model.predict(video_path, save=save_results)

        if not results:
            print("Warning: No results returned from model prediction")
            return None

        # Display results
        print("\n" + "="*60)
        print("YOLO Inference Results")
        print("="*60)
        print(f"\nFirst frame results:\n{results[0]}")

        print("\n" + "-"*60)
        print("Detected boxes:")
        print("-"*60)

        for i, box in enumerate(results[0].boxes):
            print(f"Box {i+1}: {box}")

        print("\n" + "="*60)
        print(f"Total detections: {len(results[0].boxes)}")
        print("="*60 + "\n")

        return results

    except ImportError as e:
        print(f"Error: Failed to import required module: {e}")
        print("Please ensure ultralytics is installed: pip install ultralytics")
        return None

    except Exception as e:
        print(f"Error during YOLO inference: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    # Run inference with default or command-line arguments
    if len(sys.argv) > 1:
        model_path = sys.argv[1] if len(sys.argv) > 1 else 'models/best.pt'
        video_path = sys.argv[2] if len(sys.argv) > 2 else 'input_videos/08fd33_4.mp4'
    else:
        model_path = 'models/best.pt'
        video_path = 'input_videos/08fd33_4.mp4'

    results = run_yolo_inference(model_path, video_path)

    if results is None:
        print("\nInference failed. Please check the errors above.")
        sys.exit(1)
    else:
        print("\nInference completed successfully!")
        sys.exit(0)
