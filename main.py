# import os
# from utils import read_video, save_video
# from trackers import Tracker

# def main():
#     # Read Video
#     video_frames = read_video('input_videos/08fd33_4.mp4')

#     # Initialize Tracker
#     tracker = Tracker('models/best.pt')

#     stub_path = "stubs/track_stubs_file.pkl"

#     # Delete existing stub file if it exists
#     if os.path.exists(stub_path):
#         os.remove(stub_path)
#         print(f"Deleted existing stub file: {stub_path}")

#     # Generate new tracks and save to stub file
#     tracks = tracker.get_object_tracks(video_frames,
#                                        read_from_stub=False,  # Set this to False to regenerate
#                                        stub_path=stub_path)

#     print(f"New stub file created at: {stub_path}")

#     # # Draw output
#     # ## Draw object tracks
#     # output_video_frames = tracker.draw_annotations(video_frames, tracks) 

#     # # Save Video
#     # save_video(output_video_frames, 'output_videos/output_video.avi')

# if __name__ == '__main__':
#     main()



# from utils import read_video, save_video
# from trackers import Tracker


# def main():
#     # Read Video
#     video_frames = read_video('input_videos/08fd33_4.mp4')

#     # Initialize Tracker
#     tracker = Tracker('models/best.pt')

#     tracks = tracker.get_object_tracks(video_frames,
#                                        read_from_stub=True,
#                                        stub_path='stubs/track_stubs.pkl')
    
#     # Draw output
#     ## Draw object tracks
#     output_video_frames = tracker.draw_annotations(video_frames, tracks) 

#     # Save Video
#     save_video(output_video_frames, 'output_videos/output_video.avi')  



# if __name__ == '__main__':
#     main()    



import cv2
from utils import read_video, save_video
import numpy as np
from trackers import Tracker
from team_assigner import TeamAssigner
from player_ball_assigner import PlayerBallAssigner
from camera_movement_estimator import CameraMovementEstimator
from view_transformer import ViewTransformer
from speed_and_distance_estimator import SpeedAndDistance_Estimator


def main():
    input_path = 'input_videos/08fd33_4.mp4'
    output_path = 'output_videos/output_video.avi'
    stub_path = 'stubs/track_stubs.pkl'

    # Read Video
    video_frames = read_video(input_path)
    print(f"Number of input frames: {len(video_frames)}")


    if not video_frames:
        print("Error: No frames read from the video. Exiting.")
        return

    if video_frames[0] is None:
        print("Error: First frame is None. This shouldn't happen. Exiting.")
        return

    # Initialize Tracker
    import os
    model_path = 'models/best.pt' if os.path.exists('models/best.pt') else 'yolov8n.pt'
    print(f"Using model: {model_path}")
    tracker = Tracker(model_path)

    # Get object tracks
    tracks = tracker.get_object_tracks(video_frames, read_from_stub=True, stub_path=stub_path)
    print(f"Number of tracked frames: {len(tracks['players'])}")


    # Get object positionsS
    tracker.add_position_to_tracks(tracks)


    # Camera Movement Estimator
    camera_movement_estimator = CameraMovementEstimator(video_frames[0])
    camera_movement_per_frame = camera_movement_estimator.get_camera_movement(video_frames,
                                                                              read_from_stub = True,
                                                                              stub_path = 'stubs/camera_movement_stub.pkl')

    camera_movement_estimator.add_adjust_positions_to_tracks(tracks, camera_movement_per_frame)

    # View Transformer
    view_transformer = ViewTransformer()
    view_transformer.add_transformed_position_to_tracks(tracks)



    # Interpolate Ball Positions
    tracks["ball"] = tracker.interpolate_ball_positions(tracks["ball"])


    # Speed and distance estimator
    speed_and_distance_estimator = SpeedAndDistance_Estimator()
    speed_and_distance_estimator.add_speed_and_distance_to_tracks(tracks)


    # Assign Player Teams
    team_assigner = TeamAssigner()
    if tracks["players"] and tracks["players"][0]:
        team_assigner.assign_team_color(video_frames[0],
                                         tracks["players"][0])
        
        # Optimization: Cache team assignments by player_id
        player_team_cache = {}

        for frame_num, player_track in enumerate(tracks["players"]):
            for player_id, track in player_track.items():
                if player_id not in player_team_cache:
                    player_team_cache[player_id] = team_assigner.get_player_team(
                        video_frames[frame_num], track["bbox"], player_id
                    )
                
                team = player_team_cache[player_id]
                tracks["players"][frame_num][player_id]["team"] = team
                tracks["players"][frame_num][player_id]["team_color"] = team_assigner.team_colors[team]

    # Assign Ball Aquisition
    player_assigner =PlayerBallAssigner()
    team_ball_control = []
   
    for frame_num, player_track in enumerate(tracks['players']):
        if 1 not in tracks['ball'][frame_num]:
            team_ball_control.append(team_ball_control[-1] if team_ball_control else 1)
            continue
        ball_bbox = tracks['ball'][frame_num][1]['bbox']
        assigned_player = player_assigner.assign_ball_to_player(player_track, ball_bbox)

        if assigned_player != -1:
            tracks['players'][frame_num][assigned_player]['has_ball'] = True
            team_ball_control.append(tracks['players'][frame_num][assigned_player]['team'] if 'team' in tracks['players'][frame_num][assigned_player] else 1)

        else:
            team_ball_control.append(team_ball_control[-1] if team_ball_control else 1)
    team_ball_control = np.array(team_ball_control)       


    # Draw annotations
    output_video_frames = tracker.draw_annotations(video_frames, tracks, team_ball_control)
    print(f"Number of output frames: {len(output_video_frames)}")

    ## Draw Camera movement
    output_video_frames = camera_movement_estimator.draw_camera_movement(output_video_frames, camera_movement_per_frame)

    ## Draw Speed and Distance
    speed_and_distance_estimator.draw_speed_and_distance(output_video_frames, tracks)

    # Check for None frames
    none_frames = sum(1 for frame in output_video_frames if frame is None)
    print(f"Number of None frames in output: {none_frames}")

    if output_video_frames[0] is None:
        print("Error: First output frame is None. Cannot save video.")
        return

    # Save Video
    save_video(output_video_frames, output_path)

if __name__ == '__main__':
    main()