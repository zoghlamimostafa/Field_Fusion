#!/usr/bin/env python3
"""
Phase 3 TacticAI Complete Demo
Demonstrates corner kick detection, graph building, GNN prediction
"""

import sys
sys.path.append('..')

import torch
import numpy as np
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader

from corner_kick_detector import CornerKick, PlayerPosition, CornerSide, PlayerRole, CornerKickDetector
from corner_graph_builder import CornerGraphBuilder
from tacticai_gnn import TacticAIGNN, TacticAITrainer


def demo_1_corner_detection():
    """Demo 1: Corner kick detection"""
    print("\n" + "=" * 80)
    print("DEMO 1: Corner Kick Detection")
    print("=" * 80)

    detector = CornerKickDetector()

    # Test with StatsBomb data
    print("\n1. Testing with StatsBomb event data...")
    try:
        from kloppy_data_loader import KloppyDataLoader

        loader = KloppyDataLoader()
        data = loader.load_statsbomb_open_data(match_id=3788741)
        events = loader.convert_events_to_training_data(data)

        corners = detector.detect_from_events(events['all_events'])
        print(f"   ✓ Detected {len(corners)} corners from StatsBomb")

    except Exception as e:
        print(f"   ⚠️ StatsBomb detection skipped: {e}")

    # Test with simulated tracking data
    print("\n2. Testing with simulated tracking data...")
    tracking_data = create_mock_corner_tracking()
    corners = detector.detect_from_tracking(tracking_data)

    if corners:
        print(f"   ✓ Detected {len(corners)} corner(s)")
        corner = corners[0]
        print(f"   ✓ Corner details:")
        print(f"      Side: {corner.corner_side.value}")
        print(f"      Attacking players: {len(corner.attacking_players)}")
        print(f"      Defending players: {len(corner.defending_players)}")

    return corners


def demo_2_graph_building(corners):
    """Demo 2: Graph construction"""
    print("\n" + "=" * 80)
    print("DEMO 2: Graph Construction")
    print("=" * 80)

    # Always create synthetic dataset for training
    print("   Creating synthetic dataset for demo...")
    from corner_graph_builder import CornerGraphBuilder
    builder = CornerGraphBuilder(k_neighbors=3)

    # Generate 50 synthetic corners for training
    synthetic_corners = [create_synthetic_corner() for _ in range(50)]

    print(f"\nBuilding graphs for {len(synthetic_corners)} corner(s)...")
    graphs = builder.batch_build_graphs(synthetic_corners)

    if graphs:
        graph = graphs[0]
        print(f"\n✓ Graphs built successfully:")
        print(f"   Total graphs: {len(graphs)}")
        print(f"   Example - Nodes: {graph.num_nodes}")
        print(f"   Example - Edges: {graph.edge_index.shape[1]}")
        print(f"   Example - Node features: {graph.x.shape}")
        print(f"   Example - Edge features: {graph.edge_attr.shape}")
        print(f"   Example - Target outcome: {graph.y.item()}")

        # Visualize first graph
        print(f"\nGenerating visualization for first graph...")
        builder.visualize_graph(graph, save_path="demo_tacticai_graph.png")

    return graphs


def demo_3_gnn_training(graphs):
    """Demo 3: GNN training"""
    print("\n" + "=" * 80)
    print("DEMO 3: GNN Training")
    print("=" * 80)

    if not graphs:
        print("   No graphs available, creating synthetic dataset...")
        graphs = create_synthetic_dataset(num_samples=50)

    # Split dataset
    train_size = int(0.8 * len(graphs))
    train_graphs = graphs[:train_size]
    val_graphs = graphs[train_size:]

    print(f"\nDataset split:")
    print(f"   Training: {len(train_graphs)} graphs")
    print(f"   Validation: {len(val_graphs)} graphs")

    # Create data loaders
    train_loader = DataLoader(train_graphs, batch_size=8, shuffle=True)
    val_loader = DataLoader(val_graphs, batch_size=8)

    # Initialize model
    model = TacticAIGNN(
        node_features=12,
        edge_features=4,
        hidden_dim=64,
        num_classes=4,
        num_heads=4,
        dropout=0.2
    )

    print(f"\nModel initialized:")
    print(f"   Total parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Train
    trainer = TacticAITrainer(model, lr=0.001)

    print(f"\nTraining model (10 epochs for demo)...")
    history = trainer.train(train_loader, val_loader, epochs=10, patience=5)

    print(f"\n✓ Training complete!")
    print(f"   Best validation accuracy: {history['best_val_acc']:.4f}")

    return model, history


def demo_4_predictions(model, graphs):
    """Demo 4: Make predictions"""
    print("\n" + "=" * 80)
    print("DEMO 4: Outcome Predictions")
    print("=" * 80)

    if not graphs:
        print("   No graphs available")
        return

    print(f"\nMaking predictions on {min(5, len(graphs))} corners...")

    for i, graph in enumerate(graphs[:5]):
        prediction = model.predict_outcome(graph)

        print(f"\nCorner {i+1}:")
        print(f"   True outcome: {graph.y.item()}")
        print(f"   Predicted: {prediction['predicted_class']}")
        print(f"   Confidence: {prediction['confidence']:.3f}")
        print(f"   Probabilities:")
        for outcome, prob in prediction['probabilities'].items():
            print(f"      {outcome}: {prob:.3f}")


def demo_5_tactical_recommendations(model):
    """Demo 5: Tactical recommendations (simplified)"""
    print("\n" + "=" * 80)
    print("DEMO 5: Tactical Recommendations")
    print("=" * 80)

    # Create baseline corner
    corner = create_synthetic_corner()
    builder = CornerGraphBuilder()
    baseline_graph = builder.build_graph(corner)

    # Get baseline prediction
    baseline_pred = model.predict_outcome(baseline_graph)

    print(f"\nBaseline corner:")
    print(f"   Predicted outcome: {baseline_pred['predicted_class']}")
    print(f"   Goal probability: {baseline_pred['probabilities']['goal']:.3f}")

    # Try tactical adjustments
    print(f"\nTesting tactical adjustments...")

    adjustments = [
        ("Move attacker forward 2m", lambda c: adjust_player_position(c, 0, dx=2)),
        ("Add attacker at near post", lambda c: add_near_post_attacker(c)),
        ("Tighten defensive marking", lambda c: compress_defense(c))
    ]

    for adjustment_name, adjustment_func in adjustments:
        # Apply adjustment
        modified_corner = create_synthetic_corner()
        adjustment_func(modified_corner)

        # Get new prediction
        modified_graph = builder.build_graph(modified_corner)
        new_pred = model.predict_outcome(modified_graph)

        # Calculate improvement
        improvement = new_pred['probabilities']['goal'] - baseline_pred['probabilities']['goal']

        print(f"\n   {adjustment_name}:")
        print(f"      Goal prob: {new_pred['probabilities']['goal']:.3f}")
        print(f"      Change: {improvement:+.3f} ({improvement*100:+.1f}%)")


# Helper functions

def create_mock_corner_tracking():
    """Create mock tracking data for testing"""
    return {
        'ball': [{'frame': 0, 'position': [105, 0]}],
        'players': [
            # Attacking
            {'frame': 0, 'player_id': 1, 'team': 1, 'position': [105, 5]},
            {'frame': 0, 'player_id': 2, 'team': 1, 'position': [95, 30]},
            {'frame': 0, 'player_id': 3, 'team': 1, 'position': [98, 38]},
            {'frame': 0, 'player_id': 4, 'team': 1, 'position': [92, 34]},
            # Defending
            {'frame': 0, 'player_id': 11, 'team': 2, 'position': [99, 34]},
            {'frame': 0, 'player_id': 12, 'team': 2, 'position': [95, 32]},
            {'frame': 0, 'player_id': 13, 'team': 2, 'position': [96, 36]},
            {'frame': 0, 'player_id': 14, 'team': 2, 'position': [92, 30]},
            {'frame': 0, 'player_id': 15, 'team': 2, 'position': [92, 38]},
            {'frame': 0, 'player_id': 16, 'team': 2, 'position': [90, 34]},
        ]
    }


def create_synthetic_corner():
    """Create a synthetic corner for testing"""
    corner = CornerKick(
        frame_id=100,
        timestamp=4.0,
        corner_side=CornerSide.BOTTOM_RIGHT,
        attacking_team=1,
        defending_team=2,
        ball_x=105,
        ball_y=0,
        outcome='shot'
    )

    # Add attacking players
    corner.attacking_players = [
        PlayerPosition(1, 1, 105, 5, 0, 0, PlayerRole.CORNER_TAKER),
        PlayerPosition(2, 1, 95, 30, 0, 0, PlayerRole.ATTACKER),
        PlayerPosition(3, 1, 98, 38, 0, 0, PlayerRole.ATTACKER),
        PlayerPosition(4, 1, 92, 34, 0, 0, PlayerRole.ATTACKER),
    ]

    # Add defending players
    corner.defending_players = [
        PlayerPosition(11, 2, 99, 34, 0, 0, PlayerRole.GOALKEEPER),
        PlayerPosition(12, 2, 95, 32, 0, 0, PlayerRole.DEFENDER),
        PlayerPosition(13, 2, 96, 36, 0, 0, PlayerRole.DEFENDER),
        PlayerPosition(14, 2, 92, 30, 0, 0, PlayerRole.DEFENDER),
    ]

    return corner


def create_synthetic_dataset(num_samples=50):
    """Create synthetic dataset for training"""
    from corner_graph_builder import CornerGraphBuilder

    builder = CornerGraphBuilder()
    graphs = []

    outcomes = ['clearance', 'possession_retained', 'shot', 'goal']

    for i in range(num_samples):
        corner = CornerKick(
            frame_id=i,
            timestamp=i * 4.0,
            corner_side=CornerSide.BOTTOM_RIGHT,
            attacking_team=1,
            defending_team=2,
            ball_x=105,
            ball_y=np.random.rand() * 10,
            outcome=np.random.choice(outcomes)
        )

        # Random player positions
        corner.attacking_players = [
            PlayerPosition(
                j, 1,
                90 + np.random.rand() * 15,
                25 + np.random.rand() * 18,
                np.random.randn() * 0.5,
                np.random.randn() * 0.5,
                PlayerRole.ATTACKER
            )
            for j in range(1, 5)
        ]

        corner.defending_players = [
            PlayerPosition(
                10 + j, 2,
                88 + np.random.rand() * 12,
                28 + np.random.rand() * 12,
                np.random.randn() * 0.5,
                np.random.randn() * 0.5,
                PlayerRole.DEFENDER
            )
            for j in range(1, 5)
        ]

        graph = builder.build_graph(corner)
        graphs.append(graph)

    return graphs


def adjust_player_position(corner, player_idx, dx=0, dy=0):
    """Adjust player position"""
    if player_idx < len(corner.attacking_players):
        corner.attacking_players[player_idx].x += dx
        corner.attacking_players[player_idx].y += dy


def add_near_post_attacker(corner):
    """Add attacker at near post"""
    new_player = PlayerPosition(
        99, corner.attacking_team,
        100, 30, 0, 0,
        PlayerRole.ATTACKER
    )
    corner.attacking_players.append(new_player)


def compress_defense(corner):
    """Move defenders closer together"""
    for defender in corner.defending_players:
        defender.x = defender.x * 0.95  # Move toward goal


def run_all_demos():
    """Run all TacticAI demos"""
    print("=" * 80)
    print("TUNISIA FOOTBALL AI - TACTICAI COMPLETE DEMO")
    print("Phase 3: Corner Kick Analysis with Graph Neural Networks")
    print("=" * 80)

    try:
        # Demo 1: Detection
        corners = demo_1_corner_detection()

        # Demo 2: Graph building
        graphs = demo_2_graph_building(corners)

        # Demo 3: Training
        model, history = demo_3_gnn_training(graphs)

        # Demo 4: Predictions
        demo_4_predictions(model, graphs)

        # Demo 5: Recommendations
        demo_5_tactical_recommendations(model)

        print("\n" + "=" * 80)
        print("✅ ALL TACTICAI DEMOS COMPLETE!")
        print("=" * 80)
        print("\nGenerated files:")
        print("   - demo_tacticai_graph.png (graph visualization)")
        print("   - models/tacticai_best.pt (trained model)")
        print("\nYou can now:")
        print("   1. Use the trained model for corner analysis")
        print("   2. Generate tactical recommendations")
        print("   3. Train on real SkillCorner data for better accuracy")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error during demos: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_demos()
