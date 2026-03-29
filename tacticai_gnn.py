"""
TacticAI Graph Neural Network
GATv2-based architecture for corner kick outcome prediction
Inspired by Google DeepMind's TacticAI paper
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATv2Conv, global_mean_pool, global_add_pool
from typing import Optional, Dict


class TacticAIGNN(nn.Module):
    """
    Graph Neural Network for corner kick analysis

    Architecture:
    - 3 GATv2 layers with multi-head attention
    - Global pooling for graph-level prediction
    - MLP for outcome classification

    Based on TacticAI paper (DeepMind, 2024)
    """

    def __init__(self,
                 node_features: int = 12,
                 edge_features: int = 4,
                 hidden_dim: int = 64,
                 num_classes: int = 4,
                 num_heads: int = 4,
                 dropout: float = 0.2):
        """
        Initialize TacticAI GNN

        Args:
            node_features: Number of node features (default: 12)
            edge_features: Number of edge features (default: 4)
            hidden_dim: Hidden dimension size (default: 64)
            num_classes: Number of outcome classes (default: 4)
            num_heads: Number of attention heads (default: 4)
            dropout: Dropout probability (default: 0.2)
        """
        super().__init__()

        self.node_features = node_features
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes

        # GATv2 layers
        self.conv1 = GATv2Conv(
            node_features, hidden_dim,
            heads=num_heads, edge_dim=edge_features, dropout=dropout
        )

        self.conv2 = GATv2Conv(
            hidden_dim * num_heads, hidden_dim,
            heads=num_heads, edge_dim=edge_features, dropout=dropout
        )

        self.conv3 = GATv2Conv(
            hidden_dim * num_heads, hidden_dim,
            heads=1, edge_dim=edge_features, dropout=dropout
        )

        # MLP for graph-level prediction
        self.mlp = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, num_classes)
        )

        # For embeddings
        self.embedding_dim = hidden_dim

    def forward(self, data):
        """
        Forward pass

        Args:
            data: PyTorch Geometric Data object with:
                - x: Node features [num_nodes, node_features]
                - edge_index: Edge connectivity [2, num_edges]
                - edge_attr: Edge features [num_edges, edge_features]
                - batch: Batch assignment [num_nodes]

        Returns:
            Outcome logits [batch_size, num_classes]
        """
        x, edge_index, edge_attr = data.x, data.edge_index, data.edge_attr
        batch = data.batch if hasattr(data, 'batch') else torch.zeros(x.size(0), dtype=torch.long)

        # GATv2 layers
        x = F.elu(self.conv1(x, edge_index, edge_attr))
        x = F.elu(self.conv2(x, edge_index, edge_attr))
        x = self.conv3(x, edge_index, edge_attr)

        # Global pooling
        x = global_mean_pool(x, batch)

        # MLP
        x = self.mlp(x)

        return x

    def get_embedding(self, data):
        """
        Get graph embedding (before classification layer)

        Args:
            data: PyTorch Geometric Data object

        Returns:
            Graph embedding [batch_size, embedding_dim]
        """
        x, edge_index, edge_attr = data.x, data.edge_index, data.edge_attr
        batch = data.batch if hasattr(data, 'batch') else torch.zeros(x.size(0), dtype=torch.long)

        # GATv2 layers
        x = F.elu(self.conv1(x, edge_index, edge_attr))
        x = F.elu(self.conv2(x, edge_index, edge_attr))
        x = self.conv3(x, edge_index, edge_attr)

        # Global pooling
        x = global_mean_pool(x, batch)

        return x

    def predict_outcome(self, corner_graph) -> Dict:
        """
        Predict outcome for a single corner kick

        Args:
            corner_graph: PyTorch Geometric Data object

        Returns:
            Dictionary with predictions and probabilities
        """
        self.eval()

        with torch.no_grad():
            # Ensure batch dimension
            if not hasattr(corner_graph, 'batch'):
                corner_graph.batch = torch.zeros(corner_graph.x.size(0), dtype=torch.long)

            logits = self.forward(corner_graph)
            probs = F.softmax(logits, dim=1)[0]

        classes = ['clearance', 'possession_retained', 'shot', 'goal']
        prediction = {
            'predicted_class': classes[probs.argmax()],
            'probabilities': {c: probs[i].item() for i, c in enumerate(classes)},
            'confidence': probs.max().item()
        }

        return prediction

    def save_model(self, path: str):
        """Save model weights"""
        torch.save(self.state_dict(), path)
        print(f"Model saved to {path}")

    def load_model(self, path: str):
        """Load model weights"""
        self.load_state_dict(torch.load(path))
        print(f"Model loaded from {path}")


class TacticAITrainer:
    """
    Training utilities for TacticAI GNN
    """

    def __init__(self, model: TacticAIGNN, lr: float = 0.001):
        """
        Initialize trainer

        Args:
            model: TacticAI GNN model
            lr: Learning rate
        """
        self.model = model
        self.optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        self.criterion = nn.CrossEntropyLoss()

        self.train_losses = []
        self.val_accs = []

    def train_epoch(self, train_loader):
        """Train for one epoch"""
        self.model.train()
        total_loss = 0
        num_batches = 0

        for batch in train_loader:
            self.optimizer.zero_grad()
            out = self.model(batch)
            loss = self.criterion(out, batch.y)
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()
            num_batches += 1

        avg_loss = total_loss / max(num_batches, 1)
        self.train_losses.append(avg_loss)
        return avg_loss

    def evaluate(self, val_loader):
        """Evaluate on validation set"""
        self.model.eval()
        correct = 0
        total = 0

        with torch.no_grad():
            for batch in val_loader:
                out = self.model(batch)
                pred = out.argmax(dim=1)
                correct += (pred == batch.y).sum().item()
                total += batch.y.size(0)

        accuracy = correct / max(total, 1)
        self.val_accs.append(accuracy)
        return accuracy

    def train(self, train_loader, val_loader, epochs: int = 100, patience: int = 10):
        """
        Full training loop with early stopping

        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            epochs: Maximum number of epochs
            patience: Early stopping patience

        Returns:
            Training history
        """
        best_val_acc = 0
        patience_counter = 0

        print(f"\nTraining TacticAI GNN for {epochs} epochs...")
        print("=" * 60)

        for epoch in range(epochs):
            train_loss = self.train_epoch(train_loader)
            val_acc = self.evaluate(val_loader)

            print(f"Epoch {epoch+1:3d}/{epochs}: Loss={train_loss:.4f}, Val Acc={val_acc:.4f}")

            # Early stopping
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                patience_counter = 0
                # Save best model
                self.model.save_model('models/tacticai_best.pt')
            else:
                patience_counter += 1

            if patience_counter >= patience:
                print(f"\nEarly stopping at epoch {epoch+1}")
                break

        print("=" * 60)
        print(f"Training complete! Best validation accuracy: {best_val_acc:.4f}")

        return {
            'train_losses': self.train_losses,
            'val_accs': self.val_accs,
            'best_val_acc': best_val_acc
        }


def demo_tacticai_gnn():
    """Demonstrate TacticAI GNN"""
    print("=" * 80)
    print("TacticAI GNN Demo")
    print("=" * 80)

    # Create sample corner graph
    from corner_kick_detector import CornerKick, PlayerPosition, CornerSide, PlayerRole
    from corner_graph_builder import CornerGraphBuilder

    # Build a sample corner
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

    # Add players
    corner.attacking_players = [
        PlayerPosition(i, 1, 95+i*2, 30+i*2, 0, 0, PlayerRole.ATTACKER)
        for i in range(4)
    ]
    corner.defending_players = [
        PlayerPosition(10+i, 2, 92+i*2, 32+i, 0, 0, PlayerRole.DEFENDER)
        for i in range(4)
    ]

    # Build graph
    builder = CornerGraphBuilder()
    graph = builder.build_graph(corner)

    print(f"\n1. Sample corner graph:")
    print(f"   Nodes: {graph.num_nodes}")
    print(f"   Edges: {graph.edge_index.shape[1]}")
    print(f"   True outcome: {graph.y.item()} (shot)")

    # Initialize model
    model = TacticAIGNN()
    print(f"\n2. Model initialized:")
    print(f"   Parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Forward pass
    print(f"\n3. Testing forward pass...")
    logits = model(graph)
    print(f"   Output shape: {logits.shape}")
    print(f"   Logits: {logits[0].detach().numpy()}")

    # Prediction
    print(f"\n4. Making prediction...")
    prediction = model.predict_outcome(graph)
    print(f"   Predicted: {prediction['predicted_class']}")
    print(f"   Confidence: {prediction['confidence']:.3f}")
    print(f"   Probabilities:")
    for outcome, prob in prediction['probabilities'].items():
        print(f"     {outcome}: {prob:.3f}")

    # Get embedding
    print(f"\n5. Extracting embedding...")
    embedding = model.get_embedding(graph)
    print(f"   Embedding shape: {embedding.shape}")
    print(f"   Embedding norm: {embedding.norm().item():.3f}")

    print("\n" + "=" * 80)
    print("✅ TacticAI GNN demo complete!")
    print("=" * 80)


if __name__ == "__main__":
    import os
    os.makedirs('models', exist_ok=True)
    demo_tacticai_gnn()
