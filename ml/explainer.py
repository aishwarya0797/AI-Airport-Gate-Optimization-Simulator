"""
Explainable AI Module.

Uses SHAP for explaining ML predictions:
- Why a gate was selected
- Why conflict probability is high
- Important features influencing predictions
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

from generator.data_generator import Flight, Gate
from ml.predictor import MLPipeline, FeatureEngineer


@dataclass
class ExplanationResult:
    """Result of explanation."""
    prediction_type: str
    main_reason: str
    contributing_factors: List[Tuple[str, float, str]]
    confidence: float
    full_explanation: str


class PredictionExplainer:
    """
    Explains ML predictions using SHAP values.
    """

    def __init__(self, ml_pipeline: MLPipeline):
        self.pipeline = ml_pipeline
        self.feature_engineer = FeatureEngineer()
        self.shap_explainers = {}

    def initialize_explainers(self):
        """Initialize SHAP explainers for trained models."""
        if not SHAP_AVAILABLE:
            return False

        try:
            # Create background data
            sample_flights = self.pipeline.flights[:20]
            sample_gates = self.pipeline.gates

            # Background data for conflict model
            X_background = []
            for flight in sample_flights:
                for gate in sample_gates[:4]:
                    features = self.feature_engineer.extract_features(flight, gate)
                    X_background.append(list(features.values()))

            X_background = np.array(X_background)

            # Create explainer for conflict predictor
            if self.pipeline.conflict_predictor.is_trained:
                self.shap_explainers['conflict'] = shap.TreeExplainer(
                    self.pipeline.conflict_predictor.model
                )

            # Create explainer for gate recommender
            if self.pipeline.gate_recommender.is_trained:
                self.shap_explainers['recommendation'] = shap.TreeExplainer(
                    self.pipeline.gate_recommender.model
                )

            # Create explainer for delay predictor
            if self.pipeline.delay_predictor.is_trained:
                self.shap_explainers['delay'] = shap.TreeExplainer(
                    self.pipeline.delay_predictor.model
                )

            return True
        except Exception as e:
            print(f"Warning: Could not initialize SHAP explainers: {e}")
            return False

    def explain_gate_selection(self, flight: Flight, gate_id: str,
                                gates: List[Gate]) -> ExplanationResult:
        """Explain why a specific gate was recommended."""
        gate_dict = {g.gate_id: g for g in gates}
        gate = gate_dict.get(gate_id)

        if not gate:
            return ExplanationResult(
                prediction_type='gate_selection',
                main_reason='Gate not found',
                contributing_factors=[],
                confidence=0.0,
                full_explanation='Gate does not exist in the system.'
            )

        factors = []

        # Analyze size compatibility
        size_compat = {
            'small': ['small', 'medium', 'large'],
            'medium': ['medium', 'large'],
            'large': ['large']
        }

        if gate.gate_size in size_compat.get(flight.aircraft_size, []):
            if gate.gate_size == flight.aircraft_size:
                factors.append(('size_match', 1.0, 'Exact size match between aircraft and gate'))
            else:
                factors.append(('size_compatible', 0.7, 'Gate size compatible with aircraft'))
        else:
            factors.append(('size_mismatch', -1.0, 'Gate size incompatible with aircraft'))

        # Analyze time factors
        arrival_hour = flight.arrival_time.hour
        if arrival_hour in [6, 7, 8, 9, 17, 18, 19, 20]:
            factors.append(('peak_hour', 0.3, 'Flight arrives during peak hours'))
        else:
            factors.append(('off_peak', 0.1, 'Flight arrives during off-peak hours'))

        # Analyze delay history
        if flight.delay > 30:
            factors.append(('high_delay', 0.2, 'Flight has significant planned delay'))
        elif flight.delay > 0:
            factors.append(('minor_delay', 0.1, 'Flight has minor planned delay'))
        else:
            factors.append(('no_delay', 0.0, 'Flight on schedule'))

        # Analyze gate availability and utilization
        # Get ML prediction if available
        if self.pipeline.gate_recommender.is_trained:
            rec_gate, confidence = self.pipeline.gate_recommender.recommend_gate(flight, gates)
            if rec_gate == gate_id:
                factors.append(('ml_recommendation', confidence * 0.5, 'ML model confidence'))
            else:
                factors.append(('alternative_recommendation', -0.2, f'ML model prefers gate {rec_gate}'))

        # Conflict probability
        if self.pipeline.conflict_predictor.is_trained:
            conflict_prob = self.pipeline.conflict_predictor.predict_conflict_probability(flight, gate)
            if conflict_prob < 0.2:
                factors.append(('low_conflict_risk', 0.4, f'Low conflict probability ({conflict_prob*100:.1f}%)'))
            elif conflict_prob < 0.5:
                factors.append(('medium_conflict_risk', 0.0, f'Medium conflict probability ({conflict_prob*100:.1f}%)'))
            else:
                factors.append(('high_conflict_risk', -0.5, f'High conflict probability ({conflict_prob*100:.1f}%)'))

        # Generate main reason
        positive_factors = [f for f in factors if f[1] > 0]
        negative_factors = [f for f in factors if f[1] < 0]

        if negative_factors and len(negative_factors) > len(positive_factors):
            main_reason = f"This gate selection has some risks due to: {', '.join([f[2] for f in negative_factors[:2]])}"
        elif positive_factors:
            main_reason = f"This gate is a good fit because: {', '.join([f[2] for f in positive_factors[:2]])}"
        else:
            main_reason = "This gate assignment is acceptable with standard considerations"

        # Generate full explanation
        explanation_parts = [
            f"Gate {gate_id} Recommendation Analysis:",
            "",
            f"Aircraft: {flight.aircraft_type} ({flight.aircraft_size} size)",
            f"Gate: Terminal {gate.terminal}, {gate.gate_size} size",
            ""
        ]

        # Add factors as checklist
        explanation_parts.append("Selection Factors:")
        for factor_name, value, description in sorted(factors, key=lambda x: -x[1]):
            symbol = "+" if value > 0 else "-" if value < 0 else "o"
            explanation_parts.append(f"  {symbol} {description}")

        full_explanation = "\n".join(explanation_parts)

        # Calculate overall confidence
        total_score = sum(f[1] for f in factors)
        confidence = min(1.0, max(0.0, (total_score + 1) / 2))

        return ExplanationResult(
            prediction_type='gate_selection',
            main_reason=main_reason,
            contributing_factors=factors,
            confidence=confidence,
            full_explanation=full_explanation
        )

    def explain_conflict_probability(self, flight: Flight, gate: Gate,
                                        probability: float) -> ExplanationResult:
        """Explain why conflict probability is high or low."""
        factors = []

        # Size mismatch analysis
        size_compat = {
            'small': ['small', 'medium', 'large'],
            'medium': ['medium', 'large'],
            'large': ['large']
        }

        if gate.gate_size not in size_compat.get(flight.aircraft_size, []):
            factors.append(('size_incompatible', 0.9, 'Aircraft size incompatible with gate'))
        else:
            factors.append(('size_compatible', -0.1, 'Aircraft size compatible with gate'))

        # Time analysis
        arrival_hour = flight.arrival_time.hour
        if arrival_hour in [6, 7, 8, 9, 17, 18, 19, 20]:
            factors.append(('peak_hour_traffic', 0.3, 'Peak hour arrival increases conflict risk'))
        else:
            factors.append(('off_peak_timing', -0.1, 'Off-peak timing reduces conflict risk'))

        # Turnaround time analysis
        if flight.turnaround_time > 90:
            factors.append(('long_turnaround', 0.2, 'Long turnaround time increases window for conflicts'))
        elif flight.turnaround_time < 45:
            factors.append(('short_turnaround', -0.1, 'Short turnaround reduces conflict window'))

        # Delay impact
        if flight.delay > 30:
            factors.append(('significant_delay', 0.4, 'High delay increases conflict risk'))
        elif flight.delay > 0:
            factors.append(('minor_delay', 0.1, 'Minor delay may increase conflict risk'))

        # Passenger count
        if flight.passenger_count > 300:
            factors.append(('high_passengers', 0.1, 'High passenger count may require extra time'))

        # Generate explanations
        if probability > 0.7:
            main_reason = f"High conflict probability ({probability*100:.1f}%) due to critical factors"
        elif probability > 0.4:
            main_reason = f"Moderate conflict probability ({probability*100:.1f}%) - some risk factors present"
        else:
            main_reason = f"Low conflict probability ({probability*100:.1f}%) - assignment appears safe"

        # Build full explanation
        explanation_parts = [
            f"Conflict Probability Analysis ({probability*100:.1f}%):",
            "",
            f"Flight: {flight.flight_number} ({flight.aircraft_type})",
            f"Gate: {gate.gate_id} (Terminal {gate.terminal})",
            ""
        ]

        explanation_parts.append("Risk Factors:")
        for factor_name, value, description in sorted(factors, key=lambda x: -x[1]):
            symbol = "!" if value > 0.3 else "+" if value > 0 else "-" if value < 0 else "o"
            explanation_parts.append(f"  {symbol} {description}")

        full_explanation = "\n".join(explanation_parts)

        return ExplanationResult(
            prediction_type='conflict_probability',
            main_reason=main_reason,
            contributing_factors=factors,
            confidence=probability,
            full_explanation=full_explanation
        )

    def explain_delay_prediction(self, flight: Flight,
                                   predicted_delay: float) -> ExplanationResult:
        """Explain why a specific delay was predicted."""
        factors = []

        # Time-based factors
        arrival_hour = flight.arrival_time.hour
        if arrival_hour in [6, 7, 8, 9, 17, 18, 19, 20]:
            factors.append(('peak_hour', 0.3, 'Peak hour arrivals often experience delays'))
        else:
            factors.append(('off_peak', -0.1, 'Off-peak timing reduces delay likelihood'))

        # Day of week
        if flight.arrival_time.weekday() >= 5:
            factors.append(('weekend', 0.1, 'Weekend flights may have different delay patterns'))

        # Aircraft size
        if flight.aircraft_size == 'large':
            factors.append(('large_aircraft', 0.2, 'Large aircraft may have longer turnaround times'))

        # Historical delay
        if flight.delay > 0:
            factors.append(('historical_delay', 0.4, f'Flight has {flight.delay} min planned delay'))
        else:
            factors.append(('on_schedule', -0.1, 'Flight currently on schedule'))

        # Generate main reason
        if predicted_delay > 30:
            main_reason = f"High delay risk ({predicted_delay:.0f} min predicted) - multiple factors contributing"
        elif predicted_delay > 15:
            main_reason = f"Moderate delay risk ({predicted_delay:.0f} min predicted)"
        elif predicted_delay > 5:
            main_reason = f"Minor delay expected ({predicted_delay:.0f} min)"
        else:
            main_reason = f"Minimal delay predicted ({predicted_delay:.0f} min) - flight likely on time"

        # Full explanation
        explanation_parts = [
            f"Delay Prediction Analysis ({predicted_delay:.0f} minutes):",
            "",
            f"Flight: {flight.flight_number}",
            f"Scheduled Arrival: {flight.arrival_time.strftime('%H:%M')}",
            ""
        ]

        explanation_parts.append("Contributing Factors:")
        for factor_name, value, description in sorted(factors, key=lambda x: -x[1]):
            symbol = "!" if value > 0.2 else "+" if value > 0 else "-" if value < 0 else "o"
            explanation_parts.append(f"  {symbol} {description}")

        full_explanation = "\n".join(explanation_parts)

        return ExplanationResult(
            prediction_type='delay_prediction',
            main_reason=main_reason,
            contributing_factors=factors,
            confidence=min(1.0, predicted_delay / 60),
            full_explanation=full_explanation
        )

    def generate_feature_importance_plot(self, model_type: str = 'conflict') -> Optional[Dict]:
        """Generate feature importance visualization data."""
        if model_type == 'conflict' and self.pipeline.conflict_predictor.is_trained:
            importance = self.pipeline.conflict_predictor.get_feature_importance()
        elif model_type == 'delay' and self.pipeline.delay_predictor.is_trained:
            importance = dict(zip(
                self.pipeline.delay_predictor.feature_names,
                self.pipeline.delay_predictor.model.feature_importances_
            ))
        else:
            return None

        # Sort by importance
        sorted_importance = sorted(importance.items(), key=lambda x: -x[1])

        return {
            'features': [f[0] for f in sorted_importance],
            'importance': [f[1] for f in sorted_importance],
            'title': f'{model_type.capitalize()} Model Feature Importance'
        }

    def generate_explanation_report(self, flight: Flight, gate: Gate,
                                     predictions: Dict) -> str:
        """Generate comprehensive explanation report."""
        report_parts = [
            "=" * 60,
            "GATE ALLOCATION PREDICTION EXPLANATION REPORT",
            "=" * 60,
            "",
            f"Flight: {flight.flight_number}",
            f"Aircraft: {flight.aircraft_type} ({flight.aircraft_size})",
            f"Passengers: {flight.passenger_count}",
            f"Arrival: {flight.arrival_time.strftime('%Y-%m-%d %H:%M')}",
            "",
            "-" * 60,
            "GATE SELECTION EXPLANATION",
            "-" * 60
        ]

        if 'recommended_gate' in predictions:
            gate_explanation = self.explain_gate_selection(
                flight, predictions['recommended_gate'],
                self.pipeline.gates
            )
            report_parts.append(gate_explanation.full_explanation)

        report_parts.extend([
            "",
            "-" * 60,
            "CONFLICT PROBABILITY EXPLANATION",
            "-" * 60
        ])

        if gate and 'conflict_probability' in predictions:
            conflict_explanation = self.explain_conflict_probability(
                flight, gate, predictions['conflict_probability']
            )
            report_parts.append(conflict_explanation.full_explanation)

        report_parts.extend([
            "",
            "-" * 60,
            "DELAY PREDICTION EXPLANATION",
            "-" * 60
        ])

        if 'predicted_delay' in predictions:
            delay_explanation = self.explain_delay_prediction(
                flight, predictions['predicted_delay']
            )
            report_parts.append(delay_explanation.full_explanation)

        report_parts.extend([
            "",
            "=" * 60,
            "END OF REPORT",
            "=" * 60
        ])

        return "\n".join(report_parts)


def format_explanation_for_display(explanation: ExplanationResult) -> str:
    """Format explanation for display in dashboard."""
    lines = [
        f"### {explanation.prediction_type.replace('_', ' ').title()}",
        "",
        f"**Main Reason:** {explanation.main_reason}",
        "",
        "**Contributing Factors:**",
        ""
    ]

    for factor_name, value, description in explanation.contributing_factors:
        icon = "+" if value > 0 else "-" if value < 0 else "o"
        lines.append(f"* {icon} {description}")

    lines.append("")
    lines.append(f"**Confidence:** {explanation.confidence*100:.1f}%")

    return "\n".join(lines)


if __name__ == "__main__":
    from generator.data_generator import SyntheticDataGenerator
    from ml.predictor import MLPipeline

    # Test explainer
    gen = SyntheticDataGenerator(seed=42)
    flights = gen.generate_flight_schedule(50)
    gates = gen.generate_gates()

    # Assign gates
    for i, flight in enumerate(flights):
        flight.assigned_gate = gates[i % len(gates)].gate_id

    # Create and train pipeline
    pipeline = MLPipeline(flights, gates)
    pipeline.train_all()

    # Create explainer
    explainer = PredictionExplainer(pipeline)

    # Test explanations
    test_flight = flights[0]
    test_gate = gates[0]

    gate_explanation = explainer.explain_gate_selection(test_flight, test_gate.gate_id, gates)
    print("Gate Selection Explanation:")
    print(gate_explanation.full_explanation)
    print("\n" + "="*60 + "\n")

    conflict_explanation = explainer.explain_conflict_probability(test_flight, test_gate, 0.35)
    print("Conflict Probability Explanation:")
    print(conflict_explanation.full_explanation)
