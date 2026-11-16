"""Janela principal da aplicação (M5 — RF01, RF04, RF09, RF11, RF14, RF18, RF19, RF21, RNF08).

Integra as duas abas principais ("Simulação" e "Pandemias reais"), a thread de
simulação assíncrona, o mapa QPainter, o player temporal, os gráficos pyqtgraph,
o painel de resultados epidemiológicos e o worker de análise de redes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
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
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from epidemia.app.export import export_timeline_csv
from epidemia.app.panel_metrics import (
    NetworkAnalysisResult,
    compute_epidemic_summary_from_timeline,
    compute_network_analysis,
)
from epidemia.app.playback import PlaybackController
from epidemia.app.real_session import RealSession
from epidemia.app.simulation_session import SimulationSession
from epidemia.config import PROCESSED_DATA_DIR
from epidemia.core.errors import EpidemiaError
from epidemia.ui.charts_view import ChartsView
from epidemia.ui.config_panel import ConfigPanel
from epidemia.ui.map_view import MapView
from epidemia.ui.player_bar import PlayerBar
from epidemia.ui.simulation_thread import SimulationThread
from epidemia.ui.styles import DARK_THEME_QSS
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


class MainWindow(QMainWindow):
    """Janela principal do Simulador de Epidemias em Redes."""

    def __init__(self, world: World | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Simulador de Epidemias em Redes — Antigravity")
        self.resize(1340, 840)

        # Se nenhum mundo fornecido, inicia com o fixture sintético (M1)
        self._world: World = (
            world if world is not None else create_synthetic_world(total_vertices=100)
        )
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

        # Aplica folha de estilo do tema escuro
        self.setStyleSheet(DARK_THEME_QSS)

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)

        self._tabs = QTabWidget(self)
        root_layout.addWidget(self._tabs)

        # Aba 1: Simulação
        self._tab_sim = QWidget()
        self._setup_simulation_tab()
        self._tabs.addTab(self._tab_sim, "🔬 Simulação")

        # Aba 2: Pandemias reais (RF09)
        self._tab_real = QWidget()
        self._setup_real_pandemics_tab()
        self._tabs.addTab(self._tab_real, "🌐 Pandemias reais")

    def _setup_simulation_tab(self) -> None:
        sim_layout = QHBoxLayout(self._tab_sim)
        sim_layout.setContentsMargins(6, 6, 6, 6)
        sim_layout.setSpacing(8)

        # Coluna 1 (Esquerda): Painel de Configuração
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        scroll_config = QScrollArea()
        scroll_config.setWidgetResizable(True)
        scroll_config.setFrameShape(QFrame.Shape.NoFrame)

        self._config_panel = ConfigPanel()
        scroll_config.setWidget(self._config_panel)
        left_layout.addWidget(scroll_config, stretch=1)

        self._btn_export_csv = QPushButton("📊 Exportar CSV da Linha do Tempo")
        self._btn_export_csv.setToolTip("Exporta o histórico da simulação em arquivo CSV (RF08)")
        self._btn_export_csv.clicked.connect(self._on_export_csv_clicked)
        left_layout.addWidget(self._btn_export_csv)

        left_widget.setMinimumWidth(320)
        left_widget.setMaximumWidth(400)

        # Coluna 2 (Centro): Mapa, Player e Gráficos
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(6)

        # Mapa com QPainter
        self._map_view = MapView()
        self._map_view.set_world(self._world)

        # Barra do Player
        self._player_bar = PlayerBar(self._playback)

        # Gráficos com pyqtgraph
        self._charts_view = ChartsView()

        center_splitter = QSplitter(Qt.Orientation.Vertical)
        center_splitter.addWidget(self._map_view)
        center_splitter.addWidget(self._charts_view)
        center_splitter.setStretchFactor(0, 3)
        center_splitter.setStretchFactor(1, 2)

        center_layout.addWidget(center_splitter, stretch=1)
        center_layout.addWidget(self._player_bar)

        # Coluna 3 (Direita): Painel de Resultados Epidemiológicos e Análise de Rede
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # Grupo Métricas Epidemiológicas (RF21)
        grp_epi = QGroupBox("Resultados da Epidemia")
        form_epi = QVBoxLayout(grp_epi)
        form_epi.setSpacing(6)

        self._lbl_res_peak_active = QLabel("Pico de ativos: --")
        self._lbl_res_peak_active_day = QLabel("Dia do pico: --")
        self._lbl_res_duration = QLabel("Duração do surto: --")
        self._lbl_res_deaths = QLabel("Óbitos totais: --")
        self._lbl_res_mortality = QLabel("Letalidade: --")
        self._lbl_res_eff_r0 = QLabel("R0 efetivo estimado: --")
        self._lbl_res_comparison = QLabel("Comparação real (RF14): Indisponível (M4)")
        self._lbl_res_comparison.setStyleSheet("color: #78909c; font-style: italic;")

        form_epi.addWidget(self._lbl_res_peak_active)
        form_epi.addWidget(self._lbl_res_peak_active_day)
        form_epi.addWidget(self._lbl_res_duration)
        form_epi.addWidget(self._lbl_res_deaths)
        form_epi.addWidget(self._lbl_res_mortality)
        form_epi.addWidget(self._lbl_res_eff_r0)
        form_epi.addWidget(self._lbl_res_comparison)

        right_layout.addWidget(grp_epi)

        # Grupo Análise de Rede (RF18, RF19)
        grp_net = QGroupBox("Análise da Rede (M2)")
        form_net = QVBoxLayout(grp_net)
        form_net.setSpacing(6)

        sample_layout = QHBoxLayout()
        sample_layout.addWidget(QLabel("Amostra intermediação:"))
        self._spin_sample_size = QSpinBox()
        self._spin_sample_size.setRange(5, 500)
        self._spin_sample_size.setValue(30)
        sample_layout.addWidget(self._spin_sample_size)
        form_net.addLayout(sample_layout)

        self._btn_calc_net = QPushButton("⚙ Calcular análise de rede")
        self._btn_calc_net.clicked.connect(self._on_calc_network_clicked)
        form_net.addWidget(self._btn_calc_net)

        self._lbl_net_vertices = QLabel("Vértices no grafo: --")
        self._lbl_net_deg_avg = QLabel("Grau médio: --")
        self._lbl_net_deg_max = QLabel("Grau máximo: --")
        self._lbl_net_betweenness = QLabel("Top intermediação: --")
        self._lbl_net_clustering = QLabel("Agrupamento médio: --")
        self._lbl_net_communities = QLabel("Comunidades (países): --")

        form_net.addWidget(self._lbl_net_vertices)
        form_net.addWidget(self._lbl_net_deg_avg)
        form_net.addWidget(self._lbl_net_deg_max)
        form_net.addWidget(self._lbl_net_betweenness)
        form_net.addWidget(self._lbl_net_clustering)
        form_net.addWidget(self._lbl_net_communities)

        right_layout.addWidget(grp_net)
        right_layout.addStretch(1)

        right_widget.setMinimumWidth(260)
        right_widget.setMaximumWidth(320)

        # Adiciona ao layout da aba simulação
        sim_layout.addWidget(left_widget)
        sim_layout.addWidget(center_widget, stretch=1)
        sim_layout.addWidget(right_widget)

    def _setup_real_pandemics_tab(self) -> None:
        real_layout = QVBoxLayout(self._tab_real)
        real_layout.setContentsMargins(20, 20, 20, 20)
        real_layout.setSpacing(14)

        title = QLabel("Histórico de Pandemias Reais (RF09)")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #90caf9;")
        real_layout.addWidget(title)

        info_box = QGroupBox("Seleção de Pandemia")
        info_layout = QVBoxLayout(info_box)

        lbl_desc = QLabel(
            "Selecione uma pandemia histórica embutida no sistema para carregar a série "
            "temporal real.\nAo carregar, o player, os gráficos epidemiológicos e o mapa "
            "mundial passam a reproduzir os dados históricos agregados por país (RF09, RF12).\n"
            "Nota: O mapa desenha a intensidade de casos acumulados por 100 mil hab. (A12) "
            "sem renderizar vértices individuais."
        )
        lbl_desc.setStyleSheet("color: #b0bec5; font-size: 13px;")
        info_layout.addWidget(lbl_desc)

        self._pandemics_info = [
            (
                "covid19",
                "COVID-19 (SARS-CoV-2)",
                "2020–2022 · Escala global · 229 países e territórios",
            ),
            (
                "ebola",
                "Ebola (África Ocidental)",
                "2014–2016 · Foco regional: Guiné, Libéria, Serra Leoa",
            ),
            (
                "h1n1",
                "H1N1 (Gripe Suína)",
                "2009 · Disseminação aérea internacional",
            ),
            (
                "sars",
                "SARS-CoV-1",
                "2003 · Primeiro surto internacional do século XXI",
            ),
        ]

        self._list_pandemics = QListWidget()
        for _, name, detail in self._pandemics_info:
            item = QListWidgetItem(f"{name}\n  {detail}")
            self._list_pandemics.addItem(item)

        self._list_pandemics.setCurrentRow(0)
        self._list_pandemics.itemDoubleClicked.connect(self._on_load_pandemic_clicked)
        info_layout.addWidget(self._list_pandemics)

        btn_row = QHBoxLayout()
        self._btn_load_real = QPushButton("▶ Carregar Pandemia e Reproduzir no Player")
        self._btn_load_real.setStyleSheet(
            "background-color: #1976d2; color: white; font-weight: bold; padding: 8px 16px;"
        )
        self._btn_load_real.clicked.connect(self._on_load_pandemic_clicked)
        btn_row.addWidget(self._btn_load_real)

        self._btn_unload_real = QPushButton("⏹ Voltar para Simulação do Modelo")
        self._btn_unload_real.clicked.connect(self._on_unload_pandemic_clicked)
        btn_row.addWidget(self._btn_unload_real)

        info_layout.addLayout(btn_row)

        self._lbl_real_status = QLabel("Status: Nenhuma pandemia real carregada.")
        self._lbl_real_status.setStyleSheet("color: #90caf9; font-weight: bold;")
        info_layout.addWidget(self._lbl_real_status)

        real_layout.addWidget(info_box)
        real_layout.addStretch(1)

    def _connect_signals(self) -> None:
        # Config Panel
        self._config_panel.start_requested.connect(self._on_start_simulation)
        self._config_panel.calibrate_requested.connect(self._on_calibrate_beta)
        self._config_panel.config_changed.connect(self._on_config_changed)

        # Simulation Thread
        self._sim_thread.day_ready.connect(self._on_day_recorded)
        self._sim_thread.calibration_done.connect(self._on_calibration_done)
        self._sim_thread.simulation_finished.connect(self._on_simulation_finished)
        self._sim_thread.error_occurred.connect(self._on_thread_error)

        # Player Bar
        self._player_bar.day_changed.connect(self._on_playback_day_changed)
        self._player_bar.reset_requested.connect(self._on_reset_requested)

    def _on_load_pandemic_clicked(self) -> None:
        row = self._list_pandemics.currentRow()
        if row < 0 or row >= len(self._pandemics_info):
            return
        p_id, p_name, _ = self._pandemics_info[row]
        self._load_pandemic_by_id(p_id, p_name)

    def _load_pandemic_by_id(
        self, p_id: str, p_name: str, series: Any = None
    ) -> None:
        """Carrega pandemia histórica e conecta player, gráficos e mapa à RealTimeline."""
        try:
            if self._sim_thread.isRunning():
                self._sim_thread.stop()
                self._sim_thread.wait(1000)

            timeline = self._real_session.load_pandemic(p_id, series=series)
            self._is_real_flow = True

            # Anexa ao player controller
            self._playback.attach_timeline(timeline)
            self._player_bar.update_state()

            # Atualiza gráficos com a nova linha do tempo
            self._charts_view.update_timeline_data(timeline, current_day=0)

            # Atualiza o mapa no modo fluxo real (A12)
            self._update_map_for_current_day()

            # Atualiza o painel de resumo epidemiológico
            self._update_epidemic_summary()

            self._lbl_real_status.setText(
                f"Pandemia {p_name} carregada com sucesso! "
                f"({timeline.days_available} dias históricos disponíveis)."
            )
            self._lbl_real_status.setStyleSheet("color: #4caf50; font-weight: bold;")

            # Alterna para a aba de reprodução/visualização
            self._tabs.setCurrentIndex(0)

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
        """Descarrega a pandemia real e retorna o sistema ao estado de simulação sintética."""
        self._is_real_flow = False
        self._playback.detach_timeline()
        self._charts_view.clear()
        self._map_view.set_day_data(None, None, is_real_flow=False)
        self._player_bar.update_state()
        self._reset_epidemic_summary_labels()
        self._lbl_real_status.setText("Pandemia real descarregada. Sistema pronto para simulações.")
        self._lbl_real_status.setStyleSheet("color: #90caf9;")

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

            self._config_panel.set_running_state(True)
            self._sim_thread.set_session(self._session)
            self._sim_thread.start()

        except EpidemiaError as exc:
            self.show_error_dialog("Erro ao Iniciar Simulação", str(exc))

    def _on_day_recorded(self, day: int) -> None:
        timeline = self._session.timeline()
        if self._playback.timeline != timeline:
            self._playback.attach_timeline(timeline)

        self._player_bar.update_state()

        # Atualiza gráficos com todos os dias disponíveis
        self._charts_view.update_timeline_data(timeline, current_day=self._playback.current_day)

        # Se o player estiver no dia mais recente, avança junto
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
            # No fluxo real, vertex_states é None e o mapa pinta por país usando country_counts
            self._map_view.set_day_data(None, counts, is_real_flow=True)
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

        self._lbl_res_peak_active.setText(f"Pico de ativos: {summary.peak_active_cases:,}")
        self._lbl_res_peak_active_day.setText(f"Dia do pico: {summary.peak_active_day}")
        self._lbl_res_duration.setText(f"Duração do surto: {summary.duration_days} dias")
        self._lbl_res_deaths.setText(f"Óbitos totais: {summary.total_deaths:,}")
        self._lbl_res_mortality.setText(f"Letalidade: {summary.mortality_fraction * 100:.2f}%")

        if summary.effective_r0 is not None:
            self._lbl_res_eff_r0.setText(f"R0 efetivo estimado: {summary.effective_r0:.3f}")
        else:
            self._lbl_res_eff_r0.setText("R0 efetivo: Não calculável na fase atual")

    def _reset_epidemic_summary_labels(self) -> None:
        self._lbl_res_peak_active.setText("Pico de ativos: --")
        self._lbl_res_peak_active_day.setText("Dia do pico: --")
        self._lbl_res_duration.setText("Duração do surto: --")
        self._lbl_res_deaths.setText("Óbitos totais: --")
        self._lbl_res_mortality.setText("Letalidade: --")
        self._lbl_res_eff_r0.setText("R0 efetivo estimado: --")

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
        self._btn_calc_net.setText("⚙ Calcular análise de rede")

        self._lbl_net_vertices.setText(f"Vértices no grafo: {res.num_vertices:,}")
        self._lbl_net_deg_avg.setText(f"Grau médio: {res.avg_degree:.2f}")
        self._lbl_net_deg_max.setText(f"Grau máx: {res.max_degree} (nó #{res.max_degree_vertex})")

        top_bet_str = ", ".join(f"#{v}:{val:.3f}" for v, val in res.top_betweenness[:3])
        bet_display = top_bet_str if top_bet_str else "--"
        self._lbl_net_betweenness.setText(f"Top intermediação: {bet_display}")
        self._lbl_net_clustering.setText(f"Agrupamento médio: {res.avg_clustering:.3f}")
        self._lbl_net_communities.setText(f"Comunidades (países): {res.num_communities}")

    def _on_network_analysis_failed(self, error: str) -> None:
        self._btn_calc_net.setEnabled(True)
        self._btn_calc_net.setText("⚙ Calcular análise de rede")
        self.show_error_dialog("Erro na Análise de Rede", error)

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
