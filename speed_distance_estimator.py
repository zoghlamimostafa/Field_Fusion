import cv2
import numpy as np


class SpeedDistanceEstimator:
    """
    Estimate player speed and distance from stabilized tracking data.
    Uses homography when available and falls back to a local player-scale estimate.
    """

    def __init__(self, fps=25, max_speed_kmh=42.0, max_gap_frames=3, smoothing_window=5):
        self.fps = fps
        self.max_speed_kmh = max_speed_kmh
        self.max_gap_frames = max_gap_frames
        self.smoothing_window = smoothing_window
        self.player_height_m = 1.75

    def _get_base_position(self, track_info):
        return track_info.get("position_adjusted") or track_info.get("position")

    def _transform_position(self, position, homography):
        if homography is None or position is None:
            return None

        try:
            pt = np.array([[position[0], position[1]]], dtype=np.float32).reshape(-1, 1, 2)
            transformed = cv2.perspectiveTransform(pt, homography)
            x, y = transformed[0][0]
            return float(x), float(y)
        except Exception:
            return None

    def _estimate_local_scale(self, previous_track, current_track):
        """
        Approximate meters-per-pixel from the tracked player's height.
        This is only used when homography is unavailable.
        """
        heights = []
        for track_info in (previous_track, current_track):
            bbox = track_info.get("bbox")
            if bbox is None:
                continue
            bbox_height = max(float(bbox[3] - bbox[1]), 1.0)
            heights.append(bbox_height)

        if not heights:
            return None

        mean_height_pixels = float(np.mean(heights))
        return self.player_height_m / mean_height_pixels

    def _add_field_positions_to_tracks(self, tracks, homography):
        for object_tracks in tracks.values():
            for frame_tracks in object_tracks:
                for track_info in frame_tracks.values():
                    base_position = self._get_base_position(track_info)
                    track_info["field_position"] = self._transform_position(base_position, homography)

    def _smoothed_speed(self, speed_history):
        if not speed_history:
            return 0.0
        window = speed_history[-self.smoothing_window:]
        return float(np.median(window))

    def add_speed_and_distance_to_tracks(self, tracks, homography):
        """
        Add speed and distance calculations to player tracks.
        Returns aggregate stats keyed by player track id.
        """
        self._add_field_positions_to_tracks(tracks, homography)

        total_distance = {}
        max_speed = {}
        avg_speed = {}
        speed_history = {}
        last_seen = {}

        player_frames = tracks.get("players", [])

        for frame_num, frame_tracks in enumerate(player_frames):
            for track_id, track_info in frame_tracks.items():
                total_distance.setdefault(track_id, 0.0)
                max_speed.setdefault(track_id, 0.0)
                avg_speed.setdefault(track_id, [])
                speed_history.setdefault(track_id, [])

                smoothed_speed = self._smoothed_speed(speed_history[track_id])
                track_info["speed"] = smoothed_speed
                track_info["distance"] = total_distance[track_id]

                base_position = self._get_base_position(track_info)
                if base_position is None:
                    continue

                current_field_position = track_info.get("field_position")
                previous = last_seen.get(track_id)

                if previous is not None:
                    frame_gap = frame_num - previous["frame_num"]
                    if 0 < frame_gap <= self.max_gap_frames:
                        if (
                            current_field_position is not None
                            and previous["field_position"] is not None
                        ):
                            distance = self.calculate_distance(
                                previous["field_position"], current_field_position
                            )
                        else:
                            local_scale = self._estimate_local_scale(previous["track_info"], track_info)
                            if local_scale is not None:
                                pixel_distance = self.calculate_distance(
                                    previous["base_position"], base_position
                                )
                                distance = pixel_distance * local_scale
                            else:
                                distance = None

                        if distance is not None and distance > 0:
                            elapsed_seconds = frame_gap / self.fps
                            speed_kmh = (distance / elapsed_seconds) * 3.6

                            if speed_kmh <= self.max_speed_kmh:
                                total_distance[track_id] += float(distance)
                                speed_history[track_id].append(float(speed_kmh))
                                max_speed[track_id] = max(max_speed[track_id], float(speed_kmh))
                                avg_speed[track_id].append(float(speed_kmh))
                                track_info["speed"] = self._smoothed_speed(speed_history[track_id])
                                track_info["distance"] = total_distance[track_id]

                last_seen[track_id] = {
                    "frame_num": frame_num,
                    "base_position": base_position,
                    "field_position": current_field_position,
                    "track_info": {
                        "bbox": track_info.get("bbox"),
                    },
                }

        avg_speed_summary = {}
        for track_id, speeds in avg_speed.items():
            avg_speed_summary[track_id] = float(np.mean(speeds)) if speeds else 0.0

        return total_distance, max_speed, avg_speed_summary

    def calculate_distance(self, pos1, pos2):
        """Calculate Euclidean distance between two 2D points."""
        return float(np.sqrt((pos2[0] - pos1[0]) ** 2 + (pos2[1] - pos1[1]) ** 2))

    def draw_speed_stats(self, frame, tracks, frame_num):
        """Draw the top player speeds for the current frame."""
        output = frame.copy()

        overlay = output.copy()
        cv2.rectangle(overlay, (10, 10), (400, 150), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, output, 0.4, 0, output)

        y_offset = 40
        current_speeds = []

        for track_id, track_info in tracks.get("players", [{}])[frame_num].items():
            speed = float(track_info.get("speed", 0.0))
            if speed > 0:
                current_speeds.append((track_id, speed))

        current_speeds.sort(key=lambda item: item[1], reverse=True)

        cv2.putText(
            output,
            "Top Speeds (km/h):",
            (20, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )
        y_offset += 30

        for track_id, speed in current_speeds[:3]:
            text = f"  Player {track_id}: {speed:.1f} km/h"
            cv2.putText(
                output,
                text,
                (20, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
            )
            y_offset += 25

        return output
