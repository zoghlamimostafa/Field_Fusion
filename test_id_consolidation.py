#!/usr/bin/env python3
"""Quick test of ID consolidation"""

import sys
sys.path.insert(0, '.')

from trackers.football_tracker import FootballTracker
from team_assigner import TeamAssigner
from player_id_consolidator import PlayerIDConsolidator
from utils import read_video

# Read first 100 frames
print("📹 Reading video...")
video_frames = read_video('input_videos/08fd33_4.mp4')[:100]
print(f"   Loaded {len(video_frames)} frames")

# Track
print("\n🎯 Tracking...")
tracker = FootballTracker(model_path=None, use_football_model=True)
tracks = tracker.get_object_tracks(video_frames, read_from_stub=False)

# Assign teams
print("\n👕 Team assignment...")
team_assigner = TeamAssigner()
team_assigner.assign_team_color(video_frames[0], tracks['players'][0])

for frame_num, player_track in enumerate(tracks['players']):
    for player_id, track in player_track.items():
        team = team_assigner.get_player_team(video_frames[frame_num], track['bbox'], player_id)
        tracks['players'][frame_num][player_id]['team'] = team

# Count before consolidation
player_ids_before = set()
for frame_tracks in tracks['players']:
    player_ids_before.update(frame_tracks.keys())

print(f"\n📊 Before consolidation: {len(player_ids_before)} unique player IDs")

# Consolidate
print("\n🔗 Consolidating...")
consolidator = PlayerIDConsolidator(expected_players_per_team=11)
id_mapping = consolidator.consolidate_player_ids(tracks)
tracks_consolidated = consolidator.apply_consolidation(tracks, id_mapping)

# Count after
player_ids_after = set()
for frame_tracks in tracks_consolidated['players']:
    player_ids_after.update(frame_tracks.keys())

print(f"\n✅ After consolidation: {len(player_ids_after)} unique player IDs")
print(f"   Reduction: {len(player_ids_before)} → {len(player_ids_after)} (-{len(player_ids_before) - len(player_ids_after)} IDs)")
