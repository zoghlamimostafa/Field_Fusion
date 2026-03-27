import cv2
import numpy as np
import json
import os

class PitchDetector:
    """
    Detects pitch lines and keypoints for homography transformation
    """
    def __init__(self):
        # Standard football pitch dimensions (in meters)
        self.pitch_length = 105  # meters
        self.pitch_width = 68    # meters

        # Define standard pitch keypoints in real-world coordinates (top-down view)
        # Using center of pitch as origin (0, 0)
        self.pitch_keypoints_real = {
            'center': (0, 0),
            'halfway_line_top': (0, -34),
            'halfway_line_bottom': (0, 34),
            'center_circle_top': (0, -9.15),
            'center_circle_bottom': (0, 9.15),
            'center_circle_left': (-9.15, 0),
            'center_circle_right': (9.15, 0),
            'penalty_box_left_top': (-52.5, -20.16),
            'penalty_box_left_bottom': (-52.5, 20.16),
            'penalty_box_right_top': (52.5, -20.16),
            'penalty_box_right_bottom': (52.5, 20.16),
            'right_penalty_area_top_left': (36.0, -20.16),
            'right_penalty_area_top_right': (52.5, -20.16),
            'right_penalty_area_bottom_left': (36.0, 20.16),
            'right_penalty_area_bottom_right': (52.5, 20.16),
            'goal_box_left_top': (-52.5, -9.16),
            'goal_box_left_bottom': (-52.5, 9.16),
            'goal_box_right_top': (52.5, -9.16),
            'goal_box_right_bottom': (52.5, 9.16),
            'corner_tl': (-52.5, -34),
            'corner_tr': (52.5, -34),
            'corner_bl': (-52.5, 34),
            'corner_br': (52.5, 34)
        }

    def detect_lines(self, frame):
        """Detect pitch lines using edge detection and Hough transform"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Edge detection
        edges = cv2.Canny(blurred, 50, 150, apertureSize=3)

        # Hough line detection
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100,
                                minLineLength=100, maxLineGap=10)

        return lines, edges

    def filter_pitch_lines(self, lines, frame_shape):
        """Filter lines to get only pitch-relevant lines"""
        if lines is None:
            return []

        pitch_lines = []
        height, width = frame_shape[:2]

        for line in lines:
            x1, y1, x2, y2 = line[0]

            # Calculate angle
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)

            # Keep horizontal and vertical lines (with some tolerance)
            if angle < 15 or angle > 165 or (80 < angle < 100):
                length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
                if length > width * 0.1:  # Filter short lines
                    pitch_lines.append(line[0])

        return pitch_lines

    def get_white_line_mask(self, frame):
        """Detect bright white field markings inside the pitch region."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        white_mask = cv2.inRange(
            hsv,
            np.array([0, 0, 150], dtype=np.uint8),
            np.array([180, 90, 255], dtype=np.uint8),
        )

        pitch_mask = self.detect_pitch_mask(frame)
        if pitch_mask is not None:
            expanded_pitch_mask = cv2.dilate(pitch_mask, np.ones((15, 15), dtype=np.uint8), iterations=1)
            white_mask = cv2.bitwise_and(white_mask, expanded_pitch_mask)

        white_mask = cv2.morphologyEx(
            white_mask,
            cv2.MORPH_OPEN,
            np.ones((3, 3), dtype=np.uint8),
        )
        return white_mask

    def resolve_calibration_profile_path(self, video_path=None, calibration_path=None,
                                         calibration_dir='calibration_profiles'):
        """Resolve an explicit or video-matched calibration profile."""
        candidates = []

        if calibration_path:
            candidates.append(calibration_path)

        if video_path:
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            candidates.append(os.path.join(calibration_dir, f'{video_name}.json'))

        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate

        return None

    def load_calibration_profile(self, profile_path):
        """Load a saved calibration profile from JSON."""
        with open(profile_path, 'r') as file:
            return json.load(file)

    def save_calibration_profile(self, profile, profile_path):
        """Persist a calibration profile to disk."""
        os.makedirs(os.path.dirname(profile_path), exist_ok=True)
        with open(profile_path, 'w') as file:
            json.dump(profile, file, indent=2)

    def _fit_line(self, segments):
        """Fit a single line through multiple Hough segments."""
        if not segments:
            return None

        points = []
        for x1, y1, x2, y2 in segments:
            points.append([x1, y1])
            points.append([x2, y2])

        points = np.array(points, dtype=np.float32)
        line = cv2.fitLine(points, cv2.DIST_L2, 0, 0.01, 0.01)
        vx, vy, x0, y0 = [float(value) for value in line.reshape(-1)]

        return vx, vy, x0, y0

    def _intersect_fitted_lines(self, line_a, line_b):
        """Intersect two parametric lines returned by cv2.fitLine."""
        if line_a is None or line_b is None:
            return None

        vx1, vy1, x1, y1 = line_a
        vx2, vy2, x2, y2 = line_b

        system = np.array([[vx1, -vx2], [vy1, -vy2]], dtype=float)
        target = np.array([x2 - x1, y2 - y1], dtype=float)

        try:
            t_value, _ = np.linalg.solve(system, target)
        except np.linalg.LinAlgError:
            return None

        return float(x1 + t_value * vx1), float(y1 + t_value * vy1)

    def _sample_ellipse_extrema(self, ellipse):
        """Sample ellipse extrema in image space for calibration seeding."""
        (cx, cy), (major_axis, minor_axis), angle_degrees = ellipse
        angle = np.deg2rad(angle_degrees)
        extrema = {name: None for name in ('left', 'right', 'top', 'bottom')}

        for theta in np.linspace(0, 2 * np.pi, 2000):
            x = (major_axis / 2.0) * np.cos(theta)
            y = (minor_axis / 2.0) * np.sin(theta)
            xr = cx + x * np.cos(angle) - y * np.sin(angle)
            yr = cy + x * np.sin(angle) + y * np.cos(angle)

            if extrema['left'] is None or xr < extrema['left'][0]:
                extrema['left'] = (xr, yr)
            if extrema['right'] is None or xr > extrema['right'][0]:
                extrema['right'] = (xr, yr)
            if extrema['top'] is None or yr < extrema['top'][1]:
                extrema['top'] = (xr, yr)
            if extrema['bottom'] is None or yr > extrema['bottom'][1]:
                extrema['bottom'] = (xr, yr)

        return {key: (float(value[0]), float(value[1])) for key, value in extrema.items()}

    def _sample_ellipse_line_intersections(self, ellipse, line, tolerance=3.0):
        """Approximate the intersections between an ellipse and a fitted line."""
        if ellipse is None or line is None:
            return []

        (cx, cy), (major_axis, minor_axis), angle_degrees = ellipse
        angle = np.deg2rad(angle_degrees)
        vx, vy, x0, y0 = line
        intersections = []

        for theta in np.linspace(0, 2 * np.pi, 5000):
            x = (major_axis / 2.0) * np.cos(theta)
            y = (minor_axis / 2.0) * np.sin(theta)
            xr = cx + x * np.cos(angle) - y * np.sin(angle)
            yr = cy + x * np.sin(angle) + y * np.cos(angle)

            distance = abs((xr - x0) * vy - (yr - y0) * vx) / max(np.sqrt(vx ** 2 + vy ** 2), 1e-6)
            if distance <= tolerance:
                intersections.append((distance, float(xr), float(yr)))

        if not intersections:
            return []

        intersections = sorted(intersections, key=lambda value: value[2])
        top_point = min(intersections, key=lambda value: value[2])
        bottom_point = max(intersections, key=lambda value: value[2])

        return [(top_point[1], top_point[2]), (bottom_point[1], bottom_point[2])]

    def _fit_center_circle_seed_ellipse(self, white_mask, halfway_line, frame_shape):
        """
        Fit an ellipse over the visible center-circle arc fragments.
        This is a seed for manual or semi-manual calibration, not a final guarantee.
        """
        if halfway_line is None:
            return None

        height, width = frame_shape[:2]
        _, _, x0, _ = halfway_line

        x_min = max(0, int(x0 - width * 0.10))
        x_max = min(width, int(x0 + width * 0.15))
        y_min = max(0, int(height * 0.33))
        y_max = min(height, int(height * 0.76))

        crop = white_mask[y_min:y_max, x_min:x_max].copy()

        vx, vy, line_x0, line_y0 = halfway_line
        if abs(vy) > 1e-6:
            top_t = (y_min - line_y0) / vy
            bottom_t = (y_max - line_y0) / vy
            top_x = int(round(line_x0 + top_t * vx)) - x_min
            bottom_x = int(round(line_x0 + bottom_t * vx)) - x_min
            cv2.line(
                crop,
                (top_x, 0),
                (bottom_x, y_max - y_min - 1),
                0,
                thickness=20,
            )

        contours, _ = cv2.findContours(crop, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

        points = []
        for contour in contours:
            area = cv2.contourArea(contour)
            x, y, contour_width, contour_height = cv2.boundingRect(contour)
            contour_center_x = x_min + x + contour_width / 2.0

            if (
                area > 50
                and width * 0.035 < contour_width < width * 0.25
                and 10 < contour_height < height * 0.12
                and (x0 - width * 0.08) < contour_center_x < (x0 + width * 0.12)
            ):
                for point in contour[:, 0, :]:
                    points.append([point[0] + x_min, point[1] + y_min])

        if len(points) < 100:
            return None

        points = np.array(points, dtype=np.int32)
        ellipse = cv2.fitEllipse(points)
        (_, _), (major_axis, minor_axis), _ = ellipse

        if major_axis < width * 0.05 or minor_axis < height * 0.08:
            return None

        return ellipse

    def suggest_calibration_points(self, frame):
        """
        Suggest a seed set of named pitch keypoints from visible field markings.
        These points are meant to bootstrap a saved calibration profile.
        """
        height, width = frame.shape[:2]
        white_mask = self.get_white_line_mask(frame)
        lines = cv2.HoughLinesP(
            white_mask,
            1,
            np.pi / 180,
            threshold=80,
            minLineLength=max(120, int(width * 0.06)),
            maxLineGap=20,
        )

        if lines is None:
            return {}

        halfway_segments = []
        far_touchline_segments = []
        near_touchline_segments = []
        right_penalty_top_segments = []

        for segment in lines[:, 0, :]:
            x1, y1, x2, y2 = [float(value) for value in segment]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            mid_x = (x1 + x2) / 2.0
            mid_y = (y1 + y2) / 2.0

            if 75 < abs(angle) < 88 and width * 0.18 < mid_x < width * 0.34 and length > width * 0.15:
                halfway_segments.append((x1, y1, x2, y2))

            if abs(angle) < 6 and mid_y < height * 0.35 and min(y1, y2) > height * 0.18 and length > width * 0.08:
                far_touchline_segments.append((x1, y1, x2, y2))

            if -8 < angle < 2 and mid_y > height * 0.82 and length > width * 0.08:
                near_touchline_segments.append((x1, y1, x2, y2))

            if 10 < angle < 45 and mid_x > width * 0.72 and mid_y < height * 0.65 and length > width * 0.12:
                right_penalty_top_segments.append((x1, y1, x2, y2))

        halfway_line = self._fit_line(halfway_segments)
        far_touchline = self._fit_line(far_touchline_segments)
        near_touchline = self._fit_line(near_touchline_segments)

        suggested_points = {}

        halfway_top = self._intersect_fitted_lines(halfway_line, far_touchline)
        halfway_bottom = self._intersect_fitted_lines(halfway_line, near_touchline)
        if halfway_top is not None:
            suggested_points['halfway_line_top'] = halfway_top
        if halfway_bottom is not None:
            suggested_points['halfway_line_bottom'] = halfway_bottom

        center_circle_ellipse = self._fit_center_circle_seed_ellipse(white_mask, halfway_line, frame.shape)
        if center_circle_ellipse is not None:
            extrema = self._sample_ellipse_extrema(center_circle_ellipse)
            for side_name, key_name in (
                ('left', 'center_circle_left'),
                ('right', 'center_circle_right'),
                ('top', 'center_circle_top'),
                ('bottom', 'center_circle_bottom'),
            ):
                suggested_points[key_name] = extrema[side_name]

            line_intersections = self._sample_ellipse_line_intersections(center_circle_ellipse, halfway_line)
            if len(line_intersections) == 2:
                suggested_points['center_circle_top'] = line_intersections[0]
                suggested_points['center_circle_bottom'] = line_intersections[1]

        if right_penalty_top_segments:
            endpoints = []
            for x1, y1, x2, y2 in right_penalty_top_segments:
                endpoints.append((x1, y1))
                endpoints.append((x2, y2))

            leftmost_endpoint = min(endpoints, key=lambda point: point[0])
            rightmost_endpoint = max(endpoints, key=lambda point: point[0])
            suggested_points['right_penalty_area_top_left'] = leftmost_endpoint
            suggested_points['right_penalty_area_top_right'] = rightmost_endpoint

        return suggested_points

    def build_calibration_profile(self, frame, video_path=None):
        """Build a JSON-serializable seed calibration profile for a video."""
        suggested_points = self.suggest_calibration_points(frame)
        preferred_keys = [
            'halfway_line_top',
            'halfway_line_bottom',
            'center_circle_top',
            'center_circle_bottom',
            'right_penalty_area_top_left',
            'right_penalty_area_top_right',
        ]
        preferred_points = {
            key: suggested_points[key]
            for key in preferred_keys
            if key in suggested_points
        }

        if len(preferred_points) >= 4:
            points_to_save = preferred_points
        else:
            points_to_save = suggested_points

        return {
            'version': 1,
            'video_name': os.path.basename(video_path) if video_path else None,
            'source': 'seeded_from_visible_markings',
            'image_points': {
                key: [round(float(point[0]), 2), round(float(point[1]), 2)]
                for key, point in points_to_save.items()
            },
        }

    def draw_named_points(self, frame, named_points):
        """Draw a labeled calibration profile preview."""
        output = frame.copy()

        for key, point in named_points.items():
            if point is None:
                continue
            x, y = int(round(point[0])), int(round(point[1]))
            cv2.circle(output, (x, y), 6, (0, 0, 255), -1)
            cv2.putText(
                output,
                key,
                (x + 8, y - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                2,
            )

        return output

    def detect_pitch_mask(self, frame):
        """Segment the dominant pitch surface using HSV thresholds."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        lower_green = np.array([30, 35, 35], dtype=np.uint8)
        upper_green = np.array([95, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_green, upper_green)

        mask = cv2.medianBlur(mask, 5)

        kernel = np.ones((9, 9), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        largest_contour = max(contours, key=cv2.contourArea)
        frame_area = frame.shape[0] * frame.shape[1]
        if cv2.contourArea(largest_contour) < frame_area * 0.08:
            return None

        pitch_mask = np.zeros_like(mask)
        cv2.drawContours(pitch_mask, [largest_contour], -1, 255, thickness=cv2.FILLED)

        return pitch_mask

    def _get_row_spans(self, mask, min_row_fraction=0.12):
        """Return horizontal spans of the detected pitch region for each useful row."""
        height, width = mask.shape
        min_pixels = int(width * min_row_fraction)
        spans = []

        for y in range(height):
            xs = np.where(mask[y] > 0)[0]
            if xs.size < min_pixels:
                continue
            spans.append((y, int(xs.min()), int(xs.max()), int(xs.size)))

        return spans

    def _aggregate_span(self, spans, ratio, window=12):
        """Average a small band of rows to stabilize quadrilateral extraction."""
        if not spans:
            return None

        index = int(np.clip(round((len(spans) - 1) * ratio), 0, len(spans) - 1))
        start = max(0, index - window)
        end = min(len(spans), index + window + 1)
        band = spans[start:end]

        if not band:
            return None

        y = int(np.mean([item[0] for item in band]))
        left = int(np.mean([item[1] for item in band]))
        right = int(np.mean([item[2] for item in band]))
        width = int(np.mean([item[3] for item in band]))

        return y, left, right, width

    def _validate_quadrilateral(self, points, frame_shape):
        """Reject degenerate pitch estimates before computing a homography."""
        if len(points) != 4:
            return False

        height, width = frame_shape[:2]
        quadrilateral = np.array(points, dtype=np.float32)
        polygon = np.array([
            quadrilateral[0],
            quadrilateral[1],
            quadrilateral[3],
            quadrilateral[2],
        ], dtype=np.float32)
        area = cv2.contourArea(polygon)
        top_width = np.linalg.norm(quadrilateral[1] - quadrilateral[0])
        bottom_width = np.linalg.norm(quadrilateral[3] - quadrilateral[2])
        vertical_span = quadrilateral[2][1] - quadrilateral[0][1]

        if area < width * height * 0.05:
            return False
        if top_width < width * 0.08:
            return False
        if bottom_width < width * 0.2:
            return False
        if vertical_span < height * 0.2:
            return False

        return True

    def estimate_homography_from_pitch_mask(self, frame):
        """
        Estimate a broadcast-view homography from the visible pitch region.
        The output coordinate system is centered on the middle of a 105m x 68m pitch.
        """
        pitch_mask = self.detect_pitch_mask(frame)
        if pitch_mask is None:
            return None

        spans = self._get_row_spans(pitch_mask)
        if len(spans) < 20:
            return None

        top_span = self._aggregate_span(spans, ratio=0.02)
        bottom_span = self._aggregate_span(spans, ratio=0.95)

        if top_span is None or bottom_span is None:
            return None

        top_y, top_left, top_right, top_width = top_span
        bottom_y, bottom_left, bottom_right, bottom_width = bottom_span

        if bottom_y <= top_y:
            return None

        image_points = np.array([
            (top_left, top_y),
            (top_right, top_y),
            (bottom_left, bottom_y),
            (bottom_right, bottom_y),
        ], dtype=np.float32)

        if not self._validate_quadrilateral(image_points, frame.shape):
            return None

        real_points = np.array([
            (-52.5, -34.0),
            (52.5, -34.0),
            (-52.5, 34.0),
            (52.5, 34.0),
        ], dtype=np.float32)

        H = self.estimate_homography_manual(image_points, real_points)
        return H

    def detect_keypoints_simple(self, frame):
        """
        Simple keypoint detection using line intersections
        For MVP - manual calibration points can be added later
        """
        lines, edges = self.detect_lines(frame)
        pitch_lines = self.filter_pitch_lines(lines, frame.shape)

        # Find line intersections (keypoints)
        keypoints = []

        if len(pitch_lines) > 1:
            # For now, use simple heuristics to find key intersections
            # This is a simplified version - in production, use ML-based keypoint detection

            # Find center line (horizontal)
            horizontal_lines = [l for l in pitch_lines
                               if abs(np.arctan2(l[3]-l[1], l[2]-l[0]) * 180 / np.pi) < 15]

            # Find vertical lines
            vertical_lines = [l for l in pitch_lines
                             if 80 < abs(np.arctan2(l[3]-l[1], l[2]-l[0]) * 180 / np.pi) < 100]

            # Find intersections
            for h_line in horizontal_lines[:5]:  # Limit to avoid too many combinations
                for v_line in vertical_lines[:5]:
                    intersection = self._line_intersection(h_line, v_line)
                    if intersection is not None:
                        keypoints.append(intersection)

        return keypoints, pitch_lines

    def _line_intersection(self, line1, line2):
        """Calculate intersection point of two lines"""
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2

        denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
        if abs(denom) < 1e-10:
            return None

        px = ((x1*y2-y1*x2)*(x3-x4) - (x1-x2)*(x3*y4-y3*x4)) / denom
        py = ((x1*y2-y1*x2)*(y3-y4) - (y1-y2)*(x3*y4-y3*x4)) / denom

        return (int(px), int(py))

    def estimate_homography_manual(self, image_points, real_points):
        """
        Estimate homography matrix from manual point correspondences
        image_points: list of (x, y) in image coordinates
        real_points: list of (x, y) in real-world coordinates (meters)
        """
        if len(image_points) < 4 or len(real_points) < 4:
            return None

        image_pts = np.array(image_points, dtype=np.float32)
        real_pts = np.array(real_points, dtype=np.float32)

        # Calculate homography
        H, mask = cv2.findHomography(image_pts, real_pts, cv2.RANSAC, 5.0)

        return H

    def estimate_homography_from_named_points(self, named_points, method=0):
        """
        Estimate homography from a dictionary of named image keypoints.
        Named points must correspond to keys in self.pitch_keypoints_real.
        """
        image_points = []
        real_points = []

        for key, point in named_points.items():
            if key not in self.pitch_keypoints_real or point is None:
                continue

            image_points.append(point)
            real_points.append(self.pitch_keypoints_real[key])

        if len(image_points) < 4:
            return None

        image_pts = np.array(image_points, dtype=np.float32)
        real_pts = np.array(real_points, dtype=np.float32)

        if method == 0:
            H, _ = cv2.findHomography(image_pts, real_pts, 0)
        else:
            H, _ = cv2.findHomography(image_pts, real_pts, method, 3.0)

        return H

    def estimate_homography_auto(self, frame, video_path=None, calibration_path=None, return_metadata=False):
        """
        Estimate homography with a preference order of:
        1. saved calibration profile
        2. seeded semantic keypoints from visible field markings
        3. pitch-mask fallback
        """
        metadata = {
            'method': None,
            'profile_path': None,
            'num_points': 0,
        }

        profile_path = self.resolve_calibration_profile_path(
            video_path=video_path,
            calibration_path=calibration_path,
        )
        if profile_path is not None:
            profile = self.load_calibration_profile(profile_path)
            named_points = profile.get('image_points', {})
            homography = self.estimate_homography_from_named_points(named_points, method=0)
            if homography is not None:
                metadata['method'] = 'calibration_profile'
                metadata['profile_path'] = profile_path
                metadata['num_points'] = len(named_points)
                if return_metadata:
                    return homography, metadata
                return homography

        suggested_points = self.suggest_calibration_points(frame)
        preferred_keys = [
            'halfway_line_top',
            'halfway_line_bottom',
            'center_circle_top',
            'center_circle_bottom',
            'right_penalty_area_top_left',
            'right_penalty_area_top_right',
        ]
        preferred_points = {
            key: suggested_points[key]
            for key in preferred_keys
            if key in suggested_points
        }
        points_for_homography = preferred_points if len(preferred_points) >= 4 else suggested_points

        homography = self.estimate_homography_from_named_points(points_for_homography, method=0)
        if homography is not None:
            metadata['method'] = 'seeded_keypoints'
            metadata['num_points'] = len(points_for_homography)
            if return_metadata:
                return homography, metadata
            return homography

        homography = self.estimate_homography_from_pitch_mask(frame)
        if homography is not None:
            metadata['method'] = 'pitch_mask'
            if return_metadata:
                return homography, metadata
            return homography

        keypoints, _ = self.detect_keypoints_simple(frame)
        if len(keypoints) < 4:
            metadata['method'] = 'failed'
            if return_metadata:
                return None, metadata
            return None

        image_points = np.array(keypoints[:4], dtype=np.float32)
        real_points = np.array([
            (-52.5, -34.0),
            (52.5, -34.0),
            (-52.5, 34.0),
            (52.5, 34.0),
        ], dtype=np.float32)

        H = self.estimate_homography_manual(image_points, real_points)
        metadata['method'] = 'line_intersections'
        metadata['num_points'] = len(keypoints[:4])
        if return_metadata:
            return H, metadata
        return H

    def transform_point(self, point, homography):
        """Transform a point from image to real-world coordinates"""
        if homography is None:
            return None

        pt = np.array([[point[0], point[1]]], dtype=np.float32)
        pt = pt.reshape(-1, 1, 2)

        transformed = cv2.perspectiveTransform(pt, homography)

        return (transformed[0][0][0], transformed[0][0][1])

    def draw_pitch_lines(self, frame, lines):
        """Draw detected pitch lines on frame"""
        output = frame.copy()

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line
                cv2.line(output, (x1, y1), (x2, y2), (0, 255, 0), 2)

        return output

    def draw_keypoints(self, frame, keypoints):
        """Draw detected keypoints on frame"""
        output = frame.copy()

        for point in keypoints:
            cv2.circle(output, point, 5, (0, 0, 255), -1)

        return output

    def get_top_down_pitch(self, width=1050, height=680):
        """
        Generate a blank top-down pitch representation
        Scale: 10 pixels = 1 meter
        """
        pitch = np.ones((height, width, 3), dtype=np.uint8) * 34  # Dark green

        # Draw pitch boundaries
        cv2.rectangle(pitch, (0, 0), (width-1, height-1), (255, 255, 255), 2)

        # Draw center line
        cv2.line(pitch, (width//2, 0), (width//2, height), (255, 255, 255), 2)

        # Draw center circle
        center = (width//2, height//2)
        cv2.circle(pitch, center, 92, (255, 255, 255), 2)  # 9.15m radius

        # Draw penalty areas
        # Left penalty area
        cv2.rectangle(pitch, (0, int(height/2 - 202)),
                     (165, int(height/2 + 202)), (255, 255, 255), 2)

        # Right penalty area
        cv2.rectangle(pitch, (width-165, int(height/2 - 202)),
                     (width, int(height/2 + 202)), (255, 255, 255), 2)

        # Goal areas
        cv2.rectangle(pitch, (0, int(height/2 - 92)),
                     (55, int(height/2 + 92)), (255, 255, 255), 2)
        cv2.rectangle(pitch, (width-55, int(height/2 - 92)),
                     (width, int(height/2 + 92)), (255, 255, 255), 2)

        return pitch
