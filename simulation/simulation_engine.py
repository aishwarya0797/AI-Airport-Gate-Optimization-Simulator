"""
Simulation Engine Module.

Simulates daily airport operations including:
- Aircraft arrival/departure
- Gate occupancy changes
- Timeline updates
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import threading
from collections import defaultdict

try:
    import simpy
except ImportError:
    simpy = None

from generator.data_generator import Flight, Gate
from simulation.airport_layout import AirportLayout


@dataclass
class GateOccupancy:
    """Tracks gate occupancy over time."""
    gate_id: str
    flight_id: str
    start_time: datetime
    end_time: datetime
    aircraft_size: str


@dataclass
class SimulationEvent:
    """Represents a simulation event."""
    event_type: str  # 'arrival', 'departure', 'gate_occupied', 'gate_freed'
    timestamp: datetime
    flight_id: str
    gate_id: str = ""
    details: str = ""


class SimulationEngine:
    """
    Airport Operations Simulation Engine.
    Simulates daily operations with real-time updates.
    """

    def __init__(self, flights: List[Flight], gates: List[Gate],
                 layout: Optional[AirportLayout] = None):
        """Initialize simulation engine with flights and gates."""
        self.flights = {f.flight_id: f for f in flights}
        self.gates = {g.gate_id: g for g in gates}
        self.layout = layout or AirportLayout()

        # Simulation state
        self.current_time = datetime.now()
        self.events: List[SimulationEvent] = []
        self.gate_occupancy: Dict[str, List[GateOccupancy]] = defaultdict(list)
        self.timeline: List[Dict] = []

        # Statistics
        self.stats = {
            'total_flights': len(flights),
            'flights_arrived': 0,
            'flights_departed': 0,
            'total_conflicts': 0,
            'average_delay': 0,
            'gate_utilization': {}
        }

    def reset_simulation(self):
        """Reset simulation state."""
        self.events = []
        self.gate_occupancy = defaultdict(list)
        self.timeline = []
        self.current_time = datetime.now()
        self.stats = {
            'total_flights': len(self.flights),
            'flights_arrived': 0,
            'flights_departed': 0,
            'total_conflicts': 0,
            'average_delay': 0,
            'gate_utilization': {}
        }

        # Reset gate states
        for gate in self.gates.values():
            gate.is_available = True
            gate.current_flight = None

        # Reset flight states
        for flight in self.flights.values():
            flight.status = 'scheduled'

    def run_simulation(self, start_time: Optional[datetime] = None,
                       duration_hours: int = 24) -> Dict:
        """
        Run the simulation for specified duration.
        Returns simulation results.
        """
        if start_time is None:
            start_time = min(f.arrival_time for f in self.flights.values())

        self.reset_simulation()
        self.current_time = start_time
        end_time = start_time + timedelta(hours=duration_hours)

        # Generate all events
        self._generate_timeline()

        # Process events chronologically
        sorted_events = sorted(self.timeline, key=lambda x: x['timestamp'])
        for event in sorted_events:
            self._process_event(event)

        # Calculate statistics
        self._calculate_statistics()

        return self.get_simulation_results()

    def _generate_timeline(self):
        """Generate event timeline from flights."""
        self.timeline = []

        for flight_id, flight in self.flights.items():
            # Arrival event
            self.timeline.append({
                'event_type': 'arrival',
                'timestamp': flight.arrival_time,
                'flight_id': flight_id,
                'gate_id': flight.assigned_gate if hasattr(flight, 'assigned_gate') else '',
                'details': f"Flight {flight.flight_number} arriving from {flight.origin}"
            })

            # Scheduled departure
            scheduled_departure = flight.arrival_time + timedelta(minutes=flight.turnaround_time)

            # Actual departure (including delay)
            actual_departure = scheduled_departure + timedelta(minutes=flight.delay)

            # Departure event
            self.timeline.append({
                'event_type': 'departure',
                'timestamp': actual_departure,
                'flight_id': flight_id,
                'gate_id': flight.assigned_gate if hasattr(flight, 'assigned_gate') else '',
                'details': f"Flight {flight.flight_number} departing to {flight.destination}"
            })

    def _process_event(self, event: Dict):
        """Process a simulation event."""
        flight_id = event['flight_id']
        gate_id = event['gate_id']

        if flight_id not in self.flights:
            return

        flight = self.flights[flight_id]

        if event['event_type'] == 'arrival':
            flight.status = 'arrived'
            self.stats['flights_arrived'] += 1

            if gate_id:
                occupancy = GateOccupancy(
                    gate_id=gate_id,
                    flight_id=flight_id,
                    start_time=event['timestamp'],
                    end_time=event['timestamp'] + timedelta(minutes=flight.turnaround_time + flight.delay),
                    aircraft_size=flight.aircraft_size
                )
                self.gate_occupancy[gate_id].append(occupancy)

                if gate_id in self.gates:
                    self.gates[gate_id].is_available = False
                    self.gates[gate_id].current_flight = flight_id

            sim_event = SimulationEvent(
                event_type='arrival',
                timestamp=event['timestamp'],
                flight_id=flight_id,
                gate_id=gate_id,
                details=event['details']
            )
            self.events.append(sim_event)

        elif event['event_type'] == 'departure':
            flight.status = 'departed'
            self.stats['flights_departed'] += 1

            if gate_id and gate_id in self.gates:
                self.gates[gate_id].is_available = True
                self.gates[gate_id].current_flight = None

            sim_event = SimulationEvent(
                event_type='departure',
                timestamp=event['timestamp'],
                flight_id=flight_id,
                gate_id=gate_id,
                details=event['details']
            )
            self.events.append(sim_event)

    def _calculate_statistics(self):
        """Calculate simulation statistics."""
        # Average delay
        delays = [f.delay for f in self.flights.values()]
        self.stats['average_delay'] = np.mean(delays) if delays else 0

        # Gate utilization
        total_time = max(f.arrival_time for f in self.flights.values()) - \
                     min(f.arrival_time for f in self.flights.values())
        total_hours = total_time.total_seconds() / 3600 if total_time.total_seconds() > 0 else 24

        for gate_id, occupancies in self.gate_occupancy.items():
            occupied_time = sum(
                (o.end_time - o.start_time).total_seconds() / 3600
                for o in occupancies
            )
            self.stats['gate_utilization'][gate_id] = (occupied_time / total_hours * 100) if total_hours > 0 else 0

    def get_gate_status_at_time(self, timestamp: datetime) -> Dict[str, Dict]:
        """Get gate status at a specific time."""
        status = {}
        for gate_id, occupancies in self.gate_occupancy.items():
            for occ in occupancies:
                if occ.start_time <= timestamp <= occ.end_time:
                    status[gate_id] = {
                        'occupied': True,
                        'flight_id': occ.flight_id,
                        'aircraft_size': occ.aircraft_size
                    }
                    break
            if gate_id not in status:
                status[gate_id] = {'occupied': False, 'flight_id': None, 'aircraft_size': None}
        return status

    def get_flight_status_at_time(self, timestamp: datetime) -> List[Dict]:
        """Get all flights at a specific time."""
        flights_at_time = []
        for flight in self.flights.values():
            departure = flight.arrival_time + timedelta(minutes=flight.turnaround_time + flight.delay)
            if flight.arrival_time <= timestamp <= departure:
                status = 'at_gate' if flight.assigned_gate else 'waiting'
                flights_at_time.append({
                    'flight_id': flight.flight_id,
                    'flight_number': flight.flight_number,
                    'airline': flight.airline,
                    'status': status,
                    'gate': flight.assigned_gate,
                    'arrival_time': flight.arrival_time,
                    'departure_time': departure
                })
        return flights_at_time

    def get_simulation_results(self) -> Dict:
        """Get complete simulation results."""
        return {
            'stats': self.stats,
            'events': [
                {
                    'event_type': e.event_type,
                    'timestamp': e.timestamp,
                    'flight_id': e.flight_id,
                    'gate_id': e.gate_id,
                    'details': e.details
                }
                for e in self.events
            ],
            'gate_occupancy': {
                gate_id: [
                    {
                        'flight_id': o.flight_id,
                        'start_time': o.start_time.isoformat(),
                        'end_time': o.end_time.isoformat(),
                        'aircraft_size': o.aircraft_size
                    }
                    for o in occupancies
                ]
                for gate_id, occupancies in self.gate_occupancy.items()
            },
            'timeline': sorted(self.timeline, key=lambda x: x['timestamp'])
        }

    def get_gantt_data(self) -> List[Dict]:
        """Generate Gantt chart data for gate occupancy."""
        gantt_data = []
        for gate_id, occupancies in self.gate_occupancy.items():
            for occ in occupancies:
                flight = self.flights.get(occ.flight_id)
                if flight:
                    gantt_data.append({
                        'Task': gate_id,
                        'Start': occ.start_time,
                        'Finish': occ.end_time,
                        'Flight': flight.flight_number,
                        'Airline': flight.airline,
                        'Resource': occ.aircraft_size
                    })
        return gantt_data

    def advance_time(self, minutes: int = 5):
        """Advance simulation time by specified minutes."""
        self.current_time += timedelta(minutes=minutes)

        # Process any events that occurred in this time window
        for event in self.events:
            event_obj = event if isinstance(event, SimulationEvent) else SimulationEvent(**event)
            if self.current_time - timedelta(minutes=minutes) <= event_obj.timestamp <= self.current_time:
                # Event already processed
                pass


class RealTimeSimulation:
    """
    Real-time simulation controller with event callbacks.
    """

    def __init__(self, engine: SimulationEngine):
        self.engine = engine
        self.is_running = False
        self.speed_multiplier = 1.0
        self.callbacks = {
            'arrival': [],
            'departure': [],
            'gate_change': []
        }

    def register_callback(self, event_type: str, callback):
        """Register callback for specific event type."""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)

    def start(self):
        """Start real-time simulation."""
        self.is_running = True

    def stop(self):
        """Stop simulation."""
        self.is_running = False

    def set_speed(self, multiplier: float):
        """Set simulation speed multiplier."""
        self.speed_multiplier = multiplier

    def tick(self):
        """Process one simulation tick."""
        if self.is_running:
            self.engine.advance_time(int(5 * self.speed_multiplier))
            # Trigger callbacks based on current state
            for callback in self.callbacks['arrival']:
                callback(self.engine.current_time)


if __name__ == "__main__":
    from generator.data_generator import SyntheticDataGenerator

    # Test the simulation
    gen = SyntheticDataGenerator(seed=42)
    flights = gen.generate_flight_schedule(50)
    gates = gen.generate_gates()

    engine = SimulationEngine(flights, gates)
    results = engine.run_simulation()

    print(f"Simulation completed!")
    print(f"Total flights: {results['stats']['total_flights']}")
    print(f"Flights arrived: {results['stats']['flights_arrived']}")
    print(f"Flights departed: {results['stats']['flights_departed']}")
    print(f"Average delay: {results['stats']['average_delay']:.2f} minutes")

    print("\nGate Utilization:")
    for gate_id, util in results['stats']['gate_utilization'].items():
        print(f"  {gate_id}: {util:.1f}%")
