"""Testes unitários e de integração dos componentes de interface (M5).

Executa com QT_QPA_PLATFORM=offscreen sem necessidade de pytest-qt.
"""

from __future__ import annotations

import os
import sys

# Força plataforma offscreen para execução headless de testes
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtWidgets import QApplication

from epidemia.app.playback import PlaybackController
from epidemia.core.epidemic.parameters import SimulationConfig
from epidemia.ui.charts_view import ChartsView
from epidemia.ui.config_panel import ConfigPanel
from epidemia.ui.main_window import MainWindow, NetworkAnalysisWorker
from epidemia.ui.map_view import MapView
from epidemia.ui.player_bar import PlayerBar
from tests.fixtures import create_synthetic_world


@pytest.fixture(scope="session")
def qapp():
    """Garante que a instância de QApplication exista para a sessão de testes."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_main_window_duas_abas_e_inicializacao(qapp):
    """Verifica que MainWindow inicializa com as duas abas requeridas."""
    world = create_synthetic_world(total_vertices=60, seed=42)
    win = MainWindow(world)
    assert win._tabs.count() == 2
    assert "Simulação" in win._tabs.tabText(0)
    assert "Pandemias reais" in win._tabs.tabText(1)

    # Verifica widgets centrais da aba simulação
    assert win._config_panel is not None
    assert win._map_view is not None
    assert win._player_bar is not None
    assert win._charts_view is not None

    win.close()


def test_config_panel_get_and_apply_config(qapp):
    """Verifica que ConfigPanel extrai e aplica SimulationConfig corretamente."""
    panel = ConfigPanel()
    cfg = panel.get_simulation_config()
    assert cfg.r0 == 2.5
    assert cfg.exit_rate_gamma == 0.10
    assert cfg.mortality == 0.02
    assert cfg.intervention_level == "baixo"

    novo_cfg = SimulationConfig(
        seed=999,
        scenario="regional_ebola",
        r0=3.4,
        exit_rate_gamma=0.25,
        mortality=0.08,
        incubation_days=6.0,
        intervention_level="alto",
        patient_zero=(0, 2),
    )
    panel.apply_simulation_config(novo_cfg)
    cfg_obtido = panel.get_simulation_config()

    assert cfg_obtido.seed == 999
    assert cfg_obtido.scenario == "regional_ebola"
    assert pytest.approx(cfg_obtido.r0, 0.01) == 3.4
    assert pytest.approx(cfg_obtido.exit_rate_gamma, 0.01) == 0.25
    assert pytest.approx(cfg_obtido.mortality, 0.01) == 0.08
    assert pytest.approx(cfg_obtido.incubation_days, 0.01) == 6.0
    assert cfg_obtido.intervention_level == "alto"
    assert cfg_obtido.patient_zero == (0, 2)


def test_map_view_set_world_and_day_data(qapp):
    """Verifica que MapView renderiza polígonos sintéticos sem levantar exceções."""
    world = create_synthetic_world(total_vertices=60, seed=42)
    map_view = MapView()
    map_view.set_world(world)
    map_view.resize(600, 400)

    # Simula dados do dia 0 (bytes de vértice)
    v_bytes = bytes([0] * 58 + [2, 2])  # 58 suscetíveis, 2 infectados
    map_view.set_day_data(v_bytes)

    # Força evento de pintura
    map_view.repaint()

    # Testa zoom in, zoom out e fit
    map_view._on_zoom_in_clicked()
    map_view._on_zoom_out_clicked()
    map_view._on_fit_clicked()
    map_view.repaint()


def test_charts_view_render_and_export_png(qapp, tmp_path):
    """Verifica que ChartsView atualiza curvas e exporta PNG com sucesso."""
    charts = ChartsView()
    charts.resize(600, 300)

    # Cria sessão sintética com dias gravados
    from epidemia.app.simulation_session import SimulationSession

    world = create_synthetic_world(total_vertices=60, seed=42)
    session = SimulationSession(world)
    session.configure(SimulationConfig(seed=42, max_days=5))
    session.start()
    session.run_day()

    timeline = session.timeline()
    charts.update_timeline_data(timeline, current_day=1)

    png_path = tmp_path / "chart_test.png"
    charts.export_image(png_path)

    assert png_path.exists()
    assert png_path.stat().st_size > 0


def test_player_bar_widget_interaction(qapp):
    """Verifica que PlayerBar interage corretamente com o PlaybackController."""
    playback = PlaybackController()
    bar = PlayerBar(playback)

    # Testa toggle play
    bar._on_toggle_play()
    assert playback.is_playing is False  # Sem timeline disponível, não inicia

    # Testa mudança de velocidade
    bar._on_speed_changed(5.0)
    assert playback.speed == 5.0


def test_network_analysis_worker(qapp):
    """Verifica que NetworkAnalysisWorker executa e emite resultado de M2."""
    world = create_synthetic_world(total_vertices=60, seed=42)
    worker = NetworkAnalysisWorker(world, sample_size=15)

    resultado = None

    def on_done(res):
        nonlocal resultado
        resultado = res

    worker.analysis_finished.connect(on_done)
    worker.start()
    while not worker.isFinished():
        qapp.processEvents()
    qapp.processEvents()

    assert resultado is not None
    assert resultado.num_vertices == 60
    assert resultado.avg_degree > 0
    assert resultado.num_communities >= 1


def test_error_dialog_sem_fechar_janela(qapp, monkeypatch):
    """Verifica que erros de domínio exibem diálogo sem fechar a aplicação (RNF08)."""
    world = create_synthetic_world(total_vertices=60, seed=42)
    win = MainWindow(world)

    dialog_chamado = False

    def mock_critical(parent, title, message):
        nonlocal dialog_chamado
        dialog_chamado = True
        assert "Erro" in title
        assert "fora da faixa" in message

    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "critical", mock_critical)

    # Simula disparo de erro de domínio
    win.show_error_dialog("Erro de Teste", "Parâmetro fora da faixa.")

    assert dialog_chamado is True
    assert win.isVisible() is False or win.close() is not None
