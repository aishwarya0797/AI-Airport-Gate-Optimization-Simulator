"""
AI Predictions & Explainable AI tab.
"""

import pandas as pd
import streamlit as st

from dashboard.utils import require_flights, chart_guide, render_html


def _risk_color(risk: str) -> str:
    return {
        "low": "#48bb78",
        "medium": "#ecc94b",
        "high": "#ed8936",
        "critical": "#e53e3e",
    }.get(risk, "#a0aec0")


def render_ml_predictions():
    """Render trained-model performance and the current flight's ML predictions."""
    st.markdown("##### 🧠 Model Performance")

    if not require_flights():
        return

    if not st.session_state.get("ml_trained"):
        st.info("Click **Train ML Models** in the sidebar to fit the conflict, "
                 "gate-recommendation, and delay-prediction models.")
        return

    ml_results = st.session_state.get("ml_results", {})
    conflict_res = ml_results.get("conflict", {})
    rec_res = ml_results.get("recommendation", {})
    delay_res = ml_results.get("delay", {})

    c1, c2, c3 = st.columns(3)
    c1.metric("Conflict Model Accuracy", f"{conflict_res.get('accuracy', 0):.1%}",
               help=f"5-fold CV mean: {conflict_res.get('cv_mean', 0):.1%}")
    c2.metric("Gate Recommender Accuracy", f"{rec_res.get('accuracy', 0):.1%}",
               help=f"Trained across {rec_res.get('num_gates', 0)} gates")
    c3.metric("Delay Model RMSE", f"{delay_res.get('rmse', 0):.1f} min",
               help=f"Mean historical delay: {delay_res.get('mean_delay', 0):.1f} min")

    chart_guide(
        "Three separate machine-learning models get trained here, each answering a different "
        "question:\n"
        "- **Conflict Model**: how likely is a gate double-booking? (Accuracy = % of past cases "
        "it correctly predicted)\n"
        "- **Gate Recommender**: which gate should a flight get? (Accuracy = % of the time it "
        "picks the same gate a human/rule-based planner would)\n"
        "- **Delay Model**: how many minutes will a flight be delayed? (RMSE = typical size of "
        "its prediction error, in minutes — lower is better)"
    )

    importance = conflict_res.get("feature_importance", {})
    if importance:
        st.markdown("###### Top Conflict-Risk Features")
        importance_df = (
            pd.Series(importance).sort_values(ascending=False).head(8).rename("Importance").to_frame()
        )
        st.bar_chart(importance_df)

        chart_guide(
            "This shows which factors the conflict-risk model actually relies on most when "
            "making its predictions — for example, if \"turnaround_time\" has the tallest bar, "
            "it means how long a flight sits at its gate is the single biggest driver of conflict "
            "risk in this data. Taller bar = more influence on the model's decisions."
        )

    st.markdown("---")
    st.markdown("##### 🔮 Selected Flight Prediction")

    flight_id = st.session_state.get("selected_flight_id")
    flights = st.session_state.get("flights", [])
    flight = next((f for f in flights if f.flight_id == flight_id), None)

    if not flight:
        st.caption("Select a flight in the sidebar to see predictions.")
        return

    prediction_entry = st.session_state.get("predictions", {}).get(flight_id)
    if not prediction_entry:
        st.info(f"Click **Predict & Explain** in the sidebar to generate a forecast for {flight.flight_number}.")
        return

    predictions = prediction_entry["predictions"]
    risk = predictions.get("delay_risk", "low")

    st.markdown(f"**Flight {flight.flight_number}** ({flight.airline}, {flight.aircraft_type})")

    p1, p2, p3 = st.columns(3)
    p1.metric("Recommended Gate", predictions.get("recommended_gate", "—"))
    p2.metric("Recommendation Confidence", f"{predictions.get('recommendation_confidence', 0):.1%}")
    p3.metric("Conflict Probability", f"{predictions.get('conflict_probability', 0):.1%}")

    render_html(
        f"""
        <div style="background-color:{_risk_color(risk)}22; border:1px solid {_risk_color(risk)};
                    border-radius:8px; padding:10px 16px; margin-top:8px;">
            <b style="color:{_risk_color(risk)};">Delay Risk: {risk.upper()}</b>
            &nbsp;—&nbsp; Predicted delay: {predictions.get('predicted_delay', 0):.0f} minutes
        </div>
        """
    )

    chart_guide(
        "This is the AI's forecast for the one flight you picked in the sidebar:\n"
        "- **Recommended Gate**: which gate the model thinks is the best fit for this flight\n"
        "- **Recommendation Confidence**: how sure the model is about that gate pick\n"
        "- **Conflict Probability**: the chance this flight ends up double-booked at that gate\n"
        "- **Delay Risk banner**: a plain-language risk level plus the predicted delay in minutes\n\n"
        "To see *why* it made these calls, scroll down to the **Explainable AI** section below."
    )


def render_explainable_ai():
    """Render human-readable SHAP-style explanations for the current prediction."""
    st.markdown("##### 🔍 Explainable AI")

    if not require_flights():
        return

    if not st.session_state.get("ml_trained"):
        st.info("Train the ML models first, then run a prediction to see explanations here.")
        return

    flight_id = st.session_state.get("selected_flight_id")
    prediction_entry = st.session_state.get("predictions", {}).get(flight_id)

    if not prediction_entry:
        st.caption("Run **Predict & Explain** in the sidebar to populate this panel.")
        return

    explanations = prediction_entry.get("explanations", {})
    if not explanations:
        st.caption("No explanation data available for this flight.")
        return

    chart_guide(
        "\"Explainable AI\" (XAI) means the model doesn't just give you an answer — it also "
        "tells you *why*, in plain language, instead of being a mysterious black box.\n\n"
        "Each section below covers one prediction and lists the specific factors that pushed "
        "the model toward its answer:\n"
        "- 🟢 **Green** = this factor pushed *for* the outcome (e.g. made a conflict more likely)\n"
        "- 🔴 **Red** = this factor pushed *against* it\n"
        "- ⚪ **Grey** = neutral / minor effect\n\n"
        "The progress bar at the bottom of each section is the model's own confidence in that "
        "specific explanation."
    )

    titles = {
        "gate_selection": "Why this gate?",
        "conflict": "Why this conflict risk?",
        "delay": "Why this delay estimate?",
    }

    for key, title in titles.items():
        explanation = explanations.get(key)
        if not explanation:
            continue
        with st.expander(f"**{title}**", expanded=(key == "gate_selection")):
            st.markdown(f"*{explanation.main_reason}*")
            for factor_name, value, description in explanation.contributing_factors:
                icon = "🟢" if value > 0 else "🔴" if value < 0 else "⚪"
                st.markdown(f"{icon} {description}")
            st.progress(min(1.0, max(0.0, explanation.confidence)))
            st.caption(f"Confidence: {explanation.confidence:.1%}")
