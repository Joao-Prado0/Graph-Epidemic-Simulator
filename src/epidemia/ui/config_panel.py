"""Painel de configuração da simulação (M5 — RF01, RF03, RF07, RF09, RF23; Tela 2).

Organizado em 3 colunas visuais alinhadas aos wireframes:
  01 Parâmetros da doença (R0, beta calibrado, gama, mortalidade, incubação)
  02 Intervenção (Níveis Baixo, Médio, Alto em cards interativos, eficácia da vacina 80%)
  03 Cenário e execução (Global/Regional, semente aleatória, paciente zero)
E rodapé de ações: Voltar, Calibrar beta, Salvar/Carregar configuração e Iniciar simulação.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from epidemia.app.config_io import load_config, save_config
from epidemia.core.epidemic.parameters import (
    DEFAULT_VACCINE_EFFICACY,
    INTERVENTION_TABLE,
    LEVEL_HIGH,
    LEVEL_LOW,
    LEVEL_MEDIUM,
    SimulationConfig,
)
from epidemia.core.errors import EpidemiaError
from epidemia.core.seeds import SUBSYSTEM_PATIENT_ZERO, SeedBook, derive_subsystem_seed
from epidemia.ui.styles import (
    ACCENT_TEAL_HEX,
    BORDER_LIGHT_HEX,
    BORDER_SUBTLE_HEX,
    TEXT_MUTED_HEX,
    TEXT_PRIMARY_HEX,
    TEXT_SECONDARY_HEX,
    format_number_br,
    format_percent_br,
)

if TYPE_CHECKING:
    from epidemia.world.world import World


def _format_intervention_card_texts(level: str) -> tuple[str, str]:
    """Formata os textos de isolamento e vacinação diretamente de INTERVENTION_TABLE (M3)."""
    params = INTERVENTION_TABLE[level]
    iso_pct = format_percent_br(params.isolation_daily_prob, decimals=0)
    iso_text = f"{iso_pct} de isolamento / {params.isolation_duration_days} dias"
    vac_pct = format_percent_br(params.vaccination_daily_fraction, decimals=1)
    vac_text = f"Vacinação no dia {params.vaccination_start_day} ({vac_pct} / dia)"
    return iso_text, vac_text


class InterventionCard(QFrame):
    """Cartão interativo somente leitura que exibe as regras de um nível de intervenção.

    Destaca-se com borda teal quando ativo e pode ser clicado para selecionar o nível.
    """

    clicked = Signal(str)

    def __init__(
        self,
        level_id: str,
        title: str,
        isolation_text: str,
        vaccination_text: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._level_id = level_id
        self._is_active = False

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self._lbl_title = QLabel(title)
        self._lbl_title.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY_HEX};"
        )
        layout.addWidget(self._lbl_title)

        self._lbl_isolation = QLabel(f"• {isolation_text}")
        self._lbl_isolation.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY_HEX};")
        layout.addWidget(self._lbl_isolation)

        self._lbl_vaccination = QLabel(f"• {vaccination_text}")
        self._lbl_vaccination.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY_HEX};")
        layout.addWidget(self._lbl_vaccination)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def set_active(self, active: bool) -> None:
        self._is_active = active
        self._update_style()

    def _update_style(self) -> None:
        if self._is_active:
            self.setStyleSheet(
                f"InterventionCard {{"
                f"  background-color: #162832;"
                f"  border: 1px solid {ACCENT_TEAL_HEX};"
                f"  border-radius: 6px;"
                f"}}"
            )
            self._lbl_title.setStyleSheet(
                f"font-size: 13px; font-weight: bold; color: {ACCENT_TEAL_HEX};"
            )
        else:
            self.setStyleSheet(
                f"InterventionCard {{"
                f"  background-color: #0b141a;"
                f"  border: 1px solid {BORDER_SUBTLE_HEX};"
                f"  border-radius: 6px;"
                f"}}"
                f"InterventionCard:hover {{"
                f"  border-color: {BORDER_LIGHT_HEX};"
                f"}}"
            )
            self._lbl_title.setStyleSheet(
                f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY_HEX};"
            )

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event is not None:
            super().mousePressEvent(event)
        self.clicked.emit(self._level_id)


class ConfigPanel(QWidget):
    """Painel de configuração de cenário com layout de 3 colunas (Tela 2)."""

    start_requested = Signal(SimulationConfig, object)  # config, patient_zero
    calibrate_requested = Signal(SimulationConfig)
    config_changed = Signal(SimulationConfig)
    back_requested = Signal()

    def __init__(self, parent: QWidget | None = None, world: World | None = None) -> None:
        super().__init__(parent)
        self._world: World | None = world
        self._calibrated_beta_value: float | None = None
        self._seed_click_count: int = 0
        self._pz_pick_count: int = 0
        self._init_ui()
        if world is not None:
            self.set_world(world)

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 12, 16, 12)
        root_layout.setSpacing(10)

        # Cabeçalho da tela
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        lbl_title = QLabel("Configuração do Cenário Epidêmico")
        lbl_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TEXT_PRIMARY_HEX};")
        lbl_subtitle = QLabel(
            "Defina os parâmetros da doença, níveis de intervenção e rede para iniciar a simulação."
        )
        lbl_subtitle.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED_HEX};")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        root_layout.addLayout(header_layout)

        # Área de rolagem para acomodar as 3 colunas com elegância
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        cols_layout = QHBoxLayout(content_widget)
        cols_layout.setContentsMargins(0, 4, 0, 4)
        cols_layout.setSpacing(12)

        # Coluna 1: 01 Parâmetros da doença
        col1 = self._build_column_disease()
        cols_layout.addWidget(col1, stretch=1)

        # Coluna 2: 02 Intervenção
        col2 = self._build_column_interventions()
        cols_layout.addWidget(col2, stretch=1)

        # Coluna 3: 03 Cenário e execução
        col3 = self._build_column_scenario_execution()
        cols_layout.addWidget(col3, stretch=1)

        scroll.setWidget(content_widget)
        root_layout.addWidget(scroll, stretch=1)

        # Rodapé de Ações (Footer)
        footer = self._build_footer()
        root_layout.addLayout(footer)

    def _build_column_disease(self) -> QGroupBox:
        grp = QGroupBox("01 Parâmetros da doença")
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(10)

        # R0
        layout.addWidget(QLabel("R₀ (Número básico de reprodução):"))
        r0_box = QHBoxLayout()
        self._spin_r0 = QDoubleSpinBox()
        self._spin_r0.setRange(0.1, 20.0)
        self._spin_r0.setSingleStep(0.1)
        self._spin_r0.setValue(2.5)
        self._spin_r0.setCursor(Qt.CursorShape.PointingHandCursor)

        self._slider_r0 = QSlider(Qt.Orientation.Horizontal)
        self._slider_r0.setRange(1, 200)
        self._slider_r0.setValue(25)
        self._slider_r0.setCursor(Qt.CursorShape.PointingHandCursor)

        self._spin_r0.valueChanged.connect(self._on_spin_r0_changed)
        self._slider_r0.valueChanged.connect(self._on_slider_r0_changed)

        r0_box.addWidget(self._spin_r0)
        r0_box.addWidget(self._slider_r0, stretch=1)
        layout.addLayout(r0_box)

        # Faixa de status de calibração de beta com botão de calibração integrado
        self._beta_card = QFrame()
        self._beta_card.setObjectName("betaCard")
        self._beta_card.setStyleSheet(
            f"QFrame#betaCard {{"
            f"  background-color: #0b171e;"
            f"  border: 1px solid #1c3545;"
            f"  border-left: 3px solid {ACCENT_TEAL_HEX};"
            f"  border-radius: 6px;"
            f"}}"
        )
        beta_layout = QVBoxLayout(self._beta_card)
        beta_layout.setContentsMargins(10, 8, 10, 8)
        beta_layout.setSpacing(4)

        beta_header_box = QHBoxLayout()
        beta_header_box.setSpacing(8)
        lbl_beta_hdr = QLabel("Taxa de transmissão (β):")
        lbl_beta_hdr.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED_HEX}; font-weight: bold;")
        beta_header_box.addWidget(lbl_beta_hdr)
        beta_header_box.addStretch(1)

        self._btn_calibrate = QPushButton("Calibrar β")
        self._btn_calibrate.setObjectName("btnPrimary")
        self._btn_calibrate.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_calibrate.setFixedHeight(26)
        self._btn_calibrate.setStyleSheet(
            "QPushButton#btnPrimary {  font-size: 11px; padding: 2px 10px; font-weight: bold;}"
        )
        self._btn_calibrate.clicked.connect(self._on_calibrate_clicked)
        beta_header_box.addWidget(self._btn_calibrate)
        beta_layout.addLayout(beta_header_box)

        self._lbl_calibrated_beta = QLabel("β: Calibração pendente")
        self._lbl_calibrated_beta.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {ACCENT_TEAL_HEX};"
        )
        self._lbl_calibration_details = QLabel("R₀ empírico: -- · R₀ Newman: --")
        self._lbl_calibration_details.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED_HEX};")
        beta_layout.addWidget(self._lbl_calibrated_beta)
        beta_layout.addWidget(self._lbl_calibration_details)
        layout.addWidget(self._beta_card)

        # Gama (taxa de saída de I)
        layout.addWidget(QLabel("Taxa de saída (γ):"))
        gamma_box = QHBoxLayout()
        self._spin_gamma = QDoubleSpinBox()
        self._spin_gamma.setRange(0.01, 2.0)
        self._spin_gamma.setSingleStep(0.01)
        self._spin_gamma.setValue(0.10)
        self._spin_gamma.setCursor(Qt.CursorShape.PointingHandCursor)

        self._slider_gamma = QSlider(Qt.Orientation.Horizontal)
        self._slider_gamma.setRange(1, 100)  # 0.01 a 1.00
        self._slider_gamma.setValue(10)
        self._slider_gamma.setCursor(Qt.CursorShape.PointingHandCursor)

        self._spin_gamma.valueChanged.connect(self._on_spin_gamma_changed)
        self._slider_gamma.valueChanged.connect(self._on_slider_gamma_changed)

        gamma_box.addWidget(self._spin_gamma)
        gamma_box.addWidget(self._slider_gamma, stretch=1)
        layout.addLayout(gamma_box)
        lbl_gamma_sub = QLabel("Período infeccioso médio: ~10 dias")
        lbl_gamma_sub.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED_HEX};")
        layout.addWidget(lbl_gamma_sub)

        # Mortalidade
        layout.addWidget(QLabel("Mortalidade:"))
        mort_box = QHBoxLayout()
        self._spin_mortality = QDoubleSpinBox()
        self._spin_mortality.setRange(0.0, 1.0)
        self._spin_mortality.setSingleStep(0.01)
        self._spin_mortality.setValue(0.02)
        self._spin_mortality.setCursor(Qt.CursorShape.PointingHandCursor)

        self._slider_mortality = QSlider(Qt.Orientation.Horizontal)
        self._slider_mortality.setRange(0, 100)  # 0% a 100%
        self._slider_mortality.setValue(2)
        self._slider_mortality.setCursor(Qt.CursorShape.PointingHandCursor)

        self._spin_mortality.valueChanged.connect(self._on_spin_mortality_changed)
        self._slider_mortality.valueChanged.connect(self._on_slider_mortality_changed)

        mort_box.addWidget(self._spin_mortality)
        mort_box.addWidget(self._slider_mortality, stretch=1)
        layout.addLayout(mort_box)

        # Período de incubação (dias em E)
        layout.addWidget(QLabel("Período de incubação (dias em E):"))
        incub_box = QHBoxLayout()
        self._spin_incubation = QDoubleSpinBox()
        self._spin_incubation.setRange(0.5, 30.0)
        self._spin_incubation.setSingleStep(0.5)
        self._spin_incubation.setValue(4.0)
        self._spin_incubation.setCursor(Qt.CursorShape.PointingHandCursor)

        self._slider_incubation = QSlider(Qt.Orientation.Horizontal)
        self._slider_incubation.setRange(1, 14)  # 1 a 14 dias
        self._slider_incubation.setValue(4)
        self._slider_incubation.setCursor(Qt.CursorShape.PointingHandCursor)

        self._spin_incubation.valueChanged.connect(self._on_spin_incubation_changed)
        self._slider_incubation.valueChanged.connect(self._on_slider_incubation_changed)

        incub_box.addWidget(self._spin_incubation)
        incub_box.addWidget(self._slider_incubation, stretch=1)
        layout.addLayout(incub_box)
        lbl_incub_sub = QLabel("Dias em latência (E) antes de transmitir infecção.")
        lbl_incub_sub.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED_HEX};")
        layout.addWidget(lbl_incub_sub)

        layout.addStretch(1)
        return grp

    def _build_column_interventions(self) -> QGroupBox:
        grp = QGroupBox("02 Intervenção")
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Nível de intervenção:"))

        # Botões rápidos de nível (Segmented style)
        lvl_btn_box = QHBoxLayout()
        lvl_btn_box.setSpacing(4)
        self._btn_lvl_baixo = QPushButton("Baixo")
        self._btn_lvl_medio = QPushButton("Médio")
        self._btn_lvl_alto = QPushButton("Alto")
        self._btn_lvl_nenhum = QPushButton("Nenhum")

        lvl_buttons = (
            self._btn_lvl_baixo,
            self._btn_lvl_medio,
            self._btn_lvl_alto,
            self._btn_lvl_nenhum,
        )
        for b in lvl_buttons:
            b.setCheckable(True)
            b.setFixedHeight(30)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            lvl_btn_box.addWidget(b)

        self._btn_lvl_baixo.clicked.connect(lambda: self._select_intervention_level("baixo"))
        self._btn_lvl_medio.clicked.connect(lambda: self._select_intervention_level("medio"))
        self._btn_lvl_alto.clicked.connect(lambda: self._select_intervention_level("alto"))
        self._btn_lvl_nenhum.clicked.connect(lambda: self._select_intervention_level("nenhum"))

        layout.addLayout(lvl_btn_box)

        # 3 Cards de regras detalhadas lidas diretamente de INTERVENTION_TABLE (M3)
        low_iso, low_vac = _format_intervention_card_texts(LEVEL_LOW)
        med_iso, med_vac = _format_intervention_card_texts(LEVEL_MEDIUM)
        high_iso, high_vac = _format_intervention_card_texts(LEVEL_HIGH)

        self._card_baixo = InterventionCard(LEVEL_LOW, "Nível Baixo", low_iso, low_vac)
        self._card_medio = InterventionCard(LEVEL_MEDIUM, "Nível Médio", med_iso, med_vac)
        self._card_alto = InterventionCard(LEVEL_HIGH, "Nível Alto", high_iso, high_vac)

        self._card_baixo.clicked.connect(self._select_intervention_level)
        self._card_medio.clicked.connect(self._select_intervention_level)
        self._card_alto.clicked.connect(self._select_intervention_level)

        layout.addWidget(self._card_baixo)
        layout.addWidget(self._card_medio)
        layout.addWidget(self._card_alto)

        # Badge informativo com eficácia da vacina lida de DEFAULT_VACCINE_EFFICACY (M3)
        card_vac = QFrame()
        card_vac.setObjectName("vacInfoCard")
        card_vac.setStyleSheet(
            f"QFrame#vacInfoCard {{"
            f"  background-color: transparent;"
            f"  border: 1px dashed {BORDER_LIGHT_HEX};"
            f"  border-radius: 6px;"
            f"}}"
        )
        vac_layout = QHBoxLayout(card_vac)
        vac_layout.setContentsMargins(10, 8, 10, 8)
        vac_layout.setSpacing(8)

        lbl_vac_icon = QLabel("🔒")
        lbl_vac_icon.setStyleSheet("font-size: 13px; color: #78909c;")
        vac_layout.addWidget(lbl_vac_icon)

        vac_text_box = QVBoxLayout()
        vac_text_box.setSpacing(1)
        eff_pct = format_percent_br(DEFAULT_VACCINE_EFFICACY, decimals=0)
        lbl_vac_hdr = QLabel("Eficácia da vacina (constante):")
        lbl_vac_hdr.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED_HEX};")
        lbl_vac_val = QLabel(f"{eff_pct} — fixo na modelagem matemática")
        lbl_vac_val.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {TEXT_SECONDARY_HEX};"
        )
        vac_text_box.addWidget(lbl_vac_hdr)
        vac_text_box.addWidget(lbl_vac_val)
        vac_layout.addLayout(vac_text_box, stretch=1)
        layout.addWidget(card_vac)

        # Armazena nível atual (default baixo)
        self._current_intervention = "baixo"
        self._update_intervention_ui()

        layout.addStretch(1)
        return grp

    def _build_column_scenario_execution(self) -> QGroupBox:
        grp = QGroupBox("03 Cenário e execução")
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(10)

        # Cenário / Distribuição geográfica
        layout.addWidget(QLabel("Distribuição geográfica:"))
        scen_box = QHBoxLayout()
        scen_box.setSpacing(4)
        self._btn_scen_global = QPushButton("Global")
        self._btn_scen_regional = QPushButton("Regional (Ebola)")
        self._btn_scen_global.setCheckable(True)
        self._btn_scen_regional.setCheckable(True)
        self._btn_scen_global.setFixedHeight(30)
        self._btn_scen_regional.setFixedHeight(30)
        self._btn_scen_global.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_scen_regional.setCursor(Qt.CursorShape.PointingHandCursor)

        self._btn_scen_global.clicked.connect(lambda: self._set_scenario("global"))
        self._btn_scen_regional.clicked.connect(lambda: self._set_scenario("regional_ebola"))

        scen_box.addWidget(self._btn_scen_global)
        scen_box.addWidget(self._btn_scen_regional)
        layout.addLayout(scen_box)

        self._current_scenario = "global"
        self._btn_scen_global.setChecked(True)

        # Semente aleatória
        layout.addWidget(QLabel("Semente aleatória (reprodutibilidade):"))
        seed_box = QHBoxLayout()
        self._spin_seed = QSpinBox()
        self._spin_seed.setRange(0, 999999)
        self._spin_seed.setValue(42)
        self._spin_seed.setCursor(Qt.CursorShape.PointingHandCursor)

        self._btn_random_seed = QPushButton("Gerar aleatória")
        self._btn_random_seed.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_random_seed.clicked.connect(self._on_generate_random_seed)

        seed_box.addWidget(self._spin_seed)
        seed_box.addWidget(self._btn_random_seed)
        layout.addLayout(seed_box)

        # Paciente zero (RF03)
        layout.addWidget(QLabel("Paciente zero:"))
        self._combo_pz_mode = QComboBox()
        self._combo_pz_mode.addItems(["Aleatório", "Manual (País e Vértice)"])
        self._combo_pz_mode.setCursor(Qt.CursorShape.PointingHandCursor)
        self._combo_pz_mode.currentIndexChanged.connect(self._on_pz_mode_changed)
        layout.addWidget(self._combo_pz_mode)

        # Aviso explicativo do modo aleatório (para deixar claro que não há inputs bloqueados)
        self._lbl_pz_disabled_notice = QLabel(
            "🔒 Modo aleatório ativo: o país e o vértice do paciente zero "
            "serão sorteados automaticamente ao iniciar a simulação."
        )
        self._lbl_pz_disabled_notice.setWordWrap(True)
        self._lbl_pz_disabled_notice.setStyleSheet(
            f"font-size: 11px; color: {TEXT_MUTED_HEX}; background-color: #091218; "
            f"border: 1px dashed {BORDER_SUBTLE_HEX}; border-radius: 6px; padding: 10px;"
        )
        layout.addWidget(self._lbl_pz_disabled_notice)

        # Painel manual do paciente zero (visível apenas quando Manual)
        self._pz_manual_frame = QFrame()
        self._pz_manual_frame.setObjectName("pzManualFrame")
        self._pz_manual_frame.setStyleSheet(
            "QFrame#pzManualFrame {"
            "  background-color: #0c161d;"
            "  border: 1px solid #1c3545;"
            "  border-radius: 6px;"
            "  padding: 6px;"
            "}"
        )
        pz_m_layout = QVBoxLayout(self._pz_manual_frame)
        pz_m_layout.setContentsMargins(4, 4, 4, 4)
        pz_m_layout.setSpacing(6)

        country_box = QHBoxLayout()
        country_box.addWidget(QLabel("País:"))
        self._combo_pz_country = QComboBox()
        self._combo_pz_country.setCursor(Qt.CursorShape.PointingHandCursor)
        self._combo_pz_country.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self._combo_pz_country.setMinimumContentsLength(14)
        self._combo_pz_country.currentIndexChanged.connect(self._on_pz_country_changed)
        country_box.addWidget(self._combo_pz_country, stretch=1)
        pz_m_layout.addLayout(country_box)

        vertex_box = QHBoxLayout()
        vertex_box.addWidget(QLabel("Vértice ID:"))
        self._spin_pz_vertex = QSpinBox()
        self._spin_pz_vertex.setRange(0, 999999)
        self._spin_pz_vertex.setValue(0)
        self._spin_pz_vertex.setCursor(Qt.CursorShape.PointingHandCursor)
        self._spin_pz_vertex.valueChanged.connect(self._on_pz_vertex_changed)

        self._edit_patient_zero = QLineEdit()
        self._edit_patient_zero.setPlaceholderText("IDs separados por vírgula (ex: 0, 10)")
        self._edit_patient_zero.hide()  # Compatibilidade interna para get/apply

        vertex_box.addWidget(self._spin_pz_vertex, stretch=1)
        pz_m_layout.addLayout(vertex_box)

        self._btn_pick_random_vertex = QPushButton("Sortear vértice no país")
        self._btn_pick_random_vertex.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_pick_random_vertex.clicked.connect(self._on_pick_random_vertex)
        pz_m_layout.addWidget(self._btn_pick_random_vertex)

        self._pz_manual_frame.setEnabled(False)
        self._pz_manual_frame.setVisible(False)
        layout.addWidget(self._pz_manual_frame)

        # Indicador visual do paciente zero
        self._lbl_pz_indicator = QLabel("Paciente zero: Aleatório (sorteio no início)")
        self._lbl_pz_indicator.setStyleSheet(
            f"font-size: 11px; color: {ACCENT_TEAL_HEX}; font-weight: bold;"
        )
        layout.addWidget(self._lbl_pz_indicator)

        layout.addStretch(1)
        return grp

    def _build_footer(self) -> QHBoxLayout:
        footer = QHBoxLayout()
        footer.setSpacing(8)

        self._btn_back = QPushButton("Voltar")
        self._btn_back.setObjectName("btnSecondary")
        self._btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_back.clicked.connect(self.back_requested.emit)

        self._btn_save = QPushButton("Salvar configuração")
        self._btn_save.setObjectName("btnSecondary")
        self._btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_save.clicked.connect(self._on_save_clicked)

        self._btn_load = QPushButton("Carregar configuração")
        self._btn_load.setObjectName("btnSecondary")
        self._btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_load.clicked.connect(self._on_load_clicked)

        self._btn_start = QPushButton("Iniciar simulação")
        self._btn_start.setObjectName("btnPrimary")
        self._btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_start.setMinimumHeight(38)
        self._btn_start.clicked.connect(self._on_start_clicked)

        footer.addWidget(self._btn_back)
        footer.addWidget(self._btn_save)
        footer.addWidget(self._btn_load)
        footer.addStretch(1)
        footer.addWidget(self._btn_start)

        return footer

        return footer

    # --- Tratamento de eventos de controles ---

    def _on_spin_r0_changed(self, value: float) -> None:
        self._slider_r0.blockSignals(True)
        self._slider_r0.setValue(int(value * 10))
        self._slider_r0.blockSignals(False)

    def _on_slider_r0_changed(self, value: int) -> None:
        self._spin_r0.blockSignals(True)
        self._spin_r0.setValue(value / 10.0)
        self._spin_r0.blockSignals(False)

    def _on_spin_gamma_changed(self, value: float) -> None:
        self._slider_gamma.blockSignals(True)
        self._slider_gamma.setValue(int(value * 100))
        self._slider_gamma.blockSignals(False)

    def _on_slider_gamma_changed(self, value: int) -> None:
        self._spin_gamma.blockSignals(True)
        self._spin_gamma.setValue(value / 100.0)
        self._spin_gamma.blockSignals(False)

    def _on_spin_mortality_changed(self, value: float) -> None:
        self._slider_mortality.blockSignals(True)
        self._slider_mortality.setValue(int(value * 100))
        self._slider_mortality.blockSignals(False)

    def _on_slider_mortality_changed(self, value: int) -> None:
        self._spin_mortality.blockSignals(True)
        self._spin_mortality.setValue(value / 100.0)
        self._spin_mortality.blockSignals(False)

    def _on_spin_incubation_changed(self, value: float) -> None:
        self._slider_incubation.blockSignals(True)
        self._slider_incubation.setValue(int(round(value)))
        self._slider_incubation.blockSignals(False)

    def _on_slider_incubation_changed(self, value: int) -> None:
        self._spin_incubation.blockSignals(True)
        self._spin_incubation.setValue(float(value))
        self._spin_incubation.blockSignals(False)

    def _select_intervention_level(self, level: str) -> None:
        self._current_intervention = level
        self._update_intervention_ui()

    def _update_intervention_ui(self) -> None:
        lvl = self._current_intervention
        self._btn_lvl_baixo.setChecked(lvl == "baixo")
        self._btn_lvl_medio.setChecked(lvl == "medio")
        self._btn_lvl_alto.setChecked(lvl == "alto")
        self._btn_lvl_nenhum.setChecked(lvl == "nenhum")

        self._card_baixo.set_active(lvl == "baixo")
        self._card_medio.set_active(lvl == "medio")
        self._card_alto.set_active(lvl == "alto")

    def _set_scenario(self, scenario: str) -> None:
        self._current_scenario = scenario
        self._btn_scen_global.setChecked(scenario == "global")
        self._btn_scen_regional.setChecked(scenario == "regional_ebola")

    def _on_generate_random_seed(self) -> None:
        self._seed_click_count += 1
        derived = derive_subsystem_seed(
            self._spin_seed.value(), f"ui_seed_{self._seed_click_count}"
        )
        self._spin_seed.setValue((derived % 999999) + 1)

    def _on_pz_mode_changed(self, index: int) -> None:
        is_manual = index == 1
        self._pz_manual_frame.setEnabled(is_manual)
        self._pz_manual_frame.setVisible(is_manual)
        self._lbl_pz_disabled_notice.setVisible(not is_manual)
        self._update_pz_indicator()

    def _on_pz_country_changed(self, _index: int) -> None:
        """Sincroniza o intervalo de vértices com os vértices reais do país selecionado."""
        self._edit_patient_zero.clear()
        if self._world is not None and self._combo_pz_country.count() > 0:
            iso3 = self._combo_pz_country.currentData()
            if iso3 and iso3 in self._world.country_vertices:
                verts = self._world.country_vertices[str(iso3)]
                if verts:
                    self._spin_pz_vertex.blockSignals(True)
                    self._spin_pz_vertex.setRange(min(verts), max(verts))
                    self._spin_pz_vertex.setValue(verts[0])
                    self._spin_pz_vertex.blockSignals(False)
        self._update_pz_indicator()

    def _on_pz_vertex_changed(self, _value: int) -> None:
        self._edit_patient_zero.clear()
        self._update_pz_indicator()

    def _on_pick_random_vertex(self) -> None:
        """Sorteia de forma determinística (SeedBook M1) um vértice do país selecionado."""
        self._pz_pick_count += 1
        self._edit_patient_zero.clear()
        rng = SeedBook(self._spin_seed.value()).rng(
            f"{SUBSYSTEM_PATIENT_ZERO}_{self._pz_pick_count}"
        )

        if self._world is not None and self._combo_pz_country.count() > 0:
            iso3 = self._combo_pz_country.currentData()
            if iso3 and iso3 in self._world.country_vertices:
                verts = self._world.country_vertices[str(iso3)]
                if verts:
                    chosen_v = rng.choice(verts)
                    self._spin_pz_vertex.setValue(chosen_v)
                    self._update_pz_indicator()
                    return

        low = self._spin_pz_vertex.minimum()
        high = min(self._spin_pz_vertex.maximum(), 999)
        self._spin_pz_vertex.setValue(rng.randint(low, max(low, high)))
        self._update_pz_indicator()

    def _update_pz_indicator(self) -> None:
        if self._combo_pz_mode.currentIndex() == 0:
            self._lbl_pz_indicator.setText("🎲 Paciente zero: Aleatório (sorteio no início)")
        else:
            v_id = self._spin_pz_vertex.value()
            if self._world is not None and 0 <= v_id < len(self._world.vertex_country):
                iso3 = self._world.country_of_vertex(v_id)
                c_name = self._world.country_names.get(iso3, iso3)
                country = f"{c_name} ({iso3})"
            else:
                country = self._combo_pz_country.currentText() or "Grafo"
            self._lbl_pz_indicator.setText(
                f"🎯 Paciente zero fixado: Vértice #{v_id:04d} ({country})"
            )

    # --- Métodos públicos da API da UI ---

    def set_world(self, world: World | None) -> None:
        """Conecta o painel aos países e vértices reais do objeto ``World`` (M1)."""
        self._world = world
        self._combo_pz_country.blockSignals(True)
        self._combo_pz_country.clear()

        if world is not None:
            for iso3 in world.country_codes:
                name = world.country_names.get(iso3, iso3)
                n_v = len(world.country_vertices.get(iso3, ()))
                self._combo_pz_country.addItem(f"{name} ({iso3}) [{n_v} nós]", iso3)

            idx_bra = self._combo_pz_country.findData("BRA")
            self._combo_pz_country.setCurrentIndex(idx_bra if idx_bra >= 0 else 0)

        self._combo_pz_country.blockSignals(False)
        if world is not None:
            self._on_pz_country_changed(self._combo_pz_country.currentIndex())

    def get_simulation_config(self) -> SimulationConfig:
        """Constrói um ``SimulationConfig`` com base nos campos atuais."""
        pz = None
        if self._combo_pz_mode.currentIndex() == 1:
            raw_text = self._edit_patient_zero.text().strip()
            if raw_text:
                try:
                    pz = tuple(int(x.strip()) for x in raw_text.split(",") if x.strip())
                except ValueError as exc:
                    raise EpidemiaError(
                        f"IDs de paciente zero inválidos: {raw_text}. "
                        "Use números separados por vírgula."
                    ) from exc
            else:
                pz = (self._spin_pz_vertex.value(),)

        return SimulationConfig(
            seed=self._spin_seed.value(),
            scenario=self._current_scenario,
            r0=self._spin_r0.value(),
            exit_rate_gamma=self._spin_gamma.value(),
            mortality=self._spin_mortality.value(),
            incubation_days=self._spin_incubation.value(),
            intervention_level=self._current_intervention,
            patient_zero=pz,
            max_days=365,
            day_zero_threshold_m=1,
        )

    def apply_simulation_config(self, cfg: SimulationConfig) -> None:
        """Atualiza os campos do painel a partir de um ``SimulationConfig``."""
        self._spin_seed.setValue(cfg.seed)
        self._set_scenario(cfg.scenario)

        self._spin_r0.setValue(cfg.r0)
        self._spin_gamma.setValue(cfg.exit_rate_gamma)
        self._spin_mortality.setValue(cfg.mortality)
        self._spin_incubation.setValue(cfg.incubation_days)

        self._select_intervention_level(cfg.intervention_level)

        if cfg.patient_zero is not None and len(cfg.patient_zero) > 0:
            self._combo_pz_mode.setCurrentIndex(1)
            first_v = cfg.patient_zero[0]
            if self._world is not None and 0 <= first_v < len(self._world.vertex_country):
                iso3 = self._world.country_of_vertex(first_v)
                c_idx = self._combo_pz_country.findData(iso3)
                if c_idx >= 0:
                    self._combo_pz_country.blockSignals(True)
                    self._combo_pz_country.setCurrentIndex(c_idx)
                    self._combo_pz_country.blockSignals(False)
                    verts = self._world.country_vertices.get(iso3, [])
                    if verts:
                        self._spin_pz_vertex.blockSignals(True)
                        self._spin_pz_vertex.setRange(min(verts), max(verts))
                        self._spin_pz_vertex.blockSignals(False)

            self._spin_pz_vertex.blockSignals(True)
            self._spin_pz_vertex.setValue(first_v)
            self._spin_pz_vertex.blockSignals(False)
            self._edit_patient_zero.setText(", ".join(str(x) for x in cfg.patient_zero))
            self._lbl_pz_indicator.setText(f"Paciente zero: Vértices {cfg.patient_zero}")
        else:
            self._combo_pz_mode.setCurrentIndex(0)
            self._edit_patient_zero.clear()
            self._update_pz_indicator()

    def set_calibrated_beta(
        self,
        beta: float | None,
        calibration_result: Any = None,
    ) -> None:
        """Exibe o valor de beta calibrado e os indicadores analíticos de M3 no label."""
        self._calibrated_beta_value = beta
        if beta is None:
            self._lbl_calibrated_beta.setText("β: Calibração pendente")
            self._lbl_calibrated_beta.setStyleSheet(
                f"font-size: 12px; font-weight: bold; color: {TEXT_MUTED_HEX};"
            )
            self._lbl_calibration_details.setText("R₀ empírico: -- · R₀ Newman: --")
        else:
            self._lbl_calibrated_beta.setText(f"β = {format_number_br(beta, 4)}")
            self._lbl_calibrated_beta.setStyleSheet(
                f"font-size: 12px; font-weight: bold; color: {ACCENT_TEAL_HEX};"
            )
            if calibration_result is not None:
                ach = getattr(
                    calibration_result,
                    "measured_r0",
                    getattr(calibration_result, "achieved_r0", None),
                )
                newm = getattr(calibration_result, "newman_r0", None)
                if ach is not None and newm is not None:
                    self._lbl_calibration_details.setText(
                        f"R₀ empírico: {format_number_br(ach, 2)} · "
                        f"R₀ Newman: {format_number_br(newm, 2)}"
                    )

    def set_running_state(self, running: bool) -> None:
        """Habilita ou desabilita campos de configuração durante a execução."""
        enabled = not running
        self._spin_r0.setEnabled(enabled)
        self._slider_r0.setEnabled(enabled)
        self._spin_gamma.setEnabled(enabled)
        self._slider_gamma.setEnabled(enabled)
        self._spin_mortality.setEnabled(enabled)
        self._slider_mortality.setEnabled(enabled)
        self._spin_incubation.setEnabled(enabled)
        self._slider_incubation.setEnabled(enabled)

        self._btn_lvl_baixo.setEnabled(enabled)
        self._btn_lvl_medio.setEnabled(enabled)
        self._btn_lvl_alto.setEnabled(enabled)
        self._btn_lvl_nenhum.setEnabled(enabled)
        self._card_baixo.setEnabled(enabled)
        self._card_medio.setEnabled(enabled)
        self._card_alto.setEnabled(enabled)

        self._btn_scen_global.setEnabled(enabled)
        self._btn_scen_regional.setEnabled(enabled)
        self._spin_seed.setEnabled(enabled)
        self._btn_random_seed.setEnabled(enabled)
        self._combo_pz_mode.setEnabled(enabled)
        self._pz_manual_frame.setEnabled(enabled and self._combo_pz_mode.currentIndex() == 1)

        self._btn_back.setEnabled(enabled)
        self._btn_calibrate.setEnabled(enabled)
        self._btn_load.setEnabled(enabled)

        if running:
            self._btn_start.setText("Simulação em andamento...")
            self._btn_start.setEnabled(False)
        else:
            self._btn_start.setText("Iniciar simulação")
            self._btn_start.setEnabled(True)

    def _on_calibrate_clicked(self) -> None:
        try:
            cfg = self.get_simulation_config()
            self.calibrate_requested.emit(cfg)
        except EpidemiaError as exc:
            QMessageBox.warning(self, "Erro de Configuração", str(exc))

    def _on_start_clicked(self) -> None:
        self._btn_start.setText("Iniciando simulação...")
        self._btn_start.setEnabled(False)
        QApplication.processEvents()
        try:
            cfg = self.get_simulation_config()
            self.start_requested.emit(cfg, cfg.patient_zero)
        except EpidemiaError as exc:
            QMessageBox.warning(self, "Erro de Configuração", str(exc))
        finally:
            self._btn_start.setText("Iniciar simulação")
            self._btn_start.setEnabled(True)

    def _on_save_clicked(self) -> None:
        try:
            cfg = self.get_simulation_config()
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar Configuração",
                "cenario_config.json",
                "Arquivos JSON (*.json)",
            )
            if path:
                save_config(path, cfg)
                QMessageBox.information(self, "Sucesso", "Configuração salva com sucesso!")
        except EpidemiaError as exc:
            QMessageBox.warning(self, "Erro ao Salvar", str(exc))

    def _on_load_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Carregar Configuração",
            "",
            "Arquivos JSON (*.json)",
        )
        if path:
            try:
                cfg = load_config(path)
                self.apply_simulation_config(cfg)
                self.config_changed.emit(cfg)
                QMessageBox.information(self, "Sucesso", "Configuração carregada com sucesso!")
            except EpidemiaError as exc:
                QMessageBox.warning(self, "Erro ao Carregar", str(exc))
