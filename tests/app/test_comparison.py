"""Testes unitários para a comparação científica simulado vs real (M4 — app/comparison.py)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from epidemia.app.comparison import (
    ComparisonResult,
    compare_simulation_to_real,
)
from epidemia.app.real_session import RealTimeline
from epidemia.app.simulation_session import SimulationSession
from epidemia.core.epidemic.parameters import SimulationConfig
from epidemia.core.timeline.protocol import CountryInfo
from epidemia.datasets.series import PANDEMIC_SARS, load_pandemic_series
from tests.fixtures import create_synthetic_world


@pytest.fixture
def sample_sars_timeline(tmp_path: Path) -> RealTimeline:
    csv_file = tmp_path / "sars.csv"
    csv_file.write_text(
        "iso3,date,cases,deaths,recovered\n"
        "BRA,2003-03-01,10,1,2\n"
        "BRA,2003-03-02,30,2,8\n"
        "BRA,2003-03-03,60,4,18\n"
        "BRA,2003-03-04,80,5,25\n"
        "BRA,2003-03-05,90,6,30\n",
        encoding="utf-8",
    )
    series = load_pandemic_series(csv_file, PANDEMIC_SARS)
    countries = [CountryInfo("BRA", "Brasil", 1000, None)]
    return RealTimeline(series, countries, num_vertices=100)


def test_compare_simulation_to_real_synthetic() -> None:
    # 1. Executa simulação curta para gerar SimulationTimeline
    world = create_synthetic_world(total_vertices=80, seed=42)
    session = SimulationSession(world)
    config = SimulationConfig(
        seed=42,
        r0=3.0,
        exit_rate_gamma=0.2,
        mortality=0.05,
        incubation_days=2.0,
        intervention_level="nenhum",
        max_days=15,
    )
    session.configure(config)
    session.start()
    for _ in range(8):
        session.run_day()

    sim_timeline = session.timeline()

    # 2. Usa a própria simulação como base para comparar contra si mesma
    # Deve dar erro zero ou quase zero
    res = compare_simulation_to_real(sim_timeline, sim_timeline, threshold_m=1)

    assert isinstance(res, ComparisonResult)
    assert res.aligned_days > 0
    assert math.isclose(res.cases_mse, 0.0, abs_tol=1e-9)
    assert math.isclose(res.cases_rmse, 0.0, abs_tol=1e-9)
    assert math.isclose(res.deaths_mse, 0.0, abs_tol=1e-9)
    assert res.peak_day_difference == 0
    assert math.isclose(res.final_size_difference, 0.0, abs_tol=1e-9)

    summary = res.formatted_summary()
    assert "RMSE casos: 0.00%" in summary
    assert "Δ dia pico: 0d" in summary


def test_compare_simulation_to_real_known_curves(tmp_path: Path) -> None:
    # Curva real sintética: 10, 30, 60, 80, 90 casos em 100 habitantes
    csv_file = tmp_path / "known.csv"
    csv_file.write_text(
        "iso3,date,cases,deaths,recovered\n"
        "BRA,2020-01-01,10,0,0\n"
        "BRA,2020-01-02,30,1,5\n"
        "BRA,2020-01-03,60,3,15\n"
        "BRA,2020-01-04,80,5,30\n",
        encoding="utf-8",
    )
    series_real = load_pandemic_series(csv_file, "teste")
    countries = [CountryInfo("BRA", "Brasil", 100, None)]
    timeline_real = RealTimeline(series_real, countries, num_vertices=100)

    # Curva alternativa sintética: 15, 35, 65, 85
    csv_alt = tmp_path / "alt.csv"
    csv_alt.write_text(
        "iso3,date,cases,deaths,recovered\n"
        "BRA,2020-01-01,15,0,0\n"
        "BRA,2020-01-02,35,1,5\n"
        "BRA,2020-01-03,65,3,15\n"
        "BRA,2020-01-04,85,5,30\n",
        encoding="utf-8",
    )
    series_alt = load_pandemic_series(csv_alt, "teste_alt")
    timeline_alt = RealTimeline(series_alt, countries, num_vertices=100)

    res = compare_simulation_to_real(timeline_alt, timeline_real, threshold_m=1)

    assert res.aligned_days == 4
    # Diferença constante de +5 casos em 100 habitantes = 0.05
    # MSE = 0.05^2 = 0.0025, RMSE = 0.05
    assert math.isclose(res.cases_mse, 0.0025, rel_tol=1e-4)
    assert math.isclose(res.cases_rmse, 0.05, rel_tol=1e-4)
    assert math.isclose(res.final_size_difference, 0.05, rel_tol=1e-4)


def test_compare_simulation_to_real_reports(sample_sars_timeline: RealTimeline) -> None:
    res = compare_simulation_to_real(
        sample_sars_timeline,
        sample_sars_timeline,
        country="BRA",
        threshold_m=1,
    )
    assert res.country_code == "BRA"
    assert "BRA" in res.formatted_summary()

    report = res.detailed_report()
    assert "Relatório de Comparação" in report
    assert "BRA" in report
    assert "RMSE Casos Acumulados" in report
    assert "Recuperados" in report
