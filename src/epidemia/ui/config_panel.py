"""Painel de configuração da simulação (M5 — RF01, RF03, RF07, RF23).

Permite configurar os parâmetros da doença (R0, gama, mortalidade, incubação),
níveis de intervenção (isolamento e vacinação automáticos), cenário, semente,
paciente zero, além de botões para calibrar beta, salvar/carregar JSON e iniciar.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from epidemia.app.config_io import load_config, save_config
from epidemia.core.epidemic.parameters import SimulationConfig
from epidemia.core.errors import EpidemiaError

if TYPE_CHECKING:
    from epidemia.world.world import World


class ConfigPanel(QWidget):
    """Painel com formulário de configuração epidemiológica e controle de início."""

    start_requested = Signal(SimulationConfig, object)  # config, patient_zero
    calibrate_requested = Signal(SimulationConfig)
    config_changed = Signal(SimulationConfig)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(12)

        # 1. Grupo Parâmetros da Doença (RF01)
        grp_disease = QGroupBox("Parâmetros da Doença (SEIRD)")
        form_disease = QFormLayout(grp_disease)
        form_disease.setSpacing(8)

        # R0 e slider
        self._spin_r0 = QDoubleSpinBox()
        self._spin_r0.setRange(0.1, 20.0)
        self._spin_r0.setSingleStep(0.1)
        self._spin_r0.setValue(2.5)

        self._slider_r0 = QSlider(Qt.Orientation.Horizontal)
        self._slider_r0.setRange(1, 200)  # Multiplicado por 10 (0.1 a 20.0)
        self._slider_r0.setValue(25)

        self._spin_r0.valueChanged.connect(self._on_spin_r0_changed)
        self._slider_r0.valueChanged.connect(self._on_slider_r0_changed)

        r0_layout = QHBoxLayout()
        r0_layout.addWidget(self._spin_r0)
        r0_layout.addWidget(self._slider_r0)
        form_disease.addRow("R0 informado:", r0_layout)

        # Gama (taxa de saída de I)
        self._spin_gamma = QDoubleSpinBox()
        self._spin_gamma.setRange(0.01, 2.0)
        self._spin_gamma.setSingleStep(0.01)
        self._spin_gamma.setValue(0.10)
        self._spin_gamma.setToolTip("Taxa total de saída de I (recuperação + óbito)")
        form_disease.addRow("Taxa de saída (γ):", self._spin_gamma)

        # Mortalidade
        self._spin_mortality = QDoubleSpinBox()
        self._spin_mortality.setRange(0.0, 1.0)
        self._spin_mortality.setSingleStep(0.01)
        self._spin_mortality.setValue(0.02)
        self._spin_mortality.setToolTip("Fração das saídas de I que resultam em óbito (D)")
        form_disease.addRow("Mortalidade:", self._spin_mortality)

        # Incubação em dias
        self._spin_incubation = QDoubleSpinBox()
        self._spin_incubation.setRange(0.5, 30.0)
        self._spin_incubation.setSingleStep(0.5)
        self._spin_incubation.setValue(4.0)
        self._spin_incubation.setToolTip("Período de incubação (dias em E)")
        form_disease.addRow("Incubação (dias):", self._spin_incubation)

        # Calibração de beta
        calib_layout = QHBoxLayout()
        self._btn_calibrate = QPushButton("Calibrar β")
        self._btn_calibrate.clicked.connect(self._on_calibrate_clicked)
        self._lbl_calibrated_beta = QLabel("β: --")
        self._lbl_calibrated_beta.setStyleSheet("font-weight: bold; color: #64b5f6;")
        calib_layout.addWidget(self._btn_calibrate)
        calib_layout.addWidget(self._lbl_calibrated_beta)
        form_disease.addRow("Calibração:", calib_layout)

        main_layout.addWidget(grp_disease)

        # 2. Grupo Intervenções e Cenário
        grp_interventions = QGroupBox("Intervenções e Cenário")
        form_interv = QFormLayout(grp_interventions)
        form_interv.setSpacing(8)

        # Nível de intervenção
        self._combo_intervention = QComboBox()
        self._combo_intervention.addItems(["nenhum", "baixo", "medio", "alto"])
        self._combo_intervention.setCurrentText("baixo")
        form_interv.addRow("Nível de intervenção:", self._combo_intervention)

        # Cenário
        self._combo_scenario = QComboBox()
        self._combo_scenario.addItems(["global", "regional"])
        self._combo_scenario.setCurrentText("global")
        form_interv.addRow("Cenário:", self._combo_scenario)

        # Semente
        self._spin_seed = QSpinBox()
        self._spin_seed.setRange(0, 999999)
        self._spin_seed.setValue(42)
        form_interv.addRow("Semente aleatória:", self._spin_seed)

        # Paciente zero (RF03)
        self._combo_patient_zero = QComboBox()
        self._combo_patient_zero.addItems(["Aleatório", "Manual por ID"])
        self._combo_patient_zero.currentIndexChanged.connect(self._on_pz_mode_changed)

        self._edit_patient_zero = QLineEdit()
        self._edit_patient_zero.setPlaceholderText("IDs separados por vírgula (ex: 0, 10)")
        self._edit_patient_zero.setEnabled(False)

        pz_layout = QVBoxLayout()
        pz_layout.addWidget(self._combo_patient_zero)
        pz_layout.addWidget(self._edit_patient_zero)
        form_interv.addRow("Paciente zero:", pz_layout)

        main_layout.addWidget(grp_interventions)

        # 3. Botões de Ação
        btn_layout = QHBoxLayout()
        self._btn_load = QPushButton("📁 Carregar")
        self._btn_load.clicked.connect(self._on_load_clicked)
        self._btn_save = QPushButton("💾 Salvar")
        self._btn_save.clicked.connect(self._on_save_clicked)

        btn_layout.addWidget(self._btn_load)
        btn_layout.addWidget(self._btn_save)
        main_layout.addLayout(btn_layout)

        # Botão Iniciar Simulação
        self._btn_start = QPushButton("🚀 Iniciar simulação")
        self._btn_start.setObjectName("btnSuccess")
        self._btn_start.setMinimumHeight(38)
        self._btn_start.clicked.connect(self._on_start_clicked)
        main_layout.addWidget(self._btn_start)

        main_layout.addStretch(1)

    def _on_spin_r0_changed(self, value: float) -> None:
        self._slider_r0.blockSignals(True)
        self._slider_r0.setValue(int(value * 10))
        self._slider_r0.blockSignals(False)

    def _on_slider_r0_changed(self, value: int) -> None:
        self._spin_r0.blockSignals(True)
        self._spin_r0.setValue(value / 10.0)
        self._spin_r0.blockSignals(False)

    def _on_pz_mode_changed(self, index: int) -> None:
        self._edit_patient_zero.setEnabled(index == 1)

    def get_simulation_config(self) -> SimulationConfig:
        """Constrói um ``SimulationConfig`` com base nos campos atuais."""
        pz = None
        if self._combo_patient_zero.currentIndex() == 1:
            raw_text = self._edit_patient_zero.text().strip()
            if raw_text:
                try:
                    pz = tuple(int(x.strip()) for x in raw_text.split(",") if x.strip())
                except ValueError as exc:
                    raise EpidemiaError(
                        f"IDs de paciente zero inválidos: {raw_text}. Use números separados por vírgula."
                    ) from exc

        return SimulationConfig(
            seed=self._spin_seed.value(),
            scenario=self._combo_scenario.currentText(),
            r0=self._spin_r0.value(),
            exit_rate_gamma=self._spin_gamma.value(),
            mortality=self._spin_mortality.value(),
            incubation_days=self._spin_incubation.value(),
            intervention_level=self._combo_intervention.currentText(),
            patient_zero=pz,
            max_days=365,
            day_zero_threshold_m=1,
        )

    def apply_simulation_config(self, cfg: SimulationConfig) -> None:
        """Atualiza os campos do painel a partir de um ``SimulationConfig``."""
        self._spin_seed.setValue(cfg.seed)
        idx_scen = self._combo_scenario.findText(cfg.scenario)
        if idx_scen >= 0:
            self._combo_scenario.setCurrentIndex(idx_scen)

        self._spin_r0.setValue(cfg.r0)
        self._spin_gamma.setValue(cfg.exit_rate_gamma)
        self._spin_mortality.setValue(cfg.mortality)
        self._spin_incubation.setValue(cfg.incubation_days)

        idx_interv = self._combo_intervention.findText(cfg.intervention_level)
        if idx_interv >= 0:
            self._combo_intervention.setCurrentIndex(idx_interv)

        if cfg.patient_zero is not None and len(cfg.patient_zero) > 0:
            self._combo_patient_zero.setCurrentIndex(1)
            self._edit_patient_zero.setText(", ".join(str(x) for x in cfg.patient_zero))
        else:
            self._combo_patient_zero.setCurrentIndex(0)
            self._edit_patient_zero.clear()

    def set_calibrated_beta(self, beta: float | None) -> None:
        """Exibe o valor de beta calibrado no label."""
        if beta is None:
            self._lbl_calibrated_beta.setText("β: --")
        else:
            self._lbl_calibrated_beta.setText(f"β: {beta:.4f}")

    def set_running_state(self, running: bool) -> None:
        """Habilita ou desabilita campos de configuração durante a execução."""
        enabled = not running
        self._spin_r0.setEnabled(enabled)
        self._slider_r0.setEnabled(enabled)
        self._spin_gamma.setEnabled(enabled)
        self._spin_mortality.setEnabled(enabled)
        self._spin_incubation.setEnabled(enabled)
        self._combo_intervention.setEnabled(enabled)
        self._combo_scenario.setEnabled(enabled)
        self._spin_seed.setEnabled(enabled)
        self._combo_patient_zero.setEnabled(enabled)
        self._edit_patient_zero.setEnabled(enabled and self._combo_patient_zero.currentIndex() == 1)
        self._btn_calibrate.setEnabled(enabled)
        self._btn_load.setEnabled(enabled)

        if running:
            self._btn_start.setText("Simulação em andamento...")
            self._btn_start.setEnabled(False)
        else:
            self._btn_start.setText("🚀 Iniciar simulação")
            self._btn_start.setEnabled(True)

    def _on_calibrate_clicked(self) -> None:
        try:
            cfg = self.get_simulation_config()
            self.calibrate_requested.emit(cfg)
        except EpidemiaError as exc:
            QMessageBox.warning(self, "Erro de Configuração", str(exc))

    def _on_start_clicked(self) -> None:
        try:
            cfg = self.get_simulation_config()
            self.start_requested.emit(cfg, cfg.patient_zero)
        except EpidemiaError as exc:
            QMessageBox.warning(self, "Erro de Configuração", str(exc))

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
