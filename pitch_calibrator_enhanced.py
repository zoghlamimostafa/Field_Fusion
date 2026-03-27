#!/usr/bin/env python3
"""
Enhanced Pitch Calibrator - Week 1, Day 1-2
CRITICAL #1 Priority for Tunisia Football AI Level 3

Features:
- Keypoint detection (corners, penalty boxes, center circle)
- Multi-frame calibration for robustness
- Tactical zone mapping (defensive/middle/attacking thirds)
- Confidence scoring for homography quality
"""

import cv2
import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple, Optional


class EnhancedPitchCalibrator:
    """
    Enhanced pitch calibration with keypoint detection and tactical zones
    """

    def __init__(self):
        # Standard FIFA pitch dimensions (meters)
        self.pitch_dimensions = {
            'length': 105.0,
            'width': 68.0,
            'penalty_box_length': 16.5,
            'penalty_box_width': 40.32,
            'goal_area_length': 5.5,
            'goal_area_width': 18.32,
            'center_circle_radius': 9.15,
            'penalty_spot_distance': 11.0
        }

        # Real-world keypoints (meters) - origin at bottom-left corner
        self.keypoints_template = self._build_keypoints_template()

        # Tactical zones
        self.tactical_zones = {
            'defensive_third': (0, 35),
            'middle_third': (35, 70),
            'attacking_third': (70, 105),
            'left_channel': (0, 22.67),
            'center_channel': (22.67, 45.33),
            'right_channel': (45.33, 68)
        }

    def _build_keypoints_template(self) -> Dict[str, List[Tuple[float, float]]]:
        """
        Build real-world keypoint coordinates for standard pitch
        Returns coordinates in meters (x, y) where origin is bottom-left corner
        """
        length = self.pitch_dimensions['length']
        width = self.pitch_dimensions['width']
        pb_length = self.pitch_dimensions['penalty_box_length']
        pb_width = self.pitch_dimensions['penalty_box_width']

        keypoints = {
            # Corner points (4 points)
            'corners': [
                (0, 0),           # Bottom-left
                (length, 0),      # Bottom-right
                (length, width),  # Top-right
                (0, width)        # Top-left
            ],

            # Center line intersections (3 points)
            'center_line': [
                (length/2, 0),        # Bottom center
                (length/2, width/2),  # Center circle
                (length/2, width)     # Top center
            ],

            # Left penalty box (4 corners)
            'left_penalty_box': [
                (0, (width - pb_width)/2),                    # Bottom-left
                (pb_length, (width - pb_width)/2),            # Bottom-right
                (pb_length, (width + pb_width)/2),            # Top-right
                (0, (width + pb_width)/2)                     # Top-left
            ],

            # Right penalty box (4 corners)
            'right_penalty_box': [
                (length - pb_length, (width - pb_width)/2),   # Bottom-left
                (length, (width - pb_width)/2),               # Bottom-right
                (length, (width + pb_width)/2),               # Top-right
                (length - pb_length, (width + pb_width)/2)    # Top-left
            ]
        }

        return keypoints

    def detect_pitch_lines(self, frame: np.ndarray) -> Tuple[List, np.ndarray]:
        """
        Detect pitch lines using enhanced edge detection
        Returns: (lines, edges_image)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Enhanced edge detection with multiple thresholds
        edges = cv2.Canny(blurred, 50, 150, apertureSize=3)

        # Dilate edges to connect broken lines
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

        # Detect lines using Hough Transform
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi/180,
            threshold=80,
            minLineLength=50,
            maxLineGap=10
        )

        return lines if lines is not None else [], edges

    def find_line_intersections(self, lines: List) -> List[Tuple[int, int]]:
        """
        Find intersection points between detected lines
        """
        intersections = []

        if len(lines) < 2:
            return intersections

        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                line1 = lines[i][0]
                line2 = lines[j][0]

                x1, y1, x2, y2 = line1
                x3, y3, x4, y4 = line2

                # Calculate intersection
                denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)

                if abs(denom) < 1e-6:  # Parallel lines
                    continue

                px = ((x1*y2 - y1*x2) * (x3 - x4) - (x1 - x2) * (x3*y4 - y3*x4)) / denom
                py = ((x1*y2 - y1*x2) * (y3 - y4) - (y1 - y2) * (x3*y4 - y3*x4)) / denom

                # Check if intersection is within frame bounds
                h, w = 720, 1280  # Approximate frame size
                if 0 <= px < w and 0 <= py < h:
                    intersections.append((int(px), int(py)))

        return intersections

    def cluster_keypoints(self, points: List[Tuple[int, int]], min_distance: int = 20) -> List[Tuple[int, int]]:
        """
        Cluster nearby points to reduce duplicates
        """
        if not points:
            return []

        clusters = []
        used = set()

        for i, pt1 in enumerate(points):
            if i in used:
                continue

            cluster = [pt1]
            used.add(i)

            for j, pt2 in enumerate(points):
                if j in used:
                    continue

                dist = np.sqrt((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)
                if dist < min_distance:
                    cluster.append(pt2)
                    used.add(j)

            # Average cluster points
            avg_x = int(np.mean([p[0] for p in cluster]))
            avg_y = int(np.mean([p[1] for p in cluster]))
            clusters.append((avg_x, avg_y))

        return clusters

    def detect_keypoints(self, frame: np.ndarray) -> Tuple[List[Tuple[int, int]], float]:
        """
        Detect pitch keypoints from frame
        Returns: (keypoints, confidence)
        """
        # Detect lines
        lines, edges = self.detect_pitch_lines(frame)

        if len(lines) < 4:
            return [], 0.0

        # Find intersections
        intersections = self.find_line_intersections(lines)

        # Cluster nearby points
        keypoints = self.cluster_keypoints(intersections, min_distance=30)

        # Calculate confidence based on number of keypoints found
        # Ideal: 15 keypoints (4 corners + 3 center + 4+4 penalty boxes)
        confidence = min(len(keypoints) / 15.0, 1.0)

        return keypoints, confidence

    def match_keypoints_to_template(self,
                                   detected_keypoints: List[Tuple[int, int]],
                                   frame_shape: Tuple[int, int]) -> Dict[str, Tuple[int, int]]:
        """
        Match detected keypoints to known pitch template
        Uses spatial layout analysis
        """
        if len(detected_keypoints) < 4:
            return {}

        h, w = frame_shape[:2]
        matched = {}

        # Sort keypoints by position for easier matching
        sorted_x = sorted(detected_keypoints, key=lambda p: p[0])
        sorted_y = sorted(detected_keypoints, key=lambda p: p[1])

        # Try to identify corners (extreme points)
        if len(sorted_x) >= 4 and len(sorted_y) >= 4:
            # Bottom-left: leftmost + lowest
            bottom_left_candidates = [p for p in sorted_x[:3] if p in sorted_y[:3]]
            if bottom_left_candidates:
                matched['bottom_left_corner'] = bottom_left_candidates[0]

            # Bottom-right: rightmost + lowest
            bottom_right_candidates = [p for p in sorted_x[-3:] if p in sorted_y[:3]]
            if bottom_right_candidates:
                matched['bottom_right_corner'] = bottom_right_candidates[-1]

            # Top-right: rightmost + highest
            top_right_candidates = [p for p in sorted_x[-3:] if p in sorted_y[-3:]]
            if top_right_candidates:
                matched['top_right_corner'] = top_right_candidates[-1]

            # Top-left: leftmost + highest
            top_left_candidates = [p for p in sorted_x[:3] if p in sorted_y[-3:]]
            if top_left_candidates:
                matched['top_left_corner'] = top_left_candidates[0]

        # Try to identify center line points (middle x-coordinate)
        center_x = w / 2
        center_candidates = [p for p in detected_keypoints if abs(p[0] - center_x) < w * 0.15]

        if center_candidates:
            center_sorted = sorted(center_candidates, key=lambda p: p[1])
            if len(center_sorted) >= 1:
                matched['center_bottom'] = center_sorted[0]
            if len(center_sorted) >= 2:
                matched['center_middle'] = center_sorted[len(center_sorted)//2]
            if len(center_sorted) >= 3:
                matched['center_top'] = center_sorted[-1]

        return matched

    def estimate_homography_from_keypoints(self,
                                          matched_keypoints: Dict[str, Tuple[int, int]],
                                          min_points: int = 4) -> Tuple[Optional[np.ndarray], float]:
        """
        Estimate homography from matched keypoints
        Returns: (homography_matrix, confidence)
        """
        if len(matched_keypoints) < min_points:
            return None, 0.0

        # Build correspondence pairs
        src_points = []  # Image coordinates
        dst_points = []  # Real-world coordinates

        # Map matched keypoints to template coordinates
        keypoint_mapping = {
            'bottom_left_corner': (0, 0),
            'bottom_right_corner': (105, 0),
            'top_right_corner': (105, 68),
            'top_left_corner': (0, 68),
            'center_bottom': (52.5, 0),
            'center_middle': (52.5, 34),
            'center_top': (52.5, 68)
        }

        for key, img_point in matched_keypoints.items():
            if key in keypoint_mapping:
                src_points.append(img_point)
                dst_points.append(keypoint_mapping[key])

        if len(src_points) < 4:
            return None, 0.0

        src_points = np.array(src_points, dtype=np.float32)
        dst_points = np.array(dst_points, dtype=np.float32)

        # Compute homography with RANSAC
        homography, mask = cv2.findHomography(src_points, dst_points, cv2.RANSAC, 5.0)

        if homography is None:
            return None, 0.0

        # Calculate confidence based on inlier ratio
        inliers = np.sum(mask) if mask is not None else 0
        confidence = inliers / len(src_points)

        return homography, confidence

    def calibrate_multi_frame(self,
                             frames: List[np.ndarray],
                             frame_indices: List[int] = [0, 100, 250, 500, 750],
                             min_confidence: float = 0.5) -> Tuple[Optional[np.ndarray], Dict]:
        """
        Calibrate using multiple frames for robustness
        Returns: (best_homography, metadata)
        """
        calibrations = []

        print(f"\n📐 Multi-frame Pitch Calibration:")
        print(f"   Testing {len(frame_indices)} frames for best homography...")

        for idx in frame_indices:
            if idx >= len(frames):
                continue

            frame = frames[idx]

            # Detect keypoints
            keypoints, kp_confidence = self.detect_keypoints(frame)

            # Match to template
            matched = self.match_keypoints_to_template(keypoints, frame.shape)

            # Estimate homography
            homography, h_confidence = self.estimate_homography_from_keypoints(matched)

            # Combined confidence
            total_confidence = (kp_confidence + h_confidence) / 2.0

            if homography is not None and total_confidence >= min_confidence:
                calibrations.append({
                    'frame_idx': idx,
                    'homography': homography,
                    'confidence': total_confidence,
                    'keypoints_detected': len(keypoints),
                    'keypoints_matched': len(matched)
                })

                print(f"   ✓ Frame {idx}: {len(keypoints)} keypoints, {len(matched)} matched, confidence={total_confidence:.2f}")
            else:
                print(f"   ✗ Frame {idx}: Low quality (confidence={total_confidence:.2f})")

        if not calibrations:
            print(f"   ⚠️  No valid calibrations found, using fallback method")
            return self._fallback_homography(frames[0]), {
                'method': 'fallback',
                'confidence': 0.3,
                'frames_tested': len(frame_indices)
            }

        # Select best calibration
        best = max(calibrations, key=lambda x: x['confidence'])

        print(f"\n   ✅ Best calibration: Frame {best['frame_idx']} (confidence={best['confidence']:.2f})")

        metadata = {
            'method': 'keypoint_detection',
            'best_frame': best['frame_idx'],
            'confidence': best['confidence'],
            'keypoints_detected': best['keypoints_detected'],
            'keypoints_matched': best['keypoints_matched'],
            'frames_tested': len(frame_indices),
            'successful_calibrations': len(calibrations)
        }

        return best['homography'], metadata

    def _fallback_homography(self, frame: np.ndarray) -> np.ndarray:
        """
        Fallback homography when keypoint detection fails
        Uses simplified corner estimation
        """
        h, w = frame.shape[:2]

        # Assume camera is viewing pitch from side
        # Estimate pitch corners in image
        src_points = np.array([
            [w * 0.15, h * 0.85],  # Bottom-left
            [w * 0.85, h * 0.85],  # Bottom-right
            [w * 0.92, h * 0.20],  # Top-right
            [w * 0.08, h * 0.20]   # Top-left
        ], dtype=np.float32)

        # Real-world pitch corners (meters)
        dst_points = np.array([
            [0, 0],
            [105, 0],
            [105, 68],
            [0, 68]
        ], dtype=np.float32)

        homography = cv2.getPerspectiveTransform(src_points, dst_points)
        return homography

    def map_tactical_zones(self,
                          homography: np.ndarray,
                          frame_shape: Tuple[int, int]) -> Dict[str, np.ndarray]:
        """
        Create tactical zone masks based on homography
        Returns: Dict of zone masks
        """
        h, w = frame_shape[:2]
        zones = {}

        # Create masks for each tactical zone
        for zone_name, (x_start, x_end) in self.tactical_zones.items():
            mask = np.zeros((h, w), dtype=np.uint8)

            # Define zone in real-world coordinates
            if 'third' in zone_name:
                # Horizontal zones (along pitch length)
                zone_corners_world = np.array([
                    [x_start, 0],
                    [x_end, 0],
                    [x_end, 68],
                    [x_start, 68]
                ], dtype=np.float32)
            else:
                # Vertical zones (channels along pitch width)
                zone_corners_world = np.array([
                    [0, x_start],
                    [105, x_start],
                    [105, x_end],
                    [0, x_end]
                ], dtype=np.float32)

            # Transform to image coordinates
            if homography is not None:
                homography_inv = np.linalg.inv(homography)
                zone_corners_img = cv2.perspectiveTransform(
                    zone_corners_world.reshape(-1, 1, 2),
                    homography_inv
                ).reshape(-1, 2).astype(np.int32)

                # Draw filled polygon
                cv2.fillPoly(mask, [zone_corners_img], 255)

            zones[zone_name] = mask

        return zones

    def get_player_tactical_zone(self,
                                 position: Tuple[float, float],
                                 homography: np.ndarray) -> Dict[str, str]:
        """
        Determine which tactical zone a player is in
        position: (x, y) in image coordinates
        Returns: {'horizontal': 'defensive_third', 'vertical': 'left_channel'}
        """
        if homography is None:
            return {'horizontal': 'unknown', 'vertical': 'unknown'}

        # Transform position to real-world coordinates
        pos_array = np.array([[position]], dtype=np.float32)
        world_pos = cv2.perspectiveTransform(pos_array, homography)[0][0]

        x_world, y_world = world_pos

        # Determine horizontal zone (thirds)
        if x_world < 35:
            horizontal = 'defensive_third'
        elif x_world < 70:
            horizontal = 'middle_third'
        else:
            horizontal = 'attacking_third'

        # Determine vertical zone (channels)
        if y_world < 22.67:
            vertical = 'left_channel'
        elif y_world < 45.33:
            vertical = 'center_channel'
        else:
            vertical = 'right_channel'

        return {'horizontal': horizontal, 'vertical': vertical}

    def visualize_calibration(self,
                             frame: np.ndarray,
                             homography: np.ndarray,
                             keypoints: List[Tuple[int, int]] = None) -> np.ndarray:
        """
        Visualize calibration results on frame
        """
        vis_frame = frame.copy()

        # Draw keypoints if provided
        if keypoints:
            for pt in keypoints:
                cv2.circle(vis_frame, pt, 5, (0, 255, 0), -1)
                cv2.circle(vis_frame, pt, 8, (0, 255, 0), 2)

        # Draw pitch overlay
        if homography is not None:
            # Create pitch template in world coordinates
            pitch_lines = [
                # Outer boundary
                [(0, 0), (105, 0), (105, 68), (0, 68), (0, 0)],
                # Center line
                [(52.5, 0), (52.5, 68)],
                # Center circle
                [(52.5 + 9.15 * np.cos(t), 34 + 9.15 * np.sin(t))
                 for t in np.linspace(0, 2*np.pi, 50)],
                # Penalty boxes
                [(0, 13.84), (16.5, 13.84), (16.5, 54.16), (0, 54.16)],
                [(105, 13.84), (88.5, 13.84), (88.5, 54.16), (105, 54.16)]
            ]

            homography_inv = np.linalg.inv(homography)

            for line in pitch_lines:
                points_world = np.array(line, dtype=np.float32).reshape(-1, 1, 2)
                points_img = cv2.perspectiveTransform(points_world, homography_inv)
                points_img = points_img.reshape(-1, 2).astype(np.int32)

                cv2.polylines(vis_frame, [points_img], False, (0, 255, 255), 2)

        return vis_frame
