#!/usr/bin/env python3
"""
Phase 2 Demonstration Script
Tunisia Football AI - Advanced Physical Analytics

This script demonstrates all Phase 2 features:
1. Metabolic Power Analysis
2. Space Control (Voronoi)
3. Action Valuation (VAEP-style)

Run this to see Phase 2 modules in action!
"""

import sys
import os
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metabolic_power_analyzer import MetabolicPowerAnalyzer, calculate_velocity_acceleration_from_trajectory
from space_control_analyzer import SpaceControlAnalyzer
from action_valuation import ActionValuationAnalyzer, Action, ActionType


def demo_metabolic_power():
    """Demonstrate metabolic power analysis"""
    print("\n" + "=" * 70)
    print("DEMO 1: METABOLIC POWER ANALYSIS")
    print("=" * 70)

    analyzer = MetabolicPowerAnalyzer(fps=25, player_mass=75.0)

    # Simulate realistic player movement over 30 minutes
    print("\nSimulating 30 minutes of player activity...")
    np.random.seed(42)
    num_frames = 25 * 60 * 30  # 30 minutes

    # Create realistic velocity profile
    velocities = np.random.choice(
        [1.5, 2.5, 4.0, 5.5, 7.0, 8.5],  # m/s
        size=num_frames,
        p=[0.35, 0.25, 0.20, 0.12, 0.05, 0.03]  # Distribution
    )
    velocities += np.random.normal(0, 0.4, num_frames)
    velocities = np.clip(velocities, 0, 11.0)

    # Calculate accelerations
    accelerations = np.diff(velocities, prepend=velocities[0]) * 25
    accelerations = np.clip(accelerations, -3.5, 3.5)

    # Analyze
    metrics = analyzer.analyze_player(
        velocities=velocities.tolist(),
        accelerations=accelerations.tolist(),
        player_id=10,
        team=1
    )

    # Display results
    print(f"\n{'Results for Player #10':^70}")
    print("-" * 70)
    print(f"Minutes Played: {metrics.minutes_played:.1f}")
    print(f"\nEnergy Expenditure:")
    print(f"  Total: {metrics.total_energy_expenditure:.1f} kJ")
    print(f"  Average Power: {metrics.average_metabolic_power:.1f} W/kg")
    print(f"  Peak Power: {metrics.max_metabolic_power:.1f} W/kg")
    print(f"  Energy Depletion: {metrics.energy_depletion_percent:.1f}%")
    print(f"\nHigh-Intensity Running:")
    print(f"  Distance (>20 W/kg): {metrics.high_intensity_distance:.1f} m")
    print(f"  Very High Distance (>35 W/kg): {metrics.very_high_intensity_distance:.1f} m")
    print(f"  Time at High Power: {metrics.time_high_power/60:.1f} minutes")
    print(f"\nEquivalent Flat Distance: {metrics.equivalent_distance:.1f} m")
    print(f"Recovery Needed: {metrics.estimated_recovery_minutes} minutes")

    print("\n✅ Metabolic power analysis complete!")


def demo_space_control():
    """Demonstrate space control analysis"""
    print("\n" + "=" * 70)
    print("DEMO 2: VORONOI SPACE CONTROL ANALYSIS")
    print("=" * 70)

    analyzer = SpaceControlAnalyzer(pitch_length=105.0, pitch_width=68.0)

    # Simulate realistic 11v11 positions (tactical setup)
    print("\nSimulating 11v11 match positions...")
    print("Team 1 Formation: 4-4-2 (Defending)")
    print("Team 2 Formation: 4-3-3 (Attacking)")

    positions = {
        # Team 1 (4-4-2 defensive)
        1: (5, 34, 1),    # GK
        2: (25, 8, 1),    # RB
        3: (25, 25, 1),   # CB
        4: (25, 43, 1),   # CB
        5: (25, 60, 1),   # LB
        6: (45, 12, 1),   # RM
        7: (45, 28, 1),   # CM
        8: (45, 40, 1),   # CM
        9: (45, 56, 1),   # LM
        10: (65, 28, 1),  # ST
        11: (65, 40, 1),  # ST

        # Team 2 (4-3-3 attacking)
        12: (100, 34, 2),  # GK
        13: (75, 10, 2),   # RB
        14: (75, 26, 2),   # CB
        15: (75, 42, 2),   # CB
        16: (75, 58, 2),   # LB
        17: (55, 20, 2),   # CM
        18: (55, 34, 2),   # CM
        19: (55, 48, 2),   # CM
        20: (35, 15, 2),   # RW
        21: (35, 34, 2),   # ST
        22: (35, 53, 2),   # LW
    }

    # Calculate space control
    metrics = analyzer.calculate_space_control(positions, frame_num=1)

    if metrics:
        print(f"\n{'Space Control Results':^70}")
        print("-" * 70)
        print(f"Overall Control:")
        print(f"  Team 1: {metrics.team_1_control_percent:.1f}%")
        print(f"  Team 2: {metrics.team_2_control_percent:.1f}%")

        print(f"\nZonal Control (Pitch Thirds):")
        print(f"  Defensive Third:")
        for team in [1, 2]:
            pct = metrics.defensive_third_control.get(team, 0)
            print(f"    Team {team}: {pct:.1f}%")

        print(f"  Middle Third:")
        for team in [1, 2]:
            pct = metrics.middle_third_control.get(team, 0)
            print(f"    Team {team}: {pct:.1f}%")

        print(f"  Attacking Third:")
        for team in [1, 2]:
            pct = metrics.attacking_third_control.get(team, 0)
            print(f"    Team {team}: {pct:.1f}%")

        print(f"\nPressure Analysis:")
        for team in [1, 2]:
            dist = metrics.average_opponent_distance.get(team, 0)
            print(f"  Team {team} avg distance to opponent: {dist:.1f} m")
        print(f"  High pressure zones (< 5m): {metrics.high_pressure_zones}")

        print(f"\nDominant Zones:")
        print(f"  Team 1: {metrics.team_1_dominant_zones} cells")
        print(f"  Team 2: {metrics.team_2_dominant_zones} cells")

    print("\n✅ Space control analysis complete!")


def demo_action_valuation():
    """Demonstrate action valuation"""
    print("\n" + "=" * 70)
    print("DEMO 3: ACTION VALUATION (VAEP-STYLE)")
    print("=" * 70)

    analyzer = ActionValuationAnalyzer()

    # Simulate a goal-scoring sequence
    print("\nSimulating goal-scoring sequence...")
    print("Sequence: Interception → Progressive Pass → Through Ball → Shot → GOAL!")

    actions = [
        Action(1, player_id=5, team_id=1, action_type=ActionType.INTERCEPTION,
               start_x=40, start_y=30, success=True),
        Action(2, player_id=5, team_id=1, action_type=ActionType.PASS,
               start_x=40, start_y=30, end_x=60, end_y=35, success=True),
        Action(3, player_id=8, team_id=1, action_type=ActionType.PASS,
               start_x=60, start_y=35, end_x=90, end_y=38, success=True),
        Action(4, player_id=10, team_id=1, action_type=ActionType.SHOT,
               start_x=90, start_y=38, success=True),

        # Counter-attack from opponent
        Action(5, player_id=15, team_id=2, action_type=ActionType.TACKLE,
               start_x=50, start_y=40, success=True),
        Action(6, player_id=15, team_id=2, action_type=ActionType.PASS,
               start_x=50, start_y=40, end_x=30, end_y=35, success=True),
        Action(7, player_id=20, team_id=2, action_type=ActionType.CROSS,
               start_x=30, start_y=20, end_x=15, end_y=34, success=False),
    ]

    # Value actions
    action_values = analyzer.value_actions(actions)

    print(f"\n{'Action-by-Action Valuation':^70}")
    print("-" * 70)
    for av in action_values:
        icon = "✓" if av.success else "✗"
        print(f"{icon} Action #{av.action_id}: {av.action_type.upper()}")
        print(f"  Player #{av.player_id} (Team {av.team_id}) - Zone: {av.start_zone}")
        print(f"  Value: Off={av.offensive_value:.4f}, Def={av.defensive_value:.4f}, Total={av.total_value:.4f}")

    # Player ratings
    ratings = analyzer.get_player_ratings(action_values)

    print(f"\n{'Player Performance Ratings':^70}")
    print("-" * 70)
    for player_id in sorted(ratings.keys()):
        rating = ratings[player_id]
        success_rate = (rating.successful_actions / rating.action_count) * 100
        print(f"Player #{player_id} (Team {rating.team_id}):")
        print(f"  Total Value: {rating.total_value:.3f}")
        print(f"  Actions: {rating.action_count} ({success_rate:.0f}% success)")
        print(f"  Avg Value/Action: {rating.total_value/rating.action_count:.4f}")

    # Top actions
    top_actions = analyzer.get_top_actions(action_values, top_n=3)

    print(f"\n{'Top 3 Most Valuable Actions':^70}")
    print("-" * 70)
    for i, av in enumerate(top_actions, 1):
        print(f"{i}. Action #{av.action_id} - {av.action_type.upper()} by Player #{av.player_id}")
        print(f"   Value: {av.total_value:.4f} | Success: {av.success}")

    print("\n✅ Action valuation complete!")


def run_all_demos():
    """Run all Phase 2 demonstrations"""
    print("\n" + "=" * 70)
    print(" " * 15 + "TUNISIA FOOTBALL AI - PHASE 2 DEMOS")
    print(" " * 12 + "Advanced Physical Analytics Demonstration")
    print("=" * 70)

    try:
        demo_metabolic_power()
        demo_space_control()
        demo_action_valuation()

        print("\n" + "=" * 70)
        print("✅ ALL PHASE 2 DEMOS COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print("\nPhase 2 modules are working correctly and ready for integration.")
        print("\nNext Steps:")
        print("  1. Integrate into complete_pipeline.py")
        print("  2. Add to gradio_complete_app.py interface")
        print("  3. Create enhanced fatigue estimator combining all metrics")
        print("\nFor more information, see README_PHASE2.md")

        return True

    except Exception as e:
        print(f"\n❌ DEMO FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_demos()
    sys.exit(0 if success else 1)
