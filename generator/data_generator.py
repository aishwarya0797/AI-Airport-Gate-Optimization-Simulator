"""
Synthetic Data Generator Module.

Generates realistic synthetic data for:
- Flights
- Aircraft
- Gates
- Passengers
- Weather
- Delays
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import random
import uuid

from utils.config import config


@dataclass
class Flight:
    """Flight data class."""
    flight_id: str
    airline: str
    flight_number: str
    aircraft_type: str
    aircraft_size: str
    arrival_time: datetime
    departure_time: datetime
    passenger_count: int
    turnaround_time: int
    delay: int = 0
    origin: str = ""
    destination: str = ""
    assigned_gate: str = ""
    status: str = "scheduled"


@dataclass
class Gate:
    """Gate data class."""
    gate_id: str
    gate_size: str
    terminal: int
    x_coord: int
    y_coord: int
    is_available: bool = True
    current_flight: Optional[str] = None


@dataclass
class Aircraft:
    """Aircraft data class."""
    aircraft_type: str
    capacity: int
    size: str


class SyntheticDataGenerator:
    """
    Generator for synthetic airport data.
    Creates realistic flight schedules, gates, and operational data.
    """

    def __init__(self, seed: Optional[int] = None):
        """Initialize generator with optional random seed."""
        if seed:
            np.random.seed(seed)
            random.seed(seed)

        self.airlines = config.airline.airlines
        self.aircraft_config = config.aircraft.types
        self.weather_conditions = config.weather.conditions

        # Airport locations for origins/destinations
        self.airports = [
            'BOM', 'MAA', 'BLR', 'CCU', 'HYD', 'AMD',
            'DXB', 'SIN', 'LHR', 'JFK', 'FRA', 'CDG',
            'HKG', 'NRT', 'SYD', 'BKK', 'KUL', 'DOH'
        ]

    def generate_flight_id(self) -> str:
        """Generate unique flight ID."""
        return f"FL{uuid.uuid4().hex[:8].upper()}"

    def generate_aircraft(self) -> Tuple[str, str, int]:
        """
        Generate random aircraft type, size, and capacity.

        Sizes are weighted by realistic gate capacity (gate count divided by
        average turnaround time per size) rather than picked uniformly.
        A flat 1-in-3 chance per size would generate ~33% large aircraft
        against only 2 of 12 gates (16.7%) able to host them, guaranteeing
        large flights get bumped regardless of how many flights are
        generated. Weighting by capacity keeps generated demand roughly in
        proportion to what the airport's 4 small / 6 medium / 2 large gate
        mix can actually turn around in a day.
        """
        # (gate_count, avg_turnaround_minutes) per size, matching the gate
        # mix in generate_gates() and the turnaround ranges used below.
        capacity_profile = {
            'small': (4, 45),
            'medium': (6, 67.5),
            'large': (2, 120),
        }
        sizes = list(self.aircraft_config.keys())
        weights = [
            capacity_profile.get(s, (1, 60))[0] / capacity_profile.get(s, (1, 60))[1]
            for s in sizes
        ]
        size = random.choices(sizes, weights=weights, k=1)[0]
        ac_config = self.aircraft_config[size]
        aircraft_type = random.choice(ac_config['models'])
        capacity = random.randint(*ac_config['capacity_range'])
        return aircraft_type, size, capacity

    def generate_flight_schedule(
        self,
        num_flights: int = 100,
        start_date: Optional[datetime] = None,
        peak_hours: bool = False
    ) -> List[Flight]:
        """Generate synthetic flight schedule."""
        if start_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        flights = []
        used_flight_numbers = set()

        for _ in range(num_flights):
            airline = random.choice(self.airlines)

            # Generate unique flight number
            flight_number = f"{airline[:2].upper()}{random.randint(100, 9999)}"
            while flight_number in used_flight_numbers:
                flight_number = f"{airline[:2].upper()}{random.randint(100, 9999)}"
            used_flight_numbers.add(flight_number)

            # Generate aircraft
            aircraft_type, aircraft_size, capacity = self.generate_aircraft()

            # Generate arrival time (weighted towards peak hours if enabled)
            if peak_hours:
                # 60% flights during peak hours (6-9 AM, 5-9 PM)
                if random.random() < 0.6:
                    peak_window = random.choice([(6, 9), (17, 21)])
                    hour = random.randint(*peak_window)
                else:
                    hour = random.randint(0, 23)
            else:
                hour = random.randint(0, 23)

            minute = random.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
            arrival_time = start_date + timedelta(hours=hour, minutes=minute)

            # Generate turnaround time based on aircraft size
            if aircraft_size == 'small':
                turnaround = random.randint(30, 60)
            elif aircraft_size == 'medium':
                turnaround = random.randint(45, 90)
            else:
                turnaround = random.randint(60, 180)

            departure_time = arrival_time + timedelta(minutes=turnaround)

            # Generate passenger count (70-95% of capacity)
            passenger_count = int(capacity * random.uniform(0.70, 0.95))

            # Generate potential delay (in minutes)
            delay = random.choices([0, 0, 0, 5, 10, 15, 30, 45, 60],
                                   weights=[40, 25, 15, 8, 5, 4, 2, 1, 1])[0]

            # Origin and destination
            origin = random.choice(self.airports)
            destination = random.choice([a for a in self.airports if a != origin])

            flight = Flight(
                flight_id=self.generate_flight_id(),
                airline=airline,
                flight_number=flight_number,
                aircraft_type=aircraft_type,
                aircraft_size=aircraft_size,
                arrival_time=arrival_time,
                departure_time=departure_time,
                passenger_count=passenger_count,
                turnaround_time=turnaround,
                delay=delay,
                origin=origin,
                destination=destination
            )
            flights.append(flight)

        # Sort flights by arrival time
        flights.sort(key=lambda x: x.arrival_time)
        return flights

    def generate_gates(self, num_terminals: int = 3, gates_per_terminal: int = 4) -> List[Gate]:
        """Generate synthetic gate information."""
        gates = []
        gate_counter = 1

        # Define gate sizes distribution
        gate_sizes_distribution = ['small'] * 4 + ['medium'] * 6 + ['large'] * 2

        for terminal in range(1, num_terminals + 1):
            for i in range(gates_per_terminal):
                gate_id = f"G{gate_counter}"
                gate_size = gate_sizes_distribution[gate_counter - 1] if gate_counter <= len(gate_sizes_distribution) else 'medium'

                # Calculate coordinates for layout
                x_coord = 100 + (i * 120)
                y_coord = 100 + (terminal - 1) * 200

                gate = Gate(
                    gate_id=gate_id,
                    gate_size=gate_size,
                    terminal=terminal,
                    x_coord=x_coord,
                    y_coord=y_coord,
                    is_available=True
                )
                gates.append(gate)
                gate_counter += 1

        return gates

    def generate_weather(self, scenario: str = 'Clear') -> Dict:
        """Generate weather conditions."""
        if scenario == 'Rain':
            conditions = ['Rain', 'Rain', 'Rain', 'Thunderstorm']
        elif scenario == 'Fog':
            conditions = ['Fog', 'Fog', 'Fog', 'Clear']
        else:
            conditions = ['Clear', 'Clear', 'Clear', 'Rain']

        condition = random.choice(conditions)

        return {
            'condition': condition,
            'visibility': random.randint(1000, 10000) if condition != 'Fog' else random.randint(200, 2000),
            'wind_speed': random.randint(5, 40),
            'temperature': random.randint(15, 35)
        }

    def flights_to_dataframe(self, flights: List[Flight]) -> pd.DataFrame:
        """Convert flight list to pandas DataFrame."""
        data = []
        for f in flights:
            data.append({
                'flight_id': f.flight_id,
                'airline': f.airline,
                'flight_number': f.flight_number,
                'aircraft_type': f.aircraft_type,
                'aircraft_size': f.aircraft_size,
                'arrival_time': f.arrival_time,
                'departure_time': f.departure_time,
                'passenger_count': f.passenger_count,
                'turnaround_time': f.turnaround_time,
                'delay': f.delay,
                'origin': f.origin,
                'destination': f.destination,
                'assigned_gate': f.assigned_gate,
                'status': f.status
            })
        return pd.DataFrame(data)

    def gates_to_dataframe(self, gates: List[Gate]) -> pd.DataFrame:
        """Convert gate list to pandas DataFrame."""
        data = []
        for g in gates:
            data.append({
                'gate_id': g.gate_id,
                'gate_size': g.gate_size,
                'terminal': g.terminal,
                'x_coord': g.x_coord,
                'y_coord': g.y_coord,
                'is_available': g.is_available,
                'current_flight': g.current_flight
            })
        return pd.DataFrame(data)


class ScenarioGenerator:
    """Generate specific operational scenarios."""

    def __init__(self, base_generator: SyntheticDataGenerator):
        self.generator = base_generator

    def peak_hour_scenario(self, num_flights: int = 200) -> List[Flight]:
        """Generate peak hour scenario with concentrated flights."""
        return self.generator.generate_flight_schedule(num_flights, peak_hours=True)

    def weather_scenario(self, weather_type: str = 'Rain') -> Dict:
        """Generate weather scenario."""
        return self.generator.generate_weather(scenario=weather_type)

    def gate_closure_scenario(self, flights: List[Flight], gates: List[Gate],
                               closed_gates: List[str]) -> Tuple[List[Flight], List[Gate]]:
        """Create gate closure scenario."""
        for gate in gates:
            if gate.gate_id in closed_gates:
                gate.is_available = False
        # Unassign flights from closed gates
        for flight in flights:
            if flight.assigned_gate in closed_gates:
                flight.assigned_gate = ""
                flight.status = "unassigned"
        return flights, gates

    def emergency_scenario(self, flights: List[Flight]) -> List[Flight]:
        """Add emergency flight."""
        emergency_flight = Flight(
            flight_id="EMERGENCY_001",
            airline="Emergency",
            flight_number="EMG101",
            aircraft_type="B777",
            aircraft_size="large",
            arrival_time=datetime.now(),
            departure_time=datetime.now() + timedelta(minutes=120),
            passenger_count=300,
            turnaround_time=120,
            delay=0,
            origin="XXX",
            destination="DEL",
            status="priority"
        )
        flights.insert(0, emergency_flight)
        return flights

    def vip_flight_scenario(self, flights: List[Flight]) -> List[Flight]:
        """Add VIP flight requiring special handling."""
        vip_flight = Flight(
            flight_id="VIP_001",
            airline="VIP",
            flight_number="VIP001",
            aircraft_type="B737",
            aircraft_size="medium",
            arrival_time=datetime.now() + timedelta(hours=2),
            departure_time=datetime.now() + timedelta(hours=3),
            passenger_count=50,
            turnaround_time=60,
            delay=0,
            origin="DEL",
            destination="BOM",
            status="vip"
        )
        flights.append(vip_flight)
        flights.sort(key=lambda x: x.arrival_time)
        return flights


if __name__ == "__main__":
    # Test the generator
    gen = SyntheticDataGenerator(seed=42)
    flights = gen.generate_flight_schedule(100)
    gates = gen.generate_gates()

    print(f"Generated {len(flights)} flights")
    print(f"Generated {len(gates)} gates")

    df = gen.flights_to_dataframe(flights)
    print(df.head())
