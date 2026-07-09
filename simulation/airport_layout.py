"""
Airport Layout Module.

Defines airport layout, gate coordinates, and distance calculations.
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import numpy as np
import math


@dataclass
class Coordinate:
    """2D coordinate representation."""
    x: int
    y: int


class AirportLayout:
    """
    Airport Layout Manager.
    Handles gate coordinates, distances, and terminal structure.
    """

    def __init__(self, num_terminals: int = 3, gates_per_terminal: int = 4):
        """Initialize airport layout."""
        self.num_terminals = num_terminals
        self.gates_per_terminal = gates_per_terminal
        self.total_gates = num_terminals * gates_per_terminal
        self.gates = self._generate_layout()

    def _generate_layout(self) -> Dict[str, Dict]:
        """Generate gate layout with coordinates."""
        gates = {}
        gate_id = 1

        # Gate sizes distribution
        gate_sizes = (
            ['small'] * 4 +
            ['medium'] * 6 +
            ['large'] * 2
        )

        for terminal in range(1, self.num_terminals + 1):
            for i in range(self.gates_per_terminal):
                gate_name = f"G{gate_id}"
                gate_size = gate_sizes[gate_id - 1] if gate_id <= len(gate_sizes) else 'medium'

                # Calculate coordinates
                # Layout: terminals arranged vertically, gates horizontally
                x_coord = 100 + (i * 150)
                y_coord = 50 + (terminal - 1) * 200

                gates[gate_name] = {
                    'gate_id': gate_name,
                    'terminal': terminal,
                    'size': gate_size,
                    'x_coord': x_coord,
                    'y_coord': y_coord,
                    'status': 'available'
                }
                gate_id += 1

        return gates

    def get_gate_coordinates(self, gate_id: str) -> Optional[Coordinate]:
        """Get coordinates for a specific gate."""
        if gate_id in self.gates:
            gate = self.gates[gate_id]
            return Coordinate(gate['x_coord'], gate['y_coord'])
        return None

    def get_distance(self, gate1_id: str, gate2_id: str) -> float:
        """Calculate Euclidean distance between two gates."""
        coord1 = self.get_gate_coordinates(gate1_id)
        coord2 = self.get_gate_coordinates(gate2_id)

        if coord1 and coord2:
            return math.sqrt((coord1.x - coord2.x)**2 + (coord1.y - coord2.y)**2)
        return float('inf')

    def get_walking_distance(self, gate_id: str, terminal_entrance: int = 1) -> float:
        """
        Calculate walking distance from gate to terminal entrance.
        Terminal entrance is at x=0, y depends on terminal.
        """
        coord = self.get_gate_coordinates(gate_id)
        if coord:
            entrance_y = 50 + (terminal_entrance - 1) * 200
            return math.sqrt(coord.x**2 + (coord.y - entrance_y)**2)
        return float('inf')

    def get_gates_by_size(self, size: str) -> List[str]:
        """Get all gates of a specific size."""
        return [gid for gid, g in self.gates.items() if g['size'] == size]

    def get_gates_by_terminal(self, terminal: int) -> List[str]:
        """Get all gates in a specific terminal."""
        return [gid for gid, g in self.gates.items() if g['terminal'] == terminal]

    def get_available_gates(self, assigned_gates: Dict[str, Tuple]) -> List[str]:
        """Get gates available at a given time."""
        return [gid for gid in self.gates if gid not in assigned_gates]

    def get_terminal_for_gate(self, gate_id: str) -> Optional[int]:
        """Get terminal number for a gate."""
        if gate_id in self.gates:
            return self.gates[gate_id]['terminal']
        return None

    def get_size_for_gate(self, gate_id: str) -> Optional[str]:
        """Get size category for a gate."""
        if gate_id in self.gates:
            return self.gates[gate_id]['size']
        return None

    def get_layout_bounds(self) -> Tuple[int, int]:
        """Get the max x and y coordinates for visualization."""
        max_x = max(g['x_coord'] for g in self.gates.values()) + 100
        max_y = max(g['y_coord'] for g in self.gates.values()) + 100
        return max_x, max_y

    def export_layout(self) -> Dict:
        """Export layout for visualization."""
        return {
            'gates': self.gates,
            'terminals': [
                {
                    'id': i,
                    'name': f"Terminal {i}",
                    'center_y': 50 + (i - 1) * 200
                }
                for i in range(1, self.num_terminals + 1)
            ],
            'bounds': self.get_layout_bounds()
        }

    def get_distance_matrix(self) -> np.ndarray:
        """Generate distance matrix between all gates."""
        gate_ids = sorted(self.gates.keys(), key=lambda x: int(x[1:]))
        n = len(gate_ids)
        matrix = np.zeros((n, n))

        for i, g1 in enumerate(gate_ids):
            for j, g2 in enumerate(gate_ids):
                if i != j:
                    matrix[i, j] = self.get_distance(g1, g2)

        return matrix, gate_ids


class AirportHeatmap:
    """Generate heatmap data for airport operations."""

    def __init__(self, layout: AirportLayout):
        self.layout = layout

    def generate_utilization_heatmap(self, gate_utilization: Dict[str, float]) -> Dict:
        """Generate utilization heatmap data."""
        heatmap_data = []
        for gate_id, utilization in gate_utilization.items():
            coord = self.layout.get_gate_coordinates(gate_id)
            if coord:
                heatmap_data.append({
                    'gate_id': gate_id,
                    'x': coord.x,
                    'y': coord.y,
                    'value': utilization,
                    'terminal': self.layout.get_terminal_for_gate(gate_id)
                })
        return heatmap_data

    def generate_conflict_heatmap(self, conflicts: List[Dict]) -> Dict:
        """Generate conflict heatmap data."""
        gate_conflicts = {}
        for conflict in conflicts:
            gate = conflict.get('gate_id', '')
            gate_conflicts[gate] = gate_conflicts.get(gate, 0) + 1

        heatmap_data = []
        for gate_id, count in gate_conflicts.items():
            coord = self.layout.get_gate_coordinates(gate_id)
            if coord:
                heatmap_data.append({
                    'gate_id': gate_id,
                    'x': coord.x,
                    'y': coord.y,
                    'conflicts': count
                })
        return heatmap_data


if __name__ == "__main__":
    # Test the layout
    layout = AirportLayout(num_terminals=3, gates_per_terminal=4)

    print("Gate Layout:")
    for gate_id, gate_info in layout.gates.items():
        print(f"{gate_id}: Terminal {gate_info['terminal']}, "
              f"Size: {gate_info['size']}, "
              f"Coords: ({gate_info['x_coord']}, {gate_info['y_coord']})")

    print(f"\nDistance G1 to G6: {layout.get_distance('G1', 'G6'):.2f}")
    print(f"Walking distance from G1: {layout.get_walking_distance('G1'):.2f}")

    print(f"\nSmall gates: {layout.get_gates_by_size('small')}")
    print(f"Large gates: {layout.get_gates_by_size('large')}")
