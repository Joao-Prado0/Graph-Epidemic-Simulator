"""Testes da Tela 13 (Diálogo de Exportação) — M5 (RF08)."""

from __future__ import annotations

import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from epidemia.app.simulation_session import SimulationSession
from epidemia.core.epidemic.parameters import SimulationConfig
from epidemia.ui.charts_view import ChartsView
from epidemia.ui.export_dialog import ExportDialog
from tests.fixtures import create_synthetic_world


def _get_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_export_dialog_initialization():
    _get_qapp()
    dialog = ExportDialog(timeline=None)
    assert dialog._chk_csv.isChecked() is True
    assert dialog._chk_png.isChecked() is True
    assert dialog._progress_bar.value() == 0
    assert dialog._btn_export.isEnabled() is True


def test_export_dialog_runs_export_csv_and_png(tmp_path, monkeypatch):
    _get_qapp()
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: None)

    world = create_synthetic_world(total_vertices=60, seed=42)
    session = SimulationSession(world)
    session.configure(SimulationConfig(seed=42, max_days=3))
    session.start()
    session.run_day()

    timeline = session.timeline()
    charts = ChartsView()
    charts.resize(400, 300)
    charts.update_timeline_data(timeline, current_day=1)

    dialog = ExportDialog(timeline=timeline, charts_view=charts)
    dest_dir = tmp_path / "test_out"
    dialog._edit_dir.setText(str(dest_dir))

    # Executa exportação
    dialog._on_export_clicked()

    csv_file = dest_dir / "series_temporais.csv"
    png_file = dest_dir / "curvas_epidemicas.png"

    assert csv_file.exists()
    assert csv_file.stat().st_size > 0
    assert png_file.exists()
    assert png_file.stat().st_size > 0
    assert dialog._progress_bar.value() == 100
    assert "Concluído" in dialog._lbl_status_csv.text()
    assert "Concluído" in dialog._lbl_status_png.text()
