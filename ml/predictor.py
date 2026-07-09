"""
Machine Learning Module.

Implements ML predictions for:
- Conflict probability
- Best gate recommendation
- Delay risk assessment
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, mean_squared_error
import joblib
import warnings
warnings.filterwarnings('ignore')

from generator.data_generator import Flight, Gate


@dataclass
class PredictionResult:
    """Result of ML prediction."""
    prediction_type: str
    value: float
    confidence: float
    features_importance: Dict[str, float]
    explanation: str


class FeatureEngineer:
    """Feature engineering for ML models."""

    def __init__(self):
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.feature_columns = []

    def extract_features(self, flight: Flight, gate: Optional[Gate] = None,
                         historical_context: Dict = None) -> Dict:
        """Extract features from flight and gate data."""
        features = {}

        # Time-based features
        arrival_hour = flight.arrival_time.hour
        features['arrival_hour'] = arrival_hour
        features['is_peak_hour'] = 1 if arrival_hour in [6, 7, 8, 9, 17, 18, 19, 20] else 0
        features['is_weekend'] = 1 if flight.arrival_time.weekday() >= 5 else 0

        # Flight features
        features['passenger_count'] = flight.passenger_count
        features['turnaround_time'] = flight.turnaround_time
        features['aircraft_size_small'] = 1 if flight.aircraft_size == 'small' else 0
        features['aircraft_size_medium'] = 1 if flight.aircraft_size == 'medium' else 0
        features['aircraft_size_large'] = 1 if flight.aircraft_size == 'large' else 0

        # Delay features
        features['planned_delay'] = flight.delay
        features['has_delay'] = 1 if flight.delay > 0 else 0

        if gate:
            # Gate features
            features['gate_terminal'] = gate.terminal
            features['gate_size_small'] = 1 if gate.gate_size == 'small' else 0
            features['gate_size_medium'] = 1 if gate.gate_size == 'medium' else 0
            features['gate_size_large'] = 1 if gate.gate_size == 'large' else 0

            # Compatibility
            size_compat = {
                'small': ['small', 'medium', 'large'],
                'medium': ['medium', 'large'],
                'large': ['large']
            }
            features['size_compatible'] = 1 if gate.gate_size in size_compat.get(flight.aircraft_size, []) else 0

        # Historical context
        if historical_context:
            features['gate_historical_conflicts'] = historical_context.get('conflicts', 0)
            features['gate_utilization'] = historical_context.get('utilization', 0.5)
            features['nearby_flights'] = historical_context.get('nearby_flights', 0)

        return features

    def extract_features_dataframe(self, flights: List[Flight], gates: List[Gate],
                                    gate_assignments: Dict[str, str] = None) -> pd.DataFrame:
        """Extract features for all flights."""
        features_list = []

        gate_dict = {g.gate_id: g for g in gates}

        for flight in flights:
            base_features = self.extract_features(flight)

            # If we have gate assignment, add gate features
            if gate_assignments and flight.flight_id in gate_assignments:
                gate_id = gate_assignments[flight.flight_id]
                gate = gate_dict.get(gate_id)
                gate_features = self.extract_features(flight, gate)
                base_features.update(gate_features)

            features_list.append(base_features)

        df = pd.DataFrame(features_list)

        # Fill missing values
        df = df.fillna(0)

        self.feature_columns = list(df.columns)

        return df

    def prepare_training_data(self, flights: List[Flight], gates: List[Gate],
                               conflict_labels: List[int]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for training."""
        gate_dict = {g.gate_id: g for g in gates}

        X = []
        y = []

        for flight in flights:
            assigned_gate = flight.assigned_gate if hasattr(flight, 'assigned_gate') and flight.assigned_gate else None
            if assigned_gate and assigned_gate in gate_dict:
                gate = gate_dict[assigned_gate]
                features = self.extract_features(flight, gate)
                X.append(list(features.values()))

        y = conflict_labels[:len(X)]

        return np.array(X), np.array(y)


class ConflictPredictor:
    """ML model for predicting gate allocation conflicts."""

    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        )
        self.feature_engineer = FeatureEngineer()
        self.is_trained = False
        self.feature_names = []

    def train(self, flights: List[Flight], gates: List[Gate],
              conflict_labels: List[int]) -> Dict:
        """Train the conflict prediction model."""
        X, y = self.feature_engineer.prepare_training_data(flights, gates, conflict_labels)

        if len(X) == 0 or len(np.unique(y)) < 2:
            # Generate synthetic training data if insufficient
            X, y = self._generate_synthetic_training(flights, gates)

        # Store feature names
        self.feature_names = list(self.feature_engineer.extract_features(flights[0], gates[0]).keys())

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Scale features
        X_train = self.feature_engineer.scaler.fit_transform(X_train)
        X_test = self.feature_engineer.scaler.transform(X_test)

        # Train model
        self.model.fit(X_train, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        # Cross-validation
        cv_scores = cross_val_score(self.model, X, y, cv=5)

        self.is_trained = True

        return {
            'accuracy': accuracy,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'feature_importance': dict(zip(self.feature_names, self.model.feature_importances_)),
            'classification_report': classification_report(y_test, y_pred, output_dict=True)
        }

    def _generate_synthetic_training(self, flights: List[Flight],
                                      gates: List[Gate]) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic training data."""
        X = []
        y = []

        gate_dict = {g.gate_id: g for g in gates}

        for flight in flights:
            # Simulate assignments to different gates
            for gate in gates:
                features = self.feature_engineer.extract_features(flight, gate)
                X.append(list(features.values()))

                # Determine if this assignment would cause conflict
                # (simplified logic for training data generation)
                has_size_mismatch = gate.gate_size not in {
                    'small': ['small', 'medium', 'large'],
                    'medium': ['medium', 'large'],
                    'large': ['large']
                }.get(flight.aircraft_size, [])

                is_peak = features.get('is_peak_hour', 0) == 1

                # Conflict more likely during peak hours or size mismatch
                conflict_prob = 0.1
                if has_size_mismatch:
                    conflict_prob = 0.9
                elif is_peak:
                    conflict_prob = 0.3
                elif features.get('planned_delay', 0) > 15:
                    conflict_prob = 0.4

                y.append(1 if np.random.random() < conflict_prob else 0)

        # Add some noise to prevent perfect separation
        for i in range(len(y)):
            if np.random.random() < 0.1:
                y[i] = 1 - y[i]

        return np.array(X), np.array(y)

    def predict_conflict_probability(self, flight: Flight, gate: Gate) -> float:
        """Predict probability of conflict for a flight-gate assignment."""
        if not self.is_trained:
            return 0.5  # Default probability if model not trained

        features = self.feature_engineer.extract_features(flight, gate)
        X = np.array([list(features.values())])
        X = self.feature_engineer.scaler.transform(X)

        proba = self.model.predict_proba(X)
        return proba[0][1] if proba.shape[1] > 1 else 0.5

    def predict(self, flight: Flight, gate: Gate) -> int:
        """Predict whether assignment will cause conflict."""
        if not self.is_trained:
            return 0

        features = self.feature_engineer.extract_features(flight, gate)
        X = np.array([list(features.values())])
        X = self.feature_engineer.scaler.transform(X)

        return self.model.predict(X)[0]

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from trained model."""
        if not self.is_trained:
            return {}
        return dict(zip(self.feature_names, self.model.feature_importances_))


class GateRecommender:
    """ML model for recommending best gate."""

    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=150,
            max_depth=15,
            random_state=42
        )
        self.feature_engineer = FeatureEngineer()
        self.is_trained = False
        self.gate_encoder = LabelEncoder()
        self.feature_names = []

    def train(self, flights: List[Flight], gates: List[Gate],
              optimal_assignments: Dict[str, str]) -> Dict:
        """Train gate recommendation model."""
        gate_dict = {g.gate_id: g for g in gates}

        X = []
        y = []

        for flight in flights:
            if flight.flight_id in optimal_assignments:
                optimal_gate = optimal_assignments[flight.flight_id]
                gate = gate_dict.get(optimal_gate)

                if gate:
                    features = self.feature_engineer.extract_features(flight)
                    X.append(list(features.values()))
                    y.append(optimal_gate)

        if len(X) < 10:
            # Generate synthetic data
            X, y = self._generate_recommendation_data(flights, gates, optimal_assignments)

        X = np.array(X)
        y = self.gate_encoder.fit_transform(y)

        # Split and train
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        self.model.fit(X_train, y_train)

        accuracy = accuracy_score(y_test, self.model.predict(X_test))

        self.is_trained = True
        self.feature_names = list(self.feature_engineer.extract_features(flights[0]).keys())

        return {
            'accuracy': accuracy,
            'num_gates': len(self.gate_encoder.classes_),
            'feature_importance': dict(zip(self.feature_names, self.model.feature_importances_))
        }

    def _generate_recommendation_data(self, flights: List[Flight], gates: List[Gate],
                                       assignments: Dict[str, str]) -> Tuple[np.ndarray, List[str]]:
        """Generate synthetic recommendation training data."""
        X = []
        y = []

        size_order = {'small': 1, 'medium': 2, 'large': 3}

        for flight in flights:
            # Find best gate based on simple rules
            compatible_gates = [
                g for g in gates
                if size_order.get(g.gate_size, 0) >= size_order.get(flight.aircraft_size, 0)
            ]

            if compatible_gates:
                # Prefer exact size match
                exact_match = [g for g in compatible_gates if g.gate_size == flight.aircraft_size]
                best_gate = min((exact_match or compatible_gates), key=lambda g: g.terminal)

                features = self.feature_engineer.extract_features(flight)
                X.append(list(features.values()))
                y.append(best_gate.gate_id)

        return np.array(X), y

    def recommend_gate(self, flight: Flight, gates: List[Gate],
                       exclude_gates: List[str] = None) -> Tuple[str, float]:
        """Recommend best gate for a flight."""
        if not self.is_trained:
            # Fallback to rule-based
            return self._fallback_recommendation(flight, gates, exclude_gates)

        features = self.feature_engineer.extract_features(flight)
        X = np.array([list(features.values())])

        # Get probabilities for all gates
        proba = self.model.predict_proba(X)[0]

        # Map probabilities back to gates
        gate_probas = {}
        for i, gate_id in enumerate(self.gate_encoder.classes_):
            gate_probas[gate_id] = 0.0

        for i, prob in enumerate(proba):
            if i < len(self.gate_encoder.classes_):
                gate_probas[self.gate_encoder.classes_[i]] = prob

        # Filter out excluded gates and incompatible gates
        size_order = {'small': 1, 'medium': 2, 'large': 3}
        flight_size = size_order.get(flight.aircraft_size, 1)

        gate_dict = {g.gate_id: g for g in gates}
        filtered_gates = {
            g: p for g, p in gate_probas.items()
            if (exclude_gates is None or g not in exclude_gates) and
               g in gate_dict and
               size_order.get(gate_dict[g].gate_size, 0) >= flight_size
        }

        if filtered_gates:
            best_gate = max(filtered_gates.items(), key=lambda x: x[1])
            return best_gate[0], best_gate[1]

        return self._fallback_recommendation(flight, gates, exclude_gates), 0.5

    def _fallback_recommendation(self, flight: Flight, gates: List[Gate],
                                  exclude_gates: List[str] = None) -> str:
        """Fallback gate recommendation."""
        exclude_set = set(exclude_gates or [])
        size_order = {'small': 1, 'medium': 2, 'large': 3}
        flight_size = size_order.get(flight.aircraft_size, 1)

        compatible = [
            g for g in gates
            if g.gate_id not in exclude_set and
               size_order.get(g.gate_size, 0) >= flight_size
        ]

        # Prefer exact size match
        exact = [g for g in compatible if g.gate_size == flight.aircraft_size]
        if exact:
            return exact[0].gate_id

        return compatible[0].gate_id if compatible else gates[0].gate_id


class DelayPredictor:
    """ML model for predicting flight delays."""

    def __init__(self):
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.feature_engineer = FeatureEngineer()
        self.is_trained = False
        self.feature_names = []

    def train(self, flights: List[Flight]) -> Dict:
        """Train delay prediction model."""
        X = []
        y = []

        for flight in flights:
            features = self.feature_engineer.extract_features(flight)
            X.append(list(features.values()))
            y.append(flight.delay)

        X = np.array(X)
        y = np.array(y)

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)

        self.is_trained = True
        self.feature_names = list(self.feature_engineer.extract_features(flights[0]).keys())

        return {
            'rmse': rmse,
            'mean_delay': np.mean(y),
            'feature_importance': dict(zip(self.feature_names, self.model.feature_importances_))
        }

    def predict_delay(self, flight: Flight) -> float:
        """Predict delay for a flight."""
        if not self.is_trained:
            return flight.delay

        features = self.feature_engineer.extract_features(flight)
        X = np.array([list(features.values())])

        return max(0, self.model.predict(X)[0])

    def get_delay_risk_level(self, flight: Flight) -> str:
        """Get delay risk level for a flight."""
        predicted_delay = self.predict_delay(flight)

        if predicted_delay < 5:
            return 'low'
        elif predicted_delay < 15:
            return 'medium'
        elif predicted_delay < 30:
            return 'high'
        else:
            return 'critical'


class MLPipeline:
    """Main ML pipeline integrating all predictors."""

    def __init__(self, flights: List[Flight], gates: List[Gate]):
        self.flights = flights
        self.gates = gates
        self.conflict_predictor = ConflictPredictor()
        self.gate_recommender = GateRecommender()
        self.delay_predictor = DelayPredictor()
        self.is_trained = False

    def train_all(self, optimal_assignments: Dict[str, str] = None,
                  conflict_labels: List[int] = None) -> Dict:
        """Train all ML models."""
        results = {}

        # Train conflict predictor
        if conflict_labels is None:
            # Generate labels based on actual conflicts
            conflict_labels = []
            for flight in self.flights:
                has_conflict = 1 if getattr(flight, 'has_conflict', False) else 0
                conflict_labels.append(has_conflict)

        results['conflict'] = self.conflict_predictor.train(self.flights, self.gates, conflict_labels)

        # Train gate recommender
        if optimal_assignments is None:
            # Use current assignments as optimal
            optimal_assignments = {
                f.flight_id: f.assigned_gate
                for f in self.flights
                if hasattr(f, 'assigned_gate') and f.assigned_gate
            }

        if optimal_assignments:
            results['recommendation'] = self.gate_recommender.train(
                self.flights, self.gates, optimal_assignments
            )

        # Train delay predictor
        results['delay'] = self.delay_predictor.train(self.flights)

        self.is_trained = True

        return results

    def predict(self, flight: Flight, gate: Gate = None) -> Dict:
        """Make all predictions for a flight."""
        predictions = {}

        # Conflict probability for each gate
        if gate:
            predictions['conflict_probability'] = self.conflict_predictor.predict_conflict_probability(flight, gate)

        # Best gate recommendation
        rec_gate, rec_confidence = self.gate_recommender.recommend_gate(flight, self.gates)
        predictions['recommended_gate'] = rec_gate
        predictions['recommendation_confidence'] = rec_confidence

        # Delay prediction
        predictions['predicted_delay'] = self.delay_predictor.predict_delay(flight)
        predictions['delay_risk'] = self.delay_predictor.get_delay_risk_level(flight)

        return predictions

    def get_explainability_data(self) -> Dict:
        """Get feature importance for all models."""
        return {
            'conflict_features': self.conflict_predictor.get_feature_importance(),
            'recommendation_features': self.gate_recommender.feature_names,
            'delay_features': self.delay_predictor.feature_names
        }


if __name__ == "__main__":
    from generator.data_generator import SyntheticDataGenerator

    # Test ML pipeline
    gen = SyntheticDataGenerator(seed=42)
    flights = gen.generate_flight_schedule(100)
    gates = gen.generate_gates()

    # Train models
    pipeline = MLPipeline(flights, gates)

    # Generate some assignments
    gate_dict = {g.gate_id: g for g in gates}
    for i, flight in enumerate(flights):
        gate_idx = i % len(gates)
        flight.assigned_gate = gates[gate_idx].gate_id

    print("Training ML models...")
    results = pipeline.train_all()

    print("\nTraining Results:")
    for model, metrics in results.items():
        print(f"\n{model}:")
        for key, value in metrics.items():
            if not isinstance(value, dict):
                print(f"  {key}: {value}")

    # Test prediction
    test_flight = flights[0]
    test_gate = gates[0]

    predictions = pipeline.predict(test_flight, test_gate)
    print("\nPredictions for test flight:")
    for key, value in predictions.items():
        print(f"  {key}: {value}")
