#!/usr/bin/env python3
"""
Unit tests for Metabolic Power Analyzer
Phase 2 - Advanced Physical Analytics
"""

import sys
import os
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metabolic_power_analyzer import (
    MetabolicPowerAnalyzer,
    MetabolicPowerMetrics,
    calculate_velocity_acceleration_from_trajectory
)


def test_metabolic_power_calculation():
    """Test metabolic power calculation with known inputs"""
    print("\n" + "=" * 60)
    print("TEST 1: Metabolic Power Calculation")
    print("=" * 60)

    analyzer = MetabolicPowerAnalyzer(fps=25)

    # Test case 1: Zero velocity and acceleration
    velocities = np.zeros(100)
    accelerations = np.zeros(100)
    power = analyzer.calculate_metabolic_power(velocities, accelerations)

    assert len(power) == 100, "Power array length should match input"
    assert np.all(power >= 0), "Power should be non-negative"
    print(f"✓ Zero velocity test: avg power = {np.mean(power):.2f} W/kg (expected ~0)")

    # Test case 2: Constant velocity (no acceleration)
    velocities = np.ones(100) * 5.0  # 5 m/s constant
    accelerations = np.zeros(100)
    power = analyzer.calculate_metabolic_power(velocities, accelerations)

    expected_power = analyzer.energy_cost_flat * 5.0  # ~18 W/kg
    avg_power = np.mean(power)
    assert 15 < avg_power < 25, f"Constant velocity power should be ~18 W/kg, got {avg_power:.2f}"
    print(f"✓ Constant velocity (5 m/s): avg power = {avg_power:.2f} W/kg (expected ~18)")

    # Test case 3: Sprint with acceleration
    velocities = np.linspace(0, 10, 100)  # Accelerating to 10 m/s
    accelerations = np.gradient(velocities) * 25  # fps=25
    power = analyzer.calculate_metabolic_power(velocities, accelerations)

    max_power = np.max(power)
    assert max_power > 30, f"Sprint power should exceed 30 W/kg, got {max_power:.2f}"
    print(f"✓ Sprint acceleration: max power = {max_power:.2f} W/kg (expected >30)")

    print("✅ All metabolic power calculation tests passed!\n")


def test_energy_expenditure():
    """Test energy expenditure calculation"""
    print("=" * 60)
    print("TEST 2: Energy Expenditure Calculation")
    print("=" * 60)

    analyzer = MetabolicPowerAnalyzer(fps=25, player_mass=75.0)

    # Simulate 10 minutes of moderate activity at ~20 W/kg
    metabolic_power = np.ones(25 * 60 * 10) * 20.0  # 10 min at 20 W/kg
    time_step = 1.0 / 25

    energy = analyzer.calculate_energy_expenditure(metabolic_power, time_step)

    # Expected: 20 W/kg * 75 kg * 600 s = 900,000 J = 900 kJ
    expected_energy = 20.0 * 75.0 * 600.0 / 1000.0  # kJ
    error = abs(energy - expected_energy) / expected_energy

    assert error < 0.01, f"Energy calculation error too large: {error:.3%}"
    print(f"✓ Energy expenditure: {energy:.1f} kJ (expected {expected_energy:.1f} kJ)")
    print(f"  Error: {error:.3%}")

    print("✅ Energy expenditure test passed!\n")


def test_equivalent_distance():
    """Test equivalent distance calculation"""
    print("=" * 60)
    print("TEST 3: Equivalent Distance Calculation")
    print("=" * 60)

    analyzer = MetabolicPowerAnalyzer(fps=25)

    # Test: Running at constant 5 m/s for 10 minutes on flat ground
    velocities = np.ones(25 * 60 * 10) * 5.0  # 5 m/s for 10 minutes
    accelerations = np.zeros(len(velocities))

    metabolic_power = analyzer.calculate_metabolic_power(velocities, accelerations)
    time_step = 1.0 / 25

    equivalent_dist = analyzer.calculate_equivalent_distance(
        velocities, metabolic_power, time_step
    )

    # Actual distance covered
    actual_dist = 5.0 * 600  # 3000 meters

    # On flat ground with no acceleration, equivalent should equal actual
    ratio = equivalent_dist / actual_dist
    assert 0.9 < ratio < 1.1, f"Equivalent/actual ratio should be ~1.0, got {ratio:.2f}"
    print(f"✓ Actual distance: {actual_dist:.1f} m")
    print(f"✓ Equivalent distance: {equivalent_dist:.1f} m")
    print(f"  Ratio: {ratio:.2f} (expected ~1.0 for flat running)")

    print("✅ Equivalent distance test passed!\n")


def test_player_analysis():
    """Test complete player analysis"""
    print("=" * 60)
    print("TEST 4: Complete Player Analysis")
    print("=" * 60)

    analyzer = MetabolicPowerAnalyzer(fps=25, player_mass=75.0)

    # Simulate realistic player activity for 20 minutes
    np.random.seed(42)
    num_frames = 25 * 60 * 20  # 20 minutes

    # Mix of different activity levels
    velocities = np.random.choice(
        [1.5, 3.0, 5.0, 7.0],  # m/s
        size=num_frames,
        p=[0.4, 0.3, 0.2, 0.1]  # Probability distribution
    ) + np.random.normal(0, 0.3, num_frames)
    velocities = np.clip(velocities, 0, 10.0)

    accelerations = np.gradient(velocities) * 25
    accelerations = np.clip(accelerations, -3.0, 3.0)

    # Analyze player
    metrics = analyzer.analyze_player(
        velocities=velocities.tolist(),
        accelerations=accelerations.tolist(),
        player_id=10,
        team=1
    )

    # Validate metrics
    assert isinstance(metrics, MetabolicPowerMetrics), "Should return MetabolicPowerMetrics"
    assert metrics.player_id == 10, "Player ID should match"
    assert metrics.team == 1, "Team should match"
    assert 15 < metrics.minutes_played < 25, f"Minutes played should be ~20, got {metrics.minutes_played:.1f}"
    assert metrics.total_energy_expenditure > 0, "Energy expenditure should be positive"
    assert 10 < metrics.average_metabolic_power < 50, f"Average power should be reasonable, got {metrics.average_metabolic_power:.1f}"
    assert metrics.frames_analyzed == num_frames, "Should analyze all frames"

    print(f"✓ Player ID: {metrics.player_id}")
    print(f"✓ Minutes Played: {metrics.minutes_played:.1f}")
    print(f"✓ Total Energy: {metrics.total_energy_expenditure:.1f} kJ")
    print(f"✓ Average Power: {metrics.average_metabolic_power:.1f} W/kg")
    print(f"✓ Max Power: {metrics.max_metabolic_power:.1f} W/kg")
    print(f"✓ HI Distance: {metrics.high_intensity_distance:.1f} m")
    print(f"✓ Recovery: {metrics.estimated_recovery_minutes} min")

    print("✅ Player analysis test passed!\n")


def test_power_zones():
    """Test power zone classification"""
    print("=" * 60)
    print("TEST 5: Power Zone Classification")
    print("=" * 60)

    analyzer = MetabolicPowerAnalyzer(fps=25)

    # Create known power profile
    # 100 frames each at different power levels
    power_profile = np.concatenate([
        np.ones(100) * 5,   # Low
        np.ones(100) * 15,  # Moderate
        np.ones(100) * 25,  # High
        np.ones(100) * 40,  # Very high
        np.ones(100) * 60   # Maximal
    ])

    time_step = 1.0 / 25
    zone_times = analyzer._calculate_power_zones(power_profile, time_step)

    # Each zone should have 100 frames = 4 seconds
    expected_time = 100 * time_step

    for zone_name, time_s in zone_times.items():
        print(f"  {zone_name.capitalize():15s}: {time_s:>6.1f} s", end="")
        if time_s > 0:
            assert abs(time_s - expected_time) < 0.1, f"{zone_name} time should be ~{expected_time:.1f}s"
            print(" ✓")
        else:
            print()

    print("✅ Power zone test passed!\n")


def test_trajectory_conversion():
    """Test velocity/acceleration calculation from trajectory"""
    print("=" * 60)
    print("TEST 6: Trajectory Conversion")
    print("=" * 60)

    # Create simple linear trajectory
    # Move from (0,0) to (100,0) over 100 frames at 25 fps
    trajectory = [(float(i), 0.0, i) for i in range(101)]

    velocities, accelerations = calculate_velocity_acceleration_from_trajectory(
        trajectory, fps=25, pitch_length=105, pitch_width=68
    )

    # Expected: 1 meter per frame = 25 m/s velocity
    expected_velocity = 25.0  # m/s
    avg_velocity = np.mean(velocities)

    assert len(velocities) == 100, "Should have 100 velocity measurements"
    assert len(accelerations) == 100, "Should have 100 acceleration measurements"
    assert abs(avg_velocity - expected_velocity) < 0.1, f"Velocity should be ~25 m/s, got {avg_velocity:.2f}"

    print(f"✓ Trajectory points: {len(trajectory)}")
    print(f"✓ Velocities calculated: {len(velocities)}")
    print(f"✓ Accelerations calculated: {len(accelerations)}")
    print(f"✓ Average velocity: {avg_velocity:.2f} m/s (expected {expected_velocity:.2f})")

    print("✅ Trajectory conversion test passed!\n")


def test_export_format():
    """Test data export format"""
    print("=" * 60)
    print("TEST 7: Data Export Format")
    print("=" * 60)

    analyzer = MetabolicPowerAnalyzer(fps=25, player_mass=75.0)

    # Create sample metrics
    velocities = np.random.uniform(0, 8, 1000)
    accelerations = np.random.uniform(-2, 2, 1000)

    metrics = analyzer.analyze_player(
        velocities=velocities.tolist(),
        accelerations=accelerations.tolist(),
        player_id=7,
        team=2
    )

    # Test single export
    exported = analyzer.export_metrics(metrics)

    assert 'player_id' in exported, "Should have player_id"
    assert 'energy_metrics' in exported, "Should have energy_metrics"
    assert 'high_intensity_metrics' in exported, "Should have high_intensity_metrics"
    assert 'power_zones_seconds' in exported, "Should have power_zones_seconds"

    print("✓ Export contains all required fields:")
    for key in exported.keys():
        print(f"    - {key}")

    # Test batch export
    metrics_list = [metrics, metrics]  # Duplicate for testing
    batch_export = analyzer.batch_export(metrics_list)

    assert 'players' in batch_export, "Batch should have players list"
    assert 'team_summaries' in batch_export, "Batch should have team summaries"
    assert len(batch_export['players']) == 2, "Should have 2 players"

    print("✓ Batch export structure validated")

    print("✅ Export format test passed!\n")


def test_edge_cases():
    """Test edge cases and error handling"""
    print("=" * 60)
    print("TEST 8: Edge Cases")
    print("=" * 60)

    analyzer = MetabolicPowerAnalyzer(fps=25)

    # Test 1: Empty data
    metrics = analyzer.analyze_player([], [], player_id=1, team=1)
    assert metrics.total_energy_expenditure == 0.0, "Empty data should give zero energy"
    print("✓ Empty data handled correctly")

    # Test 2: Mismatched lengths (should be handled)
    velocities = list(range(100))
    accelerations = list(range(50))
    metrics = analyzer.analyze_player(velocities, accelerations, player_id=2, team=1)
    assert metrics.frames_analyzed == 50, "Should use minimum length"
    print("✓ Mismatched lengths handled correctly")

    # Test 3: Extreme values
    velocities = [100.0] * 100  # Unrealistic high velocity
    accelerations = [50.0] * 100  # Unrealistic high acceleration
    power = analyzer.calculate_metabolic_power(
        np.array(velocities), np.array(accelerations)
    )
    assert np.all(power <= 75.0), "Power should be capped at 75 W/kg"
    print("✓ Extreme values capped appropriately")

    print("✅ Edge case tests passed!\n")


def run_all_tests():
    """Run all test cases"""
    print("\n" + "=" * 60)
    print("METABOLIC POWER ANALYZER TEST SUITE")
    print("=" * 60)

    try:
        test_metabolic_power_calculation()
        test_energy_expenditure()
        test_equivalent_distance()
        test_player_analysis()
        test_power_zones()
        test_trajectory_conversion()
        test_export_format()
        test_edge_cases()

        print("=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("\nMetabolic Power Analyzer is working correctly.")
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
