"""Testes unitários para RealTimeline e RealSession (M4 — app/real_session.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from epidemia.app.panel_metrics import compute_epidemic_summary_from_timeline
from epidemia.app.real_session import (
    RealCountryCounts,
    RealSession,
    RealTimeline,
)
from epidemia.core.errors import (
    EpidemiaError,
    InvalidDatasetError,
    ParameterOutOfRangeError,
)
from epidemia.core.timeline.protocol import CountryInfo, Timeline
from epidemia.datasets.series import (
    PANDEMIC_SARS,
    load_pandemic_series,
)
from tests.fixtures import create_synthetic_world


@pytest.fixture
def sample_sars_series(tmp_path: Path):
    csv_file = tmp_path / "sars.csv"
    csv_file.write_text(
        "iso3,date,cases,deaths,recovered\n"
        "CHN,2003-03-17,10,1,2\n"
        "CHN,2003-03-18,50,4,10\n"
        "CHN,2003-03-19,100,8,25\n"
        "HKG,2003-03-17,2,0,0\n"
        "HKG,2003-03-18,8,1,2\n"
        "HKG,2003-03-19,20,2,5\n",
        encoding="utf-8",
    )
    return load_pandemic_series(csv_file, PANDEMIC_SARS)


@pytest.fixture
def sample_countries() -> list[CountryInfo]:
    return [
        CountryInfo("CHN", "China", 1_400_000_000, None),
        CountryInfo("HKG", "Hong Kong", 7_500_000, None),
    ]


def test_real_timeline_implements_protocol(sample_sars_series, sample_countries) -> None:
    timeline = RealTimeline(
        series=sample_sars_series,
        countries=sample_countries,
        num_vertices=1000,
    )

    # Verifica cumprimento formal do protocolo Timeline
    assert isinstance(timeline, Timeline)
    assert timeline.days_available == 3
    assert timeline.num_vertices == 1000
    assert len(timeline.countries) == 2

    # No fluxo real, vertex_states deve retornar None
    assert timeline.vertex_states(0) is None
    assert timeline.vertex_states(2) is None


def test_real_timeline_country_counts(sample_sars_series, sample_countries) -> None:
    timeline = RealTimeline(sample_sars_series, sample_countries, num_vertices=1000)

    # Dia 1 (2003-03-18)
    counts = timeline.country_counts(1)
    assert len(counts) == 2

    chn_c = counts[0]
    assert isinstance(chn_c, RealCountryCounts)
    assert chn_c.iso3 == "CHN"
    assert chn_c.cases == 50
    assert chn_c.deaths == 4
    assert chn_c.recovered == 10
    assert chn_c.active == 50 - (4 + 10)  # infected = 36
    assert chn_c.cumulative_cases == 50

    # Cache deve devolver os mesmos objetos
    assert timeline.country_counts(1) is counts


def test_real_timeline_country_day_zero(sample_sars_series, sample_countries) -> None:
    timeline = RealTimeline(sample_sars_series, sample_countries, num_vertices=1000)

    # Limiar explícito em casos
    # CHN: Dia 0 tem 10 casos, Dia 1 tem 50, Dia 2 tem 100
    assert timeline.country_day_zero("CHN", threshold_cases=5) == 0
    assert timeline.country_day_zero("CHN", threshold_cases=40) == 1
    assert timeline.country_day_zero("CHN", threshold_cases=90) == 2
    assert timeline.country_day_zero("CHN", threshold_cases=500) is None

    # Consulta por índice numérico
    assert timeline.country_day_zero(0, threshold_cases=50) == 1

    # País inexistente
    with pytest.raises(InvalidDatasetError, match="não encontrado"):
        timeline.country_day_zero("BRA")


def test_real_timeline_from_world(sample_sars_series) -> None:
    world = create_synthetic_world(total_vertices=60, seed=42)
    timeline = RealTimeline.from_world(world, sample_sars_series)

    assert isinstance(timeline, Timeline)
    assert timeline.num_vertices == 60
    assert len(timeline.countries) == len(world.country_codes)


def test_real_timeline_compatible_with_panel_metrics(sample_sars_series, sample_countries) -> None:
    timeline = RealTimeline(sample_sars_series, sample_countries, num_vertices=1000)
    summary = compute_epidemic_summary_from_timeline(timeline)

    # Deve calcular resumo a partir de country_counts sem falhar
    assert summary.peak_active_cases > 0
    # Convenção M2 (core/analysis/epidemic_metrics.py): duration_days é o índice do
    # último dia com novos casos ativos (t_final a partir do dia 0; dias 0, 1 e 2 -> índice 2).
    assert summary.duration_days == 2
    assert summary.total_deaths == 10  # Dia 2: 8 + 2 = 10


def test_real_session_lifecycle(tmp_path: Path, sample_sars_series) -> None:
    session = RealSession(processed_dir=tmp_path)
    assert not session.is_loaded
    assert PANDEMIC_SARS in session.available_pandemics

    # Erro ao pedir timeline antes de carregar
    with pytest.raises(EpidemiaError, match="Nenhuma pandemia carregada"):
        session.timeline()

    # Carrega via objeto series
    timeline = session.load_pandemic(PANDEMIC_SARS, series=sample_sars_series)
    assert session.is_loaded
    assert session.current_pandemic == PANDEMIC_SARS
    assert session.timeline() is timeline

    # Metadados
    meta = session.metadata()
    assert meta["name"] == PANDEMIC_SARS
    assert meta["total_days"] == 3
    assert meta["final_cumulative_cases"] == 120  # 100 + 20

    # Reset
    session.reset()
    assert not session.is_loaded
    assert session.current_pandemic is None


def test_real_session_unsupported_pandemic(tmp_path: Path) -> None:
    session = RealSession(processed_dir=tmp_path)
    with pytest.raises(ParameterOutOfRangeError, match="não suportada"):
        session.load_pandemic("gripe_espanhola")
