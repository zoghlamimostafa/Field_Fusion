"""
Corner Kick Detector for TacticAI
Detects corner kicks from tracking data and event data
Inspired by ChloeGobe/corner-kicks-analysis repository
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class CornerSide(Enum):
    """Corner kick side"""
    LEFT = "left"
    RIGHT = "right"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


class PlayerRole(Enum):
    """Player role in corner kick"""
    CORNER_TAKER = "taker"
    ATTACKER = "attacker"
    DEFENDER = "defender"
    GOALKEEPER = "goalkeeper"
    UNKNOWN = "unknown"


@dataclass
class PlayerPosition:
    """Player position at corner kick moment"""
    player_id: int
    team: int
    x: float  # meters
    y: float  # meters
    vx: float = 0.0  # velocity x (m/s)
    vy: float = 0.0  # velocity y (m/s)
    role: PlayerRole = PlayerRole.UNKNOWN
    distance_to_goal: float = 0.0
    distance_to_ball: float = 0.0


@dataclass
class CornerKick:
    """Container for corner kick data"""
    # Basic info
    frame_id: int
    timestamp: float
    corner_side: CornerSide
    attacking_team: int
    defending_team: int

    # Player positions
    attacking_players: List[PlayerPosition] = field(default_factory=list)
    defending_players: List[PlayerPosition] = field(default_factory=list)

    # Ball position
    ball_x: float = 0.0
    ball_y: float = 0.0

    # Outcome (if known)
    outcome: Optional[str] = None  # 'shot', 'goal', 'clearance', 'possession_retained'
    outcome_frame: Optional[int] = None
    outcome_timestamp: Optional[float] = None

    # Metadata
    match_id: Optional[str] = None
    period: int = 1

    def __post_init__(self):
        """Calculate derived metrics"""
        goal_x = 105.0  # Assuming attacking toward goal at x=105
        goal_y = 34.0   # Center of goal

        for player in self.attacking_players + self.defending_players:
            player.distance_to_goal = np.sqrt(
                (goal_x - player.x)**2 + (goal_y - player.y)**2
            )
            player.distance_to_ball = np.sqrt(
                (self.ball_x - player.x)**2 + (self.ball_y - player.y)**2
            )


class CornerKickDetector:
    """
    Detect corner kicks from tracking/event data

    Detection methods:
    1. From event data (StatsBomb/kloppy format)
    2. From tracking data (spatial analysis)
    """

    def __init__(self, pitch_length=105, pitch_width=68):
        """
        Initialize detector

        Args:
            pitch_length: Pitch length in meters (default: 105)
            pitch_width: Pitch width in meters (default: 68)
        """
        self.pitch_length = pitch_length
        self.pitch_width = pitch_width

        # Detection parameters
        self.corner_radius = 5.0  # meters from corner
        self.penalty_box_x = 88.5  # Penalty box edge
        self.penalty_box_y_min = 18.3
        self.penalty_box_y_max = 49.7

        # Clustering parameters
        self.cluster_threshold = 10.0  # meters
        self.min_players_in_box = 6  # Minimum players in penalty area

    def detect_from_events(self, events: List[Dict]) -> List[CornerKick]:
        """
        Detect corner kicks from event data (StatsBomb/kloppy format)

        Args:
            events: List of event dictionaries from kloppy_data_loader

        Returns:
            List of CornerKick objects
        """
        corners = []

        for i, event in enumerate(events):
            # Check if event is a corner kick
            event_type = event.get('type', '').upper()

            if 'CORNER' in event_type or event.get('sub_type') == 'corner_kick':
                corner = self._extract_corner_from_event(event, i, events)
                if corner:
                    corners.append(corner)

        print(f"Detected {len(corners)} corner kicks from event data")
        return corners

    def _extract_corner_from_event(self, event: Dict, event_idx: int,
                                   all_events: List[Dict]) -> Optional[CornerKick]:
        """Extract CornerKick object from event"""
        try:
            # Get basic info
            frame_id = event.get('frame', event_idx)
            timestamp = event.get('timestamp', event_idx * 0.04)  # Assume 25fps
            team = event.get('team', 1)

            # Determine corner side
            x = event.get('x', event.get('x_start', 0))
            y = event.get('y', event.get('y_start', 0))
            corner_side = self._determine_corner_side(x, y)

            # Create corner object
            corner = CornerKick(
                frame_id=frame_id,
                timestamp=timestamp,
                corner_side=corner_side,
                attacking_team=team,
                defending_team=2 if team == 1 else 1,
                ball_x=x,
                ball_y=y
            )

            # Try to find outcome in next few events
            outcome = self._find_outcome(event_idx, all_events, max_lookahead=10)
            if outcome:
                corner.outcome = outcome['type']
                corner.outcome_frame = outcome['frame']
                corner.outcome_timestamp = outcome['timestamp']

            return corner

        except Exception as e:
            print(f"Error extracting corner from event: {e}")
            return None

    def detect_from_tracking(self, tracking_data: Dict,
                            fps: int = 25) -> List[CornerKick]:
        """
        Detect corner kicks from tracking data

        Detection criteria:
        1. Ball near corner (<5m)
        2. Player clustering in penalty box
        3. Static phase (low ball velocity)

        Args:
            tracking_data: Dictionary with 'players' and 'ball' lists
            fps: Frames per second

        Returns:
            List of CornerKick objects
        """
        corners = []

        if 'ball' not in tracking_data or 'players' not in tracking_data:
            print("Warning: tracking_data missing 'ball' or 'players'")
            return corners

        ball_frames = tracking_data.get('ball', [])
        player_frames = tracking_data.get('players', [])

        # Group player data by frame
        players_by_frame = {}
        for player_data in player_frames:
            frame = player_data.get('frame', 0)
            if frame not in players_by_frame:
                players_by_frame[frame] = []
            players_by_frame[frame].append(player_data)

        # Scan through frames
        i = 0
        while i < len(ball_frames):
            frame_data = ball_frames[i]
            frame_id = frame_data.get('frame', i)

            if self._is_corner_situation(frame_data, players_by_frame.get(frame_id, []), frame_id):
                # Extract corner
                corner = self._extract_corner_from_tracking(
                    frame_id, frame_data, players_by_frame.get(frame_id, []),
                    ball_frames, fps
                )

                if corner:
                    corners.append(corner)
                    # Skip ahead to avoid duplicates
                    i += fps * 5  # Skip 5 seconds
                    continue

            i += 1

        print(f"Detected {len(corners)} corner kicks from tracking data")
        return corners

    def _is_corner_situation(self, ball_frame: Dict,
                            players: List[Dict], frame_id: int) -> bool:
        """Check if current frame represents corner kick setup"""

        # Get ball position
        ball_pos = ball_frame.get('position', [0, 0])
        if len(ball_pos) < 2:
            return False

        ball_x, ball_y = ball_pos[0], ball_pos[1]

        # Check 1: Ball near corner
        near_corner = self._is_near_corner(ball_x, ball_y)
        if not near_corner:
            return False

        # Check 2: Player clustering in penalty box
        players_in_box = 0
        for player in players:
            pos = player.get('position', [0, 0])
            if len(pos) >= 2:
                px, py = pos[0], pos[1]
                if self._is_in_penalty_box(px, py):
                    players_in_box += 1

        if players_in_box < self.min_players_in_box:
            return False

        # Check 3: Low ball velocity (static phase)
        # Simplified - just check if ball hasn't moved much
        # In production, calculate velocity from position history

        return True

    def _is_near_corner(self, x: float, y: float) -> bool:
        """Check if position is near a corner"""
        # Check all four corners
        corners = [
            (0, 0), (0, self.pitch_width),
            (self.pitch_length, 0), (self.pitch_length, self.pitch_width)
        ]

        for cx, cy in corners:
            dist = np.sqrt((x - cx)**2 + (y - cy)**2)
            if dist < self.corner_radius:
                return True

        return False

    def _is_in_penalty_box(self, x: float, y: float) -> bool:
        """Check if position is in penalty box"""
        return (x >= self.penalty_box_x and
                y >= self.penalty_box_y_min and
                y <= self.penalty_box_y_max)

    def _determine_corner_side(self, x: float, y: float) -> CornerSide:
        """Determine which corner"""
        mid_x = self.pitch_length / 2
        mid_y = self.pitch_width / 2

        if x < mid_x and y < mid_y:
            return CornerSide.BOTTOM_LEFT
        elif x < mid_x and y >= mid_y:
            return CornerSide.TOP_LEFT
        elif x >= mid_x and y < mid_y:
            return CornerSide.BOTTOM_RIGHT
        else:
            return CornerSide.TOP_RIGHT

    def _extract_corner_from_tracking(self, frame_id: int, ball_frame: Dict,
                                     players: List[Dict], all_ball_frames: List[Dict],
                                     fps: int) -> Optional[CornerKick]:
        """Extract CornerKick from tracking data"""
        try:
            ball_pos = ball_frame.get('position', [0, 0])
            ball_x, ball_y = ball_pos[0], ball_pos[1]

            # Determine attacking team (team on the side of the corner)
            # Simplified: assume team 1 attacks right, team 2 attacks left
            attacking_team = 1 if ball_x > self.pitch_length / 2 else 2

            corner = CornerKick(
                frame_id=frame_id,
                timestamp=frame_id / fps,
                corner_side=self._determine_corner_side(ball_x, ball_y),
                attacking_team=attacking_team,
                defending_team=2 if attacking_team == 1 else 1,
                ball_x=ball_x,
                ball_y=ball_y
            )

            # Extract player positions
            for player in players:
                pos = player.get('position', [0, 0])
                if len(pos) < 2:
                    continue

                px, py = pos[0], pos[1]
                team = player.get('team', 1)
                player_id = player.get('player_id', 0)

                player_pos = PlayerPosition(
                    player_id=player_id,
                    team=team,
                    x=px,
                    y=py
                )

                if team == corner.attacking_team:
                    corner.attacking_players.append(player_pos)
                else:
                    corner.defending_players.append(player_pos)

            # Assign roles
            self._assign_player_roles(corner)

            # Try to detect outcome
            outcome = self._detect_outcome_from_tracking(frame_id, all_ball_frames, fps)
            if outcome:
                corner.outcome = outcome['type']
                corner.outcome_frame = outcome['frame']
                corner.outcome_timestamp = outcome['timestamp']

            return corner

        except Exception as e:
            print(f"Error extracting corner from tracking: {e}")
            return None

    def _assign_player_roles(self, corner: CornerKick):
        """Assign roles to players based on positions"""
        # Find corner taker (closest attacking player to ball)
        min_dist = float('inf')
        taker_idx = -1

        for i, player in enumerate(corner.attacking_players):
            if player.distance_to_ball < min_dist:
                min_dist = player.distance_to_ball
                taker_idx = i

        if taker_idx >= 0:
            corner.attacking_players[taker_idx].role = PlayerRole.CORNER_TAKER

        # Assign attackers (in penalty box)
        for player in corner.attacking_players:
            if player.role == PlayerRole.UNKNOWN:
                if self._is_in_penalty_box(player.x, player.y):
                    player.role = PlayerRole.ATTACKER

        # Assign goalkeeper (furthest defender from ball)
        max_dist = 0
        gk_idx = -1

        for i, player in enumerate(corner.defending_players):
            if player.distance_to_ball > max_dist:
                max_dist = player.distance_to_ball
                gk_idx = i

        if gk_idx >= 0:
            corner.defending_players[gk_idx].role = PlayerRole.GOALKEEPER

        # Remaining are defenders
        for player in corner.defending_players:
            if player.role == PlayerRole.UNKNOWN:
                player.role = PlayerRole.DEFENDER

    def _find_outcome(self, event_idx: int, events: List[Dict],
                     max_lookahead: int = 10) -> Optional[Dict]:
        """Find outcome of corner kick in next few events"""
        for i in range(event_idx + 1, min(event_idx + max_lookahead, len(events))):
            event = events[i]
            event_type = event.get('type', '').upper()

            if 'SHOT' in event_type:
                return {
                    'type': 'shot',
                    'frame': event.get('frame', i),
                    'timestamp': event.get('timestamp', i * 0.04)
                }
            elif 'GOAL' in event_type:
                return {
                    'type': 'goal',
                    'frame': event.get('frame', i),
                    'timestamp': event.get('timestamp', i * 0.04)
                }
            elif 'CLEARANCE' in event_type or 'INTERCEPTION' in event_type:
                return {
                    'type': 'clearance',
                    'frame': event.get('frame', i),
                    'timestamp': event.get('timestamp', i * 0.04)
                }

        return None

    def _detect_outcome_from_tracking(self, corner_frame: int,
                                     ball_frames: List[Dict],
                                     fps: int) -> Optional[Dict]:
        """Detect outcome from tracking data (simplified)"""
        # Look ahead 10 seconds
        max_frame = corner_frame + fps * 10

        for i in range(corner_frame + 1, min(max_frame, len(ball_frames))):
            frame_data = ball_frames[i]
            pos = frame_data.get('position', [0, 0])

            if len(pos) >= 2:
                x, y = pos[0], pos[1]

                # Check if ball near goal
                if x > 100 and 30 < y < 38:
                    return {
                        'type': 'shot',
                        'frame': frame_data.get('frame', i),
                        'timestamp': i / fps
                    }

                # Check if ball cleared (far from penalty box)
                if x < 70:
                    return {
                        'type': 'clearance',
                        'frame': frame_data.get('frame', i),
                        'timestamp': i / fps
                    }

        return {'type': 'possession_retained', 'frame': max_frame, 'timestamp': max_frame / fps}

    def export_corners(self, corners: List[CornerKick]) -> List[Dict]:
        """Export corners to dictionary format"""
        return [self._corner_to_dict(corner) for corner in corners]

    def _corner_to_dict(self, corner: CornerKick) -> Dict:
        """Convert CornerKick to dictionary"""
        return {
            'frame_id': corner.frame_id,
            'timestamp': corner.timestamp,
            'corner_side': corner.corner_side.value,
            'attacking_team': corner.attacking_team,
            'ball_position': [corner.ball_x, corner.ball_y],
            'attacking_players': [
                {
                    'id': p.player_id,
                    'position': [p.x, p.y],
                    'velocity': [p.vx, p.vy],
                    'role': p.role.value
                }
                for p in corner.attacking_players
            ],
            'defending_players': [
                {
                    'id': p.player_id,
                    'position': [p.x, p.y],
                    'velocity': [p.vx, p.vy],
                    'role': p.role.value
                }
                for p in corner.defending_players
            ],
            'outcome': corner.outcome,
            'outcome_frame': corner.outcome_frame
        }


def demo_corner_detector():
    """Demonstrate corner kick detection"""
    print("=" * 80)
    print("Corner Kick Detector Demo")
    print("=" * 80)

    # Demo 1: Detect from StatsBomb events
    print("\n1. Testing with StatsBomb data...")
    try:
        from kloppy_data_loader import KloppyDataLoader

        loader = KloppyDataLoader()
        data = loader.load_statsbomb_open_data(match_id=3788741)

        # Convert to our format
        events = loader.convert_events_to_training_data(data)
        all_events = events['all_events']

        # Detect corners
        detector = CornerKickDetector()
        corners = detector.detect_from_events(all_events)

        if corners:
            print(f"\n✓ Found {len(corners)} corners")
            print(f"\nFirst corner details:")
            corner = corners[0]
            print(f"  Frame: {corner.frame_id}")
            print(f"  Time: {corner.timestamp:.1f}s")
            print(f"  Side: {corner.corner_side.value}")
            print(f"  Attacking team: {corner.attacking_team}")
            print(f"  Outcome: {corner.outcome}")
        else:
            print("  No corners detected (StatsBomb might not label corners explicitly)")

    except Exception as e:
        print(f"  ⚠️ Error: {e}")
        print("  (This is normal if StatsBomb data unavailable)")

    # Demo 2: Simulate tracking data
    print("\n2. Testing with simulated tracking data...")

    # Create mock tracking data for a corner situation
    tracking_data = {
        'ball': [
            {'frame': 0, 'position': [105, 0]},  # Ball in corner
        ],
        'players': [
            # Attacking players (team 1)
            {'frame': 0, 'player_id': 1, 'team': 1, 'position': [105, 5]},  # Corner taker
            {'frame': 0, 'player_id': 2, 'team': 1, 'position': [95, 30]},  # Attacker
            {'frame': 0, 'player_id': 3, 'team': 1, 'position': [98, 38]},  # Attacker
            # Defending players (team 2)
            {'frame': 0, 'player_id': 11, 'team': 2, 'position': [99, 34]},  # Goalkeeper
            {'frame': 0, 'player_id': 12, 'team': 2, 'position': [95, 32]},  # Defender
            {'frame': 0, 'player_id': 13, 'team': 2, 'position': [96, 36]},  # Defender
            {'frame': 0, 'player_id': 14, 'team': 2, 'position': [92, 30]},  # Defender
            {'frame': 0, 'player_id': 15, 'team': 2, 'position': [92, 38]},  # Defender
            {'frame': 0, 'player_id': 16, 'team': 2, 'position': [90, 34]},  # Defender
            {'frame': 0, 'player_id': 17, 'team': 2, 'position': [94, 28]},  # Defender
        ]
    }

    detector = CornerKickDetector()
    corners = detector.detect_from_tracking(tracking_data)

    if corners:
        print(f"✓ Detected {len(corners)} corner(s)")
        corner = corners[0]
        print(f"\nCorner details:")
        print(f"  Side: {corner.corner_side.value}")
        print(f"  Attacking team: {corner.attacking_team}")
        print(f"  Attacking players: {len(corner.attacking_players)}")
        print(f"  Defending players: {len(corner.defending_players)}")
        print(f"  Ball position: ({corner.ball_x:.1f}, {corner.ball_y:.1f})")

        # Show roles
        print(f"\nPlayer roles:")
        for p in corner.attacking_players:
            print(f"    Team {p.team} Player {p.player_id}: {p.role.value} @ ({p.x:.1f}, {p.y:.1f})")

    print("\n" + "=" * 80)
    print("✅ Corner detector demo complete!")
    print("=" * 80)


if __name__ == "__main__":
    demo_corner_detector()
