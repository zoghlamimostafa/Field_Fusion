"""
Jersey Number Recognition System
=================================

Detects and recognizes jersey numbers on football players using:
- Bounding box cropping from player detections
- Image preprocessing for OCR optimization
- Tesseract OCR for digit recognition
- Confidence-based filtering and validation
- Multi-frame consensus for robustness

Based on Tactic Zone approach + additional enhancements.
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
import warnings
warnings.filterwarnings('ignore')

# Optional OCR library
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("⚠️  pytesseract not available. Install with: pip install pytesseract")
    print("⚠️  Also install Tesseract OCR: sudo apt-get install tesseract-ocr")


class JerseyNumberRecognizer:
    """
    Recognizes jersey numbers on football players from video frames
    """

    def __init__(self, min_confidence: float = 0.5):
        """
        Initialize jersey number recognizer

        Args:
            min_confidence: Minimum OCR confidence to accept (0-1 scale)
        """
        self.min_confidence = min_confidence
        self.player_numbers = {}  # player_id -> jersey_number
        self.number_history = defaultdict(list)  # player_id -> [detected_numbers]
        self.confidence_history = defaultdict(list)  # player_id -> [confidence_scores]

        # OCR configuration
        if TESSERACT_AVAILABLE:
            # Configure Tesseract for digit-only recognition
            self.tesseract_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
        else:
            self.tesseract_config = None

    def preprocess_player_crop(self, player_crop: np.ndarray) -> np.ndarray:
        """
        Preprocess player crop for better OCR performance

        Steps:
        1. Focus on upper body (jersey number typically on chest/back)
        2. Convert to grayscale
        3. Apply adaptive thresholding
        4. Enhance contrast
        5. Denoise

        Args:
            player_crop: Cropped image of player

        Returns:
            Preprocessed image ready for OCR
        """
        if player_crop is None or player_crop.size == 0:
            return None

        h, w = player_crop.shape[:2]

        # Focus on upper body (top 40% of bounding box)
        # Jersey numbers are typically on chest (front) or upper back
        upper_body = player_crop[0:int(h * 0.4), :]

        if upper_body.size == 0:
            return None

        # Convert to grayscale
        if len(upper_body.shape) == 3:
            gray = cv2.cvtColor(upper_body, cv2.COLOR_BGR2GRAY)
        else:
            gray = upper_body

        # Resize for better OCR (upscale small images)
        if gray.shape[0] < 100:
            scale_factor = 100 / gray.shape[0]
            gray = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)

        # Apply bilateral filter to reduce noise while preserving edges
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)

        # Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        # Apply adaptive thresholding (works better than global thresholding)
        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # Also try inverted (black text on white background)
        binary_inv = cv2.bitwise_not(binary)

        return binary, binary_inv, enhanced

    def recognize_number_from_crop(
        self,
        player_crop: np.ndarray,
        player_id: int
    ) -> Tuple[Optional[int], float]:
        """
        Recognize jersey number from player crop using OCR

        Args:
            player_crop: Cropped image of player
            player_id: Player track ID

        Returns:
            (jersey_number, confidence) or (None, 0.0) if recognition fails
        """
        if not TESSERACT_AVAILABLE:
            return None, 0.0

        if player_crop is None or player_crop.size == 0:
            return None, 0.0

        try:
            # Preprocess image
            processed = self.preprocess_player_crop(player_crop)
            if processed is None:
                return None, 0.0

            binary, binary_inv, enhanced = processed

            # Try OCR on multiple preprocessed versions
            detected_numbers = []
            confidences = []

            for img in [binary, binary_inv, enhanced]:
                try:
                    # Get OCR data with confidence
                    ocr_data = pytesseract.image_to_data(
                        img,
                        config=self.tesseract_config,
                        output_type=pytesseract.Output.DICT
                    )

                    # Extract text and confidence
                    for i, text in enumerate(ocr_data['text']):
                        conf = int(ocr_data['conf'][i])
                        if text.strip() and conf > 0:
                            # Try to convert to integer
                            try:
                                number = int(text.strip())
                                # Valid jersey numbers: 1-99
                                if 1 <= number <= 99:
                                    detected_numbers.append(number)
                                    confidences.append(conf / 100.0)  # Normalize to 0-1
                            except ValueError:
                                continue
                except Exception as e:
                    continue

            # If we have detections, return the highest confidence one
            if detected_numbers and confidences:
                best_idx = np.argmax(confidences)
                number = detected_numbers[best_idx]
                confidence = confidences[best_idx]

                # Only return if confidence meets threshold
                if confidence >= self.min_confidence:
                    return number, confidence

            return None, 0.0

        except Exception as e:
            print(f"OCR error for player {player_id}: {e}")
            return None, 0.0

    def detect_numbers_in_frame(
        self,
        frame: np.ndarray,
        player_tracks: Dict[int, Dict],
        frame_number: int
    ) -> Dict[int, Tuple[int, float]]:
        """
        Detect jersey numbers for all players in a frame

        Args:
            frame: Video frame
            player_tracks: Dictionary of player tracks {player_id: track_data}
            frame_number: Current frame number

        Returns:
            Dictionary {player_id: (jersey_number, confidence)}
        """
        frame_detections = {}

        for player_id, track in player_tracks.items():
            bbox = track.get('bbox', None)
            if bbox is None:
                continue

            # Crop player from frame
            x1, y1, x2, y2 = map(int, bbox)

            # Add padding
            padding = 10
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(frame.shape[1], x2 + padding)
            y2 = min(frame.shape[0], y2 + padding)

            player_crop = frame[y1:y2, x1:x2]

            # Recognize number
            number, confidence = self.recognize_number_from_crop(player_crop, player_id)

            if number is not None:
                frame_detections[player_id] = (number, confidence)

                # Add to history
                self.number_history[player_id].append(number)
                self.confidence_history[player_id].append(confidence)

        return frame_detections

    def detect_numbers_in_tracks(
        self,
        video_frames: List[np.ndarray],
        tracks: Dict[str, List[Dict]],
        sample_every_n_frames: int = 25
    ) -> Dict[int, int]:
        """
        Detect jersey numbers across all frames using multi-frame consensus

        Args:
            video_frames: List of video frames
            tracks: Tracking data from FootballTracker
            sample_every_n_frames: Process every N frames (default: 25 = 1 sec at 25fps)

        Returns:
            Dictionary {player_id: jersey_number} with final consensus
        """
        print(f"\n🔢 Detecting Jersey Numbers...")

        if not TESSERACT_AVAILABLE:
            print("   ⚠️  Tesseract OCR not available. Skipping jersey number detection.")
            return {}

        total_frames = len(video_frames)
        sample_frames = range(0, total_frames, sample_every_n_frames)

        print(f"   Sampling {len(sample_frames)} frames (every {sample_every_n_frames} frames)")

        for frame_idx in sample_frames:
            if frame_idx >= len(tracks['players']):
                continue

            frame = video_frames[frame_idx]
            player_tracks = tracks['players'][frame_idx]

            # Detect numbers in this frame
            frame_detections = self.detect_numbers_in_frame(frame, player_tracks, frame_idx)

            if frame_detections:
                detected_count = len(frame_detections)
                print(f"   Frame {frame_idx}: Detected {detected_count} numbers", end='\r')

        print()  # New line after progress

        # Calculate consensus from multi-frame detections
        consensus_numbers = self._calculate_consensus()

        print(f"   ✅ Detected {len(consensus_numbers)} unique jersey numbers")

        # Print summary
        if consensus_numbers:
            print("\n   Jersey Number Assignments:")
            for player_id, number in sorted(consensus_numbers.items(), key=lambda x: x[1]):
                detections = len(self.number_history[player_id])
                avg_conf = np.mean(self.confidence_history[player_id]) if self.confidence_history[player_id] else 0
                print(f"      Player ID {player_id:2d} → #{number:2d} ({detections} detections, {avg_conf:.2f} conf)")

        return consensus_numbers

    def _calculate_consensus(self) -> Dict[int, int]:
        """
        Calculate final jersey number for each player using voting

        Uses:
        - Most common number (mode)
        - Weighted by confidence
        - Minimum 3 detections required for consensus

        Returns:
            Dictionary {player_id: jersey_number}
        """
        consensus = {}

        for player_id, numbers in self.number_history.items():
            if len(numbers) < 3:  # Need at least 3 detections for confidence
                continue

            # Weight votes by confidence
            confidences = self.confidence_history[player_id]

            # Count weighted votes
            weighted_votes = defaultdict(float)
            for num, conf in zip(numbers, confidences):
                weighted_votes[num] += conf

            # Get number with highest weighted vote
            if weighted_votes:
                best_number = max(weighted_votes.items(), key=lambda x: x[1])[0]
                consensus[player_id] = best_number

        return consensus

    def assign_numbers_to_tracks(
        self,
        tracks: Dict[str, List[Dict]],
        jersey_numbers: Dict[int, int]
    ) -> Dict[str, List[Dict]]:
        """
        Assign jersey numbers to all tracks

        Args:
            tracks: Original tracking data
            jersey_numbers: Dictionary {player_id: jersey_number}

        Returns:
            Updated tracks with jersey_number field
        """
        print(f"\n🔢 Assigning Jersey Numbers to Tracks...")

        assigned_count = 0

        for frame_idx in range(len(tracks['players'])):
            for player_id, track in tracks['players'][frame_idx].items():
                if player_id in jersey_numbers:
                    track['jersey_number'] = jersey_numbers[player_id]
                    assigned_count += 1
                else:
                    track['jersey_number'] = None

        print(f"   ✅ Assigned {assigned_count} jersey numbers across {len(tracks['players'])} frames")

        return tracks

    def get_player_name_from_number(self, jersey_number: int) -> str:
        """
        Get player name from jersey number (for display purposes)

        Args:
            jersey_number: Jersey number

        Returns:
            Player name string (e.g., "Player #10")
        """
        if jersey_number is None:
            return "Unknown"
        return f"Player #{jersey_number}"

    def export_number_mapping(self, output_path: str):
        """
        Export jersey number mapping to JSON

        Args:
            output_path: Path to save JSON file
        """
        import json

        mapping = {
            'player_id_to_number': self.player_numbers,
            'detection_history': {
                str(pid): {
                    'numbers': list(nums),
                    'confidences': [float(c) for c in self.confidence_history[pid]]
                }
                for pid, nums in self.number_history.items()
            }
        }

        with open(output_path, 'w') as f:
            json.dump(mapping, f, indent=2)

        print(f"✅ Jersey number mapping saved to {output_path}")


def main():
    """Demo jersey number recognition"""
    print("🔢 Jersey Number Recognition System\n")

    if not TESSERACT_AVAILABLE:
        print("❌ Tesseract OCR not available!")
        print("Install with:")
        print("   pip install pytesseract")
        print("   sudo apt-get install tesseract-ocr")
        return

    # Create recognizer
    recognizer = JerseyNumberRecognizer(min_confidence=0.5)

    print("✅ Jersey Number Recognition System initialized")
    print(f"   Min confidence: {recognizer.min_confidence}")
    print(f"   Tesseract config: {recognizer.tesseract_config}")

    # Test Tesseract installation
    try:
        version = pytesseract.get_tesseract_version()
        print(f"   Tesseract version: {version}")
    except Exception as e:
        print(f"   ⚠️  Tesseract check failed: {e}")

    print("\n📝 Usage:")
    print("   from jersey_number_recognizer import JerseyNumberRecognizer")
    print("   recognizer = JerseyNumberRecognizer()")
    print("   jersey_numbers = recognizer.detect_numbers_in_tracks(video_frames, tracks)")
    print("   tracks = recognizer.assign_numbers_to_tracks(tracks, jersey_numbers)")


if __name__ == "__main__":
    main()
