"""Configuration settings for GateOptimizer Sim."""

from dataclasses import dataclass, field
from typing import List, Dict
import numpy as np

@dataclass
class AirportConfig:
    """Airport configuration settings."""
    name: str = "Indira Gandhi International Airport"
    code: str = "DEL"
    terminals: int = 3
    gates_per_terminal: int = 4
    total_gates: int = 12
    # Selectable total-gate counts in the sidebar. Terminals stay fixed at 3,
    # so gates_per_terminal = total_gates // 3 for each option (keeps the
    # existing coordinate-layout logic, which lays gates out per terminal,
    # working unchanged for any of these).
    gate_options: List[int] = field(default_factory=lambda: [12, 15, 18, 21, 24, 27, 30])
    default_total_gates: int = 12

@dataclass
class SimulationConfig:
    """Simulation configuration settings."""
    num_flights_options: List[int] = field(default_factory=lambda: list(range(60, 241, 20)))
    default_num_flights: int = 120
    simulation_hours: int = 24
    min_turnaround_time: int = 30  # minutes
    max_turnaround_time: int = 180  # minutes

@dataclass
class AircraftConfig:
    """Aircraft type configurations."""
    types: Dict = field(default_factory=lambda: {
        'small': {
            'models': ['ATR72', 'Q400', 'CRJ200', 'ERJ145'],
            'capacity_range': (50, 80),
            'size': 'small',
            'gate_requirement': 'small'
        },
        'medium': {
            'models': ['A320', 'A321', 'B737', 'B738'],
            'capacity_range': (140, 200),
            'size': 'medium',
            'gate_requirement': 'medium'
        },
        'large': {
            'models': ['A350', 'A380', 'B777', 'B787', 'B747'],
            'capacity_range': (250, 550),
            'size': 'large',
            'gate_requirement': 'large'
        }
    })

@dataclass
class WeatherConfig:
    """Weather configurations."""
    conditions: List[str] = field(default_factory=lambda: ['Clear', 'Rain', 'Fog', 'Thunderstorm', 'Snow'])
    default_condition: str = 'Clear'
    # How much each condition scales up generated flight delays, e.g. 0.15
    # means delays run 15% longer on average under that condition. Applied
    # in SyntheticDataGenerator.generate_flight_schedule().
    delay_impact: Dict[str, float] = field(default_factory=lambda: {
        'Clear': 0.0,
        'Rain': 0.15,
        'Fog': 0.20,
        'Thunderstorm': 0.35,
        'Snow': 0.30,
    })

@dataclass
class AirlineConfig:
    """Airline configurations."""
    airlines: List[str] = field(default_factory=lambda: [
        'Air India', 'IndiGo', 'SpiceJet', 'Vistara', 'GoAir',
        'Air Asia', 'Emirates', 'Qatar Airways', 'British Airways'
    ])

@dataclass
class GateConfig:
    """Gate configurations."""
    gate_sizes: Dict = field(default_factory=lambda: {
        'small': {'count': 4, 'terminals': [1, 2]},
        'medium': {'count': 6, 'terminals': [1, 2, 3]},
        'large': {'count': 2, 'terminals': [3]}
    })

@dataclass
class Config:
    """Main configuration class."""
    airport: AirportConfig = field(default_factory=AirportConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    aircraft: AircraftConfig = field(default_factory=AircraftConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    airline: AirlineConfig = field(default_factory=AirlineConfig)
    gate: GateConfig = field(default_factory=GateConfig)

# Global config instance
config = Config()
