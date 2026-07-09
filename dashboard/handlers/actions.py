"""
Button-click handlers for the dashboard.

Each ``handle_*`` function is invoked from ``dashboard/app.py`` in response
to a sidebar button press. Handlers own the full lifecycle of a pipeline
stage: they call into the backend modules, mutate ``st.session_state`` with
the results, and surface a toast/error message. All exceptions are caught
so a single failed step never crashes the whole app.
"""

import copy
from dataclasses import asdict

import streamlit as st

from utils.config import config
from generator.data_generator import SyntheticDataGenerator, ScenarioGenerator
from simulation.airport_layout import AirportLayout
from simulation.simulation_engine import SimulationEngine
from allocation.gate_allocator import RuleBasedAllocator, NaiveAllocator
from allocation.conflict_detector import ConflictDetector
from optimization.optimizer import GateOptimizationEngine
from ml.predictor import MLPipeline
from ml.explainer import PredictionExplainer
from reports.report_generator import ReportGenerator


def handle_generation(num_flights: int, weather: str, scenario: str):
    """Generate a brand-new synthetic flight schedule, gates, and layout.

    Resets every downstream stage (allocation, optimization, ML, exports)
    since they all depend on the flight/gate data being regenerated.
    """
    try:
        generator = SyntheticDataGenerator()
        peak_hours = scenario == "Peak Hour Traffic"

        flights = generator.generate_flight_schedule(num_flights, peak_hours=peak_hours)
        gates = generator.generate_gates(
            num_terminals=config.airport.terminals,
            gates_per_terminal=config.airport.gates_per_terminal,
        )
        layout = AirportLayout(
            num_terminals=config.airport.terminals,
            gates_per_terminal=config.airport.gates_per_terminal,
        )
        weather_info = generator.generate_weather(scenario=weather)

        scenario_gen = ScenarioGenerator(generator)
        if scenario == "Gate Closure" and len(gates) >= 2:
            closed_gates = [gates[0].gate_id, gates[1].gate_id]
            flights, gates = scenario_gen.gate_closure_scenario(flights, gates, closed_gates)
        elif scenario == "Emergency Aircraft":
            flights = scenario_gen.emergency_scenario(flights)
        elif scenario == "VIP Flight":
            flights = scenario_gen.vip_flight_scenario(flights)

        st.session_state.update({
            "flights": flights,
            "gates": gates,
            "layout": layout,
            "generator": generator,
            "weather_info": weather_info,
            "scenario": scenario,
            "data_generated": True,
            "num_flights_last": num_flights,
            # Reset every downstream pipeline stage.
            "allocated": False,
            "rule_based_assignments": {}, "rule_based_results": [], "rule_based_summary": {},
            "naive_assignments": {}, "naive_results": [], "naive_summary": {},
            "conflicts_detected": False, "conflicts": [], "conflict_summary": {},
            "simulation_results": {},
            "optimized": False, "optimized_assignments": {}, "optimization_stats": {},
            "optimization_metrics": {}, "comparison": {},
            "ml_trained": False, "ml_pipeline": None, "ml_results": {},
            "explainer": None, "explainer_ready": False,
            "predictions": {},
            "export_data": {},
        })

        st.toast(
            f"Generated {len(flights)} flights across {len(gates)} gates ({scenario}).",
            icon="✅",
        )
    except Exception as exc:  # noqa: BLE001 - surface any generation failure to the operator
        st.error(f"Flight generation failed: {exc}")


def handle_allocation():
    """Run the rule-based allocator, a naive baseline, conflict detection, and a simulation pass."""
    flights = st.session_state.get("flights")
    gates = st.session_state.get("gates")
    if not flights or not gates:
        st.warning("Generate a flight schedule before running allocation.")
        return

    try:
        layout = st.session_state.get("layout") or AirportLayout()

        allocator = RuleBasedAllocator(gates, layout)
        flight_to_gate, results = allocator.allocate_all_flights(flights)
        summary = allocator.get_allocation_summary(results)

        # Naive first-fit baseline, computed on an isolated copy so it never
        # mutates the "live" flights the rest of the dashboard reads from.
        naive_flights = copy.deepcopy(flights)
        for f in naive_flights:
            f.assigned_gate = ""
        naive_allocator = NaiveAllocator(gates)
        naive_map, naive_results = naive_allocator.allocate_all_flights(naive_flights)
        naive_summary = allocator.get_allocation_summary(naive_results)

        detector = ConflictDetector()
        conflicts = detector.detect_all_conflicts(flights, gates)
        conflict_summary = detector.generate_conflict_summary()

        sim_engine = SimulationEngine(flights, gates, layout)
        simulation_results = sim_engine.run_simulation()

        st.session_state.update({
            "rule_based_assignments": flight_to_gate,
            "rule_based_results": results,
            "rule_based_summary": summary,
            "naive_assignments": naive_map,
            "naive_results": naive_results,
            "naive_summary": naive_summary,
            "allocated": True,
            "conflicts": conflicts,
            "conflict_summary": conflict_summary,
            "conflicts_detected": True,
            "simulation_results": simulation_results,
        })

        st.toast(
            f"Allocated {summary['successful_allocations']}/{summary['total_flights']} flights "
            f"• {len(conflicts)} conflicts detected.",
            icon="🗺️",
        )
    except Exception as exc:  # noqa: BLE001
        st.error(f"Gate allocation failed: {exc}")


def handle_optimization():
    """Run the OR-Tools optimizer and refresh conflict/simulation state to match."""
    flights = st.session_state.get("flights")
    gates = st.session_state.get("gates")
    if not flights or not gates:
        st.warning("Generate a flight schedule before running optimization.")
        return

    try:
        layout = st.session_state.get("layout") or AirportLayout()

        engine = GateOptimizationEngine(flights, gates, layout)
        assignments, stats = engine.optimize_allocations()
        metrics = engine.calculate_metrics(assignments)

        naive_assignments = st.session_state.get("naive_assignments")
        if not naive_assignments:
            naive_flights = copy.deepcopy(flights)
            for f in naive_flights:
                f.assigned_gate = ""
            naive_allocator = NaiveAllocator(gates)
            naive_assignments, naive_results = naive_allocator.allocate_all_flights(naive_flights)
            st.session_state["naive_assignments"] = naive_assignments
            st.session_state["naive_results"] = naive_results

        comparison = engine.compare_allocations(naive_assignments, assignments)

        # The optimizer mutates `flight.assigned_gate` on the live flight
        # objects, so conflicts/simulation must be recomputed to stay in sync.
        detector = ConflictDetector()
        conflicts = detector.detect_all_conflicts(flights, gates)
        conflict_summary = detector.generate_conflict_summary()

        sim_engine = SimulationEngine(flights, gates, layout)
        simulation_results = sim_engine.run_simulation()

        st.session_state.update({
            "optimized": True,
            "optimized_assignments": assignments,
            "optimization_stats": stats,
            "optimization_metrics": metrics,
            "comparison": comparison,
            "conflicts": conflicts,
            "conflict_summary": conflict_summary,
            "conflicts_detected": True,
            "simulation_results": simulation_results,
        })

        status = stats.get("status", "unknown")
        st.toast(f"Optimization complete ({status}) • {len(assignments)} flights routed.", icon="⚡")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Optimization failed: {exc}")


def handle_ml_training():
    """Train the conflict, gate-recommendation, and delay models."""
    flights = st.session_state.get("flights")
    gates = st.session_state.get("gates")
    if not flights or not gates:
        st.warning("Generate a flight schedule before training ML models.")
        return

    try:
        pipeline = MLPipeline(flights, gates)

        optimal_assignments = (
            st.session_state.get("optimized_assignments")
            or st.session_state.get("rule_based_assignments")
            or None
        )
        results = pipeline.train_all(optimal_assignments=optimal_assignments)

        explainer = PredictionExplainer(pipeline)
        explainer_ready = explainer.initialize_explainers()

        st.session_state.update({
            "ml_trained": True,
            "ml_pipeline": pipeline,
            "ml_results": results,
            "explainer": explainer,
            "explainer_ready": explainer_ready,
        })

        st.toast("ML models trained: conflict, recommendation & delay predictors ready.", icon="🧠")
    except Exception as exc:  # noqa: BLE001
        st.error(f"ML training failed: {exc}")


def handle_prediction():
    """Generate predictions + explanations for the flight selected in the sidebar."""
    if not st.session_state.get("ml_trained"):
        st.warning("Train the ML models before requesting a prediction.")
        return

    flight_id = st.session_state.get("selected_flight_id")
    flights = st.session_state.get("flights", [])
    flight = next((f for f in flights if f.flight_id == flight_id), None)

    if not flight:
        st.warning("Select a flight in the sidebar first.")
        return

    try:
        gates = st.session_state.get("gates", [])
        gate_dict = {g.gate_id: g for g in gates}
        pipeline = st.session_state["ml_pipeline"]

        predictions = pipeline.predict(flight)
        rec_gate = gate_dict.get(predictions.get("recommended_gate"))
        if rec_gate is not None:
            predictions["conflict_probability"] = pipeline.conflict_predictor.predict_conflict_probability(
                flight, rec_gate
            )

        explanations = {}
        explainer = st.session_state.get("explainer")
        if explainer is not None:
            if predictions.get("recommended_gate"):
                explanations["gate_selection"] = explainer.explain_gate_selection(
                    flight, predictions["recommended_gate"], gates
                )
            if rec_gate is not None:
                explanations["conflict"] = explainer.explain_conflict_probability(
                    flight, rec_gate, predictions.get("conflict_probability", 0.0)
                )
            explanations["delay"] = explainer.explain_delay_prediction(
                flight, predictions.get("predicted_delay", 0.0)
            )

        all_predictions = dict(st.session_state.get("predictions", {}))
        all_predictions[flight_id] = {"predictions": predictions, "explanations": explanations}
        st.session_state["predictions"] = all_predictions

        st.toast(f"Prediction ready for {flight.flight_number}.", icon="🔮")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Prediction failed: {exc}")


def handle_export():
    """Build the full CSV/PDF report bundle for whatever pipeline stages have run."""
    flights = st.session_state.get("flights")
    gates = st.session_state.get("gates")
    if not flights or not gates:
        st.warning("Generate flight data before exporting reports.")
        return

    try:
        reporter = ReportGenerator(flights, gates)
        reports = {}

        reports["Simulation Summary"] = reporter.generate_simulation_summary(
            simulation_results=st.session_state.get("simulation_results"),
            allocation_results=st.session_state.get("rule_based_summary"),
        )

        if st.session_state.get("optimized"):
            reports["Optimization Report"] = reporter.generate_optimization_report(
                naive_metrics=st.session_state.get("naive_summary", {}),
                optimized_metrics=st.session_state.get("optimization_metrics", {}),
                improvement_data=st.session_state.get("comparison", {}),
            )

        if st.session_state.get("conflicts_detected"):
            conflicts = st.session_state.get("conflicts", [])
            conflict_dicts = [asdict(c) for c in conflicts]
            reports["Conflict Report"] = reporter.generate_conflict_report(
                conflict_dicts, st.session_state.get("conflict_summary", {})
            )

        gate_utilization = st.session_state.get("optimization_metrics", {}).get("gate_utilization")
        if gate_utilization:
            flight_assignments = (
                st.session_state.get("optimized_assignments")
                or st.session_state.get("rule_based_assignments")
                or {}
            )
            reports["Gate Utilization Report"] = reporter.generate_utilization_report(
                gate_utilization, flight_assignments
            )

        if st.session_state.get("ml_trained"):
            reports["ML Performance Report"] = reporter.generate_ml_performance_report(
                st.session_state.get("ml_results", {})
            )

        export_bundle = {}
        for name, report in reports.items():
            file_stub = name.lower().replace(" ", "_")
            export_bundle[name] = {
                "report": report,
                "csv": reporter.export_to_csv(report, file_stub),
                "pdf": reporter.export_to_pdf(report, f"{file_stub}.pdf"),
            }

        st.session_state["export_data"] = export_bundle
        st.toast(f"Prepared {len(export_bundle)} report(s) — download them from the Reports tab.", icon="📤")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Report export failed: {exc}")
