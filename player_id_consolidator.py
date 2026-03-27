import numpy as np
from collections import defaultdict
from scipy.spatial.distance import cdist

class PlayerIDConsolidator:
    """
    Consolidates fragmented player IDs into actual player count (11 per team)
    Handles ID switches from tracking failures
    """

    def __init__(self, expected_players_per_team=11):
        self.expected_players_per_team = expected_players_per_team

    def consolidate_player_ids(self, tracks):
        """
        Consolidate fragmented IDs into actual players
        Returns: mapping from old_id -> new_id
        """
        # Collect all player statistics
        player_stats = defaultdict(lambda: {
            'frames': [],
            'positions': [],
            'team': None
        })

        for frame_num, frame_tracks in enumerate(tracks['players']):
            for player_id, track_info in frame_tracks.items():
                player_stats[player_id]['frames'].append(frame_num)
                if 'position' in track_info:
                    player_stats[player_id]['positions'].append(track_info['position'])
                if 'team' in track_info and player_stats[player_id]['team'] is None:
                    player_stats[player_id]['team'] = track_info['team']

        # Separate by team
        team_1_ids = [pid for pid, stats in player_stats.items() if stats['team'] == 1]
        team_2_ids = [pid for pid, stats in player_stats.items() if stats['team'] == 2]

        print(f"\n🔍 ID Consolidation Analysis:")
        print(f"   Team 1: {len(team_1_ids)} fragmented IDs")
        print(f"   Team 2: {len(team_2_ids)} fragmented IDs")
        print(f"   Expected: {self.expected_players_per_team} players per team")

        # Consolidate each team
        team_1_mapping = self._consolidate_team(player_stats, team_1_ids, team=1)
        team_2_mapping = self._consolidate_team(player_stats, team_2_ids, team=2)

        # Combine mappings
        id_mapping = {**team_1_mapping, **team_2_mapping}

        print(f"\n✅ Consolidated to:")
        print(f"   Team 1: {len(set(team_1_mapping.values()))} actual players")
        print(f"   Team 2: {len(set(team_2_mapping.values()))} actual players")

        return id_mapping

    def _consolidate_team(self, player_stats, player_ids, team):
        """
        Consolidate IDs for one team using temporal and spatial proximity
        """
        if len(player_ids) <= self.expected_players_per_team:
            # No consolidation needed
            return {pid: pid for pid in player_ids}

        # Sort by total frames (keep most persistent IDs)
        sorted_ids = sorted(player_ids,
                          key=lambda x: len(player_stats[x]['frames']),
                          reverse=True)

        # Start with top N most persistent IDs as "main" players
        main_players = sorted_ids[:self.expected_players_per_team]
        fragmented_ids = sorted_ids[self.expected_players_per_team:]

        # Initialize mapping
        id_mapping = {pid: pid for pid in main_players}

        # Try to merge fragmented IDs with main players
        for frag_id in fragmented_ids:
            frag_frames = set(player_stats[frag_id]['frames'])
            frag_positions = player_stats[frag_id]['positions']

            if not frag_positions:
                # Merge with first main player as fallback
                id_mapping[frag_id] = main_players[0]
                continue

            frag_avg_pos = np.mean(frag_positions, axis=0)

            # Find best matching main player
            best_match = None
            best_score = float('inf')

            for main_id in main_players:
                main_frames = set(player_stats[main_id]['frames'])
                main_positions = player_stats[main_id]['positions']

                # Check for temporal overlap (should be minimal)
                overlap = len(frag_frames & main_frames)
                if overlap > 10:  # Too much overlap, probably different players
                    continue

                # Check spatial proximity
                if main_positions:
                    main_avg_pos = np.mean(main_positions, axis=0)
                    spatial_dist = np.linalg.norm(frag_avg_pos - main_avg_pos)

                    # Combine temporal gap and spatial distance
                    temporal_gap = min(abs(min(frag_frames) - max(main_frames)),
                                     abs(max(frag_frames) - min(main_frames)))

                    # Score: prefer close spatial distance and small temporal gap
                    score = spatial_dist + (temporal_gap * 0.1)

                    if score < best_score:
                        best_score = score
                        best_match = main_id

            if best_match:
                id_mapping[frag_id] = best_match
            else:
                # Fallback: merge with closest main player by position
                id_mapping[frag_id] = main_players[0]

        return id_mapping

    def apply_consolidation(self, tracks, id_mapping):
        """
        Apply ID mapping to tracks
        """
        consolidated_tracks = {
            'players': [],
            'referees': tracks.get('referees', []),
            'ball': tracks.get('ball', []),
            'goalkeepers': tracks.get('goalkeepers', [])
        }

        for frame_num, frame_tracks in enumerate(tracks['players']):
            new_frame = {}

            for old_id, track_info in frame_tracks.items():
                new_id = id_mapping.get(old_id, old_id)

                # If new_id already exists in this frame, keep the one with better data
                if new_id in new_frame:
                    # Keep the one with more information
                    existing_keys = len(new_frame[new_id].keys())
                    new_keys = len(track_info.keys())
                    if new_keys > existing_keys:
                        new_frame[new_id] = track_info.copy()
                else:
                    new_frame[new_id] = track_info.copy()

            consolidated_tracks['players'].append(new_frame)

        return consolidated_tracks
