#!/usr/bin/env python3
"""
Action Valuation - Phase 2, Task 2
Tunisia Football AI Advanced Physical Analytics

Simplified VAEP-style action valuation system.
Since socceraction has dependency conflicts, this implements core VAEP concepts
using heuristic models based on research principles.

Features:
- Action value calculation for passes, shots, dribbles, tackles
- Offensive and defensive value scoring
- Player rating aggregation
- Top action identification

References:
- Decroos et al. (2019): "Actions Speak Louder than Goals"
- VAEP: Valuing Actions by Estimating Probabilities
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
from enum import Enum


class ActionType(Enum):
    """Types of actions in football"""
    PASS = "pass"
    SHOT = "shot"
    DRIBBLE = "dribble"
    TACKLE = "tackle"
    INTERCEPTION = "interception"
    CLEARANCE = "clearance"
    CROSS = "cross"
    CARRY = "carry"


@dataclass
class Action:
    """Represents a single action in a match"""
    action_id: int
    player_id: int
    team_id: int
    action_type: ActionType
    start_x: float  # 0-105 (pitch length)
    start_y: float  # 0-68 (pitch width)
    end_x: Optional[float] = None
    end_y: Optional[float] = None
    success: bool = True
    frame_num: int = 0


@dataclass
class ActionValue:
    """Value assessment for an action"""
    action_id: int
    player_id: int
    team_id: int
    action_type: str

    # VAEP-style values
    offensive_value: float  # Increases scoring probability
    defensive_value: float  # Decreases conceding probability
    total_value: float  # Combined value

    # Context
    start_zone: str  # defensive/middle/attacking
    success: bool


@dataclass
class PlayerRating:
    """Aggregated rating for a player based on action values"""
    player_id: int
    team_id: int

    # Value metrics
    total_offensive_value: float
    total_defensive_value: float
    total_value: float

    # Action counts
    action_count: int
    successful_actions: int
    failed_actions: int

    # Per-action averages
    avg_offensive_value: float
    avg_defensive_value: float

    # Top actions
    best_actions: List[int]  # Action IDs of highest-value actions


class ActionValuationAnalyzer:
    """
    Simplified VAEP-style action valuation using heuristic models

    The full VAEP model requires training on large datasets.
    This implementation uses research-based heuristics to estimate
    offensive and defensive values for different action types.
    """

    def __init__(self, pitch_length: float = 105.0, pitch_width: float = 68.0):
        """
        Initialize action valuation analyzer

        Args:
            pitch_length: Pitch length in meters
            pitch_width: Pitch width in meters
        """
        self.pitch_length = pitch_length
        self.pitch_width = pitch_width

        # Define zones
        self.defensive_third = pitch_length / 3
        self.attacking_third = 2 * pitch_length / 3

        # Action value weights (based on VAEP research)
        # These are simplified heuristics
        self.base_values = {
            ActionType.SHOT: {
                'offensive': 0.15,  # Shots have high offensive value
                'defensive': 0.0
            },
            ActionType.PASS: {
                'offensive': 0.02,  # Progressive passes have value
                'defensive': 0.01
            },
            ActionType.CROSS: {
                'offensive': 0.05,  # Crosses create chances
                'defensive': 0.0
            },
            ActionType.DRIBBLE: {
                'offensive': 0.03,  # Dribbles progress play
                'defensive': 0.0
            },
            ActionType.TACKLE: {
                'offensive': 0.0,
                'defensive': 0.04  # Tackles prevent opponent attacks
            },
            ActionType.INTERCEPTION: {
                'offensive': 0.0,
                'defensive': 0.03
            },
            ActionType.CLEARANCE: {
                'offensive': 0.0,
                'defensive': 0.02
            },
            ActionType.CARRY: {
                'offensive': 0.01,
                'defensive': 0.0
            }
        }

        # Zone multipliers
        self.zone_multipliers = {
            'defensive': {'offensive': 0.8, 'defensive': 1.2},
            'middle': {'offensive': 1.0, 'defensive': 1.0},
            'attacking': {'offensive': 1.5, 'defensive': 0.7}
        }

    def value_action(self, action: Action) -> ActionValue:
        """
        Calculate offensive and defensive value for a single action

        Args:
            action: Action object to value

        Returns:
            ActionValue object with calculated values
        """
        # Get base values
        base = self.base_values.get(action.action_type, {'offensive': 0.0, 'defensive': 0.0})

        # Determine zone
        zone = self._get_zone(action.start_x, action.team_id)

        # Get zone multipliers
        zone_mult = self.zone_multipliers[zone]

        # Calculate base offensive and defensive values
        offensive_val = base['offensive'] * zone_mult['offensive']
        defensive_val = base['defensive'] * zone_mult['defensive']

        # Adjust for success/failure
        if not action.success:
            offensive_val *= 0.3  # Failed actions have reduced value
            defensive_val *= 0.3

        # Add progression bonus for passes and carries
        if action.action_type in [ActionType.PASS, ActionType.CARRY] and action.end_x is not None:
            progression = action.end_x - action.start_x
            if action.team_id == 2:  # Team 2 attacks in opposite direction
                progression = -progression

            if progression > 0:
                # Forward progression increases offensive value
                progression_bonus = min(progression / self.pitch_length, 0.1)
                offensive_val += progression_bonus

        # Location-based adjustments
        if action.action_type == ActionType.SHOT:
            # Shots closer to goal are more valuable
            distance_to_goal = self._distance_to_goal(action.start_x, action.start_y, action.team_id)
            proximity_bonus = max(0, (30 - distance_to_goal) / 30) * 0.1
            offensive_val += proximity_bonus

        # Calculate total value
        total_val = offensive_val + defensive_val

        return ActionValue(
            action_id=action.action_id,
            player_id=action.player_id,
            team_id=action.team_id,
            action_type=action.action_type.value,
            offensive_value=offensive_val,
            defensive_value=defensive_val,
            total_value=total_val,
            start_zone=zone,
            success=action.success
        )

    def value_actions(self, actions: List[Action]) -> List[ActionValue]:
        """
        Value multiple actions

        Args:
            actions: List of Action objects

        Returns:
            List of ActionValue objects
        """
        return [self.value_action(action) for action in actions]

    def get_player_ratings(self, action_values: List[ActionValue]) -> Dict[int, PlayerRating]:
        """
        Aggregate action values into player ratings

        Args:
            action_values: List of ActionValue objects

        Returns:
            Dict mapping player_id -> PlayerRating
        """
        player_data = defaultdict(lambda: {
            'team_id': 0,
            'total_offensive': 0.0,
            'total_defensive': 0.0,
            'total_value': 0.0,
            'action_count': 0,
            'successful': 0,
            'failed': 0,
            'action_ids': []
        })

        # Aggregate values
        for av in action_values:
            data = player_data[av.player_id]
            data['team_id'] = av.team_id
            data['total_offensive'] += av.offensive_value
            data['total_defensive'] += av.defensive_value
            data['total_value'] += av.total_value
            data['action_count'] += 1

            if av.success:
                data['successful'] += 1
            else:
                data['failed'] += 1

            data['action_ids'].append((av.action_id, av.total_value))

        # Create PlayerRating objects
        ratings = {}
        for player_id, data in player_data.items():
            # Get top 5 actions
            sorted_actions = sorted(data['action_ids'], key=lambda x: x[1], reverse=True)
            best_actions = [aid for aid, _ in sorted_actions[:5]]

            ratings[player_id] = PlayerRating(
                player_id=player_id,
                team_id=data['team_id'],
                total_offensive_value=data['total_offensive'],
                total_defensive_value=data['total_defensive'],
                total_value=data['total_value'],
                action_count=data['action_count'],
                successful_actions=data['successful'],
                failed_actions=data['failed'],
                avg_offensive_value=data['total_offensive'] / data['action_count'],
                avg_defensive_value=data['total_defensive'] / data['action_count'],
                best_actions=best_actions
            )

        return ratings

    def get_top_actions(self,
                       action_values: List[ActionValue],
                       top_n: int = 10
                       ) -> List[ActionValue]:
        """
        Get the top N most valuable actions

        Args:
            action_values: List of ActionValue objects
            top_n: Number of top actions to return

        Returns:
            List of top ActionValue objects
        """
        sorted_actions = sorted(action_values, key=lambda av: av.total_value, reverse=True)
        return sorted_actions[:top_n]

    def _get_zone(self, x: float, team_id: int) -> str:
        """Determine which third of pitch the action is in"""
        if team_id == 1:
            if x < self.defensive_third:
                return 'defensive'
            elif x < self.attacking_third:
                return 'middle'
            else:
                return 'attacking'
        else:  # Team 2 attacks in opposite direction
            if x > self.attacking_third:
                return 'defensive'
            elif x > self.defensive_third:
                return 'middle'
            else:
                return 'attacking'

    def _distance_to_goal(self, x: float, y: float, team_id: int) -> float:
        """Calculate distance to opponent's goal"""
        if team_id == 1:
            goal_x, goal_y = self.pitch_length, self.pitch_width / 2
        else:
            goal_x, goal_y = 0, self.pitch_width / 2

        return np.sqrt((x - goal_x)**2 + (y - goal_y)**2)

    def export_action_value(self, av: ActionValue) -> Dict:
        """Export action value to dictionary"""
        return {
            'action_id': av.action_id,
            'player_id': av.player_id,
            'team_id': av.team_id,
            'action_type': av.action_type,
            'values': {
                'offensive': round(av.offensive_value, 4),
                'defensive': round(av.defensive_value, 4),
                'total': round(av.total_value, 4)
            },
            'context': {
                'zone': av.start_zone,
                'success': av.success
            }
        }

    def export_player_rating(self, rating: PlayerRating) -> Dict:
        """Export player rating to dictionary"""
        return {
            'player_id': rating.player_id,
            'team_id': rating.team_id,
            'values': {
                'total_offensive': round(rating.total_offensive_value, 3),
                'total_defensive': round(rating.total_defensive_value, 3),
                'total': round(rating.total_value, 3)
            },
            'averages': {
                'offensive_per_action': round(rating.avg_offensive_value, 4),
                'defensive_per_action': round(rating.avg_defensive_value, 4)
            },
            'actions': {
                'total': rating.action_count,
                'successful': rating.successful_actions,
                'failed': rating.failed_actions,
                'success_rate': round(rating.successful_actions / rating.action_count, 3) if rating.action_count > 0 else 0
            },
            'best_action_ids': rating.best_actions
        }


if __name__ == "__main__":
    """Demo: Value sample match actions"""
    print("=" * 60)
    print("Action Valuation Analyzer Demo")
    print("=" * 60)

    analyzer = ActionValuationAnalyzer()

    # Simulate sample actions from a match
    print("\nSimulating sample match actions...")

    sample_actions = [
        Action(1, player_id=10, team_id=1, action_type=ActionType.PASS,
               start_x=30, start_y=34, end_x=45, end_y=40, success=True),
        Action(2, player_id=7, team_id=1, action_type=ActionType.SHOT,
               start_x=95, start_y=36, success=True),
        Action(3, player_id=15, team_id=2, action_type=ActionType.TACKLE,
               start_x=70, start_y=30, success=True),
        Action(4, player_id=10, team_id=1, action_type=ActionType.PASS,
               start_x=50, start_y=34, end_x=80, end_y=35, success=True),
        Action(5, player_id=7, team_id=1, action_type=ActionType.DRIBBLE,
               start_x=75, start_y=35, end_x=85, end_y=36, success=True),
        Action(6, player_id=20, team_id=2, action_type=ActionType.INTERCEPTION,
               start_x=40, start_y=38, success=True),
        Action(7, player_id=10, team_id=1, action_type=ActionType.PASS,
               start_x=60, start_y=30, end_x=50, end_y=25, success=False),
    ]

    # Value all actions
    action_values = analyzer.value_actions(sample_actions)

    print(f"\n{'Action Valuations':^60}")
    print("=" * 60)
    for av in action_values:
        print(f"Action #{av.action_id} - {av.action_type} by Player #{av.player_id}")
        print(f"  Offensive: {av.offensive_value:.4f} | Defensive: {av.defensive_value:.4f} | Total: {av.total_value:.4f}")
        print(f"  Zone: {av.start_zone} | Success: {av.success}")
        print()

    # Get player ratings
    print("=" * 60)
    print(f"{'Player Ratings':^60}")
    print("=" * 60)

    ratings = analyzer.get_player_ratings(action_values)

    for player_id, rating in sorted(ratings.items()):
        print(f"Player #{player_id} (Team {rating.team_id}):")
        print(f"  Total Value: {rating.total_value:.3f}")
        print(f"  Actions: {rating.action_count} ({rating.successful_actions} successful)")
        print(f"  Avg Offensive: {rating.avg_offensive_value:.4f}")
        print(f"  Avg Defensive: {rating.avg_defensive_value:.4f}")
        print()

    # Get top actions
    top_actions = analyzer.get_top_actions(action_values, top_n=3)

    print("=" * 60)
    print(f"{'Top 3 Most Valuable Actions':^60}")
    print("=" * 60)

    for i, av in enumerate(top_actions, 1):
        print(f"{i}. Action #{av.action_id} - {av.action_type} by Player #{av.player_id}")
        print(f"   Value: {av.total_value:.4f}")
        print()

    # Export example
    print("=" * 60)
    print("JSON Export Sample (Top Action):")
    print("=" * 60)
    import json
    if top_actions:
        exported = analyzer.export_action_value(top_actions[0])
        print(json.dumps(exported, indent=2))

    print("\n✅ Action valuation analysis complete!")
