"""Testes da Tela 7 (Gráficos em Tempo Real com Chips SEIRD) — M5 (RF08, RF24)."""

from __future__ import annotations

import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from epidemia.app.simulation_session import SimulationSession
from epidemia.core.epidemic.parameters import SimulationConfig
from epidemia.ui.charts_view import ChartsView
from tests.fixtures import create_synthetic_world


def _get_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_charts_view_chips_and_pt_br_formatting(tmp_path):
    _get_qapp()
    world = create_synthetic_world(total_vertices=60, seed=42)
    session = SimulationSession(world)
    session.configure(SimulationConfig(seed=42, max_days=5))
    session.start()
    session.run_day()

    timeline = session.timeline()
    charts = ChartsView()
    charts.resize(600, 400)
    charts.update_timeline_data(timeline, current_day=1)

    # Verifica que os 5 chips foram inicializados e atualizados
    assert charts._chip_s is not None
    assert charts._chip_e is not None
    assert charts._chip_i is not None
    assert charts._chip_r is not None
    assert charts._chip_d is not None

    # Verifica formatação pt-BR nos chips (com vírgula para percentual ou ponto de milhar)
    val_s = charts._chip_s._lbl_value.text()
    assert "%" in val_s
    assert "·" in val_s

    # Testa sinal back_to_map_requested
    called = []
    charts.back_to_map_requested.connect(lambda: called.append(True))
    charts._btn_back_map.click()
    assert called == [True]

    # Testa exportação PNG
    png_path = tmp_path / "test_tela7_export.png"
    charts.export_image(png_path)
    assert png_path.exists()
    assert png_path.stat().st_size > 0

    # Testa clear
    charts.clear()
    assert charts._chip_s._lbl_value.text() == "--"
