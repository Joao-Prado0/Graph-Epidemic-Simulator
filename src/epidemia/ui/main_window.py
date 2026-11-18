"""Janela principal da aplicação (M5 — Wireframes e Interface).

Integra as abas de navegação ("Início", "Simulação" e "Pandemias reais"), os fluxos
de configuração (Tela 2), execução da simulação (Tela 5), curvas SEIRD (Tela 7),
seleção e reprodução de pandemias históricas (Telas 8 e 9), exportação (Tela 13)
e comparação científica com dados reais (RF14).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from epidemia.app.comparison import compare_simulation_to_real
from epidemia.app.config_io import load_config, save_config
from epidemia.app.export import export_timeline_csv
from epidemia.app.panel_metrics import (
    NetworkAnalysisResult,
    compute_epidemic_summary_from_timeline,
    compute_network_analysis,
    compute_shortest_epidemic_path,
)
from epidemia.app.playback import PlaybackController
from epidemia.app.real_session import RealSession
from epidemia.app.simulation_session import SimulationSession
from epidemia.config import PROCESSED_DATA_DIR, has_processed_data
from epidemia.core.errors import EpidemiaError
from epidemia.datasets.loaders import load_world_inputs
from epidemia.ui.charts_view import ChartsView
from epidemia.ui.config_panel import ConfigPanel
from epidemia.ui.export_dialog import ExportDialog
from epidemia.ui.map_view import MapView
from epidemia.ui.player_bar import PlayerBar
from epidemia.ui.simulation_thread import SimulationThread
from epidemia.ui.start_screen import StartScreen
from epidemia.ui.styles import (
    ACCENT_TEAL_HEX,
    BG_CARD_HEX,
    BORDER_LIGHT_HEX,
    BORDER_SUBTLE_HEX,
    COLOR_HEX_DECEASED,
    COLOR_HEX_EXPOSED,
    COLOR_HEX_INFECTED,
    COLOR_HEX_ISOLATED,
    COLOR_HEX_RECOVERED_NAT,
    COLOR_HEX_SUSCEPTIBLE,
    DARK_THEME_QSS,
    TEXT_MUTED_HEX,
    TEXT_PRIMARY_HEX,
    TEXT_SECONDARY_HEX,
    format_number_br,
    format_percent_br,
)
from epidemia.world.builder import build_world
from tests.fixtures import create_synthetic_world

if TYPE_CHECKING:
    from epidemia.core.epidemic.parameters import SimulationConfig
    from epidemia.world.world import World


class NetworkAnalysisWorker(QThread):
    """Executa a análise de redes (M2) em segundo plano sem congelar a interface."""

    analysis_finished = Signal(object)  # NetworkAnalysisResult
    analysis_failed = Signal(str)

    def __init__(
        self,
        world: World,
        sample_size: int = 50,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._world = world
        self._sample_size = sample_size

    def run(self) -> None:
        try:
            result = compute_network_analysis(
                self._world.graph,
                self._world.vertex_country,
                sample_size=self._sample_size,
            )
            self.analysis_finished.emit(result)
        except Exception as exc:
            self.analysis_failed.emit(str(exc))


class PandemicCard(QFrame):
    """Cartão informativo de seleção de pandemia histórica (Tela 8)."""

    open_requested = Signal(str, str)

    def __init__(
        self,
        p_id: str,
        name: str,
        period: str,
        scope: str,
        description: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._p_id = p_id
        self._name = name

        self.setStyleSheet(
            f"PandemicCard {{"
            f"  background-color: {BG_CARD_HEX};"
            f"  border: 1px solid {BORDER_SUBTLE_HEX};"
            f"  border-radius: 8px;"
            f"}}"
            f"PandemicCard:hover {{"
            f"  border-color: {BORDER_LIGHT_HEX};"
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Cabeçalho do card: Título e Badge de Escopo
        top_box = QHBoxLayout()
        lbl_name = QLabel(name)
        lbl_name.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {TEXT_PRIMARY_HEX};")
        top_box.addWidget(lbl_name)
        top_box.addStretch(1)

        tag = QLabel(scope.upper())
        tag.setStyleSheet(
            f"background-color: #162832; color: {ACCENT_TEAL_HEX};"
            f"border: 1px solid {ACCENT_TEAL_HEX}; border-radius: 4px;"
            f"padding: 2px 8px; font-size: 10px; font-weight: bold;"
        )
        top_box.addWidget(tag)
        layout.addLayout(top_box)

        # Período
        lbl_period = QLabel(period)
        lbl_period.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED_HEX};")
        layout.addWidget(lbl_period)

        # Descrição
        lbl_desc = QLabel(description)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY_HEX};")
        layout.addWidget(lbl_desc)

        layout.addStretch(1)

        # Botão Abrir
        btn_open = QPushButton("Abrir fluxo")
        btn_open.setObjectName("btnPrimary")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.clicked.connect(lambda: self.open_requested.emit(self._p_id, self._name))
        layout.addWidget(btn_open)


class MainWindow(QMainWindow):
    """Janela principal do Simulador de Epidemias em Redes."""

    def __init__(self, world: World | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Simulador de Epidemias em Redes — Antigravity")
        self.resize(1380, 880)

        self._is_synthetic_world: bool = False
        if world is not None:
            self._world: World = world
        elif has_processed_data():
            try:
                countries, edges = load_world_inputs(PROCESSED_DATA_DIR)
                self._world = build_world(
                    countries=countries,
                    routes=edges,
                    total_vertices=8000,
                )
            except Exception:
                self._world = create_synthetic_world(total_vertices=100)
                self._is_synthetic_world = True
        else:
            self._world = create_synthetic_world(total_vertices=100)
            self._is_synthetic_world = True

        self._session: SimulationSession = SimulationSession(self._world)
        self._real_session: RealSession = RealSession(
            processed_dir=PROCESSED_DATA_DIR, world=self._world
        )
        self._is_real_flow: bool = False
        self._playback: PlaybackController = PlaybackController()
        self._sim_thread: SimulationThread = SimulationThread(self._session, self)
        self._network_worker: NetworkAnalysisWorker | None = None

        self._init_ui()
        self._connect_signals()

        # Atualiza aviso de ambiente e geometria na barra de status
        status = self.statusBar()
        if self._is_synthetic_world:
            status.showMessage(
                "Aviso: countries.geojson não encontrado em data/processed. "
                "Aplicação operando com mapa sintético de demonstração (fixture)."
            )
            status.setStyleSheet("color: #ffb74d; background-color: #070c10; font-size: 12px;")
        else:
            status.showMessage(
                "Geometrias reais carregadas a partir de data/processed/countries.geojson."
            )
            status.setStyleSheet("color: #4cd7b4; background-color: #070c10; font-size: 12px;")

        self.setStyleSheet(DARK_THEME_QSS)

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # Cabeçalho Superior com Logo e Navegação (Wireframe)
        top_header = QHBoxLayout()
        top_header.setSpacing(12)

        logo_box = QVBoxLayout()
        logo_box.setSpacing(0)
        lbl_logo = QLabel("REDE / EPIDEMIAS")
        lbl_logo.setStyleSheet(
            f"font-size: 16px; font-weight: 900; color: {ACCENT_TEAL_HEX}; letter-spacing: 1px;"
        )
        lbl_sub = QLabel("Simulador de Epidemias em Redes")
        lbl_sub.setStyleSheet(f"font-size: 10px; color: {TEXT_MUTED_HEX};")
        logo_box.addWidget(lbl_logo)
        logo_box.addWidget(lbl_sub)
        top_header.addLayout(logo_box)

        top_header.addSpacing(20)

        # Abas de navegação principais (Início, Simulação, Pandemias reais)
        self._tabs = QTabWidget(self)
        top_header.addWidget(self._tabs, stretch=1)
        root_layout.addLayout(top_header)

        # Aba 0: Início (Tela 1)
        self._start_screen = StartScreen()
        self._tabs.addTab(self._start_screen, "Início")

        # Aba 1: Simulação (Tela 2 e Tela 5)
        self._tab_sim = QWidget()
        self._setup_simulation_tab()
        self._tabs.addTab(self._tab_sim, "Simulação")

        # Aba 2: Pandemias reais (Tela 8 e Tela 9)
        self._tab_real = QWidget()
        self._setup_real_pandemics_tab()
        self._tabs.addTab(self._tab_real, "Pandemias reais")

    def _setup_simulation_tab(self) -> None:
        layout = QVBoxLayout(self._tab_sim)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._sim_stack = QStackedWidget()
        layout.addWidget(self._sim_stack)

        # Página 0 da Simulação: Tela 2 (Configuração)
        self._config_panel = ConfigPanel()
        self._sim_stack.addWidget(self._config_panel)

        # Página 1 da Simulação: Tela 5 (Simulação em Andamento)
        sim_run_widget = QWidget()
        sim_run_layout = QHBoxLayout(sim_run_widget)
        sim_run_layout.setContentsMargins(6, 6, 6, 6)
        sim_run_layout.setSpacing(10)

        # Coluna Esquerda: Parâmetros Ativos e Ações (Tela 5)
        left_box = self._build_sim_active_params_column()
        sim_run_layout.addWidget(left_box)

        # Coluna Central: Mapa e Curvas (Stack com Mapa e Gráficos da Tela 7)
        center_box = self._build_sim_center_column()
        sim_run_layout.addWidget(center_box, stretch=1)

        # Coluna Direita: Painel de Resultados (RF14, RF18, RF19, RF21, RF24)
        right_box = self._build_sim_results_column()
        sim_run_layout.addWidget(right_box)

        self._sim_stack.addWidget(sim_run_widget)

    def _build_sim_active_params_column(self) -> QWidget:
        widget = QWidget()
        widget.setMinimumWidth(260)
        widget.setMaximumWidth(300)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Card de parâmetros congelados
        grp_params = QGroupBox("Parâmetros ativos")
        p_layout = QVBoxLayout(grp_params)
        p_layout.setSpacing(6)

        self._lbl_frozen_r0 = QLabel("R₀: 2,5")
        self._lbl_frozen_beta = QLabel("β: Calibrando...")
        self._lbl_frozen_gamma = QLabel("γ: 0,10")
        self._lbl_frozen_mortality = QLabel("Mortalidade: 2,0%")
        self._lbl_frozen_incubation = QLabel("Incubação: 4 dias")
        self._lbl_frozen_interv = QLabel("Intervenção: Baixo")
        self._lbl_frozen_scenario = QLabel("Cenário: Global")
        self._lbl_frozen_seed = QLabel("Semente: 42")
        self._lbl_frozen_pz = QLabel("Paciente zero: Aleatório")

        for lbl in (
            self._lbl_frozen_r0,
            self._lbl_frozen_beta,
            self._lbl_frozen_gamma,
            self._lbl_frozen_mortality,
            self._lbl_frozen_incubation,
            self._lbl_frozen_interv,
            self._lbl_frozen_scenario,
            self._lbl_frozen_seed,
            self._lbl_frozen_pz,
        ):
            lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY_HEX};")
            p_layout.addWidget(lbl)

        layout.addWidget(grp_params)

        # Aviso RN01
        warn_box = QFrame()
        warn_box.setStyleSheet(
            "background-color: #1a160d; border: 1px solid #543f1b; "
            "border-radius: 6px; padding: 8px;"
        )
        w_layout = QVBoxLayout(warn_box)
        w_layout.setContentsMargins(8, 6, 8, 6)
        lbl_warn = QLabel("Para alterar parâmetros, reinicie a simulação (RN01).")
        lbl_warn.setWordWrap(True)
        lbl_warn.setStyleSheet("color: #ffb74d; font-size: 11px;")
        w_layout.addWidget(lbl_warn)
        layout.addWidget(warn_box)

        # Botões de Ação da Tela 5
        self._btn_save_current_config = QPushButton("Salvar configuração")
        self._btn_save_current_config.setObjectName("btnSecondary")
        self._btn_save_current_config.clicked.connect(self._on_save_config_from_run)
        layout.addWidget(self._btn_save_current_config)

        self._btn_export_dialog = QPushButton("Exportar dados...")
        self._btn_export_dialog.setObjectName("btnSecondary")
        self._btn_export_dialog.clicked.connect(self._open_export_dialog)
        layout.addWidget(self._btn_export_dialog)

        # Botão mantido para compatibilidade interna
        self._btn_export_csv = self._btn_export_dialog

        self._btn_restart_sim = QPushButton("Reiniciar simulação")
        self._btn_restart_sim.setObjectName("btnDanger")
        self._btn_restart_sim.clicked.connect(self._on_reset_requested)
        layout.addWidget(self._btn_restart_sim)

        layout.addStretch(1)
        return widget

    def _build_sim_center_column(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Barra de ferramentas superior do mapa (Zoom, Fit, Alternador Curvas e Legenda)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        btn_zin = QPushButton("+")
        btn_zin.setFixedSize(32, 28)
        btn_zin.setObjectName("btnSecondary")
        btn_zin.setToolTip("Aproximar mapa")

        btn_zout = QPushButton("−")
        btn_zout.setFixedSize(32, 28)
        btn_zout.setObjectName("btnSecondary")
        btn_zout.setToolTip("Afastar mapa")

        btn_fit = QPushButton("Ajustar mapa")
        btn_fit.setObjectName("btnSecondary")
        btn_fit.setFixedHeight(28)

        toolbar.addWidget(btn_zin)
        toolbar.addWidget(btn_zout)
        toolbar.addWidget(btn_fit)

        toolbar.addSpacing(10)

        # Alternador de exibição Mapa vs Curvas em tempo real
        self._btn_toggle_view = QPushButton("Ver curvas (Tela 7)")
        self._btn_toggle_view.setObjectName("btnSecondary")
        self._btn_toggle_view.setFixedHeight(28)
        self._btn_toggle_view.clicked.connect(self._on_toggle_center_view)
        toolbar.addWidget(self._btn_toggle_view)

        toolbar.addStretch(1)

        # Legenda SEIRD e Isolados
        leg_box = QHBoxLayout()
        leg_box.setSpacing(8)
        items = [
            ("S", COLOR_HEX_SUSCEPTIBLE),
            ("E", COLOR_HEX_EXPOSED),
            ("I", COLOR_HEX_INFECTED),
            ("R", COLOR_HEX_RECOVERED_NAT),
            ("D", COLOR_HEX_DECEASED),
            ("Isolado", COLOR_HEX_ISOLATED),
        ]
        for name, color in items:
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
            lbl = QLabel(name)
            lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED_HEX};")
            leg_box.addWidget(dot)
            leg_box.addWidget(lbl)
        toolbar.addLayout(leg_box)

        layout.addLayout(toolbar)

        # Stack central contendo o Mapa e o Gráfico da Tela 7
        self._center_stack = QStackedWidget()

        # Vista 0: Mapa QPainter
        self._map_view = MapView()
        self._map_view.set_world(self._world)
        btn_zin.clicked.connect(self._map_view._on_zoom_in_clicked)
        btn_zout.clicked.connect(self._map_view._on_zoom_out_clicked)
        btn_fit.clicked.connect(self._map_view._on_fit_clicked)
        self._center_stack.addWidget(self._map_view)

        # Vista 1: Gráficos SEIRD (Tela 7)
        self._charts_view = ChartsView()
        self._charts_view.back_to_map_requested.connect(self._on_back_to_map_clicked)
        self._center_stack.addWidget(self._charts_view)

        layout.addWidget(self._center_stack, stretch=1)

        # Barra do Player inferior (RF04, RF11)
        self._player_bar = PlayerBar(self._playback)
        layout.addWidget(self._player_bar)

        return widget

    def _build_sim_results_column(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(290)
        scroll.setMaximumWidth(355)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(10)

        # Card Resultados da Epidemia (RF21, RF24)
        grp_epi = QGroupBox("Resumo da epidemia")
        epi_layout = QVBoxLayout(grp_epi)
        epi_layout.setSpacing(6)

        # Destaque de Casos Ativos
        self._lbl_res_active_big = QLabel("0")
        self._lbl_res_active_big.setStyleSheet(
            f"font-size: 26px; font-weight: bold; color: {COLOR_HEX_INFECTED};"
        )
        lbl_active_tag = QLabel("Casos ativos no dia")
        lbl_active_tag.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED_HEX};")
        epi_layout.addWidget(self._lbl_res_active_big)
        epi_layout.addWidget(lbl_active_tag)

        self._lbl_res_peak_active = QLabel("Pico de ativos: --")
        self._lbl_res_peak_active_day = QLabel("Dia do pico: --")
        self._lbl_res_duration = QLabel("Duração do surto: --")
        self._lbl_res_deaths = QLabel("Óbitos totais: --")
        self._lbl_res_mortality = QLabel("Letalidade: --")
        self._lbl_res_eff_r0 = QLabel("R₀ efetivo estimado: --")

        for lbl in (
            self._lbl_res_peak_active,
            self._lbl_res_peak_active_day,
            self._lbl_res_duration,
            self._lbl_res_deaths,
            self._lbl_res_mortality,
            self._lbl_res_eff_r0,
        ):
            lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY_HEX};")
            epi_layout.addWidget(lbl)

        layout.addWidget(grp_epi)

        # Card Comparação Científica (RF14)
        grp_comp = QGroupBox("Comparação científica (RF14)")
        comp_layout = QVBoxLayout(grp_comp)
        comp_layout.setSpacing(4)

        self._lbl_res_comp_status = QLabel("Indisponível (nenhuma pandemia real carregada)")
        self._lbl_res_comp_status.setWordWrap(True)
        self._lbl_res_comp_status.setStyleSheet(
            "color: #78909c; font-style: italic; font-size: 11px;"
        )

        self._lbl_res_comp_cases_mse = QLabel("• MSE Casos: --")
        self._lbl_res_comp_deaths_mse = QLabel("• MSE Mortes: --")
        self._lbl_res_comp_peak_diff = QLabel("• Dif. Pico Novos/Dia: --")
        self._lbl_res_comp_final_diff = QLabel("• Dif. Tamanho Final: --")

        for lbl in (
            self._lbl_res_comp_status,
            self._lbl_res_comp_cases_mse,
            self._lbl_res_comp_deaths_mse,
            self._lbl_res_comp_peak_diff,
            self._lbl_res_comp_final_diff,
        ):
            lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY_HEX};")
            comp_layout.addWidget(lbl)

        layout.addWidget(grp_comp)

        # Card Análise da Rede (M1 & M2 — RF16, RF18, RF19, RF20)
        grp_net = QGroupBox("Métricas da rede (M1 / M2)")
        net_layout = QVBoxLayout(grp_net)
        net_layout.setSpacing(4)

        sample_box = QHBoxLayout()
        sample_box.addWidget(QLabel("Amostra:"))
        self._spin_sample_size = QSpinBox()
        self._spin_sample_size.setRange(5, 500)
        self._spin_sample_size.setValue(30)
        sample_box.addWidget(self._spin_sample_size)
        net_layout.addLayout(sample_box)

        self._btn_calc_net = QPushButton("Calcular análise de rede")
        self._btn_calc_net.setObjectName("btnSecondary")
        self._btn_calc_net.clicked.connect(self._on_calc_network_clicked)
        net_layout.addWidget(self._btn_calc_net)

        self._lbl_net_vertices = QLabel("Vértices no grafo: --")
        self._lbl_net_components = QLabel("Componentes conexas (M1): --")
        self._lbl_net_tarjan = QLabel("Pontes / articulações (M2): --")
        self._lbl_net_deg_avg = QLabel("Grau médio: --")
        self._lbl_net_deg_max = QLabel("Grau máximo: --")
        self._lbl_net_betweenness = QLabel("Top intermediação: --")
        self._lbl_net_clustering = QLabel("Agrupamento médio: --")
        self._lbl_net_communities = QLabel("Comunidades (países): --")

        for lbl in (
            self._lbl_net_vertices,
            self._lbl_net_components,
            self._lbl_net_tarjan,
            self._lbl_net_deg_avg,
            self._lbl_net_deg_max,
            self._lbl_net_betweenness,
            self._lbl_net_clustering,
            self._lbl_net_communities,
        ):
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY_HEX};")
            net_layout.addWidget(lbl)

        layout.addWidget(grp_net)

        # Card Caminho Epidemiológico (M1 — Dijkstra RF17 + BFS/DFS RF16)
        grp_path = QGroupBox("Caminho mínimo (M1 — Dijkstra / BFS)")
        path_layout = QVBoxLayout(grp_path)
        path_layout.setSpacing(5)

        src_row = QHBoxLayout()
        src_row.addWidget(QLabel("Origem:"))
        self._combo_path_src = QComboBox()
        src_row.addWidget(self._combo_path_src, stretch=1)
        path_layout.addLayout(src_row)

        dst_row = QHBoxLayout()
        dst_row.addWidget(QLabel("Destino:"))
        self._combo_path_dst = QComboBox()
        dst_row.addWidget(self._combo_path_dst, stretch=1)
        path_layout.addLayout(dst_row)

        self._populate_path_combos()

        self._btn_calc_path = QPushButton("Calcular rota (Dijkstra / BFS)")
        self._btn_calc_path.setObjectName("btnSecondary")
        self._btn_calc_path.clicked.connect(self._on_calc_shortest_path_clicked)
        path_layout.addWidget(self._btn_calc_path)

        self._lbl_path_route = QLabel("Rota: --")
        self._lbl_path_cost = QLabel("Distância efetiva −ln(p): --")
        self._lbl_path_traversal = QLabel("BFS / DFS: --")

        for lbl in (self._lbl_path_route, self._lbl_path_cost, self._lbl_path_traversal):
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY_HEX};")
            path_layout.addWidget(lbl)

        layout.addWidget(grp_path)
        layout.addStretch(1)

        scroll.setWidget(widget)
        return scroll

    def _populate_path_combos(self) -> None:
        """Popula os seletores de país de origem e destino a partir do objeto World."""
        self._combo_path_src.blockSignals(True)
        self._combo_path_dst.blockSignals(True)
        self._combo_path_src.clear()
        self._combo_path_dst.clear()

        for iso3 in self._world.country_codes:
            name = self._world.country_names.get(iso3, iso3)
            label = f"{name} ({iso3})"
            self._combo_path_src.addItem(label, iso3)
            self._combo_path_dst.addItem(label, iso3)

        if self._combo_path_src.count() > 0:
            idx_bra = self._combo_path_src.findData("BRA")
            self._combo_path_src.setCurrentIndex(idx_bra if idx_bra >= 0 else 0)
        if self._combo_path_dst.count() > 1:
            idx_dst = self._combo_path_dst.findData("GIN")
            if idx_dst < 0:
                idx_dst = 1 if self._combo_path_src.currentIndex() == 0 else 0
            self._combo_path_dst.setCurrentIndex(idx_dst)

        self._combo_path_src.blockSignals(False)
        self._combo_path_dst.blockSignals(False)

    def _setup_real_pandemics_tab(self) -> None:
        layout = QVBoxLayout(self._tab_real)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._real_stack = QStackedWidget()
        layout.addWidget(self._real_stack)

        # Página 0: Tela 8 (Seleção de Pandemia)
        self._page_real_selection = self._build_real_selection_page()
        self._real_stack.addWidget(self._page_real_selection)

        # Página 1: Tela 9 (Reprodução do Fluxo Real)
        self._page_real_playback = self._build_real_playback_page()
        self._real_stack.addWidget(self._page_real_playback)

    def _build_real_selection_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header = QVBoxLayout()
        header.setSpacing(4)
        lbl_title = QLabel("Histórico de Pandemias Reais (RF09)")
        lbl_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TEXT_PRIMARY_HEX};")
        lbl_desc = QLabel(
            "Selecione uma pandemia histórica para reproduzir a disseminação real no mapa "
            "mundial (A12) e comparar com as previsões teóricas do simulador (RF14)."
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED_HEX};")
        header.addWidget(lbl_title)
        header.addWidget(lbl_desc)
        layout.addLayout(header)

        # Grid 2x2 com os 4 Cards das Pandemias (Tela 8)
        grid = QGridLayout()
        grid.setSpacing(16)

        self._pandemics_info = [
            (
                "covid19",
                "COVID-19 (SARS-CoV-2)",
                "2020 – 2022",
                "Global",
                "Disseminação mundial em larga escala, impacto no transporte aéreo e 229 países.",
            ),
            (
                "ebola",
                "Ebola (África Ocidental)",
                "2014 – 2016",
                "Regional",
                "Surto severo na Guiné, Libéria e Serra Leoa com contenção comunitária.",
            ),
            (
                "h1n1",
                "H1N1 (Gripe Suína)",
                "2009 – 2010",
                "Global",
                "Disseminação internacional por passageiros e alta suscetibilidade populacional.",
            ),
            (
                "sars",
                "SARS-CoV-1",
                "2003",
                "Global",
                "Primeiro alerta pandêmico do século XXI, controlado após medidas de isolamento.",
            ),
        ]

        # Mantém QListWidget para compatibilidade com testes unitários existentes
        self._list_pandemics = QListWidget()
        self._list_pandemics.hide()
        for _p_id, p_name, p_per, p_sc, _ in self._pandemics_info:
            item = QListWidgetItem(f"{p_name}\n  {p_per} · {p_sc}")
            self._list_pandemics.addItem(item)
        layout.addWidget(self._list_pandemics)

        for idx, (p_id, p_name, p_per, p_sc, p_desc) in enumerate(self._pandemics_info):
            card = PandemicCard(p_id, p_name, p_per, p_sc, p_desc)
            card.open_requested.connect(self._load_pandemic_by_id)
            row = idx // 2
            col = idx % 2
            grid.addWidget(card, row, col)

        layout.addLayout(grid)

        self._lbl_real_status = QLabel("Status: Nenhuma pandemia real carregada.")
        self._lbl_real_status.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED_HEX};")
        layout.addWidget(self._lbl_real_status)

        layout.addStretch(1)
        return widget

    def _build_real_playback_page(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        # Coluna Esquerda: Informações e Voltar
        left_box = QWidget()
        left_box.setMinimumWidth(260)
        left_box.setMaximumWidth(300)
        l_layout = QVBoxLayout(left_box)
        l_layout.setContentsMargins(0, 0, 0, 0)
        l_layout.setSpacing(10)

        btn_back_surto = QPushButton("← Todos os surtos")
        btn_back_surto.setObjectName("btnSecondary")
        btn_back_surto.clicked.connect(self._on_unload_pandemic_clicked)
        l_layout.addWidget(btn_back_surto)

        grp_pinfo = QGroupBox("Pandemia selecionada")
        pi_layout = QVBoxLayout(grp_pinfo)
        self._lbl_real_active_name = QLabel("SARS-CoV-1")
        self._lbl_real_active_name.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {ACCENT_TEAL_HEX};"
        )
        self._lbl_real_active_desc = QLabel("Dados históricos agregados por país.")
        self._lbl_real_active_desc.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED_HEX};")
        pi_layout.addWidget(self._lbl_real_active_name)
        pi_layout.addWidget(self._lbl_real_active_desc)
        l_layout.addWidget(grp_pinfo)

        btn_compare_model = QPushButton("Comparar com modelo")
        btn_compare_model.setObjectName("btnPrimary")
        btn_compare_model.clicked.connect(self._update_comparison_metrics)
        l_layout.addWidget(btn_compare_model)

        l_layout.addStretch(1)
        layout.addWidget(left_box)

        # Coluna Central: Mapa Real com Escala de Incidência (A12)
        center_box = QWidget()
        c_layout = QVBoxLayout(center_box)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(6)

        # Barra de ferramentas do mapa real com a legenda de 6 classes (A12)
        r_toolbar = QHBoxLayout()
        r_toolbar.setSpacing(8)

        lbl_map_hdr = QLabel("Incidência por 100 mil hab. (A12)")
        lbl_map_hdr.setStyleSheet(f"font-weight: bold; color: {TEXT_PRIMARY_HEX};")
        r_toolbar.addWidget(lbl_map_hdr)
        r_toolbar.addStretch(1)

        scale_items = [
            ("< 10", "#2d3748"),
            ("10–49", "#fff5f0"),
            ("50–99", "#fee0d2"),
            ("100–499", "#fc9272"),
            ("500–999", "#ef3b2c"),
            ("1.000+", "#99000d"),
        ]
        for s_lbl, s_col in scale_items:
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background-color: {s_col}; border-radius: 4px;")
            lbl_s = QLabel(s_lbl)
            lbl_s.setStyleSheet(f"font-size: 10px; color: {TEXT_MUTED_HEX};")
            r_toolbar.addWidget(dot)
            r_toolbar.addWidget(lbl_s)

        c_layout.addLayout(r_toolbar)

        self._real_map_view = MapView()
        self._real_map_view.set_world(self._world)
        c_layout.addWidget(self._real_map_view, stretch=1)

        # Player da Pandemia Real
        self._real_player_bar = PlayerBar(self._playback)
        c_layout.addWidget(self._real_player_bar)
        layout.addWidget(center_box, stretch=1)

        # Coluna Direita: Casos, Mortes, Recuperados e Comparação RF14
        right_box = QWidget()
        right_box.setMinimumWidth(260)
        right_box.setMaximumWidth(300)
        r_layout = QVBoxLayout(right_box)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(10)

        grp_tot = QGroupBox("Totais acumulados")
        t_layout = QVBoxLayout(grp_tot)
        self._lbl_real_cases_tot = QLabel("Casos: --")
        self._lbl_real_deaths_tot = QLabel("Óbitos: --")
        self._lbl_real_rec_tot = QLabel("Recuperados: Não disponível")
        for lbl in (self._lbl_real_cases_tot, self._lbl_real_deaths_tot, self._lbl_real_rec_tot):
            lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY_HEX};")
            t_layout.addWidget(lbl)
        r_layout.addWidget(grp_tot)

        # Card de Comparação RF14 na Tela 9
        grp_comp9 = QGroupBox("Comparação RF14")
        c9_layout = QVBoxLayout(grp_comp9)
        self._lbl_real_comp_summary = QLabel("Aguardando comparação...")
        self._lbl_real_comp_summary.setWordWrap(True)
        self._lbl_real_comp_summary.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED_HEX};")
        c9_layout.addWidget(self._lbl_real_comp_summary)
        r_layout.addWidget(grp_comp9)

        r_layout.addStretch(1)
        layout.addWidget(right_box)

        return widget

    def _connect_signals(self) -> None:
        # StartScreen (Tela 1)
        self._start_screen.simulation_requested.connect(lambda: self._tabs.setCurrentIndex(1))
        self._start_screen.real_pandemics_requested.connect(lambda: self._tabs.setCurrentIndex(2))
        self._start_screen.load_config_requested.connect(self._on_load_config_from_start_screen)

        # Config Panel (Tela 2)
        self._config_panel.back_requested.connect(lambda: self._tabs.setCurrentIndex(0))
        self._config_panel.start_requested.connect(self._on_start_simulation)
        self._config_panel.calibrate_requested.connect(self._on_calibrate_beta)
        self._config_panel.config_changed.connect(self._on_config_changed)

        # Simulation Thread
        self._sim_thread.day_ready.connect(self._on_day_recorded)
        self._sim_thread.calibration_done.connect(self._on_calibration_done)
        self._sim_thread.simulation_finished.connect(self._on_simulation_finished)
        self._sim_thread.error_occurred.connect(self._on_thread_error)

        # Player Bars
        self._player_bar.day_changed.connect(self._on_playback_day_changed)
        self._player_bar.reset_requested.connect(self._on_reset_requested)
        self._real_player_bar.day_changed.connect(self._on_playback_day_changed)
        self._real_player_bar.reset_requested.connect(self._on_unload_pandemic_clicked)

    def _on_toggle_center_view(self) -> None:
        if self._center_stack.currentIndex() == 0:
            self._center_stack.setCurrentIndex(1)
            self._btn_toggle_view.setText("Ver mapa")
        else:
            self._center_stack.setCurrentIndex(0)
            self._btn_toggle_view.setText("Ver curvas (Tela 7)")

    def _on_back_to_map_clicked(self) -> None:
        self._center_stack.setCurrentIndex(0)
        self._btn_toggle_view.setText("Ver curvas (Tela 7)")

    def _on_load_config_from_start_screen(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Carregar Configuração",
            "",
            "Arquivos JSON (*.json)",
        )
        if path:
            try:
                cfg = load_config(path)
                self._config_panel.apply_simulation_config(cfg)
                self._tabs.setCurrentIndex(1)
                self.statusBar().showMessage("Configuração carregada com sucesso!", 5000)
            except EpidemiaError as exc:
                self.show_error_dialog("Erro ao Carregar", str(exc))

    def _on_save_config_from_run(self) -> None:
        try:
            cfg = self._session.config or self._config_panel.get_simulation_config()
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar Configuração",
                "cenario_config.json",
                "Arquivos JSON (*.json)",
            )
            if path:
                save_config(path, cfg)
                self.statusBar().showMessage(f"Configuração salva em {path}", 5000)
                QMessageBox.information(self, "Sucesso", "Configuração salva com sucesso!")
        except EpidemiaError as exc:
            self.show_error_dialog("Erro ao Salvar", str(exc))

    def _open_export_dialog(self) -> None:
        timeline = self._session.timeline() if self._session.is_started else None
        dlg = ExportDialog(timeline, self._charts_view, self)
        dlg.exec()

    def _on_load_pandemic_clicked(self) -> None:
        row = self._list_pandemics.currentRow()
        if row < 0 or row >= len(self._pandemics_info):
            row = 0
        p_id, p_name, _, _, _ = self._pandemics_info[row]
        self._load_pandemic_by_id(p_id, p_name)

    def _load_pandemic_by_id(self, p_id: str, p_name: str, series: Any = None) -> None:
        """Carrega pandemia histórica e conecta player, gráficos e mapa à RealTimeline."""
        try:
            if self._sim_thread.isRunning():
                self._sim_thread.stop()
                self._sim_thread.wait(1000)

            timeline = self._real_session.load_pandemic(p_id, series=series)
            self._is_real_flow = True

            self._playback.attach_timeline(timeline)
            self._player_bar.update_state()
            self._real_player_bar.update_state()

            self._charts_view.update_timeline_data(timeline, current_day=0)
            self._update_map_for_current_day()
            self._update_epidemic_summary()

            # Atualiza textos da Tela 9
            self._lbl_real_active_name.setText(p_name)
            self._lbl_real_active_desc.setText(
                f"{timeline.days_available} dias históricos gravados."
            )

            self._lbl_real_status.setText(
                f"Pandemia {p_name} carregada com sucesso! "
                f"({timeline.days_available} dias históricos disponíveis)."
            )
            self._lbl_real_status.setStyleSheet("color: #4cd7b4; font-weight: bold;")

            # Muda para a Tela 9 dentro da aba Pandemias reais
            self._real_stack.setCurrentIndex(1)
            self._tabs.setCurrentIndex(2)

        except FileNotFoundError:
            msg = (
                f"Arquivo '{p_id}.csv' não encontrado em data/processed/.\n"
                "A validação com dados reais fica pendente por falta dos arquivos do M4."
            )
            self._lbl_real_status.setText(msg)
            self._lbl_real_status.setStyleSheet("color: #ffb74d; font-weight: bold;")
        except EpidemiaError as exc:
            self.show_error_dialog("Erro ao Carregar Pandemia", str(exc))

    def _on_unload_pandemic_clicked(self) -> None:
        """Descarrega a pandemia real e retorna à Tela 8 de seleção."""
        self._is_real_flow = False
        self._playback.detach_timeline()
        self._charts_view.clear()
        self._map_view.set_day_data(None, None, is_real_flow=False)
        self._real_map_view.set_day_data(None, None, is_real_flow=False)
        self._player_bar.update_state()
        self._real_player_bar.update_state()
        self._reset_epidemic_summary_labels()

        self._lbl_real_status.setText("Pandemia real descarregada. Pronto para seleção.")
        self._lbl_real_status.setStyleSheet("color: #78909c;")
        self._real_stack.setCurrentIndex(0)

    def _on_calibrate_beta(self, config: SimulationConfig) -> None:
        try:
            self._session.configure(config)
            beta = self._session.calibrate_beta()
            self._config_panel.set_calibrated_beta(beta)
        except EpidemiaError as exc:
            self.show_error_dialog("Erro na Calibração", str(exc))

    def _on_calibration_done(self, beta: float) -> None:
        self._config_panel.set_calibrated_beta(beta)

    def _on_config_changed(self, config: SimulationConfig) -> None:
        if not self._session.is_started:
            self._session.configure(config)

    def _on_start_simulation(self, config: SimulationConfig, patient_zero: Any) -> None:
        try:
            if self._sim_thread.isRunning():
                self._sim_thread.stop()
                self._sim_thread.wait(1000)

            self._is_real_flow = False
            self._session.reset()
            self._session.configure(config)

            # Atualiza resumo dos parâmetros congelados na Tela 5
            self._lbl_frozen_r0.setText(f"R₀: {format_number_br(config.r0, 1)}")
            self._lbl_frozen_gamma.setText(f"γ: {format_number_br(config.exit_rate_gamma, 2)}")
            self._lbl_frozen_mortality.setText(
                f"Mortalidade: {format_percent_br(config.mortality, 1)}"
            )
            self._lbl_frozen_incubation.setText(
                f"Incubação: {format_number_br(config.incubation_days, 0)} dias"
            )
            self._lbl_frozen_interv.setText(
                f"Intervenção: {config.intervention_level.capitalize()}"
            )
            self._lbl_frozen_scenario.setText(f"Cenário: {config.scenario.capitalize()}")
            self._lbl_frozen_seed.setText(f"Semente: {config.seed}")
            if config.patient_zero:
                self._lbl_frozen_pz.setText(f"Paciente zero: #{config.patient_zero[0]}")
            else:
                self._lbl_frozen_pz.setText("Paciente zero: Aleatório")

            self._config_panel.set_running_state(True)
            self._sim_stack.setCurrentIndex(1)  # Comuta para Tela 5 de execução

            self._sim_thread.set_session(self._session)
            self._sim_thread.start()

        except EpidemiaError as exc:
            self.show_error_dialog("Erro ao Iniciar Simulação", str(exc))

    def _on_day_recorded(self, day: int) -> None:
        timeline = self._session.timeline()
        if self._playback.timeline != timeline:
            self._playback.attach_timeline(timeline)

        self._player_bar.update_state()
        self._charts_view.update_timeline_data(timeline, current_day=self._playback.current_day)

        if self._playback.is_at_end or self._playback.current_day == day - 1:
            self._playback.set_day(day)
            self._player_bar.update_state()
            self._update_map_for_current_day()

        self._update_epidemic_summary()

    def _on_simulation_finished(self) -> None:
        self._config_panel.set_running_state(False)
        self._update_epidemic_summary()

    def _on_thread_error(self, message: str) -> None:
        self._config_panel.set_running_state(False)
        self.show_error_dialog("Erro de Execução", message)

    def _on_playback_day_changed(self, day: int) -> None:
        self._update_map_for_current_day()
        self._charts_view.set_current_day(day)

    def _update_map_for_current_day(self) -> None:
        if self._is_real_flow:
            counts = self._playback.current_country_counts()
            self._map_view.set_day_data(None, counts, is_real_flow=True)
            self._real_map_view.set_day_data(None, counts, is_real_flow=True)

            # Atualiza totais da Tela 9
            if counts:
                tot_c = sum(c.infected for c in counts)
                tot_d = sum(c.deceased for c in counts)
                tot_r = sum(c.recovered for c in counts)
                self._lbl_real_cases_tot.setText(f"Casos acumulados: {format_number_br(tot_c)}")
                self._lbl_real_deaths_tot.setText(f"Óbitos acumulados: {format_number_br(tot_d)}")
                if tot_r > 0:
                    self._lbl_real_rec_tot.setText(
                        f"Recuperados acumulados: {format_number_br(tot_r)}"
                    )
                else:
                    self._lbl_real_rec_tot.setText("Recuperados: Não disponível")
        else:
            states = self._playback.current_vertex_states()
            counts = self._playback.current_country_counts()
            self._map_view.set_day_data(states, counts, is_real_flow=False)

    def _update_epidemic_summary(self) -> None:
        timeline = None
        cfg = None
        if self._is_real_flow and self._real_session.is_loaded:
            timeline = self._real_session.timeline()
        elif self._session.is_started:
            timeline = self._session.timeline()
            cfg = self._session.config

        if timeline is None or timeline.days_available <= 0:
            self._reset_epidemic_summary_labels()
            return

        summary = compute_epidemic_summary_from_timeline(timeline, cfg)

        self._lbl_res_active_big.setText(format_number_br(summary.peak_active_cases))
        self._lbl_res_peak_active.setText(
            f"Pico de ativos: {format_number_br(summary.peak_active_cases)}"
        )
        self._lbl_res_peak_active_day.setText(f"Dia do pico: Dia {summary.peak_active_day}")
        self._lbl_res_duration.setText(f"Duração do surto: {summary.duration_days} dias")
        self._lbl_res_deaths.setText(f"Óbitos totais: {format_number_br(summary.total_deaths)}")
        self._lbl_res_mortality.setText(
            f"Letalidade: {format_percent_br(summary.mortality_fraction, 2)}"
        )

        if summary.effective_r0 is not None:
            r0_fmt = format_number_br(summary.effective_r0, 3)
            self._lbl_res_eff_r0.setText(f"R₀ efetivo estimado: {r0_fmt}")
        else:
            self._lbl_res_eff_r0.setText("R₀ efetivo: Não calculável na fase atual")

        self._update_comparison_metrics()

    def _update_comparison_metrics(self) -> None:
        """Atualiza a comparação entre a simulação atual e a pandemia real carregada (RF14)."""
        if not self._real_session.is_loaded:
            msg = "Indisponível (nenhuma pandemia real carregada)"
            self._lbl_res_comp_status.setText(f"Comparação (RF14): {msg}")
            self._lbl_res_comp_status.setStyleSheet("color: #78909c; font-style: italic;")
            self._lbl_res_comp_cases_mse.setText("• MSE Casos: --")
            self._lbl_res_comp_deaths_mse.setText("• MSE Mortes: --")
            self._lbl_res_comp_peak_diff.setText("• Dif. Pico Novos/Dia: --")
            self._lbl_res_comp_final_diff.setText("• Dif. Tamanho Final: --")
            self._lbl_real_comp_summary.setText(msg)
            return

        if not self._session.is_started or self._session.timeline().days_available <= 0:
            msg = "Indisponível (simulação não concluída ou sem dados)"
            self._lbl_res_comp_status.setText(f"Comparação (RF14): {msg}")
            self._lbl_res_comp_status.setStyleSheet("color: #78909c; font-style: italic;")
            self._lbl_res_comp_cases_mse.setText("• MSE Casos: --")
            self._lbl_res_comp_deaths_mse.setText("• MSE Mortes: --")
            self._lbl_res_comp_peak_diff.setText("• Dif. Pico Novos/Dia: --")
            self._lbl_res_comp_final_diff.setText("• Dif. Tamanho Final: --")
            self._lbl_real_comp_summary.setText(msg)
            return

        try:
            p_name = (self._real_session.current_pandemic or "real").upper()
            comp = compare_simulation_to_real(
                self._session.timeline(), self._real_session.timeline(), country=None
            )
            self._lbl_res_comp_status.setText(f"Comparação RF14 ({p_name}):")
            self._lbl_res_comp_status.setStyleSheet(f"color: {ACCENT_TEAL_HEX}; font-weight: bold;")

            self._lbl_res_comp_cases_mse.setText(
                f"• MSE Casos: {format_number_br(comp.cases_mse, 6)}"
            )
            self._lbl_res_comp_deaths_mse.setText(
                f"• MSE Mortes: {format_number_br(comp.deaths_mse, 6)}"
            )
            self._lbl_res_comp_peak_diff.setText(
                f"• Dif. Pico Novos/Dia: {comp.peak_day_difference:+d} dias"
            )
            self._lbl_res_comp_final_diff.setText(
                f"• Dif. Tamanho Final: {format_number_br(comp.final_size_difference, 4)}"
            )

            self._lbl_real_comp_summary.setText(
                f"Comparação ativa com {p_name}:\n"
                f"MSE Casos: {format_number_br(comp.cases_mse, 4)}\n"
                f"Dif. Pico: {comp.peak_day_difference:+d} dias"
            )
        except Exception as exc:
            msg = f"Indisponível ({exc})"
            self._lbl_res_comp_status.setText(f"Comparação RF14: {msg}")
            self._lbl_res_comp_status.setStyleSheet("color: #ef5350; font-style: italic;")
            self._lbl_res_comp_cases_mse.setText("• MSE Casos: --")
            self._lbl_res_comp_deaths_mse.setText("• MSE Mortes: --")
            self._lbl_res_comp_peak_diff.setText("• Dif. Pico Novos/Dia: --")
            self._lbl_res_comp_final_diff.setText("• Dif. Tamanho Final: --")
            self._lbl_real_comp_summary.setText(msg)

    def _reset_epidemic_summary_labels(self) -> None:
        self._lbl_res_active_big.setText("0")
        self._lbl_res_peak_active.setText("Pico de ativos: --")
        self._lbl_res_peak_active_day.setText("Dia do pico: --")
        self._lbl_res_duration.setText("Duração do surto: --")
        self._lbl_res_deaths.setText("Óbitos totais: --")
        self._lbl_res_mortality.setText("Letalidade: --")
        self._lbl_res_eff_r0.setText("R₀ efetivo estimado: --")
        self._update_comparison_metrics()

    def _on_reset_requested(self) -> None:
        if self._sim_thread.isRunning():
            self._sim_thread.stop()
            self._sim_thread.wait(1000)

        self._session.reset()
        self._playback.detach_timeline()
        self._config_panel.set_running_state(False)
        self._charts_view.clear()
        self._map_view.set_day_data(None, None)
        self._player_bar.update_state()
        self._reset_epidemic_summary_labels()

        # Retorna para a página de configuração (Tela 2)
        self._sim_stack.setCurrentIndex(0)

    def _on_calc_network_clicked(self) -> None:
        sample_size = self._spin_sample_size.value()
        self._btn_calc_net.setEnabled(False)
        self._btn_calc_net.setText("Calculando análise de rede...")

        self._network_worker = NetworkAnalysisWorker(
            self._world, sample_size=sample_size, parent=self
        )
        self._network_worker.analysis_finished.connect(self._on_network_analysis_finished)
        self._network_worker.analysis_failed.connect(self._on_network_analysis_failed)
        self._network_worker.start()

    def _on_network_analysis_finished(self, res: NetworkAnalysisResult) -> None:
        self._btn_calc_net.setEnabled(True)
        self._btn_calc_net.setText("Calcular análise de rede")

        self._lbl_net_vertices.setText(f"Vértices no grafo: {format_number_br(res.num_vertices)}")
        comp_pct = res.largest_component_size / res.num_vertices if res.num_vertices > 0 else 0.0
        self._lbl_net_components.setText(
            f"Componentes conexas (M1): {res.num_components} "
            f"(gigante: {format_number_br(res.largest_component_size)} · "
            f"{format_percent_br(comp_pct, 1)})"
        )
        self._lbl_net_tarjan.setText(
            f"Pontes / articulações (M2): {format_number_br(res.num_bridges)} pontes · "
            f"{format_number_br(res.num_articulation_points)} artic."
        )
        self._lbl_net_deg_avg.setText(f"Grau médio: {format_number_br(res.avg_degree, 2)}")
        self._lbl_net_deg_max.setText(f"Grau máx: {res.max_degree} (nó #{res.max_degree_vertex})")

        top_bet_str = ", ".join(
            f"#{v}:{format_number_br(val, 3)}" for v, val in res.top_betweenness[:3]
        )
        bet_display = top_bet_str if top_bet_str else "--"
        self._lbl_net_betweenness.setText(f"Top intermediação: {bet_display}")
        self._lbl_net_clustering.setText(
            f"Agrupamento médio: {format_number_br(res.avg_clustering, 3)}"
        )
        self._lbl_net_communities.setText(f"Comunidades (países): {res.num_communities}")

    def _on_network_analysis_failed(self, error: str) -> None:
        self._btn_calc_net.setEnabled(True)
        self._btn_calc_net.setText("Calcular análise de rede")
        self.show_error_dialog("Erro na Análise de Rede", error)

    def _on_calc_shortest_path_clicked(self) -> None:
        """Calcula e exibe o caminho mínimo (Dijkstra RF17) e busca (BFS/DFS RF16)."""
        src_iso = self._combo_path_src.currentData()
        dst_iso = self._combo_path_dst.currentData()
        if not src_iso or not dst_iso:
            return

        try:
            beta = self._session.calibrated_beta
            summary = compute_shortest_epidemic_path(
                self._world,
                str(src_iso),
                str(dst_iso),
                beta=beta,
            )
            if not summary.reachable:
                self._lbl_path_route.setText(
                    f"Rota ({summary.source_iso3} → {summary.target_iso3}): "
                    f"Inalcançável (componentes desconexas)"
                )
                self._lbl_path_cost.setText("Distância efetiva −ln(p): ∞ (prob: 0,0%)")
                self._lbl_path_traversal.setText(
                    f"BFS: ∞ saltos · Alcance DFS origem: "
                    f"{format_number_br(summary.dfs_reachable_count)} nós"
                )
            else:
                countries_str = " → ".join(summary.country_path)
                self._lbl_path_route.setText(
                    f"Rota: {countries_str} "
                    f"(#{summary.source_vertex} → #{summary.target_vertex}, "
                    f"{len(summary.vertex_path) - 1} arestas)"
                )
                dist_fmt = format_number_br(summary.effective_distance, 3)
                prob_fmt = format_percent_br(summary.path_probability, 2)
                self._lbl_path_cost.setText(
                    f"Distância efetiva −ln(p): {dist_fmt} (P = {prob_fmt})"
                )
                hops_val = summary.bfs_hops if summary.bfs_hops is not None else 0
                self._lbl_path_traversal.setText(
                    f"BFS: {hops_val} saltos · Alcance DFS: "
                    f"{format_number_br(summary.dfs_reachable_count)} nós"
                )
        except EpidemiaError as exc:
            self.show_error_dialog("Erro no Caminho Mínimo", str(exc))

    def _on_export_csv_clicked(self) -> None:
        if not self._session.is_started:
            self.show_error_dialog(
                "Exportação",
                "A simulação precisa ter iniciado para exportar o histórico.",
            )
            return

        timeline = self._session.timeline()
        if timeline.days_available <= 0:
            self.show_error_dialog("Exportação", "Nenhum dia gravado disponível para exportação.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Histórico da Simulação",
            "historico_simulacao.csv",
            "Arquivos CSV (*.csv)",
        )
        if path:
            try:
                n = export_timeline_csv(timeline, path)
                QMessageBox.information(self, "Sucesso", f"{n} dias exportados com sucesso em CSV!")
            except EpidemiaError as exc:
                self.show_error_dialog("Erro ao Exportar CSV", str(exc))

    def show_error_dialog(self, title: str, message: str) -> None:
        """Exibe erros de domínio em caixa de diálogo sem encerrar a aplicação (RNF08)."""
        QMessageBox.critical(self, title, message)

    def closeEvent(self, event) -> None:
        """Encerra threads trabalhadoras antes de fechar a janela."""
        if self._sim_thread.isRunning():
            self._sim_thread.stop()
            self._sim_thread.wait(1000)
        if self._network_worker is not None and self._network_worker.isRunning():
            self._network_worker.wait(1000)
        event.accept()
