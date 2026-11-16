"""Testes unitários para styles.py (formatadores pt-BR) e StartScreen (Tela 1)."""

from __future__ import annotations

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtWidgets import QApplication

from epidemia.ui.start_screen import StartScreen
from epidemia.ui.styles import (
    COLOR_HEX_DECEASED,
    COLOR_HEX_EXPOSED,
    COLOR_HEX_INFECTED,
    COLOR_HEX_ISOLATED,
    COLOR_HEX_RECOVERED_NAT,
    COLOR_HEX_SUSCEPTIBLE,
    format_number_br,
    format_percent_br,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_compartment_colors_match_wireframe_spec() -> None:
    assert COLOR_HEX_SUSCEPTIBLE == "#4caf50"
    assert COLOR_HEX_EXPOSED == "#ffb300"
    assert COLOR_HEX_INFECTED == "#e53935"
    assert COLOR_HEX_RECOVERED_NAT == "#42a5f5"
    assert COLOR_HEX_DECEASED == "#9e9e9e"
    assert COLOR_HEX_ISOLATED == "#ab47bc"


def test_format_number_br() -> None:
    assert format_number_br(1840) == "1.840"
    assert format_number_br(1000000) == "1.000.000"
    assert format_number_br(0) == "0"
    assert format_number_br(42) == "42"
    assert format_number_br(2.5, decimals=1) == "2,5"
    assert format_number_br(1840.75, decimals=2) == "1.840,75"


def test_format_percent_br() -> None:
    assert format_percent_br(0.184) == "18,4%"
    assert format_percent_br(0.02, decimals=1) == "2,0%"
    assert format_percent_br(0.02, decimals=0) == "2%"
    assert format_percent_br(1.0) == "100,0%"


def test_start_screen_initialization_and_signals(qapp) -> None:
    screen = StartScreen()
    assert screen is not None

    sim_called = False
    real_called = False
    load_called = False

    screen.open_simulation.connect(lambda: nonlocal_set("sim"))
    screen.open_real_pandemics.connect(lambda: nonlocal_set("real"))
    screen.load_config.connect(lambda: nonlocal_set("load"))

    def nonlocal_set(which: str) -> None:
        nonlocal sim_called, real_called, load_called
        if which == "sim":
            sim_called = True
        elif which == "real":
            real_called = True
        elif which == "load":
            load_called = True

    screen.open_simulation.emit()
    assert sim_called is True

    screen.open_real_pandemics.emit()
    assert real_called is True

    screen.load_config.emit()
    assert load_called is True
    screen.close()
