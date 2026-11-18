"""Camada de aplicação: sessões e casos de uso sem dependência de interface gráfica."""

from epidemia.app.comparison import ComparisonResult, compare_simulation_to_real
from epidemia.app.config_io import load_config, save_config
from epidemia.app.export import export_timeline_csv
from epidemia.app.panel_metrics import (
    NetworkAnalysisResult,
    ShortestEpidemicPathSummary,
    VertexInspectionResult,
    compute_epidemic_summary_from_timeline,
    compute_network_analysis,
    compute_shortest_epidemic_path,
    inspect_vertex_metrics,
)
from epidemia.app.playback import PlaybackController
from epidemia.app.real_session import RealCountryCounts, RealSession, RealTimeline
from epidemia.app.simulation_session import SimulationSession

__all__ = [
    "ComparisonResult",
    "NetworkAnalysisResult",
    "PlaybackController",
    "RealCountryCounts",
    "RealSession",
    "RealTimeline",
    "ShortestEpidemicPathSummary",
    "SimulationSession",
    "VertexInspectionResult",
    "compare_simulation_to_real",
    "compute_epidemic_summary_from_timeline",
    "compute_network_analysis",
    "compute_shortest_epidemic_path",
    "export_timeline_csv",
    "inspect_vertex_metrics",
    "load_config",
    "save_config",
]
