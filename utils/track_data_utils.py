from typing import Dict, Iterator, List, Tuple


def get_player_frames(tracks: Dict) -> Dict[int, Dict]:
    """Normalize player tracking data to frame-number -> frame-data."""
    if not isinstance(tracks, dict):
        return {}

    players = tracks.get("players", {})
    if isinstance(players, dict):
        return players
    if isinstance(players, list):
        return {frame_num: frame_data or {} for frame_num, frame_data in enumerate(players)}
    return {}


def get_frame_numbers(tracks: Dict) -> List[int]:
    """Return sorted frame numbers for player tracking data."""
    return sorted(get_player_frames(tracks).keys())


def iter_player_frames(tracks: Dict) -> Iterator[Tuple[int, Dict]]:
    """Iterate over normalized player frames."""
    player_frames = get_player_frames(tracks)
    for frame_num in sorted(player_frames.keys()):
        yield frame_num, player_frames[frame_num]


def get_player_stats_list(analytics: Dict) -> List[Dict]:
    """Normalize analytics player stats to a list of dicts."""
    if not isinstance(analytics, dict):
        return []

    player_stats = analytics.get("player_stats", [])
    if isinstance(player_stats, list):
        return [stats for stats in player_stats if isinstance(stats, dict)]

    if isinstance(player_stats, dict):
        normalized = []
        for player_id, stats in player_stats.items():
            if not isinstance(stats, dict):
                continue
            stats_copy = dict(stats)
            stats_copy.setdefault("player_id", player_id)
            normalized.append(stats_copy)
        return normalized

    return []


def iter_player_stats(analytics: Dict) -> Iterator[Tuple[int, Dict]]:
    """Iterate over normalized player stats as (player_id, stats)."""
    for stats in get_player_stats_list(analytics):
        player_id = stats.get("player_id")
        if player_id is None:
            continue
        yield player_id, stats


def count_player_stats(analytics: Dict) -> int:
    """Count normalized player stats entries."""
    return len(get_player_stats_list(analytics))


def get_player_frame_count(tracks: Dict, player_id: int) -> int:
    """Count the number of frames where a player is present."""
    return sum(1 for _, frame_data in iter_player_frames(tracks) if player_id in frame_data)
