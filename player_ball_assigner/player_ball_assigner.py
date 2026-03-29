import sys
sys.path.append('../')
from utils import get_center_of_bbox, measure_distance


class PlayerBallAssigner():
    def __init__(self, max_player_ball_distance=70):
        """
        Initialize Player-Ball Assigner

        Args:
            max_player_ball_distance (int): Maximum distance in pixels to consider ball-player assignment
        """
        self.max_player_ball_distance = max_player_ball_distance

    def assign_ball_to_player(self, players, ball_bbox):
        """
        Assign ball to the nearest player within max distance

        Args:
            players (dict): Dictionary of player_id -> player_info with bbox
            ball_bbox (tuple): Ball bounding box coordinates (x1, y1, x2, y2)

        Returns:
            int: Player ID assigned to ball, or -1 if no player is close enough
        """
        # Validate inputs
        if not players:
            return -1

        if ball_bbox is None or len(ball_bbox) < 4:
            return -1

        try:
            ball_position = get_center_of_bbox(ball_bbox)
        except (TypeError, IndexError, ValueError) as e:
            print(f"Warning: Invalid ball bbox {ball_bbox}: {e}")
            return -1

        if ball_position is None:
            return -1

        minimum_distance = float('inf')
        assigned_player = -1

        for player_id, player in players.items():
            if not isinstance(player, dict) or "bbox" not in player:
                continue

            player_bbox = player["bbox"]

            # Validate player bbox
            if player_bbox is None or len(player_bbox) < 4:
                continue

            try:
                distance_left = measure_distance((player_bbox[0], player_bbox[-1]), ball_position)
                distance_right = measure_distance((player_bbox[2], player_bbox[-1]), ball_position)
                distance = min(distance_left, distance_right)
            except (TypeError, IndexError, ValueError) as e:
                print(f"Warning: Distance calculation failed for player {player_id}: {e}")
                continue

            if distance < self.max_player_ball_distance:
                if distance < minimum_distance:
                    minimum_distance = distance
                    assigned_player = player_id

        return assigned_player
