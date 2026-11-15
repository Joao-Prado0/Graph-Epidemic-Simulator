"""Estilos, constantes visuais, limiares de mapa e tema escuro (M5 — RF22, RF26).

Centraliza as cores dos compartimentos epidemiológicos, parâmetros de renderização,
limiares de exibição de vértices no mapa e a folha de estilo QSS para o tema escuro.
"""

from __future__ import annotations

from PySide6.QtGui import QColor

# ---------------------------------------------------------------------------
# Cores dos compartimentos epidemiológicos (hexadecimal e QColor)
# ---------------------------------------------------------------------------
COLOR_HEX_SUSCEPTIBLE = "#4caf50"  # Verde (S)
COLOR_HEX_EXPOSED = "#ff9800"  # Laranja (E)
COLOR_HEX_INFECTED = "#f44336"  # Vermelho (I)
COLOR_HEX_RECOVERED_NAT = "#2196f3"  # Azul (R natural)
COLOR_HEX_RECOVERED_VAC = "#00bcd4"  # Ciano (R vacinado)
COLOR_HEX_DECEASED = "#9e9e9e"  # Cinza (D)
COLOR_HEX_ISOLATED = "#ab47bc"  # Roxo (Isolado)

COLOR_SUSCEPTIBLE = QColor(COLOR_HEX_SUSCEPTIBLE)
COLOR_EXPOSED = QColor(COLOR_HEX_EXPOSED)
COLOR_INFECTED = QColor(COLOR_HEX_INFECTED)
COLOR_RECOVERED_NAT = QColor(COLOR_HEX_RECOVERED_NAT)
COLOR_RECOVERED_VAC = QColor(COLOR_HEX_RECOVERED_VAC)
COLOR_DECEASED = QColor(COLOR_HEX_DECEASED)
COLOR_ISOLATED = QColor(COLOR_HEX_ISOLATED)

# Mapeamento do byte de estado (0=S, 1=E, 2=I, 3=R, 4=D) para cor
STATE_COLORS: dict[int, QColor] = {
    0: COLOR_SUSCEPTIBLE,
    1: COLOR_EXPOSED,
    2: COLOR_INFECTED,
    3: COLOR_RECOVERED_NAT,
    4: COLOR_DECEASED,
}

# ---------------------------------------------------------------------------
# Parâmetros de renderização do mapa (RF22, Arquitetura 4.1)
# ---------------------------------------------------------------------------
# Histerese de exibição de vértices por país na tela (em pixels)
# [Validação pendente no protótipo / máquina mais fraca do grupo]
VERTEX_SHOW_THRESHOLD_PX: float = 40.0
VERTEX_HIDE_THRESHOLD_PX: float = 36.0
VERTEX_MARKER_RADIUS: float = 3.0

# ---------------------------------------------------------------------------
# Regra de cor do fluxo real por intensidade de casos (A12 da Arquitetura)
# [Decisão registrada: intensidade de casos por 100 mil hab. Validação pendente]
# ---------------------------------------------------------------------------
REAL_FLOW_MIN_CASES_PER_100K: float = 10.0  # Limiar inicial de 10 por 100k (0,01%)
REAL_FLOW_SCALE: list[tuple[float, str]] = [
    (10.0, "#fff5f0"),
    (50.0, "#fee0d2"),
    (200.0, "#fcbba1"),
    (500.0, "#fc9272"),
    (1000.0, "#fb6a4a"),
    (2500.0, "#ef3b2c"),
    (5000.0, "#cb181d"),
    (10000.0, "#99000d"),
]


def color_for_real_cases_per_100k(cases_per_100k: float) -> QColor:
    """Calcula a cor sequencial para o fluxo real por intensidade de casos por 100k hab."""
    if cases_per_100k < REAL_FLOW_MIN_CASES_PER_100K:
        return QColor("#2d3748")  # Neutro escuro para países abaixo do limiar

    selected_hex = REAL_FLOW_SCALE[0][1]
    for threshold, hex_code in REAL_FLOW_SCALE:
        if cases_per_100k >= threshold:
            selected_hex = hex_code
        else:
            break
    return QColor(selected_hex)


# ---------------------------------------------------------------------------
# QSS Tema Escuro
# ---------------------------------------------------------------------------
DARK_THEME_QSS = """
QMainWindow, QWidget#centralWidget {
    background-color: #121212;
    color: #e0e0e0;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #2d3748;
    background-color: #18191c;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #202225;
    color: #9e9e9e;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-weight: bold;
}

QTabBar::tab:selected {
    background-color: #18191c;
    color: #2196f3;
    border-bottom: 2px solid #2196f3;
}

QTabBar::tab:hover:!selected {
    background-color: #2b2d31;
    color: #ffffff;
}

QGroupBox {
    border: 1px solid #333a42;
    border-radius: 6px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: bold;
    color: #90caf9;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 10px;
}

QLabel {
    color: #cccccc;
}

QPushButton {
    background-color: #2c323d;
    color: #ffffff;
    border: 1px solid #3e4451;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #3e4451;
    border-color: #2196f3;
}

QPushButton:pressed {
    background-color: #1e2229;
}

QPushButton:checked {
    background-color: #1976d2;
    color: #ffffff;
    border-color: #64b5f6;
}

QPushButton#btnPrimary {
    background-color: #1976d2;
    color: #ffffff;
    font-weight: bold;
}

QPushButton#btnPrimary:hover {
    background-color: #2196f3;
}

QPushButton#btnSuccess {
    background-color: #388e3c;
    color: #ffffff;
    font-weight: bold;
}

QPushButton#btnSuccess:hover {
    background-color: #4caf50;
}

QPushButton#btnDanger {
    background-color: #d32f2f;
    color: #ffffff;
    font-weight: bold;
}

QPushButton#btnDanger:hover {
    background-color: #f44336;
}

QSlider::groove:horizontal {
    border: 1px solid #333a42;
    height: 6px;
    background: #202225;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #2196f3;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #90caf9;
    border: 1px solid #1976d2;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #ffffff;
}

QDoubleSpinBox, QSpinBox, QComboBox, QLineEdit {
    background-color: #1e2024;
    border: 1px solid #3e4451;
    border-radius: 4px;
    padding: 4px 8px;
    color: #ffffff;
    selection-background-color: #1976d2;
}

QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus, QLineEdit:focus {
    border: 1px solid #2196f3;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #1e2024;
    color: #ffffff;
    selection-background-color: #1976d2;
    border: 1px solid #3e4451;
}

QScrollBar:vertical, QScrollBar:horizontal {
    background-color: #18191c;
    border: none;
    width: 10px;
    height: 10px;
}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background-color: #3e4451;
    border-radius: 5px;
    min-height: 20px;
    min-width: 20px;
}

QScrollBar::handle:hover {
    background-color: #5c6370;
}

QScrollBar::add-line, QScrollBar::sub-line {
    background: none;
    border: none;
}

QToolTip {
    background-color: #2b2d31;
    color: #ffffff;
    border: 1px solid #4f545c;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
}
"""
