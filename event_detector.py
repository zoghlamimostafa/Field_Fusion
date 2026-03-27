import numpy as np


class EventDetector:
    """
    Detect simple football events from possession segments and ball movement.
    """

    def __init__(self):
        self.min_possession_frames = 3
        self.max_transition_gap_frames = 12
        self.min_pass_distance_m = 5.0
        self.max_pass_distance_m = 40.0
        self.min_pass_distance_px = 25.0
        self.max_pass_distance_px = 450.0
        self.shot_speed_threshold_kmh = 35.0
        self.shot_speed_ceiling_kmh = 200.0
        self.shot_travel_distance_m = 8.0
        self.shot_travel_distance_px = 90.0
        self.shot_goal_progress_m = 6.0
        self.shot_cooldown_frames = 20
        self.goal_channel_half_width_m = 24.0

    def _ball_position(self, ball_tracks, frame_num):
        if frame_num < 0 or frame_num >= len(ball_tracks):
            return None

        ball_info = ball_tracks[frame_num].get(1)
        if not ball_info:
            return None

        field_position = ball_info.get("field_position")
        if field_position is not None:
            return tuple(field_position)

        bbox = ball_info.get("bbox")
        if bbox is None:
            return None

        center_x = (bbox[0] + bbox[2]) / 2.0
        center_y = (bbox[1] + bbox[3]) / 2.0
        return float(center_x), float(center_y)

    def _distance(self, point_a, point_b):
        if point_a is None or point_b is None:
            return None
        return float(np.linalg.norm(np.array(point_a) - np.array(point_b)))

    def _frame_possession(self, tracks, frame_num):
        player_tracks = tracks["players"][frame_num]

        for player_id, player_info in player_tracks.items():
            if player_info.get("has_ball", False):
                return {
                    "frame": frame_num,
                    "player": player_id,
                    "team": player_info.get("team"),
                }

        return {"frame": frame_num, "player": None, "team": None}

    def _build_possession_segments(self, tracks, ball_tracks):
        segments = []
        current_segment = None

        for frame_num in range(len(tracks["players"])):
            possession = self._frame_possession(tracks, frame_num)
            player_id = possession["player"]
            team_id = possession["team"]

            if player_id is None or team_id is None:
                if current_segment is not None:
                    current_segment["end_frame"] = frame_num - 1
                    current_segment["end_ball_position"] = self._ball_position(
                        ball_tracks, current_segment["end_frame"]
                    )
                    segments.append(current_segment)
                    current_segment = None
                continue

            if (
                current_segment is None
                or current_segment["player"] != player_id
                or current_segment["team"] != team_id
            ):
                if current_segment is not None:
                    current_segment["end_frame"] = frame_num - 1
                    current_segment["end_ball_position"] = self._ball_position(
                        ball_tracks, current_segment["end_frame"]
                    )
                    segments.append(current_segment)

                current_segment = {
                    "player": player_id,
                    "team": team_id,
                    "start_frame": frame_num,
                    "start_ball_position": self._ball_position(ball_tracks, frame_num),
                }

        if current_segment is not None:
            current_segment["end_frame"] = len(tracks["players"]) - 1
            current_segment["end_ball_position"] = self._ball_position(
                ball_tracks, current_segment["end_frame"]
            )
            segments.append(current_segment)

        filtered_segments = []
        for segment in segments:
            segment["duration_frames"] = segment["end_frame"] - segment["start_frame"] + 1
            if segment["duration_frames"] >= self.min_possession_frames:
                filtered_segments.append(segment)

        return filtered_segments

    def _uses_field_coordinates(self, ball_tracks):
        for frame_tracks in ball_tracks:
            ball_info = frame_tracks.get(1)
            if ball_info and ball_info.get("field_position") is not None:
                return True
        return False

    def detect_passes(self, tracks, ball_tracks):
        """
        Detect successful passes from stable consecutive possessions on the same team.
        """
        passes = []
        segments = self._build_possession_segments(tracks, ball_tracks)
        uses_field_coordinates = self._uses_field_coordinates(ball_tracks)

        min_distance = self.min_pass_distance_m if uses_field_coordinates else self.min_pass_distance_px
        max_distance = self.max_pass_distance_m if uses_field_coordinates else self.max_pass_distance_px

        for previous_segment, next_segment in zip(segments, segments[1:]):
            gap_frames = next_segment["start_frame"] - previous_segment["end_frame"] - 1
            if gap_frames > self.max_transition_gap_frames:
                continue
            if previous_segment["team"] != next_segment["team"]:
                continue
            if previous_segment["player"] == next_segment["player"]:
                continue

            pass_distance = self._distance(
                previous_segment["end_ball_position"], next_segment["start_ball_position"]
            )
            if pass_distance is None:
                continue
            if not (min_distance <= pass_distance <= max_distance):
                continue

            passes.append(
                {
                    "frame": next_segment["start_frame"],
                    "from_player": previous_segment["player"],
                    "to_player": next_segment["player"],
                    "team": previous_segment["team"],
                    "duration_frames": gap_frames + next_segment["duration_frames"],
                    "distance": pass_distance,
                    "type": "pass",
                }
            )

        return passes

    def detect_shots(self, tracks, ball_tracks):
        """
        Detect likely shots as high-speed releases that move the ball toward a goal line.
        """
        shots = []
        segments = self._build_possession_segments(tracks, ball_tracks)
        uses_field_coordinates = self._uses_field_coordinates(ball_tracks)
        last_shot_frame = -self.shot_cooldown_frames

        for segment in segments:
            release_frame = segment["end_frame"] + 1
            if release_frame - last_shot_frame < self.shot_cooldown_frames:
                continue

            start_position = self._ball_position(ball_tracks, segment["end_frame"])
            future_positions = []
            for frame_num in range(release_frame, min(release_frame + 6, len(ball_tracks))):
                position = self._ball_position(ball_tracks, frame_num)
                if position is not None:
                    future_positions.append((frame_num, position))

            if start_position is None or not future_positions:
                continue

            end_frame, end_position = future_positions[-1]
            travel_distance = self._distance(start_position, end_position)
            if travel_distance is None:
                continue

            elapsed_seconds = max(1, end_frame - segment["end_frame"]) / 25.0
            speed_kmh = (travel_distance / elapsed_seconds) * 3.6

            if uses_field_coordinates:
                goal_progress = abs(end_position[0]) - abs(start_position[0])
                central_channel = abs(end_position[1]) <= self.goal_channel_half_width_m
                if (
                    speed_kmh < self.shot_speed_threshold_kmh
                    or speed_kmh > self.shot_speed_ceiling_kmh
                    or travel_distance < self.shot_travel_distance_m
                    or goal_progress < self.shot_goal_progress_m
                    or not central_channel
                ):
                    continue
            else:
                if (
                    speed_kmh < self.shot_speed_threshold_kmh
                    or speed_kmh > self.shot_speed_ceiling_kmh
                    or travel_distance < self.shot_travel_distance_px
                ):
                    continue

            last_shot_frame = release_frame
            shots.append(
                {
                    "frame": release_frame,
                    "player": segment["player"],
                    "team": segment["team"],
                    "speed": float(speed_kmh),
                    "distance": float(travel_distance),
                    "type": "shot",
                }
            )

        return shots

    def detect_interceptions(self, tracks, passes):
        """
        Detect possession changes between teams that are not same-team passes.
        """
        interceptions = []
        segments = self._build_possession_segments(tracks, tracks["ball"])
        pass_frames = {event["frame"] for event in passes}

        for previous_segment, next_segment in zip(segments, segments[1:]):
            gap_frames = next_segment["start_frame"] - previous_segment["end_frame"] - 1
            if gap_frames > self.max_transition_gap_frames:
                continue
            if previous_segment["team"] == next_segment["team"]:
                continue
            if next_segment["start_frame"] in pass_frames:
                continue

            interceptions.append(
                {
                    "frame": next_segment["start_frame"],
                    "from_team": previous_segment["team"],
                    "to_team": next_segment["team"],
                    "from_player": previous_segment["player"],
                    "to_player": next_segment["player"],
                    "type": "interception",
                }
            )

        return interceptions

    def generate_event_summary(self, passes, shots, interceptions):
        """
        Generate summary statistics of all events.
        """
        summary = {
            "total_passes": len(passes),
            "total_shots": len(shots),
            "total_interceptions": len(interceptions),
            "passes_by_team": {},
            "shots_by_team": {},
            "passes_by_player": {},
            "shots_by_player": {},
        }

        for pass_event in passes:
            team = pass_event["team"]
            player = pass_event["from_player"]
            summary["passes_by_team"][team] = summary["passes_by_team"].get(team, 0) + 1
            summary["passes_by_player"][player] = summary["passes_by_player"].get(player, 0) + 1

        for shot_event in shots:
            team = shot_event["team"]
            player = shot_event["player"]
            summary["shots_by_team"][team] = summary["shots_by_team"].get(team, 0) + 1
            summary["shots_by_player"][player] = summary["shots_by_player"].get(player, 0) + 1

        return summary
