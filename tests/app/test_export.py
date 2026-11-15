"""Testes unitários de exportação de CSV a partir do Timeline (RF08)."""

from __future__ import annotations

import csv

import pytest

from epidemia.app.export import CSV_HEADER, export_timeline_csv
from epidemia.app.simulation_session import SimulationSession
from epidemia.core.epidemic.parameters import SimulationConfig
from epidemia.core.errors import ParameterOutOfRangeError
from tests.fixtures import create_synthetic_world


def test_export_timeline_csv_uma_linha_por_dia(tmp_path):
    """Verifica que o CSV exportado possui cabeçalho e exatamente uma linha por dia gravado."""
    world = create_synthetic_world(total_vertices=60, seed=42)
    session = SimulationSession(world)
    config = SimulationConfig(
        seed=42,
        r0=2.5,
        exit_rate_gamma=0.2,
        mortality=0.05,
        incubation_days=3.0,
        intervention_level="baixo",
        max_days=30,
    )
    session.configure(config)
    session.start()

    # Roda 10 dias adicionais (totalizando 11 dias: dia 0 a 10)
    for _ in range(10):
        session.run_day()

    timeline = session.timeline()
    assert timeline.days_available == 11

    arquivo_csv = tmp_path / "simulacao.csv"
    linhas_exportadas = export_timeline_csv(timeline, arquivo_csv)

    assert linhas_exportadas == 11
    assert arquivo_csv.exists()

    with arquivo_csv.open("r", encoding="utf-8") as f:
        reader = list(csv.reader(f))

    # Linha 0 é o cabeçalho, linhas 1..11 são os dias 0..10
    assert len(reader) == 12
    assert reader[0] == CSV_HEADER

    for idx, row in enumerate(reader[1:]):
        assert int(row[0]) == idx
        s = int(row[1])
        e = int(row[2])
        i = int(row[3])
        r_nat = int(row[4])
        r_vac = int(row[5])
        d = int(row[6])
        iso = int(row[7])
        total = int(row[8])

        # Invariante da população total
        assert s + e + i + r_nat + r_vac + d == 60
        assert total == 60
        assert iso >= 0


def test_export_timeline_none_raises_error(tmp_path):
    """Verifica que timeline None levanta ParameterOutOfRangeError."""
    with pytest.raises(ParameterOutOfRangeError):
        export_timeline_csv(None, tmp_path / "teste.csv")
