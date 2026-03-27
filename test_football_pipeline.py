#!/usr/bin/env python3
"""
Test the complete pipeline with football-specific model
"""

from trackers.football_tracker import FootballTracker
from team_assigner import TeamAssigner
from player_ball_assigner import PlayerBallAssigner
from utils import read_video, save_video
import cv2
import numpy as np

def main():
    print("=" * 60)
    print("Testing Complete Football Pipeline")
    print("=" * 60)

    # Read video
    print("\n📹 Reading video...")
    video_frames = read_video('input_videos/08fd33_4.mp4')
    print(f"   Total frames: {len(video_frames)}")

    # Initialize tracker with football-specific model
    print("\n🔄 Initializing football-specific tracker...")
    tracker = FootballTracker(model_path=None, use_football_model=True)

    # Get tracks
    print("\n🎯 Detecting and tracking objects...")
    tracks = tracker.get_object_tracks(
        video_frames,
        read_from_stub=False,
        stub_path='stubs/track_stubs_football.pkl'
    )

    print(f"\n📊 Detection Statistics:")
    print(f"   Players tracked: {sum(len(frame) for frame in tracks['players'])} detections")
    print(f"   Goalkeepers: {sum(len(frame) for frame in tracks['goalkeepers'])} detections")
    print(f"   Referees: {sum(len(frame) for frame in tracks['referees'])} detections")
    print(f"   Ball: {sum(len(frame) for frame in tracks['ball'])} detections")

    # Interpolate ball positions
    print("\n⚽ Interpolating ball positions...")
    tracks["ball"] = tracker.interpolate_ball_positions(tracks["ball"])

    # Assign teams
    print("\n👕 Assigning teams...")
    team_assigner = TeamAssigner()
    team_assigner.assign_team_color(video_frames[0], tracks['players'][0])

    for frame_num, player_track in enumerate(tracks['players']):
        for player_id, track in player_track.items():
            team = team_assigner.get_player_team(video_frames[frame_num], track['bbox'], player_id)
            tracks['players'][frame_num][player_id]['team'] = team
            tracks['players'][frame_num][player_id]['team_color'] = team_assigner.team_colors[team]

    # Assign ball possession
    print("\n🎯 Assigning ball possession...")
    player_assigner = PlayerBallAssigner()
    team_ball_control = []

    for frame_num, player_track in enumerate(tracks['players']):
        ball_bbox = tracks['ball'][frame_num][1]['bbox']
        assigned_player = player_assigner.assign_ball_to_player(player_track, ball_bbox)

        if assigned_player != -1:
            tracks['players'][frame_num][assigned_player]['has_ball'] = True
            team_ball_control.append(tracks['players'][frame_num][assigned_player]['team'])
        else:
            team_ball_control.append(team_ball_control[-1] if team_ball_control else 0)

    team_ball_control = np.array(team_ball_control)

    # Draw annotations
    print("\n🎨 Drawing annotations...")
    output_video_frames = tracker.draw_annotations(video_frames, tracks, team_ball_control)

    # Save output
    print("\n💾 Saving output video...")
    save_video(output_video_frames, 'output_videos/output_football_model.avi')

    print("\n✅ Pipeline complete!")
    print(f"   Output saved to: output_videos/output_football_model.avi")

    # Print team statistics
    print("\n📊 Team Statistics:")
    team_1_frames = (team_ball_control == 1).sum()
    team_2_frames = (team_ball_control == 2).sum()
    total = team_1_frames + team_2_frames
    if total > 0:
        print(f"   Team 1 possession: {team_1_frames/total*100:.1f}%")
        print(f"   Team 2 possession: {team_2_frames/total*100:.1f}%")

    print("=" * 60)

if __name__ == '__main__':
    main()
