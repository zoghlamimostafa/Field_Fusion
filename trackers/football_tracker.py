
from ultralytics import YOLO
import supervision as sv
import pickle
import os
import cv2
import sys
import pandas as pd
import numpy as np
import torch

sys.path.append('../')
from utils import get_center_of_bbox, get_bbox_width, get_foot_position

class FootballTracker:
    """
    Enhanced tracker using football-specific YOLO model
    Model: uisikdag/yolo-v8-football-players-detection
    Classes: ball, goalkeeper, player, referee
    """
    def __init__(self, model_path, use_football_model=True, device=None):
        self.device = device if device is not None else (0 if torch.cuda.is_available() else "cpu")
        if use_football_model and (model_path is None or 'huggingface' not in model_path.lower()):
            # Load football-specific model from HuggingFace
            from huggingface_hub import hf_hub_download

            print("🔄 Loading football-specific model from HuggingFace...")
            model_path = hf_hub_download(
                repo_id="uisikdag/yolo-v8-football-players-detection",
                filename="best.pt"
            )

            # Patch torch.load for older model compatibility
            _original_torch_load = torch.load
            def patched_load(*args, **kwargs):
                kwargs['weights_only'] = False
                return _original_torch_load(*args, **kwargs)
            torch.load = patched_load

            self.model = YOLO(model_path)

            # Restore original torch.load
            torch.load = _original_torch_load
            print("✅ Football-specific model loaded!")
        else:
            self.model = YOLO(model_path)

        self.tracker = sv.ByteTrack()
        self.is_football_model = use_football_model
        print(f"🎯 Detection device: {self.device}")


    def add_position_to_tracks(self,tracks):
        for object, object_tracks in tracks.items():
            for frame_num, track in enumerate(object_tracks):
                for track_id, track_info in track.items():
                    bbox = track_info['bbox']
                    if object == 'ball':
                        position= get_center_of_bbox(bbox)
                    else:
                        position = get_foot_position(bbox)
                    tracks[object][frame_num][track_id]['position'] = position



    def interpolate_ball_positions(self, ball_positions):
        ball_positions = [x.get(1, {}).get('bbox', []) for x in ball_positions]
        df_ball_positions = pd.DataFrame(ball_positions, columns=['x1', 'y1', 'x2', 'y2'])

        # Interpolate missing values
        df_ball_positions  = df_ball_positions.interpolate()
        df_ball_positions = df_ball_positions.bfill()


        ball_positions = [{1: {'bbox': x}}for x in df_ball_positions.to_numpy().tolist()]

        return ball_positions



    def detect_frames(self, frames):
        batch_size = 20
        detections = []
        for i in range(0, len(frames), batch_size):
            detections_batch = self.model.predict(
                frames[i:i+batch_size],
                conf=0.1,
                verbose=False,
                device=self.device,
            )
            detections += detections_batch
        return detections

    def get_object_tracks(self, frames, read_from_stub=False, stub_path=None):
        if read_from_stub and stub_path is not None and os.path.exists(stub_path):
            with open(stub_path, 'rb') as f:
                tracks = pickle.load(f)
            return tracks

        detections = self.detect_frames(frames)

        tracks = {
            "players": [],
            "referees": [],
            "ball": [],
            "goalkeepers": []  # New: separate goalkeeper tracking
        }

        for frame_num, detection in enumerate(detections):
            cls_names = detection.names
            cls_names_inv = {v: k for k, v in cls_names.items()}

            # Convert to supervision Detection format
            detection_supervision = sv.Detections.from_ultralytics(detection)

            # Get class IDs
            player_class_id = cls_names_inv.get('player', cls_names_inv.get('person'))
            goalkeeper_class_id = cls_names_inv.get('goalkeeper')
            ball_class_id = cls_names_inv.get('ball', cls_names_inv.get('sports ball'))
            referee_class_id = cls_names_inv.get('referee')

            # Convert GoalKeeper to player object for unified tracking
            goalkeeper_detections = []
            for object_ind, class_id in enumerate(detection_supervision.class_id):
                if cls_names[class_id] == "goalkeeper":
                    goalkeeper_detections.append(object_ind)
                    if player_class_id is not None:
                        detection_supervision.class_id[object_ind] = player_class_id

            # Track Objects
            detection_with_tracks = self.tracker.update_with_detections(detection_supervision)

            tracks["players"].append({})
            tracks["referees"].append({})
            tracks["ball"].append({})
            tracks["goalkeepers"].append({})

            for frame_detection in detection_with_tracks:
                bbox = frame_detection[0].tolist()
                cls_id = frame_detection[3]
                track_id = frame_detection[4]

                if player_class_id is not None and cls_id == player_class_id:
                    tracks["players"][frame_num][track_id] = {"bbox": bbox}

                if referee_class_id is not None and cls_id == referee_class_id:
                    tracks["referees"][frame_num][track_id] = {"bbox": bbox}

            # Track goalkeepers separately (for analytics)
            goalkeeper_track_ids = []
            for detection_idx in goalkeeper_detections:
                # Find matching track_id in detection_with_tracks by comparing bbox
                for track_detection in detection_with_tracks:
                    bbox = track_detection[0].tolist()
                    track_id = track_detection[4]

                    # Store goalkeeper track IDs
                    if detection_idx < len(detection_supervision):
                        orig_bbox = detection_supervision.xyxy[detection_idx].tolist()
                        if np.allclose(bbox, orig_bbox, atol=1.0):
                            goalkeeper_track_ids.append(track_id)
                            tracks["goalkeepers"][frame_num][track_id] = {"bbox": bbox}
                            break

            for frame_detection in detection_supervision:
                bbox = frame_detection[0].tolist()
                cls_id = frame_detection[3]

                if ball_class_id is not None and cls_id == ball_class_id:
                    tracks["ball"][frame_num][1] = {"bbox": bbox}

        if stub_path is not None:
            with open(stub_path, 'wb') as f:
                pickle.dump(tracks, f)
        return tracks


    def draw_ellipse(self, frame, bbox, color, track_id=None):
        y2 = int(bbox[3])
        x_center, _ = get_center_of_bbox(bbox)
        width = get_bbox_width(bbox)

        cv2.ellipse(
            frame,
            center=(int(x_center), y2),
            axes=(int(width), int(0.35 * width)),
            angle=0.0,
            startAngle=-45,
            endAngle=235,
            color=color,
            thickness=2,
            lineType=cv2.LINE_4
        )

        rectangle_width = 40
        rectangle_height = 20
        x1_rect = x_center - rectangle_width//2
        x2_rect = x_center + rectangle_width//2
        y1_rect = (y2 - rectangle_height//2) + 15
        y2_rect = (y2 + rectangle_height//2) + 15


        if track_id is not None:
            cv2.rectangle(frame,
                          (int(x1_rect), int(y1_rect)),
                          (int(x2_rect), int(y2_rect)),
                          color,
                          cv2.FILLED)

            x1_text = x1_rect + 12
            if track_id > 99:
                x1_text -= 10

            cv2.putText(
                frame,
                f"{track_id}",
                (int(x1_text), int(y1_rect + 15)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0,0,0),
                2
            )

        return frame


    def draw_triangle(self,frame,bbox,color):
        y= int(bbox[1])
        x,_ = get_center_of_bbox(bbox)

        triangle_points = np.array([
            [x,y],
            [x-10,y-20],
            [x+10,y-20],
        ])
        cv2.drawContours(frame, [triangle_points],0,color, cv2.FILLED)
        cv2.drawContours(frame, [triangle_points],0,(0,0,0), 2)

        return frame

    def draw_team_ball_control(self,frame,frame_num,team_ball_control):
        # Draw a semi-transparent rectangle
        overlay = frame.copy()
        cv2.rectangle(overlay, (1350, 850), (1900,970), (255,255,255), -1 )
        alpha = 0.4
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


        team_ball_control_till_frame = team_ball_control[:frame_num+1]
        # Get the number of time each team had ball control
        team_1_num_frames = team_ball_control_till_frame[team_ball_control_till_frame==1].shape[0]
        team_2_num_frames = team_ball_control_till_frame[team_ball_control_till_frame==2].shape[0]
        team_1 = team_1_num_frames/(team_1_num_frames+team_2_num_frames)
        team_2 = team_2_num_frames/(team_1_num_frames+team_2_num_frames)

        cv2.putText(frame, f"Team 1 Ball Control: {team_1*100:.2f}%",(1400,900), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 3)
        cv2.putText(frame, f"Team 2 Ball Control: {team_2*100:.2f}%",(1400,950), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 3)

        return frame


    def draw_annotations(self, video_frames, tracks, team_ball_control):
        output_video_frames = []
        for frame_num, frame in enumerate(video_frames):
            if frame is None:
                print(f"Warning: Input frame {frame_num} is None. Skipping.")
                continue

            annotated_frame = frame.copy()

            player_dict = tracks["players"][frame_num]
            ball_dict = tracks["ball"][frame_num]
            referee_dict = tracks["referees"][frame_num]
            goalkeeper_dict = tracks.get("goalkeepers", [{}])[frame_num] if frame_num < len(tracks.get("goalkeepers", [])) else {}

            # Draw Players
            for track_id, player in player_dict.items():
                # Check if this is a goalkeeper
                is_goalkeeper = track_id in goalkeeper_dict
                color = (255, 165, 0) if is_goalkeeper else player.get("team_color", (0, 0, 255))  # Orange for goalkeepers
                annotated_frame = self.draw_ellipse(annotated_frame, player['bbox'], color, track_id)

                if player.get('has_ball', False):
                    annotated_frame = self.draw_triangle(annotated_frame, player['bbox'], (0, 0, 255))

            # Draw ball
            for track_id, ball in ball_dict.items():
                annotated_frame = self.draw_triangle(annotated_frame, ball["bbox"],(0,255,0))

            # Draw referees
            for _, referee in referee_dict.items():
                annotated_frame = self.draw_ellipse(annotated_frame, referee['bbox'], (0, 255, 255))


            # Draw Team Ball Control
            annotated_frame = self.draw_team_ball_control(annotated_frame, frame_num, team_ball_control)

            output_video_frames.append(annotated_frame)

        print(f"Annotated {len(output_video_frames)} frames")
        if output_video_frames and output_video_frames[0] is None:
            print("Error: First annotated frame is None")
        return output_video_frames

    def detect_frame(self, frame):
        """
        Detect and track objects in a single frame (for real-time streaming)

        Args:
            frame: Single video frame (numpy array)

        Returns:
            Dict with tracks for the frame:
            {
                'players': {player_id: {'bbox': [x1,y1,x2,y2]}},
                'ball': {1: {'bbox': [x1,y1,x2,y2]}},
                'goalkeepers': {...},
                'referees': {...}
            }
        """
        # Run detection
        results = self.model.predict(frame, conf=0.1, device=self.device)[0]

        # Convert to supervision format
        detections = sv.Detections.from_ultralytics(results)

        # Update tracker
        detections_with_tracks = self.tracker.update_with_detections(detections)

        # Organize tracks by object type
        tracks = {
            'players': {},
            'ball': {},
            'goalkeepers': {},
            'referees': {}
        }

        for detection_idx, track_id in enumerate(detections_with_tracks.tracker_id):
            bbox = detections_with_tracks.xyxy[detection_idx].tolist()
            class_id = detections_with_tracks.class_id[detection_idx]

            if self.is_football_model:
                # Football-specific model: 0=ball, 1=goalkeeper, 2=player, 3=referee
                if class_id == 0:  # Ball
                    tracks['ball'][1] = {'bbox': bbox}
                elif class_id == 1:  # Goalkeeper
                    tracks['goalkeepers'][track_id] = {'bbox': bbox}
                elif class_id == 2:  # Player
                    tracks['players'][track_id] = {'bbox': bbox}
                elif class_id == 3:  # Referee
                    tracks['referees'][track_id] = {'bbox': bbox}
            else:
                # Generic model
                if class_id == 32:  # Sports ball
                    tracks['ball'][1] = {'bbox': bbox}
                elif class_id == 0:  # Person
                    tracks['players'][track_id] = {'bbox': bbox}

        return tracks
