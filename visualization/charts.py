"""
Visualization Module.

Creates interactive visualizations for:
- Airport layout
- Gate heatmap
- Flight timeline
- Delay charts
- Gate utilization
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

from generator.data_generator import Flight, Gate
from simulation.airport_layout import AirportLayout


def _apply_dark_theme(fig):
    """Apply dark theme to a plotly figure."""
    fig.update_layout(
        paper_bgcolor='#0d1421',
        plot_bgcolor='#0d1421'
    )
    fig.update_xaxes(tickfont=dict(color='#a0aec0'), title_font=dict(color='#a0aec0'))
    fig.update_yaxes(tickfont=dict(color='#a0aec0'), title_font=dict(color='#a0aec0'))
    return fig


class AirportVisualizer:
    """Creates airport layout visualizations."""

    def __init__(self, layout: AirportLayout):
        self.layout = layout

    def create_airport_layout_plot(self, gate_statuses: Dict[str, str] = None,
                                     flight_positions: Dict[str, Tuple[int, int]] = None) -> go.Figure:
        """Create interactive airport layout visualization."""
        fig = go.Figure()

        max_x, max_y = self.layout.get_layout_bounds()

        # Draw terminal backgrounds
        terminal_colors = ['#1a365d', '#2d3748', '#4a5568']

        for terminal_id in range(1, self.layout.num_terminals + 1):
            center_y = 50 + (terminal_id - 1) * 200
            fig.add_shape(
                type="rect",
                x0=0, y0=center_y - 60,
                x1=max_x, y1=center_y + 60,
                fillcolor=terminal_colors[(terminal_id - 1) % len(terminal_colors)],
                opacity=0.3,
                line=dict(color='#4a5568', width=1),
                layer='below'
            )
            fig.add_annotation(
                x=-50, y=center_y,
                text=f"Terminal {terminal_id}",
                showarrow=False,
                font=dict(color='#63b3ed', size=12)
            )

        # Draw gates
        gate_sizes = {'small': 20, 'medium': 30, 'large': 40}
        size_colors = {'small': '#48bb78', 'medium': '#ed8936', 'large': '#e53e3e'}
        status_colors = {
            'available': '#48bb78',
            'occupied': '#e53e3e',
            'reserved': '#ed8936'
        }

        for gate_id, gate_info in self.layout.gates.items():
            x = gate_info['x_coord']
            y = gate_info['y_coord']
            size = gate_sizes.get(gate_info['size'], 25)

            if gate_statuses and gate_id in gate_statuses:
                color = status_colors.get(gate_statuses[gate_id], '#a0aec0')
            else:
                color = size_colors.get(gate_info['size'], '#a0aec0')

            fig.add_shape(
                type="circle",
                x0=x - size, y0=y - size,
                x1=x + size, y1=y + size,
                fillcolor=color,
                line=dict(color='#2d3748', width=2),
                opacity=0.8
            )

            fig.add_annotation(
                x=x, y=y,
                text=gate_id,
                showarrow=False,
                font=dict(color='white', size=10, family='Arial Black')
            )

        fig.update_layout(
            title=dict(text="Airport Gate Layout", font=dict(color='#63b3ed', size=18)),
            showlegend=False,
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, range=[-100, max_x + 100]),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, range=[-50, max_y + 100]),
            plot_bgcolor='#0d1421',
            paper_bgcolor='#0d1421',
            margin=dict(l=20, r=20, t=50, b=20),
            height=600
        )

        return fig

    def create_utilization_heatmap(self, utilization_data: Dict[str, float]) -> go.Figure:
        """Create gate utilization heatmap."""
        gate_ids = sorted(utilization_data.keys(), key=lambda x: int(x[1:]))
        values = [utilization_data.get(g, 0) for g in gate_ids]

        n_terminals = self.layout.num_terminals
        gates_per_terminal = max(1, len(gate_ids) // n_terminals)

        z_data = []
        for t in range(n_terminals):
            row = values[t * gates_per_terminal:(t + 1) * gates_per_terminal]
            while len(row) < gates_per_terminal:
                row.append(0)
            z_data.append(row)

        fig = go.Figure(data=go.Heatmap(
            z=z_data,
            colorscale=[[0, '#1a365d'], [0.3, '#2b6cb0'], [0.6, '#ed8936'], [0.8, '#e53e3e'], [1, '#c53030']],
            colorbar=dict(title="Utilization %", x=1.02),
            hovertemplate="Gate: %{text}<br>Utilization: %{z:.1f}%<extra></extra>",
            text=[[g for g in gate_ids[i * gates_per_terminal:(i + 1) * gates_per_terminal]] for i in range(n_terminals)]
        ))

        fig.update_layout(
            title=dict(text="Gate Utilization Heatmap", font=dict(color='#63b3ed', size=16)),
            xaxis=dict(title="Gate Position"),
            yaxis=dict(title="Terminal", tickvals=list(range(n_terminals)), ticktext=[f"Terminal {i+1}" for i in range(n_terminals)]),
            plot_bgcolor='#0d1421',
            paper_bgcolor='#0d1421',
            height=300
        )
        _apply_dark_theme(fig)

        return fig


class FlightVisualizer:
    """Creates flight-related visualizations."""

    @staticmethod
    def create_flight_timeline(flights: List[Flight]) -> go.Figure:
        """Create flight timeline Gantt chart."""
        data = []
        for flight in flights:
            if flight.assigned_gate:
                departure = flight.arrival_time + timedelta(minutes=flight.turnaround_time + flight.delay)
                data.append({
                    'Flight': flight.flight_number,
                    'Gate': flight.assigned_gate,
                    'Start': flight.arrival_time,
                    'Finish': departure,
                    'Airline': flight.airline,
                    'Size': flight.aircraft_size,
                    'Delay': flight.delay
                })

        df = pd.DataFrame(data)
        if df.empty:
            fig = go.Figure()
            _apply_dark_theme(fig)
            return fig

        size_colors = {'small': '#48bb78', 'medium': '#ed8936', 'large': '#e53e3e'}
        fig = go.Figure()

        for idx, row in df.iterrows():
            color = size_colors.get(row['Size'], '#a0aec0')
            delay_text = f" (+{row['Delay']}min delay)" if row['Delay'] > 0 else ""

            fig.add_trace(go.Bar(
                x=[(row['Finish'] - row['Start']).total_seconds() / 3600],
                y=[row['Gate']],
                base=[row['Start'].hour + row['Start'].minute / 60],
                orientation='h',
                marker=dict(color=color, line=dict(color='#2d3748', width=1)),
                text=f"{row['Flight']}{delay_text}",
                textposition='inside',
                textfont=dict(color='white', size=9),
                hovertemplate=f"<b>{row['Flight']}</b><br>Airline: {row['Airline']}<br>Gate: {row['Gate']}<extra></extra>",
                showlegend=False
            ))

        fig.update_layout(
            title=dict(text="Flight Timeline by Gate", font=dict(color='#63b3ed', size=16)),
            xaxis=dict(title="Hour of Day", range=[0, 24]),
            yaxis=dict(title="Gate"),
            barmode='overlay',
            plot_bgcolor='#0d1421',
            paper_bgcolor='#0d1421',
            height=400,
            margin=dict(l=60, r=20, t=50, b=40)
        )
        _apply_dark_theme(fig)

        return fig

    @staticmethod
    def create_delay_distribution(delays: List[int]) -> go.Figure:
        """Create delay distribution histogram."""
        fig = go.Figure()

        fig.add_trace(go.Histogram(
            x=delays,
            nbinsx=20,
            marker=dict(color='#ed8936', line=dict(color='#dd6b20', width=1)),
            opacity=0.8,
            hovertemplate="Delay: %{x} min<br>Count: %{y}<extra></extra>"
        ))

        if delays:
            mean_delay = np.mean(delays)
            fig.add_vline(x=mean_delay, line=dict(color='#48bb78', width=2, dash='dash'))

        fig.update_layout(
            title=dict(text="Flight Delay Distribution", font=dict(color='#63b3ed', size=16)),
            xaxis=dict(title="Delay (minutes)"),
            yaxis=dict(title="Number of Flights"),
            plot_bgcolor='#0d1421',
            paper_bgcolor='#0d1421',
            height=300
        )
        _apply_dark_theme(fig)

        return fig

    @staticmethod
    def create_airline_pie_chart(flights: List[Flight]) -> go.Figure:
        """Create pie chart of flights by airline."""
        airline_counts = {}
        for flight in flights:
            airline_counts[flight.airline] = airline_counts.get(flight.airline, 0) + 1

        fig = go.Figure(data=go.Pie(
            labels=list(airline_counts.keys()),
            values=list(airline_counts.values()),
            hole=0.4,
            marker=dict(colors=px.colors.qualitative.Set2),
            textposition='inside',
            textinfo='percent+label',
            textfont=dict(color='white', size=10),
            hovertemplate="<b>%{label}</b><br>Flights: %{value}<extra></extra>"
        ))

        fig.update_layout(
            title=dict(text="Flights by Airline", font=dict(color='#63b3ed', size=16)),
            plot_bgcolor='#0d1421',
            paper_bgcolor='#0d1421',
            height=350,
            showlegend=True,
            legend=dict(font=dict(color='#a0aec0'), orientation='h', y=-0.1)
        )

        return fig


class MetricsVisualizer:
    """Creates metric and statistics visualizations."""

    @staticmethod
    def create_utilization_bar_chart(gate_utilization: Dict[str, float]) -> go.Figure:
        """Create gate utilization bar chart."""
        gates = sorted(gate_utilization.keys(), key=lambda x: int(x[1:]))
        values = [gate_utilization.get(g, 0) for g in gates]

        colors = []
        for v in values:
            if v < 30:
                colors.append('#48bb78')
            elif v < 60:
                colors.append('#ed8936')
            else:
                colors.append('#e53e3e')

        fig = go.Figure(data=go.Bar(
            x=gates,
            y=values,
            marker=dict(color=colors, line=dict(color='#2d3748', width=1)),
            text=[f"{v:.1f}%" for v in values],
            textposition='outside',
            textfont=dict(color='#a0aec0', size=10),
            hovertemplate="Gate: %{x}<br>Utilization: %{y:.1f}%<extra></extra>"
        ))

        fig.update_layout(
            title=dict(text="Gate Utilization", font=dict(color='#63b3ed', size=16)),
            xaxis=dict(title="Gate"),
            yaxis=dict(title="Utilization %", range=[0, 100]),
            plot_bgcolor='#0d1421',
            paper_bgcolor='#0d1421',
            height=350
        )
        _apply_dark_theme(fig)

        return fig

    @staticmethod
    def create_optimization_comparison(naive_metrics: Dict, optimized_metrics: Dict) -> go.Figure:
        """Create comparison chart between naive and optimized allocations."""
        categories = ['Walking Distance', 'Gate Utilization', 'Conflicts', 'Efficiency Score']

        naive_values = [
            naive_metrics.get('total_walking_distance', 1000) / 100,
            naive_metrics.get('average_gate_utilization', 50),
            naive_metrics.get('total_conflicts', 5) * 20 if naive_metrics.get('total_conflicts', 0) > 0 else 0,
            max(0, 100 - naive_metrics.get('total_conflicts', 5) * 5)
        ]

        opt_values = [
            optimized_metrics.get('total_walking_distance', 1000) / 100,
            optimized_metrics.get('average_gate_utilization', 50),
            optimized_metrics.get('total_conflicts', 5) * 20 if optimized_metrics.get('total_conflicts', 0) > 0 else 0,
            max(0, 100 - optimized_metrics.get('total_conflicts', 5) * 5)
        ]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            name='Naive',
            x=categories,
            y=naive_values,
            marker_color='#718096',
            text=[f"{v:.1f}" for v in naive_values],
            textposition='auto'
        ))

        fig.add_trace(go.Bar(
            name='Optimized',
            x=categories,
            y=opt_values,
            marker_color='#48bb78',
            text=[f"{v:.1f}" for v in opt_values],
            textposition='auto'
        ))

        fig.update_layout(
            title=dict(text="Naive vs Optimized Allocation Comparison", font=dict(color='#63b3ed', size=16)),
            barmode='group',
            plot_bgcolor='#0d1421',
            paper_bgcolor='#0d1421',
            height=400,
            legend=dict(font=dict(color='#a0aec0'), orientation='h', y=1.02)
        )
        _apply_dark_theme(fig)

        return fig


class ConflictVisualizer:
    """Creates conflict-related visualizations."""

    @staticmethod
    def create_conflict_timeline(conflicts: List[Dict]) -> go.Figure:
        """Create timeline of conflicts."""
        if not conflicts:
            fig = go.Figure()
            _apply_dark_theme(fig)
            return fig

        df = pd.DataFrame(conflicts)

        severity_colors = {
            'critical': '#e53e3e',
            'high': '#ed8936',
            'medium': '#ecc94b',
            'low': '#48bb78'
        }

        fig = go.Figure()

        for severity in ['critical', 'high', 'medium', 'low']:
            severity_conflicts = df[df['severity'] == severity] if 'severity' in df.columns else pd.DataFrame()

            if not severity_conflicts.empty:
                fig.add_trace(go.Scatter(
                    x=severity_conflicts['time'] if 'time' in severity_conflicts.columns else [],
                    y=[1] * len(severity_conflicts),
                    mode='markers',
                    marker=dict(color=severity_colors.get(severity, '#a0aec0'), size=15 if severity == 'critical' else 12),
                    name=severity.capitalize(),
                    text=severity_conflicts.get('description', '') if 'description' in severity_conflicts.columns else [],
                    hovertemplate="<b>%{text}</b><extra></extra>"
                ))

        fig.update_layout(
            title=dict(text="Conflict Timeline", font=dict(color='#63b3ed', size=16)),
            xaxis=dict(title="Time"),
            yaxis=dict(showticklabels=False, showgrid=False),
            plot_bgcolor='#0d1421',
            paper_bgcolor='#0d1421',
            height=250,
            showlegend=True,
            legend=dict(font=dict(color='#a0aec0'))
        )

        return fig

    @staticmethod
    def create_conflict_summary_chart(conflict_data: Dict) -> go.Figure:
        """Create conflict summary visualization."""
        fig = make_subplots(rows=1, cols=2, specs=[[{"type": "pie"}, {"type": "bar"}]], horizontal_spacing=0.15)

        by_type = conflict_data.get('by_type', {})
        if by_type:
            fig.add_trace(go.Pie(
                labels=list(by_type.keys()),
                values=list(by_type.values()),
                hole=0.4,
                marker=dict(colors=px.colors.qualitative.Set2),
                textfont=dict(color='white', size=10),
                showlegend=False
            ), row=1, col=1)

        by_severity = conflict_data.get('by_severity', {})
        if by_severity:
            severity_colors = {'critical': '#e53e3e', 'high': '#ed8936', 'medium': '#ecc94b', 'low': '#48bb78'}
            severities = ['critical', 'high', 'medium', 'low']
            values = [by_severity.get(s, 0) for s in severities]
            colors = [severity_colors[s] for s in severities]

            fig.add_trace(go.Bar(
                x=severities,
                y=values,
                marker_color=colors,
                text=values,
                textposition='auto'
            ), row=1, col=2)

        fig.update_layout(
            title=dict(text="Conflict Analysis", font=dict(color='#63b3ed', size=16)),
            plot_bgcolor='#0d1421',
            paper_bgcolor='#0d1421',
            height=350,
            annotations=[
                dict(text="By Type", x=0.18, y=1.05, font=dict(color='#a0aec0'), showarrow=False),
                dict(text="By Severity", x=0.82, y=1.05, font=dict(color='#a0aec0'), showarrow=False)
            ]
        )

        return fig
