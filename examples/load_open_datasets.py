#!/usr/bin/env python3
"""
Example Scripts for Loading Open Football Datasets
Demonstrates how to use kloppy_data_loader with various providers
"""

import sys
sys.path.append('..')

from kloppy_data_loader import KloppyDataLoader
from pitch_visualizations import FootballVisualizer
import pandas as pd
import numpy as np


def example_1_statsbomb_basic():
    """
    Example 1: Load StatsBomb open data and extract basic stats
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 1: StatsBomb Open Data - Basic Loading")
    print("=" * 80)

    loader = KloppyDataLoader()

    # Load Barcelona vs Deportivo (free open data)
    print("\nLoading match data...")
    data = loader.load_statsbomb_open_data(match_id=3788741)

    # Get dataset info
    info = loader.get_dataset_info(data)
    print(f"\n✓ Match: {info['teams'][0]} vs {info['teams'][1]}")
    print(f"✓ Total events: {info['event_count']}")
    print(f"✓ Event types: {', '.join(info['event_types'][:5])}...")

    # Convert to training data
    training_data = loader.convert_events_to_training_data(
        data,
        event_types=['PASS', 'SHOT']
    )

    print(f"\n📊 Event breakdown:")
    print(f"  - Passes: {len(training_data['passes'])}")
    print(f"  - Shots: {len(training_data['shots'])}")

    # Analyze pass success rate
    passes = training_data['passes']
    successful_passes = [p for p in passes if p.get('successful', False)]
    pass_success_rate = len(successful_passes) / len(passes) * 100 if passes else 0

    print(f"\n⚽ Pass statistics:")
    print(f"  - Success rate: {pass_success_rate:.1f}%")
    print(f"  - Successful: {len(successful_passes)}")
    print(f"  - Failed: {len(passes) - len(successful_passes)}")

    # Analyze shots
    shots = training_data['shots']
    goals = [s for s in shots if s.get('is_goal', False)]

    print(f"\n🎯 Shot statistics:")
    print(f"  - Total shots: {len(shots)}")
    print(f"  - Goals: {len(goals)}")
    print(f"  - Conversion rate: {len(goals) / len(shots) * 100 if shots else 0:.1f}%")

    return data, training_data


def example_2_statsbomb_for_xg_training():
    """
    Example 2: Prepare StatsBomb data for xG model training
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: StatsBomb Data - xG Model Training Preparation")
    print("=" * 80)

    loader = KloppyDataLoader()

    print("\nLoading match data...")
    data = loader.load_statsbomb_open_data(match_id=3788741)

    # Convert events
    training_data = loader.convert_events_to_training_data(data, event_types=['SHOT'])

    shots = training_data['shots']
    print(f"\n✓ Loaded {len(shots)} shots for xG training")

    # Convert to DataFrame for ML training
    shot_features = []
    for shot in shots:
        # Calculate features for xG model
        x = shot.get('x_start', 0)
        y = shot.get('y_start', 0)

        # Distance from goal (assuming goal at x=105)
        distance = np.sqrt((105 - x) ** 2 + (34 - y) ** 2)

        # Angle to goal
        angle = np.abs(np.arctan2(34 - y, 105 - x))

        shot_features.append({
            'x': x,
            'y': y,
            'distance': distance,
            'angle': np.degrees(angle),
            'is_goal': shot.get('is_goal', False)
        })

    df = pd.DataFrame(shot_features)

    print("\n📊 Shot features prepared for xG training:")
    print(df.describe())

    print(f"\n🎯 Target distribution:")
    print(f"  - Goals: {df['is_goal'].sum()}")
    print(f"  - Non-goals: {(~df['is_goal']).sum()}")
    print(f"  - Goal rate: {df['is_goal'].mean() * 100:.1f}%")

    print("\n💡 Next step: Use this data with level_4_advanced_analytics.py")
    print("   to train the xG model!")

    return df


def example_3_visualize_statsbomb():
    """
    Example 3: Visualize StatsBomb data with mplsoccer
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Visualize StatsBomb Data with mplsoccer")
    print("=" * 80)

    loader = KloppyDataLoader()
    viz = FootballVisualizer(pitch_type='statsbomb')

    print("\nLoading match data...")
    data = loader.load_statsbomb_open_data(match_id=3788741)
    training_data = loader.convert_events_to_training_data(data, event_types=['PASS', 'SHOT'])

    # 1. Create pass network
    print("\n1. Generating pass network...")
    passes = training_data['passes']
    team_1_passes = [p for p in passes if p['team'] == 1][:50]  # Limit for demo

    if team_1_passes:
        pass_df = pd.DataFrame(team_1_passes)
        pass_df['passer_id'] = pass_df['player_id']
        pass_df['receiver_id'] = pass_df.get('receiver_id', pass_df['player_id'])  # Fallback
        pass_df['successful'] = pass_df.get('successful', True)

        fig = viz.create_pass_network(pass_df, "Team 1")
        fig.savefig("example_pass_network.png", dpi=150, bbox_inches='tight')
        print("   ✓ Saved to example_pass_network.png")

    # 2. Create shot map
    print("\n2. Generating shot map...")
    shots = training_data['shots']
    team_1_shots = [s for s in shots if s['team'] == 1]

    if team_1_shots:
        shot_df = pd.DataFrame(team_1_shots)
        shot_df['x'] = shot_df['x_start']
        shot_df['y'] = shot_df['y_start']
        shot_df['outcome'] = shot_df['is_goal'].apply(lambda x: 'goal' if x else 'miss')
        shot_df['xg'] = 0.15  # Placeholder xG

        fig = viz.create_shot_map(shot_df, "Team 1")
        fig.savefig("example_shot_map.png", dpi=150, bbox_inches='tight')
        print("   ✓ Saved to example_shot_map.png")

    print("\n✅ Visualizations generated!")


def example_4_integrate_with_pipeline():
    """
    Example 4: Show how to integrate kloppy data with Tunisia Football AI pipeline
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Integration with Tunisia Football AI Pipeline")
    print("=" * 80)

    print("""
This example shows how to use kloppy data in your existing pipeline:

### Option 1: Train Models on Open Data

```python
from kloppy_data_loader import KloppyDataLoader
from level_4_advanced_analytics import AdvancedAnalytics

# Load StatsBomb data
loader = KloppyDataLoader()
data = loader.load_statsbomb_open_data()
training_data = loader.convert_events_to_training_data(data)

# Train xG model
analytics = AdvancedAnalytics()
analytics.train_xg_model(training_data['shots'])
```

### Option 2: Load Tracking Data for Testing

```python
# Load SkillCorner tracking data
data = loader.load_skillcorner_tracking(
    "match_data.jsonl",
    "structured_data.jsonl"
)

# Convert to pipeline format
pipeline_data = loader.convert_tracking_to_pipeline_format(data)

# Use with existing modules
from fatigue_estimator import FatigueEstimator
fatigue = FatigueEstimator()
fatigue_scores = fatigue.estimate(pipeline_data['players'])
```

### Option 3: Load Multiple Matches for Large-Scale Training

```python
# Load entire StatsBomb competition
match_ids = [3788741, 3788742, 3788743]  # Multiple matches

all_shots = []
for match_id in match_ids:
    data = loader.load_statsbomb_open_data(match_id)
    training_data = loader.convert_events_to_training_data(data)
    all_shots.extend(training_data['shots'])

# Train on combined dataset
analytics.train_xg_model(all_shots)
print(f"Trained on {len(all_shots)} shots from {len(match_ids)} matches")
```
    """)


def example_5_compare_providers():
    """
    Example 5: Compare data from different providers
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Supported Data Providers")
    print("=" * 80)

    providers_info = {
        'StatsBomb': {
            'type': 'Event Data',
            'free_data': 'Yes (7 competitions)',
            'format': 'JSON',
            'use_case': 'xG training, pass analysis, event detection'
        },
        'SkillCorner': {
            'type': 'Tracking Data',
            'free_data': 'Yes (10 A-League matches)',
            'format': 'JSONL (10 fps)',
            'use_case': 'GNN training, formation detection, tactical analysis'
        },
        'Metrica Sports': {
            'type': 'Tracking Data',
            'free_data': 'Yes (3 sample matches)',
            'format': 'CSV',
            'use_case': 'Testing, algorithm development'
        },
        'Wyscout': {
            'type': 'Event Data',
            'free_data': 'Limited',
            'format': 'JSON',
            'use_case': 'Action valuation, player scouting'
        },
        'Tracab': {
            'type': 'Tracking Data',
            'free_data': 'No',
            'format': 'DAT',
            'use_case': 'Professional tracking analysis'
        },
        'EPTS (FIFA)': {
            'type': 'Tracking Data',
            'free_data': 'Depends',
            'format': 'XML + CSV',
            'use_case': 'Standardized tracking format'
        }
    }

    print("\n📊 Comparison of Data Providers:\n")
    for provider, info in providers_info.items():
        print(f"### {provider}")
        print(f"  Type: {info['type']}")
        print(f"  Free Data: {info['free_data']}")
        print(f"  Format: {info['format']}")
        print(f"  Use Case: {info['use_case']}")
        print()


def run_all_examples():
    """
    Run all examples sequentially
    """
    print("\n" + "=" * 80)
    print("TUNISIA FOOTBALL AI - OPEN DATA EXAMPLES")
    print("Demonstrating kloppy + mplsoccer integration")
    print("=" * 80)

    try:
        # Example 1: Basic loading
        example_1_statsbomb_basic()

        # Example 2: xG training preparation
        example_2_statsbomb_for_xg_training()

        # Example 3: Visualizations
        example_3_visualize_statsbomb()

        # Example 4: Pipeline integration
        example_4_integrate_with_pipeline()

        # Example 5: Provider comparison
        example_5_compare_providers()

        print("\n" + "=" * 80)
        print("✅ ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 80)

        print("\n📚 Next Steps:")
        print("  1. Load more StatsBomb matches for larger training datasets")
        print("  2. Integrate with level_4_advanced_analytics.py for xG training")
        print("  3. Download SkillCorner data for GNN/TacticAI training")
        print("  4. Use mplsoccer visualizations in Gradio dashboard")
        print()

    except Exception as e:
        print(f"\n⚠️ Error running examples: {e}")
        print("   (This may be due to missing internet connection or data files)")
        print("   The loaders are still functional - check individual examples.")


if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        examples = {
            '1': example_1_statsbomb_basic,
            '2': example_2_statsbomb_for_xg_training,
            '3': example_3_visualize_statsbomb,
            '4': example_4_integrate_with_pipeline,
            '5': example_5_compare_providers
        }

        if example_num in examples:
            examples[example_num]()
        else:
            print(f"Unknown example: {example_num}")
            print("Available: 1, 2, 3, 4, 5")
    else:
        # Run all examples
        run_all_examples()
