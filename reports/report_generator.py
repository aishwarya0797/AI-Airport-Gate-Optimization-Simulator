"""
Reports Module.

Generates comprehensive reports:
- Simulation Summary
- Optimization Summary
- Conflict Report
- Gate Utilization Report
- ML Performance Report

Exports: CSV, PDF
"""

from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
import io
import base64

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

from generator.data_generator import Flight, Gate


@dataclass
class ReportData:
    """Container for report data."""
    report_type: str
    generated_at: datetime
    data: Dict
    summary: str


class PDFReport(FPDF):
    """Custom PDF generator with dark theme styling."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(30, 54, 93)  # Dark blue
        self.cell(0, 10, 'GateOptimizer Sim - Airport Operations Report', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()} | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 0, 'C')

    def chapter_title(self, title: str):
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(54, 54, 54)
        self.cell(0, 8, title, 0, 1, 'L')
        self.ln(2)

    def chapter_body(self, content: str):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(74, 74, 74)
        self.multi_cell(0, 5, content)
        self.ln(3)

    def add_table(self, headers: List[str], data: List[List[str]], col_widths: List[int] = None):
        """Add a formatted table."""
        if col_widths is None:
            col_widths = [190 // len(headers)] * len(headers)

        # Header
        self.set_font('Helvetica', 'B', 10)
        self.set_fill_color(30, 54, 93)
        self.set_text_color(255, 255, 255)

        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8, str(header), 1, 0, 'C', True)
        self.ln()

        # Data rows
        self.set_font('Helvetica', '', 9)
        self.set_text_color(54, 54, 54)

        fill = False
        for row in data:
            if fill:
                self.set_fill_color(240, 240, 240)
            else:
                self.set_fill_color(255, 255, 255)

            for i, cell in enumerate(row):
                self.cell(col_widths[i], 7, str(cell)[:25], 1, 0, 'C', True)
            self.ln()
            fill = not fill


class ReportGenerator:
    """Generate various operational reports."""

    def __init__(self, flights: List[Flight], gates: List[Gate]):
        self.flights = flights
        self.gates = gates
        self.flight_df = None
        self.gate_df = None

    def _create_flight_dataframe(self) -> pd.DataFrame:
        """Create DataFrame from flights."""
        data = []
        for f in self.flights:
            data.append({
                'Flight ID': f.flight_id,
                'Flight Number': f.flight_number,
                'Airline': f.airline,
                'Aircraft Type': f.aircraft_type,
                'Aircraft Size': f.aircraft_size,
                'Arrival Time': f.arrival_time.strftime('%Y-%m-%d %H:%M'),
                'Departure Time': (f.arrival_time + pd.Timedelta(minutes=f.turnaround_time + f.delay)).strftime('%Y-%m-%d %H:%M'),
                'Passengers': f.passenger_count,
                'Turnaround (min)': f.turnaround_time,
                'Delay (min)': f.delay,
                'Gate': f.assigned_gate if hasattr(f, 'assigned_gate') else '',
                'Origin': f.origin,
                'Destination': f.destination,
                'Status': f.status
            })
        self.flight_df = pd.DataFrame(data)
        return self.flight_df

    def _create_gate_dataframe(self) -> pd.DataFrame:
        """Create DataFrame from gates."""
        data = []
        for g in self.gates:
            data.append({
                'Gate ID': g.gate_id,
                'Size': g.gate_size,
                'Terminal': g.terminal,
                'X Coord': g.x_coord,
                'Y Coord': g.y_coord,
                'Available': g.is_available,
                'Current Flight': g.current_flight or ''
            })
        self.gate_df = pd.DataFrame(data)
        return self.gate_df

    def generate_simulation_summary(self, simulation_results: Dict = None,
                                     allocation_results: Dict = None) -> ReportData:
        """Generate simulation summary report."""
        self._create_flight_dataframe()
        self._create_gate_dataframe()

        # Calculate statistics
        total_flights = len(self.flights)
        total_passengers = sum(f.passenger_count for f in self.flights)
        avg_turnaround = np.mean([f.turnaround_time for f in self.flights])
        avg_delay = np.mean([f.delay for f in self.flights])
        flights_by_size = {}
        for f in self.flights:
            flights_by_size[f.aircraft_size] = flights_by_size.get(f.aircraft_size, 0) + 1

        # Assigned flights
        assigned_flights = sum(1 for f in self.flights if hasattr(f, 'assigned_gate') and f.assigned_gate)

        data = {
            'total_flights': total_flights,
            'total_passengers': total_passengers,
            'avg_turnaround_minutes': avg_turnaround,
            'avg_delay_minutes': avg_delay,
            'flights_by_size': flights_by_size,
            'assigned_flights': assigned_flights,
            'simulation_results': simulation_results,
            'allocation_results': allocation_results
        }

        summary = f"""
        Simulation Summary Report
        =========================

        Total Flights Processed: {total_flights}
        Total Passengers: {total_passengers:,}
        Average Turnaround Time: {avg_turnaround:.1f} minutes
        Average Delay: {avg_delay:.1f} minutes
        Successfully Assigned Flights: {assigned_flights}/{total_flights}

        Aircraft Size Distribution:
          - Small: {flights_by_size.get('small', 0)} flights
          - Medium: {flights_by_size.get('medium', 0)} flights
          - Large: {flights_by_size.get('large', 0)} flights

        Total Gates: {len(self.gates)}
        """

        return ReportData(
            report_type='simulation_summary',
            generated_at=datetime.now(),
            data=data,
            summary=summary
        )

    def generate_optimization_report(self, naive_metrics: Dict,
                                       optimized_metrics: Dict,
                                       improvement_data: Dict) -> ReportData:
        """Generate optimization comparison report."""
        data = {
            'naive_metrics': naive_metrics,
            'optimized_metrics': optimized_metrics,
            'improvement': improvement_data
        }

        improvement_pct = improvement_data.get('distance_improvement_percent', 0)
        conflict_reduction = naive_metrics.get('total_conflicts', 0) - optimized_metrics.get('total_conflicts', 0)

        summary = f"""
        Optimization Performance Report
        ================================

        Walking Distance Optimization:
          - Naive Total: {naive_metrics.get('total_walking_distance', 0):,.0f}
          - Optimized Total: {optimized_metrics.get('total_walking_distance', 0):,.0f}
          - Improvement: {improvement_pct:.1f}%

        Conflict Reduction:
          - Naive Conflicts: {naive_metrics.get('total_conflicts', 0)}
          - Optimized Conflicts: {optimized_metrics.get('total_conflicts', 0)}
          - Reduction: {conflict_reduction} conflicts

        Gate Utilization:
          - Naive Average: {naive_metrics.get('average_gate_utilization', 0):.1f}%
          - Optimized Average: {optimized_metrics.get('average_gate_utilization', 0):.1f}%
        """

        return ReportData(
            report_type='optimization_summary',
            generated_at=datetime.now(),
            data=data,
            summary=summary
        )

    def generate_conflict_report(self, conflicts: List[Dict],
                                   conflict_summary: Dict) -> ReportData:
        """Generate detailed conflict analysis report."""
        data = {
            'conflicts': conflicts,
            'summary': conflict_summary,
            'total_conflicts': len(conflicts)
        }

        summary = f"""
        Conflict Analysis Report
        =========================

        Total Conflicts Detected: {len(conflicts)}

        By Severity:
          - Critical: {conflict_summary.get('critical_count', 0)}
          - High: {conflict_summary.get('high_count', 0)}
          - Medium: {conflict_summary.get('medium_count', 0)}
          - Low: {conflict_summary.get('low_count', 0)}

        By Type:
          - Overlap: {conflict_summary.get('by_type', {}).get('overlap', 0)}
          - Size Mismatch: {conflict_summary.get('by_type', {}).get('size_mismatch', 0)}
          - Delay Conflict: {conflict_summary.get('by_type', {}).get('delay_conflict', 0)}
          - Double Booking: {conflict_summary.get('by_type', {}).get('double_booking', 0)}
        """

        return ReportData(
            report_type='conflict_analysis',
            generated_at=datetime.now(),
            data=data,
            summary=summary
        )

    def generate_utilization_report(self, gate_utilization: Dict[str, float],
                                      flight_assignments: Dict[str, str]) -> ReportData:
        """Generate gate utilization report."""
        # Calculate statistics
        avg_utilization = np.mean(list(gate_utilization.values()))
        max_utilization_gate = max(gate_utilization.items(), key=lambda x: x[1])
        min_utilization_gate = min(gate_utilization.items(), key=lambda x: x[1])

        # Count flights per gate
        flights_per_gate = {}
        for gate_id in flight_assignments.values():
            flights_per_gate[gate_id] = flights_per_gate.get(gate_id, 0) + 1

        data = {
            'gate_utilization': gate_utilization,
            'avg_utilization': avg_utilization,
            'max_utilization': max_utilization_gate,
            'min_utilization': min_utilization_gate,
            'flights_per_gate': flights_per_gate
        }

        summary = f"""
        Gate Utilization Report
        ========================

        Overall Statistics:
          - Average Utilization: {avg_utilization:.1f}%
          - Highest Utilized Gate: {max_utilization_gate[0]} ({max_utilization_gate[1]:.1f}%)
          - Lowest Utilized Gate: {min_utilization_gate[0]} ({min_utilization_gate[1]:.1f}%)

        Utilization by Gate:
        {self._format_gate_utilization(gate_utilization, flights_per_gate)}
        """

        return ReportData(
            report_type='gate_utilization',
            generated_at=datetime.now(),
            data=data,
            summary=summary
        )

    def generate_ml_performance_report(self, ml_results: Dict) -> ReportData:
        """Generate ML model performance report."""
        summary = f"""
        Machine Learning Performance Report
        ====================================

        Conflict Prediction Model:
          - Training Accuracy: {ml_results.get('conflict', {}).get('accuracy', 0):.2%}
          - Cross-Validation Score: {ml_results.get('conflict', {}).get('cv_mean', 0):.2%}

        Gate Recommendation Model:
          - Recommendation Accuracy: {ml_results.get('recommendation', {}).get('accuracy', 0):.2%}
          - Number of Gates: {ml_results.get('recommendation', {}).get('num_gates', 0)}

        Delay Prediction Model:
          - RMSE: {ml_results.get('delay', {}).get('rmse', 0):.2f} minutes
          - Mean Delay: {ml_results.get('delay', {}).get('mean_delay', 0):.1f} minutes
        """

        return ReportData(
            report_type='ml_performance',
            generated_at=datetime.now(),
            data=ml_results,
            summary=summary
        )

    def _format_gate_utilization(self, utilization: Dict, flights: Dict) -> str:
        """Format gate utilization for report."""
        lines = []
        for gate_id in sorted(utilization.keys(), key=lambda x: int(x[1:])):
            util = utilization[gate_id]
            flight_count = flights.get(gate_id, 0)
            lines.append(f"          {gate_id}: {util:.1f}% ({flight_count} flights)")
        return "\n".join(lines)

    def export_to_csv(self, report: ReportData, filename: str) -> str:
        """Export report data to CSV."""
        output = io.StringIO()

        if report.report_type == 'simulation_summary':
            if self.flight_df is not None and not self.flight_df.empty:
                self.flight_df.to_csv(output, index=False)
            else:
                self._dict_to_csv(report.data, output)

        elif report.report_type == 'conflict_analysis':
            if report.data.get('conflicts'):
                conflict_df = pd.DataFrame(report.data['conflicts'])
                conflict_df.to_csv(output, index=False)
            else:
                pd.DataFrame([{'total_conflicts': report.data.get('total_conflicts', 0)}]).to_csv(output, index=False)

        elif report.report_type == 'gate_utilization':
            util_df = pd.DataFrame([
                {'Gate ID': g, 'Utilization %': u, 'Flights': report.data['flights_per_gate'].get(g, 0)}
                for g, u in report.data['gate_utilization'].items()
            ])
            util_df.to_csv(output, index=False)

        elif report.report_type == 'optimization_summary':
            naive = report.data.get('naive_metrics', {})
            optimized = report.data.get('optimized_metrics', {})
            rows = []
            for metric in set(naive.keys()) | set(optimized.keys()):
                if isinstance(naive.get(metric), dict) or isinstance(optimized.get(metric), dict):
                    continue
                rows.append({
                    'Metric': metric,
                    'Naive': naive.get(metric, ''),
                    'Optimized': optimized.get(metric, ''),
                })
            pd.DataFrame(rows).to_csv(output, index=False)

        elif report.report_type == 'ml_performance':
            self._dict_to_csv(report.data, output)

        else:
            self._dict_to_csv(report.data, output)

        return output.getvalue()

    @staticmethod
    def _dict_to_csv(data: Dict, output: io.StringIO) -> None:
        """Fallback CSV writer: flattens a (possibly nested) dict to key/value rows."""
        rows = []

        def _flatten(prefix: str, value):
            if isinstance(value, dict):
                for k, v in value.items():
                    _flatten(f"{prefix}.{k}" if prefix else str(k), v)
            else:
                rows.append({'Metric': prefix, 'Value': value})

        _flatten('', data)
        pd.DataFrame(rows).to_csv(output, index=False)

    def export_to_pdf(self, report: ReportData, filename: str = 'report.pdf') -> bytes:
        """Export report to PDF."""
        if not FPDF_AVAILABLE:
            return b"PDF generation not available. Install fpdf package."

        pdf = PDFReport()
        pdf.add_page()

        # Report title
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(30, 54, 93)
        pdf.cell(0, 10, report.report_type.replace('_', ' ').title(), 0, 1, 'C')
        pdf.ln(5)

        # Generation timestamp
        pdf.set_font('Helvetica', 'I', 10)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 5, f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'R')
        pdf.ln(10)

        # Report summary
        pdf.chapter_title("Executive Summary")
        pdf.chapter_body(report.summary)

        # Add data tables based on report type
        if report.report_type == 'simulation_summary':
            pdf.chapter_title("Flight Statistics")
            data = report.data

            stats_data = [
                ['Total Flights', str(data['total_flights'])],
                ['Total Passengers', f"{data['total_passengers']:,}"],
                ['Avg Turnaround', f"{data['avg_turnaround_minutes']:.1f} min"],
                ['Avg Delay', f"{data['avg_delay_minutes']:.1f} min"],
                ['Assigned Flights', f"{data['assigned_flights']}/{data['total_flights']}"]
            ]

            pdf.add_table(['Metric', 'Value'], stats_data, [100, 90])

        elif report.report_type == 'conflict_analysis':
            pdf.chapter_title("Conflict Statistics")

            conflict_data = report.data
            summary = conflict_data.get('summary', {})

            severity_data = [
                ['Critical', str(summary.get('critical_count', 0))],
                ['High', str(summary.get('high_count', 0))],
                ['Medium', str(summary.get('medium_count', 0))],
                ['Low', str(summary.get('low_count', 0))]
            ]

            pdf.add_table(['Severity', 'Count'], severity_data, [100, 90])

        elif report.report_type == 'gate_utilization':
            pdf.chapter_title("Gate Utilization")

            util_data = report.data
            utilization = util_data.get('gate_utilization', {})
            flights_per_gate = util_data.get('flights_per_gate', {})

            gate_data = [
                [gate, f"{util:.1f}%", str(flights_per_gate.get(gate, 0))]
                for gate, util in sorted(utilization.items(), key=lambda x: int(x[0][1:]))
            ]

            pdf.add_table(['Gate', 'Utilization', 'Flights'], gate_data, [50, 80, 60])

        elif report.report_type == 'optimization_summary':
            pdf.chapter_title("Naive vs Optimized")
            naive = report.data.get('naive_metrics', {})
            optimized = report.data.get('optimized_metrics', {})

            comparison_data = [
                ['Total Walking Distance',
                 f"{naive.get('total_walking_distance', 0):,.0f}",
                 f"{optimized.get('total_walking_distance', 0):,.0f}"],
                ['Avg Gate Utilization',
                 f"{naive.get('average_gate_utilization', 0):.1f}%",
                 f"{optimized.get('average_gate_utilization', 0):.1f}%"],
                ['Total Conflicts',
                 str(naive.get('total_conflicts', 0)),
                 str(optimized.get('total_conflicts', 0))],
            ]
            pdf.add_table(['Metric', 'Naive', 'Optimized'], comparison_data, [90, 50, 50])

        elif report.report_type == 'ml_performance':
            pdf.chapter_title("Model Performance")
            ml = report.data
            perf_data = [
                ['Conflict Model Accuracy', f"{ml.get('conflict', {}).get('accuracy', 0):.1%}"],
                ['Recommendation Accuracy', f"{ml.get('recommendation', {}).get('accuracy', 0):.1%}"],
                ['Delay Model RMSE', f"{ml.get('delay', {}).get('rmse', 0):.2f} min"],
            ]
            pdf.add_table(['Model Metric', 'Value'], perf_data, [120, 70])

        # Get PDF bytes.
        # fpdf2 (the maintained successor to the classic `fpdf` package) returns
        # a bytearray/bytes object from output() and no longer accepts/needs the
        # legacy `dest='S'` argument. The classic `fpdf` package instead returns a
        # `str` that must be encoded. Support both transparently.
        try:
            output = pdf.output()
        except TypeError:
            output = pdf.output(dest='S')

        if isinstance(output, (bytes, bytearray)):
            return bytes(output)
        return output.encode('latin-1')


class ReportExporter:
    """Export reports in various formats."""

    @staticmethod
    def get_csv_download_link(report: ReportData, filename: str) -> Dict:
        """Get CSV download data."""
        generator = ReportGenerator([], [])
        csv_content = generator.export_to_csv(report, filename)

        return {
            'content': csv_content,
            'filename': f"{filename}.csv",
            'mime_type': 'text/csv'
        }

    @staticmethod
    def get_pdf_download_link(report: ReportData, filename: str) -> Dict:
        """Get PDF download data."""
        generator = ReportGenerator([], [])
        pdf_bytes = generator.export_to_pdf(report, filename)

        return {
            'content': base64.b64encode(pdf_bytes).decode(),
            'filename': f"{filename}.pdf",
            'mime_type': 'application/pdf'
        }


if __name__ == "__main__":
    from generator.data_generator import SyntheticDataGenerator

    # Test report generation
    gen = SyntheticDataGenerator(seed=42)
    flights = gen.generate_flight_schedule(50)
    gates = gen.generate_gates()

    # Assign gates
    for i, flight in enumerate(flights):
        flight.assigned_gate = gates[i % len(gates)].gate_id

    # Generate reports
    reporter = ReportGenerator(flights, gates)

    print("Generating reports...")

    # Simulation summary
    sim_report = reporter.generate_simulation_summary()
    print("\n" + sim_report.summary)

    # Conflict report
    conflicts = [
        {'conflict_id': 'C001', 'type': 'overlap', 'severity': 'high', 'gate_id': 'G1'},
        {'conflict_id': 'C002', 'type': 'size_mismatch', 'severity': 'critical', 'gate_id': 'G3'}
    ]
    conflict_report = reporter.generate_conflict_report(conflicts, {'high_count': 1, 'critical_count': 1, 'by_type': {'overlap': 1, 'size_mismatch': 1}})
    print("\n" + conflict_report.summary)

    print("\nReport generation complete!")
