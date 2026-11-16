"""Testes da Tela 2 de Configuração (ConfigPanel) — M5 (RF01, RF03, RF23)."""

from __future__ import annotations

import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from epidemia.core.epidemic.parameters import SimulationConfig
from epidemia.ui.config_panel import ConfigPanel


def _get_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_config_panel_layout_tres_colunas():
    _get_qapp()
    panel = ConfigPanel()

    # Verifica os componentes das 3 colunas
    assert panel._spin_r0 is not None
    assert panel._slider_r0 is not None
    assert panel._spin_gamma is not None
    assert panel._spin_mortality is not None
    assert panel._spin_incubation is not None

    # Coluna 2: Intervenção e cards
    assert panel._card_baixo is not None
    assert panel._card_medio is not None
    assert panel._card_alto is not None
    assert panel._card_baixo._is_active is True
    assert panel._card_medio._is_active is False

    # Seleção de outro nível via card
    panel._card_alto.mousePressEvent(None)
    assert panel._current_intervention == "alto"
    assert panel._card_alto._is_active is True
    assert panel._card_baixo._is_active is False

    # Coluna 3: Cenário e paciente zero
    assert panel._btn_scen_global.isChecked() is True
    panel._btn_scen_regional.click()
    assert panel._current_scenario == "regional_ebola"

    # Paciente zero manual
    panel._combo_pz_mode.setCurrentIndex(1)
    panel._spin_pz_vertex.setValue(42)
    assert panel._pz_manual_frame.isEnabled() is True
    assert "42" in panel._lbl_pz_indicator.text()


def test_config_panel_calibrated_beta_formatting():
    _get_qapp()
    panel = ConfigPanel()
    assert "Calibração pendente" in panel._lbl_calibrated_beta.text()

    panel.set_calibrated_beta(0.3200)
    assert "0,3200" in panel._lbl_calibrated_beta.text()

    panel.set_calibrated_beta(None)
    assert "Calibração pendente" in panel._lbl_calibrated_beta.text()


def test_config_panel_running_state_and_signals():
    _get_qapp()
    panel = ConfigPanel()

    panel.set_running_state(True)
    assert not panel._spin_r0.isEnabled()
    assert not panel._btn_start.isEnabled()
    assert "em andamento" in panel._btn_start.text()

    panel.set_running_state(False)
    assert panel._spin_r0.isEnabled()
    assert panel._btn_start.isEnabled()

    back_called = []
    panel.back_requested.connect(lambda: back_called.append(True))
    panel._btn_back.click()
    assert back_called == [True]


def test_config_panel_get_and_apply_custom_config():
    _get_qapp()
    panel = ConfigPanel()

    cfg = SimulationConfig(
        seed=123,
        scenario="regional_ebola",
        r0=3.2,
        exit_rate_gamma=0.15,
        mortality=0.05,
        incubation_days=5.0,
        intervention_level="medio",
        patient_zero=(10,),
    )
    panel.apply_simulation_config(cfg)
    obtained = panel.get_simulation_config()

    assert obtained.seed == 123
    assert obtained.scenario == "regional_ebola"
    assert round(obtained.r0, 1) == 3.2
    assert round(obtained.exit_rate_gamma, 2) == 0.15
    assert round(obtained.mortality, 2) == 0.05
    assert round(obtained.incubation_days, 1) == 5.0
    assert obtained.intervention_level == "medio"
    assert obtained.patient_zero == (10,)
