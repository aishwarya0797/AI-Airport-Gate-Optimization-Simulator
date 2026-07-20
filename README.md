# GateOptimizer Sim

## AI-Powered Airport Gate Allocation Decision Support System

**Developed for Airport Authority of India (AAI)**

## Overview

GateOptimizer Sim is a professional web application designed to help Airport Operations Staff efficiently:

- Assign aircraft to gates
- Minimize conflicts
- Reduce passenger walking distance
- Improve gate utilization
- Simulate different airport operational scenarios

## Features

### Core Capabilities

- **Synthetic Data Generator**: Generates realistic flight schedules, aircraft data, passenger counts, and weather conditions
- **Airport Layout**: Visual representation of terminals and gates with coordinate-based distance calculations
- **Simulation Engine**: Real-time simulation of daily airport operations
- **Gate Allocation**: Rule-based allocation following airport operational rules
- **Conflict Detection**: Identifies schedule overlaps, size mismatches, and delay-induced conflicts
- **Optimization Engine**: OR-Tools powered optimization for walking distance and utilization
- **Machine Learning**: Predictive models for conflicts, gate recommendations, and delays
- **Explainable AI**: SHAP-based explanations for all AI predictions
- **Interactive Dashboard**: Professional dark-themed Streamlit interface

### Scenarios Supported

- Normal Operations
- Peak Hour Traffic
- Adverse Weather (Rain, Fog, Thunderstorm, Snow)
- Gate Closure
- Emergency Aircraft
- VIP Flights
- Heavy Delay Conditions

## Local Installation

```bash
cd GateOptimizerSim
pip install -r requirements.txt
```

## Running Locally

```bash
streamlit run dashboard/app.py
```

## Deploy to Streamlit Cloud

1. Push this project to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with your GitHub account
4. Click "New app"
5. Select your repository and set:
   - **Main file path**: `dashboard/app.py`
   - **Python version**: 3.11 or higher
6. Click "Deploy"

## Project Structure

```
GateOptimizerSim/
├── dashboard/
│   └── app.py              # Main Streamlit dashboard
├── generator/
│   └── data_generator.py   # Synthetic data generation
├── simulation/
│   ├── airport_layout.py   # Airport layout and distances
│   └── simulation_engine.py# Daily operations simulation
├── allocation/
│   ├── gate_allocator.py   # Rule-based gate allocation
│   └── conflict_detector.py# Conflict detection
├── optimization/
│   └── optimizer.py        # OR-Tools optimization
├── ml/
│   ├── predictor.py        # ML prediction models
│   └── explainer.py        # Explainable AI with SHAP
├── visualization/
│   └── charts.py           # Plotly visualizations
├── reports/
│   └── report_generator.py # Report generation
├── utils/
│   └── config.py           # Configuration settings
├── .streamlit/
│   └── config.toml         # Streamlit configuration
├── requirements.txt
└── README.md
```

## Usage Guide

1. **Generate Simulation**: Select number of flights, weather, and scenario. Click "Generate"
2. **Allocate Gates**: Click "Allocate" to assign gates using rule-based allocation
3. **Optimize**: Click "Optimize" to run OR-Tools optimization
4. **Train AI**: Click "Train AI" to train ML models on simulation data
5. **Predict**: Select a flight and generate AI predictions with explanations
6. **Export Reports**: Download CSV or PDF reports

## Technology Stack

- **Language**: Python 3.8+
- **Frontend**: Streamlit
- **Visualization**: Plotly
- **Optimization**: OR-Tools
- **Machine Learning**: Scikit-learn, SHAP
- **Reporting**: FPDF

## Target Users

- Airport Operations Staff
- Airport Planning Team
- Airport Duty Manager
- Apron Management Team
- Training & Simulation Team

## Note

This application uses 100% synthetic data. No confidential airport operational information is required. The architecture is designed for easy replacement of synthetic data with real airport APIs or databases.

## License

Developed as an internship project for Airport Authority of India (AAI).
