"""
Optimization Engine Module.

Uses OR-Tools to optimize gate assignments based on:
- Passenger walking distance
- Gate utilization
- Idle time minimization
- Conflict avoidance
- Turnaround efficiency
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from ortools.linear_solver import pywraplp

from generator.data_generator import Flight, Gate
from simulation.airport_layout import AirportLayout


@dataclass
class OptimizationResult:
    """Result of optimization."""
    flight_id: str
    gate_id: str
    objective_score: float
    walking_distance: float
    utilization_contribution: float


class GateOptimizationEngine:
    """
    Optimization engine for gate allocation using OR-Tools.
    """

    def __init__(self, flights: List[Flight], gates: List[Gate],
                 layout: Optional[AirportLayout] = None):
        """Initialize optimization engine."""
        self.flights = {f.flight_id: f for f in flights}
        self.gates = {g.gate_id: g for g in gates}
        self.layout = layout or AirportLayout()

        # Pre-compute flight list and gate list for ordering
        self.flight_list = list(self.flights.values())
        self.gate_list = list(self.gates.values())
        self.flight_ids = [f.flight_id for f in self.flight_list]
        self.gate_ids = [g.gate_id for g in self.gate_list]

        # Size compatibility matrix
        self.size_compat = self._build_size_compatibility()

    def _build_size_compatibility(self) -> Dict[str, List[str]]:
        """Build size compatibility mapping."""
        return {
            'small': ['small', 'medium', 'large'],
            'medium': ['medium', 'large'],
            'large': ['large']
        }

    def _is_compatible(self, flight_size: str, gate_size: str) -> bool:
        """Check if flight and gate sizes are compatible."""
        return gate_size in self.size_compat.get(flight_size, [])

    def _calculate_distance_matrix(self) -> np.ndarray:
        """Calculate walking distance for all flight-gate combinations."""
        n_flights = len(self.flight_ids)
        n_gates = len(self.gate_ids)

        distance_matrix = np.zeros((n_flights, n_gates))

        for i, flight_id in enumerate(self.flight_ids):
            flight = self.flights[flight_id]
            for j, gate_id in enumerate(self.gate_ids):
                gate = self.gates[gate_id]
                if self._is_compatible(flight.aircraft_size, gate.gate_size):
                    distance = self.layout.get_walking_distance(gate_id)
                    # Weight by passenger count
                    distance_matrix[i, j] = distance * flight.passenger_count
                else:
                    distance_matrix[i, j] = float('inf')

        return distance_matrix

    def _check_time_overlap(self, flight1: Flight, flight2: Flight) -> bool:
        """Check if two flights overlap in time."""
        end1 = flight1.arrival_time + timedelta(minutes=flight1.turnaround_time + flight1.delay)
        end2 = flight2.arrival_time + timedelta(minutes=flight2.turnaround_time + flight2.delay)

        return not (end1 <= flight2.arrival_time or flight1.arrival_time >= end2)

    def optimize_allocations(self,
                             weight_distance: float = 0.4,
                             weight_utilization: float = 0.3,
                             weight_conflicts: float = 0.3) -> Tuple[Dict[str, str], Dict]:
        """
        Optimize gate allocations using Linear Programming.
        Returns optimal assignments and optimization statistics.
        """
        # Create solver
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            # Fallback to GLPK if SCIP not available
            solver = pywraplp.Solver.CreateSolver('GLPK')
        if not solver:
            return self._fallback_allocation(), {'status': 'Solver not available'}

        # Hard cap on solve time. Without this, SCIP can run indefinitely on
        # larger instances (300-500 flights) and appear to freeze the app.
        # If the time limit is hit before proving optimality, OR-Tools still
        # returns the best feasible solution found so far (status FEASIBLE).
        solver.SetTimeLimit(30000)  # milliseconds

        n_flights = len(self.flight_ids)
        n_gates = len(self.gate_ids)

        # Decision variables: x[i,j] = 1 if flight i assigned to gate j
        x = {}
        for i, flight_id in enumerate(self.flight_ids):
            for j, gate_id in enumerate(self.gate_ids):
                flight = self.flights[flight_id]
                gate = self.gates[gate_id]

                # Only create variables for compatible assignments
                if self._is_compatible(flight.aircraft_size, gate.gate_size):
                    x[i, j] = solver.IntVar(0, 1, f'x_{i}_{j}')

        # Objective: primarily maximize the number of flights seated at a
        # gate, secondarily minimize total walking distance among those.
        #
        # This is implemented as a single minimization objective by giving
        # every real assignment a large negative "reward" (PENALTY) relative
        # to its walking-distance cost. Because leaving a flight unassigned
        # is always a feasible fallback (Constraint 1 below is `<= 1`, not
        # `== 1`), the model is *always* solvable — the solver will only
        # leave a flight ungated when there is truly no non-conflicting,
        # size-compatible gate left for it (a genuine capacity shortfall),
        # rather than the whole optimization failing outright.
        distance_matrix = self._calculate_distance_matrix()
        finite_distances = distance_matrix[np.isfinite(distance_matrix)]
        max_distance = float(finite_distances.max()) if finite_distances.size else 1.0
        PENALTY = max(max_distance * 10.0, 1.0)

        objective = solver.Objective()

        for i, flight_id in enumerate(self.flight_ids):
            for j, gate_id in enumerate(self.gate_ids):
                if (i, j) in x:
                    dist = distance_matrix[i, j]
                    if dist < float('inf'):
                        # Net coefficient is negative: assigning this flight
                        # is always preferable to leaving it unassigned,
                        # while still favoring the shortest walk available.
                        objective.SetCoefficient(x[i, j], dist - PENALTY)

        objective.SetMinimization()

        # Constraint 1: Each flight assigned to AT MOST one gate (soft goal,
        # not a hard requirement — see objective above for why).
        for i, flight_id in enumerate(self.flight_ids):
            constraint = solver.Constraint(0, 1)
            for j, gate_id in enumerate(self.gate_ids):
                if (i, j) in x:
                    constraint.SetCoefficient(x[i, j], 1)

        # Constraint 2: No overlapping flights at same gate
        for j, gate_id in enumerate(self.gate_ids):
            gate = self.gates[gate_id]

            # Find all flights compatible with this gate
            compatible_flights = []
            for i, flight_id in enumerate(self.flight_ids):
                flight = self.flights[flight_id]
                if self._is_compatible(flight.aircraft_size, gate.gate_size):
                    compatible_flights.append((i, flight_id))

            # For each pair of overlapping flights, only one can be assigned
            for idx1 in range(len(compatible_flights)):
                i1, f1_id = compatible_flights[idx1]
                for idx2 in range(idx1 + 1, len(compatible_flights)):
                    i2, f2_id = compatible_flights[idx2]
                    flight1 = self.flights[f1_id]
                    flight2 = self.flights[f2_id]

                    if self._check_time_overlap(flight1, flight2):
                        # Constraint: sum <= 1 (at most one can be assigned)
                        constraint = solver.Constraint(0, 1)
                        if (i1, j) in x:
                            constraint.SetCoefficient(x[i1, j], 1)
                        if (i2, j) in x:
                            constraint.SetCoefficient(x[i2, j], 1)

        # Solve
        status = solver.Solve()

        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            # Extract solution
            assignments = {}
            for i, flight_id in enumerate(self.flight_ids):
                for j, gate_id in enumerate(self.gate_ids):
                    if (i, j) in x and x[i, j].solution_value() > 0.5:
                        assignments[flight_id] = gate_id
                        flight = self.flights[flight_id]
                        flight.assigned_gate = gate_id

            # Flights the solver could not seat anywhere (true capacity
            # shortfall, or no size-compatible gate exists at all). Clear
            # any stale assignment from an earlier allocation pass so the
            # rest of the dashboard reflects this run's plan accurately.
            unassigned_flight_ids = [fid for fid in self.flight_ids if fid not in assignments]
            for fid in unassigned_flight_ids:
                self.flights[fid].assigned_gate = ""

            # Calculate statistics
            total_distance = sum(
                distance_matrix[i, j]
                for i, flight_id in enumerate(self.flight_ids)
                for j, gate_id in enumerate(self.gate_ids)
                if (i, j) in x and x[i, j].solution_value() > 0.5 and distance_matrix[i, j] < float('inf')
            )

            optimization_stats = {
                'status': 'optimal' if status == pywraplp.Solver.OPTIMAL else 'feasible',
                'total_walking_distance': total_distance,
                'objective_value': objective.Value(),
                'solve_time_ms': solver.wall_time(),
                'num_variables': solver.NumVariables(),
                'num_constraints': solver.NumConstraints(),
                'num_flights': n_flights,
                'num_seated': len(assignments),
                'num_unassigned': len(unassigned_flight_ids),
                'unassigned_flight_ids': unassigned_flight_ids,
            }

            return assignments, optimization_stats
        else:
            # Fallback to a simple greedy allocation. Report solver diagnostics
            # (variables/constraints/solve time were still real work the
            # solver did, even though it didn't find a feasible solution).
            fallback_assignments = self._fallback_allocation()

            total_distance = sum(
                distance_matrix[i, j]
                for i, flight_id in enumerate(self.flight_ids)
                for j, gate_id in enumerate(self.gate_ids)
                if fallback_assignments.get(flight_id) == gate_id and distance_matrix[i, j] < float('inf')
            )

            optimization_stats = {
                'status': 'Failed to find solution',
                'total_walking_distance': total_distance,
                'objective_value': None,
                'solve_time_ms': solver.wall_time(),
                'num_variables': solver.NumVariables(),
                'num_constraints': solver.NumConstraints(),
            }
            return fallback_assignments, optimization_stats

    def _fallback_allocation(self) -> Dict[str, str]:
        """Simple fallback allocation if optimization fails."""
        assignments = {}
        gate_occupancy = {g_id: [] for g_id in self.gate_ids}

        for flight in sorted(self.flight_list, key=lambda f: f.arrival_time):
            for gate_id in self.gate_ids:
                gate = self.gates[gate_id]
                if self._is_compatible(flight.aircraft_size, gate.gate_size):
                    # Check for conflicts
                    end_time = flight.arrival_time + timedelta(minutes=flight.turnaround_time + flight.delay)
                    has_conflict = False

                    for (start, end) in gate_occupancy[gate_id]:
                        if not (end_time <= start or flight.arrival_time >= end):
                            has_conflict = True
                            break

                    if not has_conflict:
                        assignments[flight.flight_id] = gate_id
                        gate_occupancy[gate_id].append(
                            (flight.arrival_time, end_time)
                        )
                        # Keep the Flight object's assigned_gate in sync with
                        # the assignments dict returned to the caller.
                        flight.assigned_gate = gate_id
                        break

        return assignments

    def compare_allocations(self, naive_assignments: Dict[str, str],
                            optimized_assignments: Dict[str, str]) -> Dict:
        """Compare naive and optimized allocations."""
        distance_matrix = self._calculate_distance_matrix()

        # Calculate metrics for naive assignment
        naive_distance = 0
        for flight_id, gate_id in naive_assignments.items():
            i = self.flight_ids.index(flight_id)
            j = self.gate_ids.index(gate_id)
            naive_distance += distance_matrix[i, j]

        # Calculate metrics for optimized assignment
        opt_distance = 0
        for flight_id, gate_id in optimized_assignments.items():
            i = self.flight_ids.index(flight_id)
            j = self.gate_ids.index(gate_id)
            opt_distance += distance_matrix[i, j]

        # Count gate usage
        naive_gate_usage = {}
        for gate_id in naive_assignments.values():
            naive_gate_usage[gate_id] = naive_gate_usage.get(gate_id, 0) + 1

        opt_gate_usage = {}
        for gate_id in optimized_assignments.values():
            opt_gate_usage[gate_id] = opt_gate_usage.get(gate_id, 0) + 1

        # Calculate improvement
        distance_improvement = ((naive_distance - opt_distance) / naive_distance * 100) if naive_distance > 0 else 0

        return {
            'naive_total_distance': naive_distance,
            'optimized_total_distance': opt_distance,
            'distance_improvement_percent': distance_improvement,
            'naive_gate_usage': naive_gate_usage,
            'optimized_gate_usage': opt_gate_usage,
            'naive_unique_gates': len(naive_gate_usage),
            'optimized_unique_gates': len(opt_gate_usage)
        }

    def calculate_metrics(self, assignments: Dict[str, str]) -> Dict:
        """Calculate metrics for current assignments."""
        from allocation.conflict_detector import ConflictDetector

        # Update flight assignments
        for flight in self.flight_list:
            if flight.flight_id in assignments:
                flight.assigned_gate = assignments[flight.flight_id]

        # Calculate metrics
        total_distance = 0
        gate_occupancy_minutes = {g_id: 0 for g_id in self.gate_ids}

        for flight_id, gate_id in assignments.items():
            flight = self.flights[flight_id]
            gate = self.gates[gate_id]

            # Walking distance
            distance = self.layout.get_walking_distance(gate_id)
            total_distance += distance * flight.passenger_count

            # Gate occupancy
            occupancy = flight.turnaround_time + flight.delay
            gate_occupancy_minutes[gate_id] += occupancy

        # Calculate utilization
        simulation_hours = 24
        total_minutes = simulation_hours * 60

        gate_utilization = {
            g_id: (occ / total_minutes * 100) if total_minutes > 0 else 0
            for g_id, occ in gate_occupancy_minutes.items()
        }

        # Average utilization
        avg_utilization = np.mean(list(gate_utilization.values()))

        # Detect conflicts
        detector = ConflictDetector()
        conflicts = detector.detect_all_conflicts(
            self.flight_list,
            self.gate_list
        )

        return {
            'total_walking_distance': total_distance,
            'average_walking_distance': total_distance / len(assignments) if assignments else 0,
            'gate_utilization': gate_utilization,
            'average_gate_utilization': avg_utilization,
            'total_conflicts': len(conflicts),
            'conflict_summary': detector.generate_conflict_summary()
        }


class MultiObjectiveOptimizer:
    """
    Multi-objective optimization considering multiple goals.
    """

    def __init__(self, flights: List[Flight], gates: List[Gate]):
        self.flights = flights
        self.gates = gates
        self.engine = GateOptimizationEngine(flights, gates)

    def optimize_pareto(self,
                        weight_distance: float = 0.4,
                        weight_utilization: float = 0.3,
                        weight_conflicts: float = 0.3) -> Tuple[Dict[str, str], Dict]:
        """
        Optimize with weighted objectives.
        """
        return self.engine.optimize_allocations(
            weight_distance=weight_distance,
            weight_utilization=weight_utilization,
            weight_conflicts=weight_conflicts
        )

    def optimize_for_scenario(self, scenario: str) -> Tuple[Dict[str, str], Dict]:
        """Optimize based on specific operational scenario."""
        if scenario == 'peak_hour':
            # Minimize conflicts, maximize throughput
            return self.optimize_pareto(
                weight_distance=0.2,
                weight_utilization=0.5,
                weight_conflicts=0.3
            )
        elif scenario == 'passenger_comfort':
            # Minimize walking distance
            return self.optimize_pareto(
                weight_distance=0.6,
                weight_utilization=0.2,
                weight_conflicts=0.2
            )
        elif scenario == 'low_conflict':
            # Prioritize conflict avoidance
            return self.optimize_pareto(
                weight_distance=0.2,
                weight_utilization=0.3,
                weight_conflicts=0.5
            )
        else:
            return self.optimize_pareto()


if __name__ == "__main__":
    from generator.data_generator import SyntheticDataGenerator

    # Test optimization
    gen = SyntheticDataGenerator(seed=42)
    flights = gen.generate_flight_schedule(50)
    gates = gen.generate_gates()

    print("Running optimization...")
    engine = GateOptimizationEngine(flights, gates)
    assignments, stats = engine.optimize_allocations()

    print(f"\nOptimization Status: {stats.get('status', 'unknown')}")
    print(f"Total Walking Distance: {stats.get('total_walking_distance', 0):.2f}")
    print(f"Assigned {len(assignments)} flights")

    # Calculate metrics
    metrics = engine.calculate_metrics(assignments)
    print(f"\nMetrics:")
    print(f"  Average Walking Distance: {metrics['average_walking_distance']:.2f}")
    print(f"  Average Gate Utilization: {metrics['average_gate_utilization']:.1f}%")
    print(f"  Total Conflicts: {metrics['total_conflicts']}")
