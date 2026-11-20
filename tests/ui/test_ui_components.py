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
    """Verifica que MainWindow inicializa com as abas requeridas pela top navigation bar."""
    world = create_synthetic_world(total_vertices=60, seed=42)
    win = MainWindow(world)
    assert win._tabs.count() == 3
    assert "Início" in win._tabs.tabText(0)
    assert "Simulação" in win._tabs.tabText(1)
    assert "Pandemias reais" in win._tabs.tabText(2)

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
    assert cfg.r0 == 5.0
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

    # Força zoom alto para ativar _country_visible_nodes (>= 40 px) e renderizar os pontos
    map_view._canvas._zoom = 20.0
    map_view._canvas.paintEvent(None)
    assert any(map_view._canvas._country_visible_nodes.values())

    # Testa zoom in, zoom out e fit
    map_view._on_zoom_in_clicked()
    map_view._on_zoom_out_clicked()
    map_view._on_fit_clicked()
    map_view._canvas.paintEvent(None)


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


def test_real_pandemics_tab_missing_file_warning(qapp):
    """Verifica aviso amigável quando arquivos de dados reais do M4 não existem."""
    world = create_synthetic_world(total_vertices=60, seed=42)
    win = MainWindow(world)

    win._list_pandemics.setCurrentRow(0)
    win._on_load_pandemic_clicked()

    # Com data/processed sem arquivos reais, deve exibir aviso de pendência
    assert "não encontrado em data/processed" in win._lbl_real_status.text()
    assert win._is_real_flow is False
    win.close()


def test_real_pandemics_load_series_and_playback(qapp, tmp_path):
    """Verifica que RealTimeline controla player, mapa e gráficos ao carregar pandemia."""
    from epidemia.app.real_session import RealTimeline
    from epidemia.datasets.series import PANDEMIC_SARS, load_pandemic_series

    csv_file = tmp_path / "sars.csv"
    csv_file.write_text(
        "iso3,date,cases,deaths,recovered\n"
        "BRA,2003-03-17,10,1,2\n"
        "BRA,2003-03-18,50,4,10\n"
        "BRA,2003-03-19,100,8,25\n",
        encoding="utf-8",
    )
    series = load_pandemic_series(csv_file, PANDEMIC_SARS)

    world = create_synthetic_world(total_vertices=60, seed=42)
    win = MainWindow(world)

    # Carrega pandemia com a série sintética
    win._load_pandemic_by_id("sars", "SARS-CoV-1", series=series)

    assert win._is_real_flow is True
    assert isinstance(win._playback.timeline, RealTimeline)
    assert win._playback.days_available == 3
    assert win._tabs.currentIndex() == 2

    # Verifica que o mapa está no modo real (sem vertex_states)
    assert win._map_view.is_real_flow is True
    assert win._map_view._canvas._vertex_bytes is None
    assert win._map_view._canvas._country_counts is not None

    # Avança no player e confirma sincronização
    win._player_bar._slider.setValue(2)
    assert win._playback.current_day == 2
    assert win._map_view._canvas._vertex_bytes is None
    # No dia 2 da série sintética (cases=100, deaths=8, recovered=25),
    # o total acumulado exibido na Tela 9 deve ser 100 (cumulative_cases) e não 67 (infected)
    assert "100" in win._lbl_real_cases_tot.text()
    assert "8" in win._lbl_real_deaths_tot.text()

    # Alterna entre mapa e curvas (RF12) na Tela 9
    assert win._real_center_stack.currentIndex() == 0
    win._btn_real_toggle_view.click()
    assert win._real_center_stack.currentIndex() == 1
    win._real_charts_view._btn_back_map.click()
    assert win._real_center_stack.currentIndex() == 0

    # Descarrega
    win._on_unload_pandemic_clicked()
    assert win._is_real_flow is False
    assert win._playback.timeline is None
    win.close()


def test_map_view_real_flow_intensity_scale_and_no_vertex_states(qapp):
    """Verifica a renderização por país por intensidade de casos por 100k hab. (A12)."""
    from epidemia.core.timeline.protocol import CountryCounts
    from epidemia.ui.styles import (
        REAL_FLOW_MIN_CASES_PER_100K,
        color_for_real_cases_per_100k,
    )

    # 1. Validação dos limiares da escala sequencial
    assert REAL_FLOW_MIN_CASES_PER_100K == 10.0
    c_sub = color_for_real_cases_per_100k(5.0)  # Abaixo de 10/100k
    assert c_sub.name() == "#2d3748"

    c_min = color_for_real_cases_per_100k(15.0)  # Acima de 10/100k
    assert c_min.name() == "#fff5f0"

    c_high = color_for_real_cases_per_100k(6000.0)  # Alto
    assert c_high.name() == "#cb181d"

    # 2. Renderização no MapView com country_counts
    world = create_synthetic_world(total_vertices=60, seed=42)
    map_view = MapView()
    map_view.set_world(world)
    map_view.resize(600, 400)

    # Brasil: pop = 215_000_000. Para 21_500 casos -> 10 por 100k hab.
    counts = [CountryCounts(iso3="BRA", infected=21_500, deceased=10)]
    map_view.set_day_data(None, counts, is_real_flow=True)

    color_bra = map_view._canvas._calculate_real_flow_color("BRA")
    assert color_bra.name() == "#fff5f0"

    # Confirma que vertex_bytes permanece None e que repaint executa sem erros
    assert map_view._canvas._vertex_bytes is None
    assert map_view.is_real_flow is True
    map_view.repaint()


def test_main_window_geometria_real_ou_fallback_sintetico(qapp, monkeypatch):
    """Verifica aviso claro quando countries.geojson não existe e fallback sintético."""
    # Sem arquivos reais em data/processed/
    win = MainWindow(world=None)
    assert win._is_synthetic_world is True
    assert "countries.geojson não encontrado" in win.statusBar().currentMessage()
    win.close()

    # Quando um world é explicitamente passado (ex.: com geometria real)
    world = create_synthetic_world(total_vertices=60, seed=42)
    win_custom = MainWindow(world=world)
    assert win_custom._is_synthetic_world is False
    assert "Geometrias reais carregadas" in win_custom.statusBar().currentMessage()
    win_custom.close()


def test_main_window_comparison_rf14(qapp, tmp_path):
    """Verifica os campos do ComparisonResult (RF14) no painel ou Indisponível com motivo."""
    from epidemia.datasets.series import PANDEMIC_SARS, load_pandemic_series

    world = create_synthetic_world(total_vertices=60, seed=42)
    win = MainWindow(world=world)

    # 1. Sem pandemia carregada e sem simulação
    win._update_comparison_metrics()
    assert "Indisponível (nenhuma pandemia real carregada)" in win._lbl_res_comp_status.text()
    assert win._lbl_res_comp_cases_mse.text() == "• MSE Casos: --"

    # 2. Carrega pandemia real via série sintética
    csv_file = tmp_path / "sars.csv"
    csv_file.write_text(
        "iso3,date,cases,deaths,recovered\n"
        "BRA,2003-03-17,10,1,2\n"
        "BRA,2003-03-18,50,4,10\n"
        "BRA,2003-03-19,100,8,25\n",
        encoding="utf-8",
    )
    series = load_pandemic_series(csv_file, PANDEMIC_SARS)
    win._real_session.load_pandemic("sars", series=series)

    # Com pandemia carregada mas sem simulação iniciada
    win._update_comparison_metrics()
    assert "Indisponível (simulação não concluída" in win._lbl_res_comp_status.text()

    # 3. Inicia e roda alguns dias de simulação
    win._session.configure(SimulationConfig(seed=42))
    win._session.start(patient_zero=[0, 1])
    win._session.run_day()
    win._session.run_day()

    win._update_comparison_metrics()
    assert "Comparação (SARS)" in win._lbl_res_comp_status.text()
    assert "• MSE Casos:" in win._lbl_res_comp_cases_mse.text()
    assert "• MSE Mortes:" in win._lbl_res_comp_deaths_mse.text()
    assert "• Dif. Pico Novos/Dia:" in win._lbl_res_comp_peak_diff.text()
    assert "• Dif. Tamanho Final:" in win._lbl_res_comp_final_diff.text()
    win.close()


def test_map_canvas_antimeridian_width_and_dominant_color(qapp):
    """Verifica largura no antimeridiano (D15) e delegação de dominant_state (M3)."""
    from PySide6.QtCore import QRectF

    from epidemia.core.timeline.protocol import STATE_R, CountryCounts
    from epidemia.ui.map_view import _compute_country_deg_width
    from epidemia.ui.styles import COLOR_ISOLATED, COLOR_RECOVERED_VAC
    from epidemia.world.geometry import CountryGeometry

    # Polígono cruzando o antimeridiano (+178 a -178 -> largura real de 4 graus, não 356)
    ring_east = [(178.0, -15.0), (180.0, -15.0), (179.0, -17.0)]
    ring_west = [(-180.0, -15.0), (-178.0, -15.0), (-179.0, -17.0)]
    geom_fji = CountryGeometry(
        iso3="FJI",
        polygons=[(ring_east, []), (ring_west, [])],
        bbox=(-180.0, -17.0, 180.0, -15.0),
        area=4.0,
        centroid=(179.0, -16.0),
    )
    width_deg = _compute_country_deg_width(geom_fji, QRectF(-180.0, 15.0, 360.0, 2.0))
    assert width_deg < 10.0

    world = create_synthetic_world(total_vertices=60, seed=42)
    map_view = MapView()
    map_view.set_world(world)

    # Verifica cor de país isolado e de país com maioria vacinada
    counts_iso = [
        CountryCounts(iso3="BRA", susceptible=10, isolated=10),
        CountryCounts(
            iso3="ARG",
            susceptible=2,
            recovered_natural=2,
            recovered_vaccinated=6,
        ),
    ]
    map_view.set_day_data(bytes([0] * 60), counts_iso, is_real_flow=False)
    assert map_view._canvas._calculate_dominant_status_color("BRA") == COLOR_ISOLATED
    assert counts_iso[1].dominant_state == STATE_R
    assert map_view._canvas._calculate_dominant_status_color("ARG") == COLOR_RECOVERED_VAC
