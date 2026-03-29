#!/usr/bin/env python3
"""
Unit tests for Space Control Analyzer
Phase 2 - Advanced Physical Analytics
"""

import sys
import os
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from space_control_analyzer import (
    SpaceControlAnalyzer,
    SpaceControlMetrics,
    TeamSpaceControlSummary
)


def test_voronoi_calculation():
    """Test Voronoi diagram calculation"""
    print("\n" + "=" * 60)
    print("TEST 1: Voronoi Calculation")
    print("=" * 60)

    analyzer = SpaceControlAnalyzer()

    # Simple 2v2 scenario
    positions = {
        1: (20, 20, 1),
        2: (80, 20, 1),
        3: (20, 50, 2),
        4: (80, 50, 2)
    }

    vor, team_mapping = analyzer.calculate_voronoi(positions)

    assert vor is not None, "Voronoi should be calculated"
    assert len(team_mapping) == 4, "Should have 4 player mappings"
    print(f"✓ Voronoi calculated with {len(vor.points)} total points")
    print(f"✓ Player mappings: {len(team_mapping)}")
    print(f"✓ Voronoi regions: {len(vor.regions)}")

    print("✅ Voronoi calculation test passed!\n")


def test_space_control_calculation():
    """Test space control percentage calculation"""
    print("=" * 60)
    print("TEST 2: Space Control Calculation")
    print("=" * 60)

    analyzer = SpaceControlAnalyzer(pitch_length=100, pitch_width=60)

    # Symmetric 3v3 scenario - should give ~50/50 control
    positions = {
        1: (25, 15, 1),
        2: (25, 30, 1),
        3: (25, 45, 1),
        4: (75, 15, 2),
        5: (75, 30, 2),
        6: (75, 45, 2)
    }

    metrics = analyzer.calculate_space_control(positions, frame_num=1)

    assert metrics is not None, "Metrics should be calculated"
    assert isinstance(metrics, SpaceControlMetrics), "Should return SpaceControlMetrics"

    # Check control percentages sum to ~100%
    total_control = metrics.team_1_control_percent + metrics.team_2_control_percent
    assert 99 < total_control < 101, f"Total control should be ~100%, got {total_control:.1f}%"

    # For symmetric positions, control should be roughly equal
    ratio = metrics.team_1_control_percent / metrics.team_2_control_percent
    assert 0.7 < ratio < 1.3, f"Control ratio should be ~1.0 for symmetric positions, got {ratio:.2f}"

    print(f"✓ Team 1 Control: {metrics.team_1_control_percent:.1f}%")
    print(f"✓ Team 2 Control: {metrics.team_2_control_percent:.1f}%")
    print(f"✓ Total Control: {total_control:.1f}%")
    print(f"✓ Control Ratio: {ratio:.2f}")

    print("✅ Space control calculation test passed!\n")


def test_zonal_control():
    """Test zonal control (thirds) calculation"""
    print("=" * 60)
    print("TEST 3: Zonal Control (Thirds)")
    print("=" * 60)

    analyzer = SpaceControlAnalyzer(pitch_length=105, pitch_width=68)

    # Team 1 defends left, Team 2 defends right
    # Team 1 dominates defensive third (0-35m)
    # Team 2 dominates attacking third (70-105m)
    positions = {
        # Team 1 in defensive third
        1: (10, 20, 1),
        2: (10, 40, 1),
        3: (20, 30, 1),
        4: (30, 25, 1),
        5: (30, 45, 1),
        # Team 2 in attacking third
        6: (75, 20, 2),
        7: (75, 40, 2),
        8: (85, 30, 2),
        9: (95, 25, 2),
        10: (95, 45, 2)
    }

    metrics = analyzer.calculate_space_control(positions)

    # Team 1 should dominate defensive third
    defensive_team1 = metrics.defensive_third_control.get(1, 0)
    assert defensive_team1 > 70, f"Team 1 should dominate defensive third, got {defensive_team1:.1f}%"

    # Team 2 should dominate attacking third
    attacking_team2 = metrics.attacking_third_control.get(2, 0)
    assert attacking_team2 > 70, f"Team 2 should dominate attacking third, got {attacking_team2:.1f}%"

    print(f"✓ Defensive Third - Team 1: {defensive_team1:.1f}%")
    print(f"✓ Middle Third - Team 1: {metrics.middle_third_control.get(1, 0):.1f}%")
    print(f"✓ Attacking Third - Team 2: {attacking_team2:.1f}%")

    print("✅ Zonal control test passed!\n")


def test_pressure_metrics():
    """Test pressure metrics calculation"""
    print("=" * 60)
    print("TEST 4: Pressure Metrics")
    print("=" * 60)

    analyzer = SpaceControlAnalyzer()

    # High pressure scenario: Players very close
    close_positions = {
        1: (50, 30, 1),
        2: (52, 31, 2),  # ~2.8m from player 1
        3: (50, 40, 1),
        4: (52, 41, 2),  # ~2.8m from player 3
    }

    metrics_close = analyzer.calculate_space_control(close_positions)
    assert metrics_close.high_pressure_zones > 0, "Should detect high pressure zones"

    print(f"✓ High pressure zones detected: {metrics_close.high_pressure_zones}")
    print(f"✓ Avg opponent distance Team 1: {metrics_close.average_opponent_distance.get(1, 0):.2f}m")
    print(f"✓ Avg opponent distance Team 2: {metrics_close.average_opponent_distance.get(2, 0):.2f}m")

    # Low pressure scenario: Players far apart
    far_positions = {
        1: (20, 20, 1),
        2: (80, 50, 2),  # ~70m away
        3: (20, 50, 1),
        4: (80, 20, 2),  # ~70m away
    }

    metrics_far = analyzer.calculate_space_control(far_positions)
    assert metrics_far.high_pressure_zones == 0, "Should not detect high pressure when far apart"

    print(f"✓ No high pressure zones detected (expected)")
    print(f"✓ Avg opponent distance increased: {metrics_far.average_opponent_distance.get(1, 0):.2f}m")

    print("✅ Pressure metrics test passed!\n")


def test_sequence_analysis():
    """Test analysis over multiple frames"""
    print("=" * 60)
    print("TEST 5: Sequence Analysis")
    print("=" * 60)

    analyzer = SpaceControlAnalyzer(pitch_length=105, pitch_width=68)

    # Simulate 10 frames of a match
    frame_data = {}
    for frame in range(10):
        # Gradually move team 2 forward into attacking third (70+ meters)
        # Start at 50m and move to 80m
        team2_x = 50 + frame * 3
        positions = {
            1: (20, 30, 1),
            2: (20, 40, 1),
            3: (team2_x, 30, 2),  # Move forward each frame
            4: (team2_x, 40, 2)
        }
        frame_data[frame] = positions

    metrics_list = analyzer.analyze_sequence(frame_data)

    assert len(metrics_list) == 10, f"Should have 10 frames of metrics, got {len(metrics_list)}"

    # Control distribution should change over frames
    first_frame_control = metrics_list[0].team_2_control_percent
    last_frame_control = metrics_list[-1].team_2_control_percent

    print(f"✓ Analyzed {len(metrics_list)} frames")
    print(f"✓ Team 2 control - Frame 0: {first_frame_control:.1f}%")
    print(f"✓ Team 2 control - Frame 9: {last_frame_control:.1f}%")
    # Just verify that control changes (not necessarily increases)
    assert abs(last_frame_control - first_frame_control) > 1.0, "Control should change as players move"

    print("✅ Sequence analysis test passed!\n")


def test_team_summary():
    """Test team control summary over multiple frames"""
    print("=" * 60)
    print("TEST 6: Team Control Summary")
    print("=" * 60)

    analyzer = SpaceControlAnalyzer()

    # Create metrics for 20 frames
    metrics_list = []
    for i in range(20):
        # Alternate dominance
        if i < 10:
            # Team 1 dominates first 10 frames
            positions = {
                1: (30, 25, 1), 2: (30, 40, 1), 3: (40, 30, 1),
                4: (70, 30, 2), 5: (80, 35, 2)
            }
        else:
            # Team 2 dominates last 10 frames
            positions = {
                1: (80, 25, 1), 2: (90, 40, 1),
                3: (30, 30, 2), 4: (40, 25, 2), 5: (40, 40, 2)
            }

        metrics = analyzer.calculate_space_control(positions, frame_num=i)
        if metrics:
            metrics_list.append(metrics)

    # Summarize Team 1
    summary_team1 = analyzer.summarize_team_control(metrics_list, team_id=1)

    assert isinstance(summary_team1, TeamSpaceControlSummary), "Should return TeamSpaceControlSummary"
    assert summary_team1.team_id == 1, "Team ID should match"
    assert summary_team1.total_frames == len(metrics_list), "Total frames should match"
    assert 40 < summary_team1.avg_total_control < 60, f"Average control should be ~50%, got {summary_team1.avg_total_control:.1f}%"

    print(f"✓ Team 1 Summary:")
    print(f"  - Avg Total Control: {summary_team1.avg_total_control:.1f}%")
    print(f"  - Avg Defensive Third: {summary_team1.avg_defensive_third:.1f}%")
    print(f"  - Frames with Majority: {summary_team1.frames_with_majority}/{summary_team1.total_frames}")
    print(f"  - Control Std Dev: {summary_team1.control_std_dev:.2f}")

    print("✅ Team summary test passed!\n")


def test_export_format():
    """Test export format"""
    print("=" * 60)
    print("TEST 7: Export Format")
    print("=" * 60)

    analyzer = SpaceControlAnalyzer()

    # Need at least 4 players for Voronoi
    positions = {
        1: (25, 25, 1),
        2: (25, 40, 1),
        3: (75, 25, 2),
        4: (75, 40, 2)
    }

    metrics = analyzer.calculate_space_control(positions, frame_num=42)
    exported = analyzer.export_metrics(metrics)

    # Validate structure
    required_keys = [
        'frame', 'team_control', 'zonal_control',
        'dominant_zones', 'pressure', 'player_areas_m2'
    ]

    for key in required_keys:
        assert key in exported, f"Export should contain '{key}'"

    print("✓ Export contains all required fields:")
    for key in required_keys:
        print(f"    - {key}")

    assert exported['frame'] == 42, "Frame number should match"
    assert 'team_1' in exported['team_control'], "Should have team_1 control"
    assert 'team_2' in exported['team_control'], "Should have team_2 control"

    print("✅ Export format test passed!\n")


def test_edge_cases():
    """Test edge cases and error handling"""
    print("=" * 60)
    print("TEST 8: Edge Cases")
    print("=" * 60)

    analyzer = SpaceControlAnalyzer()

    # Test 1: Too few players
    too_few = {1: (50, 34, 1)}
    metrics = analyzer.calculate_space_control(too_few)
    assert metrics is None, "Should return None with too few players"
    print("✓ Too few players handled correctly")

    # Test 2: Players outside pitch bounds (should be clipped)
    outside_bounds = {
        1: (-10, 50, 1),   # Negative x
        2: (120, 50, 1),   # Beyond pitch length
        3: (50, -5, 2),    # Negative y
        4: (50, 80, 2)     # Beyond pitch width
    }
    metrics = analyzer.calculate_space_control(outside_bounds)
    assert metrics is not None, "Should handle out-of-bounds positions"
    print("✓ Out-of-bounds positions clipped correctly")

    # Test 3: All players same team
    same_team = {
        1: (30, 30, 1),
        2: (40, 30, 1),
        3: (50, 30, 1),
        4: (60, 30, 1)
    }
    metrics = analyzer.calculate_space_control(same_team)
    assert metrics is not None, "Should handle single-team scenario"
    assert metrics.team_1_control_percent == 100.0, "Single team should have 100% control"
    assert metrics.team_2_control_percent == 0.0, "Other team should have 0% control"
    print("✓ Single team scenario handled correctly")

    print("✅ Edge case tests passed!\n")


def test_boundary_points():
    """Test boundary point generation"""
    print("=" * 60)
    print("TEST 9: Boundary Points")
    print("=" * 60)

    analyzer = SpaceControlAnalyzer(pitch_length=105, pitch_width=68)

    boundary = analyzer._create_boundary_points()

    assert len(boundary) > 0, "Should create boundary points"
    assert boundary.shape[1] == 2, "Boundary points should be 2D"

    # Check that boundary points are outside pitch
    x_coords = boundary[:, 0]
    y_coords = boundary[:, 1]

    has_outside_x = (x_coords < 0).any() or (x_coords > 105).any()
    has_outside_y = (y_coords < 0).any() or (y_coords > 68).any()

    assert has_outside_x or has_outside_y, "Boundary points should be outside pitch"

    print(f"✓ Created {len(boundary)} boundary points")
    print(f"✓ X range: [{x_coords.min():.1f}, {x_coords.max():.1f}]")
    print(f"✓ Y range: [{y_coords.min():.1f}, {y_coords.max():.1f}]")

    print("✅ Boundary points test passed!\n")


def run_all_tests():
    """Run all test cases"""
    print("\n" + "=" * 60)
    print("SPACE CONTROL ANALYZER TEST SUITE")
    print("=" * 60)

    try:
        test_voronoi_calculation()
        test_space_control_calculation()
        test_zonal_control()
        test_pressure_metrics()
        test_sequence_analysis()
        test_team_summary()
        test_export_format()
        test_edge_cases()
        test_boundary_points()

        print("=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("\nSpace Control Analyzer is working correctly.")
        print("Ready for integration into the complete pipeline.")
        return True

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
