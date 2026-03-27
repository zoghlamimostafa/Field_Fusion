#!/usr/bin/env python3
"""
Pass Network Analyzer - Week 2, Day 10-11
Tunisia Football AI Level 3

Analyzes passing networks to identify key players and tactical patterns.

Features:
- Build directed pass graph (NetworkX)
- Identify central/influential players
- Detect passing triangles
- Calculate pass completion rates per link
- Visualize network on pitch
- Microservice-ready architecture
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
import cv2
from utils.track_data_utils import iter_player_frames

# NetworkX for graph analysis
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    print("⚠️  NetworkX not installed. Pass network analysis will be limited.")


@dataclass
class PassNetwork:
    """Pass network analysis results"""
    team: int

    # Network structure
    total_passes: int
    completed_passes: int
    pass_accuracy: float  # %

    # Player metrics
    most_passes_player: Optional[int]
    most_passes_count: int
    central_players: List[int]  # Most influential in network

    # Network patterns
    passing_triangles: List[Tuple[int, int, int]]  # Trios with high pass frequency
    isolated_players: List[int]  # Players with few connections

    # Network metrics (if NetworkX available)
    network_density: float  # 0-1 scale
    average_path_length: float  # Average passes to reach any player

    frames_analyzed: int


class PassNetworkAnalyzer:
    """
    Analyzes team passing networks using graph theory
    Microservice-ready: Can be deployed as independent FastAPI service
    """

    def __init__(self, fps: int = 25):
        self.fps = fps
        self.min_passes_for_link = 2  # Minimum passes to show connection
        self.central_player_threshold = 0.7  # Top 30% by degree centrality

    def analyze_pass_networks(self,
                             analytics: Dict,
                             tracks: Dict = None) -> Dict[int, PassNetwork]:
        """
        Analyze passing networks for both teams

        Args:
            analytics: Match analytics with pass events
            tracks: Player tracking data (for positions)

        Returns:
            Dict mapping team -> PassNetwork
        """
        print("\n🔗 Analyzing Pass Networks...")

        networks = {}

        for team in [1, 2]:
            network = self._analyze_team_network(team, analytics, tracks)

            if network:
                networks[team] = network
                print(f"   Team {team}: {network.completed_passes}/{network.total_passes} passes "
                      f"({network.pass_accuracy:.1f}%), "
                      f"{len(network.passing_triangles)} triangles")

        return networks

    def _analyze_team_network(self,
                             team: int,
                             analytics: Dict,
                             tracks: Dict = None) -> Optional[PassNetwork]:
        """Analyze pass network for a specific team"""

        events = analytics.get('events', {})
        passes = events.get('passes', [])

        if not passes:
            return None

        # Filter team passes
        team_passes = [p for p in passes if p.get('team') == team]

        if len(team_passes) < 2:
            return None

        # Build pass graph
        pass_links = defaultdict(int)  # (from_player, to_player) -> count
        pass_success = defaultdict(lambda: {'success': 0, 'total': 0})
        player_passes_sent = defaultdict(int)
        player_passes_received = defaultdict(int)

        for pass_event in team_passes:
            from_player = pass_event.get('from_player')
            to_player = pass_event.get('to_player')
            success = pass_event.get('success', True)

            if from_player is None or to_player is None:
                continue

            pass_links[(from_player, to_player)] += 1
            player_passes_sent[from_player] += 1
            player_passes_received[to_player] += 1

            pass_success[(from_player, to_player)]['total'] += 1
            if success:
                pass_success[(from_player, to_player)]['success'] += 1

        total_passes = len(team_passes)
        completed_passes = sum(1 for p in team_passes if p.get('success', True))
        pass_accuracy = (completed_passes / total_passes * 100) if total_passes > 0 else 0.0

        # Find most active passer
        most_passes_player = max(player_passes_sent.items(), key=lambda x: x[1]) if player_passes_sent else (None, 0)

        # Identify central players and triangles (if NetworkX available)
        central_players = []
        passing_triangles = []
        network_density = 0.0
        avg_path_length = 0.0

        if NETWORKX_AVAILABLE:
            G = nx.DiGraph()

            # Add edges with weights
            for (from_p, to_p), count in pass_links.items():
                if count >= self.min_passes_for_link:
                    G.add_edge(from_p, to_p, weight=count)

            # Calculate centrality
            if len(G.nodes()) > 0:
                try:
                    degree_centrality = nx.degree_centrality(G)
                    threshold = np.percentile(list(degree_centrality.values()), 70)
                    central_players = [p for p, c in degree_centrality.items() if c >= threshold]

                    # Network density
                    network_density = nx.density(G)

                    # Average path length (if connected)
                    if nx.is_weakly_connected(G):
                        avg_path_length = nx.average_shortest_path_length(G.to_undirected())
                    else:
                        # Use largest component
                        largest_cc = max(nx.weakly_connected_components(G), key=len)
                        subgraph = G.subgraph(largest_cc)
                        if len(subgraph.nodes()) > 1:
                            avg_path_length = nx.average_shortest_path_length(subgraph.to_undirected())

                    # Find triangles (3-player passing patterns)
                    passing_triangles = self._find_passing_triangles(pass_links)

                except:
                    pass  # Handle any graph analysis errors

        # Identify isolated players (low connectivity)
        all_players = set(player_passes_sent.keys()) | set(player_passes_received.keys())
        isolated_players = [
            p for p in all_players
            if (player_passes_sent[p] + player_passes_received[p]) < 3
        ]

        network = PassNetwork(
            team=team,
            total_passes=total_passes,
            completed_passes=completed_passes,
            pass_accuracy=pass_accuracy,
            most_passes_player=most_passes_player[0],
            most_passes_count=most_passes_player[1],
            central_players=central_players,
            passing_triangles=passing_triangles,
            isolated_players=isolated_players,
            network_density=network_density,
            average_path_length=avg_path_length,
            frames_analyzed=0  # Not using frames here
        )

        return network

    def _find_passing_triangles(self, pass_links: Dict[Tuple[int, int], int]) -> List[Tuple[int, int, int]]:
        """
        Find passing triangles (3 players with mutual passing connections)
        """
        triangles = []

        # Get unique players
        players = set()
        for (from_p, to_p) in pass_links.keys():
            players.add(from_p)
            players.add(to_p)

        players = list(players)

        # Check all combinations of 3 players
        for i in range(len(players)):
            for j in range(i + 1, len(players)):
                for k in range(j + 1, len(players)):
                    p1, p2, p3 = players[i], players[j], players[k]

                    # Check if triangle exists (any direction of passes)
                    links = [
                        (p1, p2), (p2, p1),
                        (p2, p3), (p3, p2),
                        (p3, p1), (p1, p3)
                    ]

                    existing_links = sum(1 for link in links if link in pass_links)

                    # Triangle if at least 4 of 6 possible links exist
                    if existing_links >= 4:
                        triangles.append((p1, p2, p3))

        return triangles

    def visualize_pass_network(self,
                               network: PassNetwork,
                               analytics: Dict,
                               tracks: Dict,
                               frame: np.ndarray) -> np.ndarray:
        """
        Visualize pass network on pitch image
        """
        vis_frame = frame.copy()

        if not NETWORKX_AVAILABLE:
            cv2.putText(vis_frame, "NetworkX not installed", (50, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            return vis_frame

        # Get player positions (average across frames)
        player_positions = self._get_average_player_positions(tracks, network.team)

        # Get pass events
        events = analytics.get('events', {})
        passes = [p for p in events.get('passes', []) if p.get('team') == network.team]

        # Count passes between players
        pass_counts = defaultdict(int)
        for p in passes:
            from_p = p.get('from_player')
            to_p = p.get('to_player')
            if from_p and to_p:
                pass_counts[(from_p, to_p)] += 1

        # Draw pass links
        for (from_p, to_p), count in pass_counts.items():
            if count < self.min_passes_for_link:
                continue

            if from_p not in player_positions or to_p not in player_positions:
                continue

            start_pos = player_positions[from_p]
            end_pos = player_positions[to_p]

            # Line thickness based on pass count
            thickness = min(count, 5)

            # Color based on centrality
            if from_p in network.central_players and to_p in network.central_players:
                color = (0, 255, 0)  # Green for central players
            else:
                color = (255, 255, 255)  # White for others

            cv2.arrowedLine(vis_frame, start_pos, end_pos, color, thickness, tipLength=0.3)

        # Draw player nodes
        for player_id, pos in player_positions.items():
            if player_id in network.central_players:
                color = (0, 255, 0)  # Green for central players
                radius = 12
            elif player_id in network.isolated_players:
                color = (0, 0, 255)  # Red for isolated
                radius = 8
            else:
                color = (255, 255, 255)  # White for others
                radius = 10

            cv2.circle(vis_frame, pos, radius, color, -1)
            cv2.circle(vis_frame, pos, radius + 2, (0, 0, 0), 2)

            # Draw player ID
            cv2.putText(vis_frame, str(player_id), (pos[0] - 10, pos[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

        return vis_frame

    def _get_average_player_positions(self, tracks: Dict, team: int) -> Dict[int, Tuple[int, int]]:
        """Get average position for each player across frames"""
        player_positions = defaultdict(list)

        if 'players' not in tracks:
            return {}

        for _, frame_data in iter_player_frames(tracks):
            for player_id, data in frame_data.items():
                if data.get('team') != team:
                    continue

                bbox = data.get('bbox', [])
                if len(bbox) >= 4:
                    center_x = int((bbox[0] + bbox[2]) / 2)
                    center_y = int((bbox[1] + bbox[3]) / 2)
                    player_positions[player_id].append((center_x, center_y))

        # Average positions
        avg_positions = {}
        for player_id, positions in player_positions.items():
            avg_x = int(np.mean([p[0] for p in positions]))
            avg_y = int(np.mean([p[1] for p in positions]))
            avg_positions[player_id] = (avg_x, avg_y)

        return avg_positions

    def export_pass_network_data(self, networks: Dict[int, PassNetwork]) -> Dict:
        """
        Export pass network data to dictionary format for JSON/API
        Microservice-ready output format
        """
        return {
            'pass_networks': {
                team: {
                    'team': n.team,
                    'passes': {
                        'total': n.total_passes,
                        'completed': n.completed_passes,
                        'accuracy_percent': round(n.pass_accuracy, 1)
                    },
                    'key_players': {
                        'most_passes_player': n.most_passes_player,
                        'most_passes_count': n.most_passes_count,
                        'central_players': n.central_players,
                        'isolated_players': n.isolated_players
                    },
                    'network_structure': {
                        'passing_triangles': n.passing_triangles,
                        'network_density': round(n.network_density, 3),
                        'average_path_length': round(n.average_path_length, 2)
                    }
                }
                for team, n in networks.items()
            }
        }

    def generate_pass_network_summary(self, networks: Dict[int, PassNetwork]) -> str:
        """Generate human-readable pass network summary"""
        if not networks:
            return "No pass network data available."

        summary = "🔗 Pass Network Analysis:\n\n"

        for team, n in networks.items():
            summary += f"Team {team}:\n"
            summary += f"   Passes: {n.completed_passes}/{n.total_passes} ({n.pass_accuracy:.1f}%)\n"
            summary += f"   Most Active: Player #{n.most_passes_player} ({n.most_passes_count} passes)\n"
            summary += f"   Central Players: {n.central_players}\n"
            summary += f"   Passing Triangles: {len(n.passing_triangles)}\n"
            summary += f"   Network Density: {n.network_density:.2f}\n\n"

        return summary
