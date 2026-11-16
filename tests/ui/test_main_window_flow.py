"""Testes integrados da MainWindow e seus fluxos (Telas 1, 2, 5, 7, 8, 9, 12, 13) — M5."""

from __future__ import annotations

import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QMessageBox

from epidemia.ui.main_window import MainWindow
from tests.fixtures import create_synthetic_world


def _get_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_main_window_flow_navigation(monkeypatch):
    _get_qapp()
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)

    world = create_synthetic_world(total_vertices=60, seed=42)
    win = MainWindow(world)

    # 1. Tela Inicial
    assert win._tabs.currentIndex() == 0
    # Dispara o sinal do card Simulação
    win._start_screen.open_simulation.emit()
    assert win._tabs.currentIndex() == 1

    # 2. Na aba Simulação, inicia na Tela 2 (configuração)
    assert win._sim_stack.currentIndex() == 0
    # Clica em Voltar no config panel -> volta para Tela Inicial
    win._config_panel._btn_back.click()
    assert win._tabs.currentIndex() == 0

    # Volta para Simulação e Inicia a Simulação
    win._tabs.setCurrentIndex(1)
    win._config_panel._btn_start.click()
    # Deve comutar para a Tela 5 (execução)
    assert win._sim_stack.currentIndex() == 1
    assert "2,5" in win._lbl_frozen_r0.text()

    # Alterna visualização central entre Mapa e Curvas da Tela 7
    assert win._center_stack.currentIndex() == 0
    win._btn_toggle_view.click()
    assert win._center_stack.currentIndex() == 1
    win._charts_view._btn_back_map.click()
    assert win._center_stack.currentIndex() == 0

    # Reiniciar simulação volta para Tela 2 de configuração
    win._btn_restart_sim.click()
    assert win._sim_stack.currentIndex() == 0

    # 3. Aba Pandemias Reais (Tela 8)
    win._tabs.setCurrentIndex(2)
    assert win._real_stack.currentIndex() == 0

    # Simula carregamento de pandemia inexistente e aviso amigável
    win._list_pandemics.setCurrentRow(0)
    win._on_load_pandemic_clicked()
    assert "não encontrado em data/processed" in win._lbl_real_status.text()

    win.close()
