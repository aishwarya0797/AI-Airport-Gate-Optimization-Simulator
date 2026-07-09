"""
Conflict Detection Module.

Detects and analyzes gate allocation conflicts:
- Double booking
- Schedule overlaps
- Size incompatibility
- Delay-induced conflicts
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
import numpy as np

from generator.data_generator import Flight, Gate


@dataclass
class Conflict:
    """Represents a detected conflict."""
    conflict_id: str
    conflict_type: str  # 'overlap', 'size_mismatch', 'double_booking', 'delay_conflict'
    severity: str  # 'low', 'medium', 'high', 'critical'
    gate_id: str
    flight_ids: List[str]
    start_time: datetime
    end_time: datetime
    description: str
    resolution_suggestions: List[str] = field(default_factory=list)


class ConflictDetector:
    """
    Detects and analyzes conflicts in gate assignments.
    """

    def __init__(self):
        self.conflicts: List[Conflict] = []
        self.conflict_counter = 0

    def reset(self):
        """Reset conflict detector state."""
        self.conflicts = []
        self.conflict_counter = 0

    def generate_conflict_id(self) -> str:
        """Generate unique conflict ID."""
        self.conflict_counter += 1
        return f"C{self.conflict_counter:04d}"

    def detect_all_conflicts(self, flights: List[Flight],
                             gates: List[Gate]) -> List[Conflict]:
        """
        Detect all types of conflicts in the given assignments.
        """
        self.reset()

        # Build gate to flight mapping
        gate_flights = defaultdict(list)
        for flight in flights:
            if flight.assigned_gate:
                gate_flights[flight.assigned_gate].append(flight)

        # Check each gate for conflicts
        for gate in gates:
            gate_assignments = gate_flights.get(gate.gate_id, [])

            # Check size compatibility
            self._check_size_compatibility(gate, gate_assignments)

            # Check schedule overlaps
            self._check_schedule_overlaps(gate, gate_assignments)

            # Check delay conflicts
            self._check_delay_conflicts(gate, gate_assignments, flights)

        # Check double bookings across all gates
        self._check_double_bookings(flights)

        return self.conflicts

    def _check_size_compatibility(self, gate: Gate, flights: List[Flight]) -> None:
        """Check for aircraft size vs gate size conflicts."""
        size_order = {'small': 1, 'medium': 2, 'large': 3}

        for flight in flights:
            required_size = size_order.get(flight.aircraft_size, 0)
            gate_size = size_order.get(gate.gate_size, 0)

            if required_size > gate_size:
                conflict = Conflict(
                    conflict_id=self.generate_conflict_id(),
                    conflict_type='size_mismatch',
                    severity='critical',
                    gate_id=gate.gate_id,
                    flight_ids=[flight.flight_id],
                    start_time=flight.arrival_time,
                    end_time=flight.arrival_time + timedelta(minutes=flight.turnaround_time),
                    description=f"Aircraft {flight.aircraft_type} ({flight.aircraft_size}) too large for gate {gate.gate_id} ({gate.gate_size})",
                    resolution_suggestions=[
                        f"Reassign flight {flight.flight_number} to a {flight.aircraft_size} gate",
                        f"Upgrade gate {gate.gate_id} infrastructure",
                        "Consider alternative parking stand"
                    ]
                )
                self.conflicts.append(conflict)

    def _check_schedule_overlaps(self, gate: Gate, flights: List[Flight]) -> None:
        """Check for time overlaps in gate assignments."""
        if len(flights) < 2:
            return

        # Sort by arrival time
        sorted_flights = sorted(flights, key=lambda f: f.arrival_time)

        for i in range(len(sorted_flights) - 1):
            flight1 = sorted_flights[i]
            flight2 = sorted_flights[i + 1]

            end_time1 = flight1.arrival_time + timedelta(minutes=flight1.turnaround_time + flight1.delay)

            # Check if flights overlap
            if end_time1 > flight2.arrival_time:
                overlap_duration = (end_time1 - flight2.arrival_time).total_seconds() / 60

                severity = 'critical' if overlap_duration > 30 else 'high' if overlap_duration > 15 else 'medium'

                conflict = Conflict(
                    conflict_id=self.generate_conflict_id(),
                    conflict_type='overlap',
                    severity=severity,
                    gate_id=gate.gate_id,
                    flight_ids=[flight1.flight_id, flight2.flight_id],
                    start_time=flight2.arrival_time,
                    end_time=end_time1,
                    description=f"Scheduled overlap at {gate.gate_id}: {flight1.flight_number} departs at {end_time1.strftime('%H:%M')} but {flight2.flight_number} arrives at {flight2.arrival_time.strftime('%H:%M')} ({overlap_duration:.0f} min overlap)",
                    resolution_suggestions=[
                        f"Delay {flight2.flight_number} arrival",
                        f"Reassign {flight2.flight_number} to alternate gate",
                        "Adjust turnaround time for earlier flight",
                        "Consider remote parking for one flight"
                    ]
                )
                self.conflicts.append(conflict)

    def _check_delay_conflicts(self, gate: Gate, gate_flights: List[Flight],
                                all_flights: List[Flight]) -> None:
        """Check for conflicts caused by flight delays."""
        if len(gate_flights) < 2:
            return

        sorted_flights = sorted(gate_flights, key=lambda f: f.arrival_time)

        for i in range(len(sorted_flights) - 1):
            flight1 = sorted_flights[i]
            flight2 = sorted_flights[i + 1]

            # Calculate actual departure time including delay
            actual_departure1 = flight1.arrival_time + timedelta(
                minutes=flight1.turnaround_time + flight1.delay
            )

            # If delay creates a conflict that wouldn't exist otherwise
            planned_departure1 = flight1.arrival_time + timedelta(minutes=flight1.turnaround_time)

            if flight1.delay > 0 and actual_departure1 > flight2.arrival_time:
                conflict = Conflict(
                    conflict_id=self.generate_conflict_id(),
                    conflict_type='delay_conflict',
                    severity='high',
                    gate_id=gate.gate_id,
                    flight_ids=[flight1.flight_id, flight2.flight_id],
                    start_time=flight2.arrival_time,
                    end_time=actual_departure1,
                    description=f"Delay-induced conflict: {flight1.flight_number} delayed {flight1.delay} min, now overlaps with {flight2.flight_number} at {gate.gate_id}",
                    resolution_suggestions=[
                        f"Prioritize {flight1.flight_number} turnaround",
                        f"Prepare alternate gate for {flight2.flight_number}",
                        "Notify ground crew for expedited turnaround",
                        "Consider holding {flight2.flight_number} at remote stand"
                    ]
                )
                self.conflicts.append(conflict)

    def _check_double_bookings(self, flights: List[Flight]) -> None:
        """Check if any flight is assigned to multiple gates."""
        flight_gates = defaultdict(list)
        for flight in flights:
            if flight.assigned_gate:
                flight_gates[flight.flight_id].append(flight.assigned_gate)

        for flight_id, gate_list in flight_gates.items():
            if len(gate_list) > 1:
                # Find the flight
                flight = next((f for f in flights if f.flight_id == flight_id), None)
                if flight:
                    conflict = Conflict(
                        conflict_id=self.generate_conflict_id(),
                        conflict_type='double_booking',
                        severity='critical',
                        gate_id=", ".join(gate_list),
                        flight_ids=[flight_id],
                        start_time=flight.arrival_time,
                        end_time=flight.arrival_time + timedelta(minutes=flight.turnaround_time),
                        description=f"Flight {flight.flight_number} assigned to multiple gates: {', '.join(gate_list)}",
                        resolution_suggestions=[
                            "Remove duplicate gate assignment",
                            "Verify correct gate from schedule"
                        ]
                    )
                    self.conflicts.append(conflict)

    def get_conflicts_by_severity(self, severity: str) -> List[Conflict]:
        """Get conflicts filtered by severity."""
        return [c for c in self.conflicts if c.severity == severity]

    def get_conflicts_by_type(self, conflict_type: str) -> List[Conflict]:
        """Get conflicts filtered by type."""
        return [c for c in self.conflicts if c.conflict_type == conflict_type]

    def get_conflicts_by_gate(self, gate_id: str) -> List[Conflict]:
        """Get conflicts for a specific gate."""
        return [c for c in self.conflicts if c.gate_id == gate_id]

    def generate_conflict_summary(self) -> Dict:
        """Generate summary of detected conflicts."""
        severity_counts = defaultdict(int)
        type_counts = defaultdict(int)

        for conflict in self.conflicts:
            severity_counts[conflict.severity] += 1
            type_counts[conflict.conflict_type] += 1

        return {
            'total_conflicts': len(self.conflicts),
            'by_severity': dict(severity_counts),
            'by_type': dict(type_counts),
            'critical_count': severity_counts.get('critical', 0),
            'high_count': severity_counts.get('high', 0),
            'medium_count': severity_counts.get('medium', 0),
            'low_count': severity_counts.get('low', 0)
        }

    def conflicts_to_dataframe(self) -> pd.DataFrame:
        """Convert conflicts to pandas DataFrame."""
        data = []
        for c in self.conflicts:
            data.append({
                'conflict_id': c.conflict_id,
                'type': c.conflict_type,
                'severity': c.severity,
                'gate_id': c.gate_id,
                'flights': ", ".join(c.flight_ids),
                'start_time': c.start_time,
                'end_time': c.end_time,
                'description': c.description,
                'resolutions': " | ".join(c.resolution_suggestions)
            })
        return pd.DataFrame(data)

    def generate_conflict_timeline(self) -> List[Dict]:
        """Generate timeline view of conflicts."""
        timeline = []
        for conflict in sorted(self.conflicts, key=lambda c: c.start_time):
            timeline.append({
                'time': conflict.start_time.strftime('%H:%M'),
                'conflict_id': conflict.conflict_id,
                'type': conflict.conflict_type,
                'severity': conflict.severity,
                'gate': conflict.gate_id,
                'description': conflict.description
            })
        return timeline

    def predict_potential_conflicts(self, flights: List[Flight],
                                     gate_assignments: Dict[str, str],
                                     delay_probability: float = 0.3) -> List[Conflict]:
        """
        Predict potential conflicts based on delay probability.
        """
        potential_conflicts = []

        # Group flights by gate
        gate_flights = defaultdict(list)
        for flight in flights:
            if flight.flight_id in gate_assignments:
                gate_flights[gate_assignments[flight.flight_id]].append(flight)

        for gate_id, flights_at_gate in gate_flights.items():
            sorted_flights = sorted(flights_at_gate, key=lambda f: f.arrival_time)

            for i in range(len(sorted_flights) - 1):
                flight1 = sorted_flights[i]
                flight2 = sorted_flights[i + 1]

                # Calculate buffer time
                planned_departure = flight1.arrival_time + timedelta(minutes=flight1.turnaround_time)
                buffer_minutes = (flight2.arrival_time - planned_departure).total_seconds() / 60

                # If buffer is small, there's potential for conflict
                if buffer_minutes < 30 and buffer_minutes > 0:
                    # Calculate conflict probability based on buffer and delay history
                    conflict_probability = delay_probability * (30 - buffer_minutes) / 30

                    if conflict_probability > 0.2:  # Only report if probability > 20%
                        potential_conflicts.append(Conflict(
                            conflict_id=f"PC{len(potential_conflicts)+1:04d}",
                            conflict_type='potential_delay',
                            severity='low' if conflict_probability < 0.5 else 'medium',
                            gate_id=gate_id,
                            flight_ids=[flight1.flight_id, flight2.flight_id],
                            start_time=planned_departure,
                            end_time=flight2.arrival_time,
                            description=f"Potential conflict: {flight1.flight_number} has only {buffer_minutes:.0f} min buffer before {flight2.flight_number} arrives ({conflict_probability*100:.0f}% probability)"
                        ))

        return potential_conflicts

    def resolve_conflict(self, conflict: Conflict, flights: List[Flight],
                         gates: List[Gate],
                         resolution_strategy: str = 'reassign') -> Dict:
        """
        Attempt to resolve a conflict.
        Returns resolution details.
        """
        import copy

        resolution = {
            'conflict_id': conflict.conflict_id,
            'strategy': resolution_strategy,
            'success': False,
            'new_assignment': None,
            'message': ''
        }

        if resolution_strategy == 'reassign':
            # Find an alternative gate for one of the flights
            conflicting_flights = [f for f in flights if f.flight_id in conflict.flight_ids]

            if conflicting_flights:
                # Choose the second flight to reassign
                flight_to_move = max(conflicting_flights, key=lambda f: f.arrival_time)

                # Find alternative gate
                for gate in gates:
                    if gate.gate_id != conflict.gate_id:
                        # Check size compatibility
                        size_ok = (
                            (flight_to_move.aircraft_size == 'small') or
                            (flight_to_move.aircraft_size == 'medium' and gate.gate_size in ['medium', 'large']) or
                            (flight_to_move.aircraft_size == 'large' and gate.gate_size == 'large')
                        )

                        if size_ok:
                            resolution['success'] = True
                            resolution['new_assignment'] = {
                                'flight_id': flight_to_move.flight_id,
                                'old_gate': conflict.gate_id,
                                'new_gate': gate.gate_id
                            }
                            resolution['message'] = f"Reassign {flight_to_move.flight_number} from {conflict.gate_id} to {gate.gate_id}"
                            return resolution

            resolution['message'] = "Could not find alternative gate"

        elif resolution_strategy == 'delay':
            # Suggest delaying the second flight
            conflicting_flights = [f for f in flights if f.flight_id in conflict.flight_ids]

            if len(conflicting_flights) >= 2:
                first_flight = min(conflicting_flights, key=lambda f: f.arrival_time)
                second_flight = max(conflicting_flights, key=lambda f: f.arrival_time)

                first_departure = first_flight.arrival_time + timedelta(minutes=first_flight.turnaround_time + first_flight.delay)
                required_delay = (first_departure - second_flight.arrival_time).total_seconds() / 60 + 15  # 15 min buffer

                resolution['success'] = True
                resolution['new_assignment'] = {
                    'flight_id': second_flight.flight_id,
                    'additional_delay': required_delay
                }
                resolution['message'] = f"Delay {second_flight.flight_number} by {required_delay:.0f} minutes"

        return resolution


if __name__ == "__main__":
    from generator.data_generator import SyntheticDataGenerator

    # Test conflict detector
    gen = SyntheticDataGenerator(seed=42)
    flights = gen.generate_flight_schedule(50)
    gates = gen.generate_gates()

    # Simple assignment for testing
    for i, flight in enumerate(flights):
        flight.assigned_gate = f"G{(i % 12) + 1}"

    detector = ConflictDetector()
    conflicts = detector.detect_all_conflicts(flights, gates)

    print(f"Detected {len(conflicts)} conflicts")
    summary = detector.generate_conflict_summary()
    print("\nConflict Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    print("\nDetailed Conflicts:")
    for conflict in conflicts[:5]:
        print(f"\n{conflict.conflict_id} [{conflict.severity}] {conflict.conflict_type}")
        print(f"  Gate: {conflict.gate_id}")
        print(f"  Flights: {', '.join(conflict.flight_ids)}")
        print(f"  Description: {conflict.description}")
        print(f"  Resolutions: {', '.join(conflict.resolution_suggestions[:2])}")
