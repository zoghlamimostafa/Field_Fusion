"""
Corner Graph Builder for TacticAI
Converts corner kick data into graph representation for GNN processing
"""

import numpy as np
import torch
from torch_geometric.data import Data
from sklearn.neighbors import kneighbors_graph
from typing import List, Tuple, Optional
from corner_kick_detector import CornerKick, PlayerRole


class CornerGraphBuilder:
    """
    Build graph representation for corner kicks

    Graph structure:
    - Nodes: 22 players (11 attacking + 11 defending)
    - Node features: position, velocity, team, role
    - Edges: k-nearest neighbors + tactical connections
    - Edge features: distance, angle, relative velocity
    """

    def __init__(self, k_neighbors: int = 5, include_ball: bool = False):
        """
        Initialize graph builder

        Args:
            k_neighbors: Number of nearest neighbors for edge construction
            include_ball: Whether to include ball as a node (default: False)
        """
        self.k_neighbors = k_neighbors
        self.include_ball = include_ball

        # Feature dimensions
        self.node_feature_dim = 12  # x, y, vx, vy, team(2), role(4), dist_to_goal, dist_to_ball
        self.edge_feature_dim = 4   # distance, angle, rel_vx, rel_vy

        # Outcome encoding
        self.outcome_classes = ['clearance', 'possession_retained', 'shot', 'goal']
        self.num_classes = len(self.outcome_classes)

    def build_graph(self, corner: CornerKick, normalize: bool = True) -> Data:
        """
        Convert CornerKick to PyTorch Geometric graph

        Args:
            corner: CornerKick object
            normalize: Whether to normalize coordinates (default: True)

        Returns:
            torch_geometric.data.Data object
        """
        # Extract node features
        node_features = self._extract_node_features(corner, normalize)

        # Build edges
        edge_index = self._build_edges(corner)

        # Extract edge features
        edge_attr = self._extract_edge_features(corner, edge_index, normalize)

        # Encode outcome
        y = self._encode_outcome(corner.outcome)

        # Create graph
        graph = Data(
            x=torch.tensor(node_features, dtype=torch.float),
            edge_index=torch.tensor(edge_index, dtype=torch.long),
            edge_attr=torch.tensor(edge_attr, dtype=torch.float),
            y=torch.tensor([y], dtype=torch.long)
        )

        # Add metadata
        graph.num_nodes = len(node_features)
        graph.corner_id = corner.frame_id

        return graph

    def _extract_node_features(self, corner: CornerKick, normalize: bool) -> np.ndarray:
        """
        Extract features for each player node

        Features per node (dim=12):
        - x, y position (2)
        - vx, vy velocity (2)
        - team one-hot (2): [1,0] for attacking, [0,1] for defending
        - role one-hot (4): [taker, attacker, defender, goalkeeper]
        - distance to goal (1)
        - distance to ball (1)

        Args:
            corner: CornerKick object
            normalize: Whether to normalize spatial features

        Returns:
            Node feature matrix of shape (num_players, feature_dim)
        """
        all_players = corner.attacking_players + corner.defending_players
        features = []

        for player in all_players:
            # Position
            x, y = player.x, player.y
            if normalize:
                x /= 105.0  # Normalize to [0, 1]
                y /= 68.0

            # Velocity
            vx, vy = player.vx, player.vy
            if normalize:
                vx /= 10.0  # Normalize velocity (assume max ~10 m/s)
                vy /= 10.0

            # Team encoding
            is_attacking = int(player.team == corner.attacking_team)
            team_encoding = [is_attacking, 1 - is_attacking]

            # Role encoding (one-hot)
            role_encoding = self._encode_role(player.role)

            # Distances
            dist_goal = player.distance_to_goal
            dist_ball = player.distance_to_ball
            if normalize:
                dist_goal /= 105.0
                dist_ball /= 105.0

            # Combine features
            feature_vec = [
                x, y, vx, vy,
                *team_encoding,
                *role_encoding,
                dist_goal, dist_ball
            ]

            features.append(feature_vec)

        return np.array(features, dtype=np.float32)

    def _encode_role(self, role: PlayerRole) -> List[int]:
        """
        Encode player role as one-hot vector

        Roles: [taker, attacker, defender, goalkeeper]
        """
        role_map = {
            PlayerRole.CORNER_TAKER: [1, 0, 0, 0],
            PlayerRole.ATTACKER: [0, 1, 0, 0],
            PlayerRole.DEFENDER: [0, 0, 1, 0],
            PlayerRole.GOALKEEPER: [0, 0, 0, 1],
            PlayerRole.UNKNOWN: [0, 0, 0, 0]
        }
        return role_map.get(role, [0, 0, 0, 0])

    def _build_edges(self, corner: CornerKick) -> np.ndarray:
        """
        Build edge connectivity

        Edge types:
        1. k-nearest neighbors (spatial proximity)
        2. Same-team connections
        3. Marking relationships (optional)

        Returns:
            Edge index of shape (2, num_edges)
        """
        all_players = corner.attacking_players + corner.defending_players
        num_players = len(all_players)

        if num_players == 0:
            return np.array([[],  []], dtype=np.int64)

        # Extract positions
        positions = np.array([[p.x, p.y] for p in all_players])

        # 1. Build k-NN graph
        knn_graph = kneighbors_graph(
            positions, self.k_neighbors,
            mode='connectivity', include_self=False
        )

        # Convert to edge index format
        edge_sources, edge_targets = knn_graph.nonzero()
        edge_index = np.array([edge_sources, edge_targets], dtype=np.int64)

        # 2. Add same-team connections
        team_edges = self._add_team_edges(corner, num_players)
        if team_edges.shape[1] > 0:
            edge_index = np.concatenate([edge_index, team_edges], axis=1)

        # 3. Add marking relationships (defender-attacker pairs)
        marking_edges = self._add_marking_edges(corner, all_players)
        if marking_edges.shape[1] > 0:
            edge_index = np.concatenate([edge_index, marking_edges], axis=1)

        # Remove duplicate edges
        edge_index = self._remove_duplicate_edges(edge_index)

        return edge_index

    def _add_team_edges(self, corner: CornerKick, num_players: int) -> np.ndarray:
        """Add edges between teammates"""
        attacking_count = len(corner.attacking_players)
        edges = []

        # Connect attacking players
        for i in range(attacking_count):
            for j in range(i + 1, attacking_count):
                edges.append([i, j])
                edges.append([j, i])  # Bidirectional

        # Connect defending players
        defending_start = attacking_count
        for i in range(defending_start, num_players):
            for j in range(i + 1, num_players):
                edges.append([i, j])
                edges.append([j, i])

        if edges:
            return np.array(edges, dtype=np.int64).T
        return np.array([[],[]], dtype=np.int64)

    def _add_marking_edges(self, corner: CornerKick,
                          all_players: List) -> np.ndarray:
        """
        Add edges for marking relationships

        Connect each attacker to their nearest defender
        """
        attacking_count = len(corner.attacking_players)
        edges = []

        for i, attacker in enumerate(corner.attacking_players):
            min_dist = float('inf')
            nearest_defender_idx = -1

            for j, defender in enumerate(corner.defending_players):
                dist = np.sqrt(
                    (attacker.x - defender.x)**2 + (attacker.y - defender.y)**2
                )
                if dist < min_dist:
                    min_dist = dist
                    nearest_defender_idx = j

            if nearest_defender_idx >= 0:
                defender_global_idx = attacking_count + nearest_defender_idx
                edges.append([i, defender_global_idx])
                edges.append([defender_global_idx, i])  # Bidirectional

        if edges:
            return np.array(edges, dtype=np.int64).T
        return np.array([[],[]], dtype=np.int64)

    def _remove_duplicate_edges(self, edge_index: np.ndarray) -> np.ndarray:
        """Remove duplicate edges"""
        if edge_index.shape[1] == 0:
            return edge_index

        # Convert to tuples for uniqueness check
        edges = set()
        unique_edges = []

        for i in range(edge_index.shape[1]):
            edge = (edge_index[0, i], edge_index[1, i])
            if edge not in edges:
                edges.add(edge)
                unique_edges.append(edge)

        if unique_edges:
            return np.array(unique_edges, dtype=np.int64).T
        return np.array([[],[]], dtype=np.int64)

    def _extract_edge_features(self, corner: CornerKick,
                               edge_index: np.ndarray,
                               normalize: bool) -> np.ndarray:
        """
        Extract edge features

        Features per edge (dim=4):
        - distance between players (1)
        - angle between players (1)
        - relative velocity x (1)
        - relative velocity y (1)

        Args:
            corner: CornerKick object
            edge_index: Edge connectivity
            normalize: Whether to normalize features

        Returns:
            Edge feature matrix of shape (num_edges, edge_feature_dim)
        """
        all_players = corner.attacking_players + corner.defending_players

        if edge_index.shape[1] == 0:
            return np.array([]).reshape(0, self.edge_feature_dim)

        edge_features = []

        for i in range(edge_index.shape[1]):
            src_idx = edge_index[0, i]
            dst_idx = edge_index[1, i]

            src_player = all_players[src_idx]
            dst_player = all_players[dst_idx]

            # Distance
            distance = np.sqrt(
                (src_player.x - dst_player.x)**2 +
                (src_player.y - dst_player.y)**2
            )

            # Angle
            dx = dst_player.x - src_player.x
            dy = dst_player.y - src_player.y
            angle = np.arctan2(dy, dx)

            # Relative velocity
            rel_vx = dst_player.vx - src_player.vx
            rel_vy = dst_player.vy - src_player.vy

            if normalize:
                distance /= 105.0
                angle /= np.pi  # Normalize to [-1, 1]
                rel_vx /= 10.0
                rel_vy /= 10.0

            edge_features.append([distance, angle, rel_vx, rel_vy])

        return np.array(edge_features, dtype=np.float32)

    def _encode_outcome(self, outcome: Optional[str]) -> int:
        """
        Encode outcome as class index

        Classes: clearance (0), possession_retained (1), shot (2), goal (3)
        """
        if outcome is None:
            return 1  # Default: possession_retained

        outcome_lower = outcome.lower()

        if 'goal' in outcome_lower:
            return 3
        elif 'shot' in outcome_lower:
            return 2
        elif 'clearance' in outcome_lower or 'clear' in outcome_lower:
            return 0
        else:
            return 1  # possession_retained

    def batch_build_graphs(self, corners: List[CornerKick]) -> List[Data]:
        """
        Build graphs for a batch of corners

        Args:
            corners: List of CornerKick objects

        Returns:
            List of graph Data objects
        """
        graphs = []

        for corner in corners:
            try:
                graph = self.build_graph(corner)
                graphs.append(graph)
            except Exception as e:
                print(f"Error building graph for corner {corner.frame_id}: {e}")
                continue

        return graphs

    def visualize_graph(self, graph: Data, save_path: Optional[str] = None):
        """
        Visualize graph structure

        Args:
            graph: PyTorch Geometric Data object
            save_path: Optional path to save visualization
        """
        try:
            import matplotlib.pyplot as plt
            import networkx as nx

            # Create NetworkX graph
            G = nx.Graph()

            num_nodes = graph.x.shape[0]
            G.add_nodes_from(range(num_nodes))

            # Add edges
            edge_index = graph.edge_index.numpy()
            for i in range(edge_index.shape[1]):
                G.add_edge(edge_index[0, i], edge_index[1, i])

            # Extract positions from node features
            positions = graph.x[:, :2].numpy()  # x, y coordinates
            pos_dict = {i: positions[i] for i in range(num_nodes)}

            # Determine node colors based on team
            team_features = graph.x[:, 4:6].numpy()  # team encoding
            colors = ['red' if t[0] > 0.5 else 'blue' for t in team_features]

            # Plot
            plt.figure(figsize=(12, 8))
            nx.draw(G, pos=pos_dict, node_color=colors, with_labels=True,
                   node_size=500, font_size=8, edge_color='gray', alpha=0.7)

            plt.title(f"Corner Kick Graph (Outcome class: {graph.y.item()})")
            plt.xlabel("Normalized X")
            plt.ylabel("Normalized Y")

            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                print(f"Graph visualization saved to {save_path}")
            else:
                plt.show()

            plt.close()

        except ImportError:
            print("Matplotlib not available for visualization")
        except Exception as e:
            print(f"Error visualizing graph: {e}")


def demo_graph_builder():
    """Demonstrate graph building"""
    print("=" * 80)
    print("Corner Graph Builder Demo")
    print("=" * 80)

    # Create a sample corner kick
    from corner_kick_detector import CornerKick, PlayerPosition, CornerSide, PlayerRole

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

    # Build graph
    builder = CornerGraphBuilder(k_neighbors=3)
    graph = builder.build_graph(corner)

    print(f"\n✓ Graph built successfully!")
    print(f"  Nodes: {graph.num_nodes}")
    print(f"  Node features shape: {graph.x.shape}")
    print(f"  Edges: {graph.edge_index.shape[1]}")
    print(f"  Edge features shape: {graph.edge_attr.shape}")
    print(f"  Target outcome: {graph.y.item()} (shot)")

    # Show node features for first player
    print(f"\nFirst node features (Player 1):")
    print(f"  {graph.x[0].numpy()}")

    # Visualize graph
    print(f"\nGenerating graph visualization...")
    builder.visualize_graph(graph, save_path="demo_corner_graph.png")

    print("\n" + "=" * 80)
    print("✅ Graph builder demo complete!")
    print("=" * 80)


if __name__ == "__main__":
    demo_graph_builder()
