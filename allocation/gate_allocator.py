"""
Rule-Based Gate Allocation Module.

Implements gate allocation based on airport rules:
- Aircraft size compatibility
- Gate availability
- Schedule overlap avoidance
- Walking distance minimization
- Gate idle time minimization
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

from generator.data_generator import Flight, Gate
from simulation.airport_layout import AirportLayout


@dataclass
class AllocationResult:
    """Result of gate allocation."""
    flight_id: str
    gate_id: str
    success: bool
    reason: str
    walking_distance: float = 0.0
    utilization_score: float = 0.0


class RuleBasedAllocator:
    """
    Rule-Based Gate Allocator.
    Assigns gates based on airport operational rules.
    """

    def __init__(self, gates: List[Gate], layout: Optional[AirportLayout] = None):
        """Initialize allocator with gate information."""
        self.gates = {g.gate_id: g for g in gates}
        self.layout = layout or AirportLayout()
        self.size_compatibility = {
            'small': ['small', 'medium', 'large'],
            'medium': ['medium', 'large'],
            'large': ['large']
        }

    def get_compatible_gates(self, aircraft_size: str,
                              unavailable_gates: set = None) -> List[str]:
        """Get gates compatible with aircraft size."""
        compatible_sizes = self.size_compatibility.get(aircraft_size, [])
        compatible_gates = [
            gid for gid, g in self.gates.items()
            if g.gate_size in compatible_sizes and
               (unavailable_gates is None or gid not in unavailable_gates)
        ]
        return compatible_gates

    def check_schedule_conflict(self, gate_id: str, arrival_time: datetime,
                                departure_time: datetime,
                                existing_assignments: Dict[str, List[Tuple[datetime, datetime]]]) -> bool:
        """Check if assigning a flight creates a schedule conflict."""
        if gate_id not in existing_assignments:
            return False

        for existing_start, existing_end in existing_assignments[gate_id]:
            # Check for overlap
            if arrival_time < existing_end and departure_time > existing_start:
                return True

        return False

    def calculate_walking_distance_score(self, gate_id: str, passenger_count: int) -> float:
        """Calculate walking distance score (lower is better)."""
        distance = self.layout.get_walking_distance(gate_id)
        # Score weighted by passenger count
        return distance * passenger_count / 100

    def prioritize_gates(self, flight: Flight,
                         compatible_gates: List[str],
                         existing_assignments: Dict[str, List[Tuple[datetime, datetime]]]) -> List[Tuple[str, float]]:
        """
        Prioritize gates based on multiple criteria.
        Returns list of (gate_id, score) sorted by priority.
        """
        scored_gates = []
        arrival = flight.arrival_time
        departure = arrival + timedelta(minutes=flight.turnaround_time + flight.delay)

        for gate_id in compatible_gates:
            # Skip if schedule conflict exists
            if self.check_schedule_conflict(gate_id, arrival, departure, existing_assignments):
                continue

            score = 0.0

            # Walking distance (lower is better)
            walking_score = self.calculate_walking_distance_score(gate_id, flight.passenger_count)
            score += walking_score

            # Prefer same-size gate (exact match)
            gate_size = self.layout.get_size_for_gate(gate_id)
            if gate_size == flight.aircraft_size:
                score -= 50  # Bonus for exact size match

            # Prefer gates with recent activity (reduce idle time)
            if gate_id in existing_assignments and existing_assignments[gate_id]:
                last_departure = max(end for _, end in existing_assignments[gate_id])
                idle_time = (arrival - last_departure).total_seconds() / 60
                score -= max(0, 30 - idle_time)  # Bonus for low idle time

            scored_gates.append((gate_id, score))

        # Sort by score (lower is better)
        scored_gates.sort(key=lambda x: x[1])
        return scored_gates

    def allocate_flight(self, flight: Flight,
                        existing_assignments: Dict[str, List[Tuple[datetime, datetime]]],
                        priority: str = 'normal') -> AllocationResult:
        """
        Allocate a gate to a flight.
        Priority can be: 'normal', 'vip', 'emergency'
        """
        compatible_gates = self.get_compatible_gates(flight.aircraft_size)

        if not compatible_gates:
            return AllocationResult(
                flight_id=flight.flight_id,
                gate_id="",
                success=False,
                reason="No compatible gates available for aircraft size"
            )

        # Prioritize based on criteria
        prioritized_gates = self.prioritize_gates(flight, compatible_gates, existing_assignments)

        if not prioritized_gates:
            # All gates have conflicts - try to find a gate with minimal conflict
            min_conflict_gate = self._find_minimal_conflict_gate(
                flight, compatible_gates, existing_assignments
            )
            if min_conflict_gate:
                return AllocationResult(
                    flight_id=flight.flight_id,
                    gate_id=min_conflict_gate,
                    success=True,
                    reason="Assigned with resolvable conflict",
                    walking_distance=self.layout.get_walking_distance(min_conflict_gate)
                )
            else:
                return AllocationResult(
                    flight_id=flight.flight_id,
                    gate_id="",
                    success=False,
                    reason="All compatible gates have conflicts"
                )

        # Assign best gate
        best_gate = prioritized_gates[0][0]

        # Add bonus for priority flights
        if priority == 'vip':
            # Prefer gates closest to terminal entrance
            best_gate = self._select_vip_gate(flight, prioritized_gates)
        elif priority == 'emergency':
            # Assign immediately available gate
            best_gate = self._select_emergency_gate(flight, compatible_gates, existing_assignments)

        return AllocationResult(
            flight_id=flight.flight_id,
            gate_id=best_gate,
            success=True,
            reason="Successfully assigned based on rules",
            walking_distance=self.layout.get_walking_distance(best_gate),
            utilization_score=prioritized_gates[0][1]
        )

    def _find_minimal_conflict_gate(self, flight: Flight,
                                     compatible_gates: List[str],
                                     existing_assignments: Dict[str, List[Tuple[datetime, datetime]]]) -> Optional[str]:
        """Find gate with minimal conflict for overflow situations."""
        min_conflicts = float('inf')
        best_gate = None

        arrival = flight.arrival_time
        departure = arrival + timedelta(minutes=flight.turnaround_time + flight.delay)

        for gate_id in compatible_gates:
            conflicts = 0
            if gate_id in existing_assignments:
                for existing_start, existing_end in existing_assignments[gate_id]:
                    if arrival < existing_end and departure > existing_start:
                        conflicts += 1

            if conflicts < min_conflicts:
                min_conflicts = conflicts
                best_gate = gate_id

        return best_gate if min_conflicts < float('inf') else None

    def _select_vip_gate(self, flight: Flight,
                         prioritized_gates: List[Tuple[str, float]]) -> str:
        """Select optimal gate for VIP flight."""
        # Choose gate closest to terminal entrance
        min_distance = float('inf')
        vip_gate = prioritized_gates[0][0]

        for gate_id, _ in prioritized_gates[:3]:  # Check top 3 candidates
            distance = self.layout.get_walking_distance(gate_id)
            if distance < min_distance:
                min_distance = distance
                vip_gate = gate_id

        return vip_gate

    def _select_emergency_gate(self, flight: Flight,
                                compatible_gates: List[str],
                                existing_assignments: Dict[str, List[Tuple[datetime, datetime]]]) -> str:
        """Select gate for emergency flight."""
        # Emergency flights get immediate priority - any available large gate
        large_gates = [g for g in compatible_gates
                       if self.layout.get_size_for_gate(g) == 'large']

        if large_gates:
            # Find first available large gate
            for gate_id in large_gates:
                if gate_id not in existing_assignments:
                    return gate_id

        # Fall back to first compatible gate
        return compatible_gates[0] if compatible_gates else ""

    def allocate_all_flights(self, flights: List[Flight]) -> Tuple[Dict[str, str], List[AllocationResult]]:
        """
        Allocate gates to all flights.
        Returns mapping of flight_id to gate_id and list of results.
        """
        # Sort flights by arrival time
        sorted_flights = sorted(flights, key=lambda f: f.arrival_time)

        # Track assignments for each gate
        existing_assignments: Dict[str, List[Tuple[datetime, datetime]]] = defaultdict(list)

        # Track flight priorities
        priority_flights = {
            f.flight_id: 'emergency' if 'EMERGENCY' in f.flight_id or f.status == 'priority'
                        else 'vip' if f.status == 'vip' or 'VIP' in f.flight_id
                        else 'normal'
            for f in flights
        }

        # Process emergency and VIP flights first
        emergency_flights = [f for f in sorted_flights if priority_flights[f.flight_id] == 'emergency']
        vip_flights = [f for f in sorted_flights if priority_flights[f.flight_id] == 'vip']
        normal_flights = [f for f in sorted_flights if priority_flights[f.flight_id] == 'normal']

        ordered_flights = emergency_flights + vip_flights + normal_flights

        results = []
        flight_to_gate = {}

        for flight in ordered_flights:
            result = self.allocate_flight(
                flight,
                existing_assignments,
                priority=priority_flights[flight.flight_id]
            )
            results.append(result)

            if result.success:
                flight_to_gate[flight.flight_id] = result.gate_id
                flight.assigned_gate = result.gate_id

                # Update existing assignments
                arrival = flight.arrival_time
                departure = arrival + timedelta(minutes=flight.turnaround_time + flight.delay)
                existing_assignments[result.gate_id].append((arrival, departure))

        return flight_to_gate, results

    def get_allocation_summary(self, results: List[AllocationResult]) -> Dict:
        """Generate summary of allocation results."""
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)

        gate_usage = defaultdict(int)
        for r in results:
            if r.success:
                gate_usage[r.gate_id] += 1

        return {
            'total_flights': len(results),
            'successful_allocations': successful,
            'failed_allocations': failed,
            'success_rate': successful / len(results) * 100 if results else 0,
            'average_walking_distance': np.mean([r.walking_distance for r in results if r.success]) if successful > 0 else 0,
            'gate_usage': dict(gate_usage),
            'most_used_gate': max(gate_usage.items(), key=lambda x: x[1])[0] if gate_usage else None
        }


class NaiveAllocator:
    """
    Simple first-fit allocator for comparison.
    """

    def __init__(self, gates: List[Gate]):
        self.gates = {g.gate_id: g for g in gates}

    def allocate_all_flights(self, flights: List[Flight]) -> Tuple[Dict[str, str], List[AllocationResult]]:
        """
        Simple first-fit allocation (for comparison).
        """
        sorted_flights = sorted(flights, key=lambda f: f.arrival_time)
        existing_assignments: Dict[str, List[Tuple[datetime, datetime]]] = defaultdict(list)
        results = []
        flight_to_gate = {}

        size_order = ['small', 'medium', 'large']

        for flight in sorted_flights:
            assigned = False

            # Try gates in order
            for gate_id, gate in self.gates.items():
                # Check size compatibility
                if flight.aircraft_size == 'large' and gate.gate_size != 'large':
                    continue
                if flight.aircraft_size == 'medium' and gate.gate_size not in ['medium', 'large']:
                    continue

                # Check availability
                arrival = flight.arrival_time
                departure = arrival + timedelta(minutes=flight.turnaround_time + flight.delay)

                conflict = False
                for start, end in existing_assignments[gate_id]:
                    if arrival < end and departure > start:
                        conflict = True
                        break

                if not conflict:
                    flight_to_gate[flight.flight_id] = gate_id
                    flight.assigned_gate = gate_id
                    existing_assignments[gate_id].append((arrival, departure))
                    results.append(AllocationResult(
                        flight_id=flight.flight_id,
                        gate_id=gate_id,
                        success=True,
                        reason="First-fit assignment",
                        walking_distance=0.0
                    ))
                    assigned = True
                    break

            if not assigned:
                results.append(AllocationResult(
                    flight_id=flight.flight_id,
                    gate_id="",
                    success=False,
                    reason="No available gate"
                ))

        return flight_to_gate, results


if __name__ == "__main__":
    from generator.data_generator import SyntheticDataGenerator

    # Test the allocator
    gen = SyntheticDataGenerator(seed=42)
    flights = gen.generate_flight_schedule(50)
    gates = gen.generate_gates()

    allocator = RuleBasedAllocator(gates)
    flight_to_gate, results = allocator.allocate_all_flights(flights)

    summary = allocator.get_allocation_summary(results)
    print(f"Allocation Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    # Compare with naive allocator
    gen2 = SyntheticDataGenerator(seed=42)
    flights2 = gen2.generate_flight_schedule(50)
    naive = NaiveAllocator(gates)
    naive_mapping, naive_results = naive.allocate_all_flights(flights2)

    naive_summary = allocator.get_allocation_summary(naive_results)
    print(f"\nNaive Allocation Summary:")
    for key, value in naive_summary.items():
        print(f"  {key}: {value}")
