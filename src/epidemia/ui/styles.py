"""Estilos, constantes visuais, limiares de mapa e tema escuro (M5 — RF22, RF26).

Centraliza a paleta visual alinhada aos wireframes (fundo #070c10, cards #111d25,
acento teal #4cd7b4), cores dos compartimentos epidemiológicos, parâmetros de
renderização do mapa, funções de formatação numérica pt-BR e folha de estilo QSS.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor

# Diretório de recursos visuais
RESOURCES_DIR = Path(__file__).resolve().parent / "resources"
ARROW_DOWN_PATH = (RESOURCES_DIR / "arrow_down.png").as_posix()
ARROW_DOWN_DISABLED_PATH = (RESOURCES_DIR / "arrow_down_disabled.png").as_posix()
ARROW_UP_PATH = (RESOURCES_DIR / "arrow_up.png").as_posix()
ARROW_DN_PATH = (RESOURCES_DIR / "arrow_dn.png").as_posix()

# ---------------------------------------------------------------------------
# Paleta geral do tema escuro (Wireframes)
# ---------------------------------------------------------------------------
BG_MAIN_HEX = "#070c10"
BG_CARD_HEX = "#111d25"
BG_CARD_HOVER_HEX = "#16252f"
BORDER_SUBTLE_HEX = "#1c2c36"
BORDER_LIGHT_HEX = "#283e4d"
ACCENT_TEAL_HEX = "#4cd7b4"
ACCENT_TEAL_HOVER_HEX = "#7df8d6"  # Variação mais iluminada e destacada para feedback tátil visual
TEXT_PRIMARY_HEX = "#e6edf3"
TEXT_SECONDARY_HEX = "#b0bec5"
TEXT_MUTED_HEX = "#78909c"

# ---------------------------------------------------------------------------
# Cores dos compartimentos epidemiológicos (hexadecimal e QColor)
# ---------------------------------------------------------------------------
COLOR_HEX_SUSCEPTIBLE = "#4caf50"  # Verde (S)
COLOR_HEX_EXPOSED = "#ffb300"  # Âmbar / Laranja (E)
COLOR_HEX_INFECTED = "#e53935"  # Vermelho (I)
COLOR_HEX_RECOVERED_NAT = "#42a5f5"  # Azul (R natural)
COLOR_HEX_RECOVERED_VAC = "#26c6da"  # Ciano (R vacinado)
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
# Funções de formatação pt-BR (ponto para milhar, vírgula para decimal)
# ---------------------------------------------------------------------------
def format_number_br(val: int | float, decimals: int = 0) -> str:
    """Formata número no padrão brasileiro pt-BR (ex.: 1.840 ou 2,5)."""
    if decimals == 0:
        val_int = int(round(val))
        return f"{val_int:,}".replace(",", ".")
    formatted = f"{float(val):,.{decimals}f}"
    main_part, dec_part = formatted.split(".")
    return f"{main_part.replace(',', '.')},{dec_part}"


def format_percent_br(fraction: float, decimals: int = 1) -> str:
    """Formata fração (0..1) em percentual pt-BR (ex.: 0.184 -> '18,4%')."""
    pct = fraction * 100.0
    return f"{format_number_br(pct, decimals=decimals)}%"


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
    """Calcula a cor sequencial para o fluxo real por intensidade de casos por 100k hab.

    [Decisão registrada A12: escala sequencial a partir de 10 por 100 mil hab.
    Validação pendente no protótipo / máquina mais fraca do grupo].
    """
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
# QSS Tema Escuro Alinhado aos Wireframes
# ---------------------------------------------------------------------------
DARK_THEME_QSS = f"""
QMainWindow, QWidget#centralWidget {{
    background-color: {BG_MAIN_HEX};
    color: {TEXT_PRIMARY_HEX};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

QTabWidget::pane {{
    border: 1px solid {BORDER_SUBTLE_HEX};
    background-color: {BG_MAIN_HEX};
    border-radius: 6px;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {TEXT_MUTED_HEX};
    padding: 10px 22px;
    margin-right: 4px;
    font-size: 14px;
    font-weight: 600;
    border-bottom: 3px solid transparent;
}}

QTabBar::tab:selected {{
    color: {ACCENT_TEAL_HEX};
    border-bottom: 3px solid {ACCENT_TEAL_HEX};
}}

QTabBar::tab:hover:!selected {{
    color: {TEXT_PRIMARY_HEX};
}}

QGroupBox {{
    background-color: {BG_CARD_HEX};
    border: 1px solid {BORDER_SUBTLE_HEX};
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px;
    font-weight: bold;
    color: {TEXT_PRIMARY_HEX};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    left: 12px;
    color: {ACCENT_TEAL_HEX};
    font-size: 13px;
}}

QLabel {{
    color: {TEXT_PRIMARY_HEX};
}}

QPushButton {{
    background-color: #16232b;
    color: {TEXT_PRIMARY_HEX};
    border: 1px solid {BORDER_SUBTLE_HEX};
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: #1e3542;
    border-color: {BORDER_LIGHT_HEX};
}}

QPushButton:pressed {{
    background-color: #0d161c;
}}

QPushButton:checked {{
    background-color: #16333c;
    color: {ACCENT_TEAL_HEX};
    border: 1px solid {ACCENT_TEAL_HEX};
}}

QPushButton#btnPrimary {{
    background-color: {ACCENT_TEAL_HEX};
    color: #041014;
    border: 1px solid {ACCENT_TEAL_HEX};
    border-radius: 6px;
    font-weight: 700;
    font-size: 13px;
    padding: 8px 16px;
}}

QPushButton#btnPrimary:hover {{
    background-color: {ACCENT_TEAL_HOVER_HEX};
    border: 1px solid #9efce4;
    color: #020b0e;
}}

QPushButton#btnPrimary:pressed {{
    background-color: #38bfa0;
    border: 1px solid #38bfa0;
}}

QPushButton#btnSecondary {{
    background-color: #16232b;
    color: {TEXT_PRIMARY_HEX};
    border: 1px solid {BORDER_SUBTLE_HEX};
    border-radius: 6px;
}}

QPushButton#btnSecondary:hover {{
    background-color: #1e3542;
    border-color: {ACCENT_TEAL_HEX};
    color: #ffffff;
}}

QPushButton#btnLoadConfig {{
    background-color: #16232b;
    color: {TEXT_PRIMARY_HEX};
    border: 1px solid {BORDER_SUBTLE_HEX};
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton#btnLoadConfig:hover {{
    background-color: #1e3542;
    border: 1px solid {ACCENT_TEAL_HEX};
    color: {ACCENT_TEAL_HEX};
}}

QPushButton#btnLoadConfig:pressed {{
    background-color: #0e181e;
    border: 1px solid #38bfa0;
}}

QPushButton#btnDanger {{
    background-color: #2c1214;
    color: #ef5350;
    border: 1px solid #5c2427;
    font-weight: bold;
}}

QPushButton#btnDanger:hover {{
    background-color: #3b181b;
    border-color: #e53935;
}}

QSlider::groove:horizontal {{
    border: none;
    height: 4px;
    background: {BORDER_SUBTLE_HEX};
    border-radius: 2px;
}}

QSlider::groove:horizontal:disabled {{
    background: #142028;
}}

QSlider::sub-page:horizontal {{
    background: {ACCENT_TEAL_HEX};
    border-radius: 2px;
}}

QSlider::sub-page:horizontal:disabled {{
    background: #1e3831;
}}

QSlider::handle:horizontal {{
    background: {ACCENT_TEAL_HEX};
    border: 2px solid {BG_MAIN_HEX};
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background: #ffffff;
}}

QSlider::handle:horizontal:disabled {{
    background: #284c42;
}}

QLineEdit {{
    background-color: #0b141a;
    border: 1px solid {BORDER_SUBTLE_HEX};
    border-radius: 6px;
    padding: 6px 10px;
    color: #ffffff;
    selection-background-color: {ACCENT_TEAL_HEX};
    selection-color: #07151a;
}}

QLineEdit:focus {{
    border: 1px solid {ACCENT_TEAL_HEX};
}}

QLineEdit:disabled {{
    background-color: #080f14;
    color: #485b66;
    border: 1px solid #142028;
}}

QDoubleSpinBox, QSpinBox {{
    background-color: #0b141a;
    border: 1px solid {BORDER_SUBTLE_HEX};
    border-radius: 6px;
    padding: 6px 22px 6px 10px;
    color: #ffffff;
    selection-background-color: {ACCENT_TEAL_HEX};
    selection-color: #07151a;
}}

QDoubleSpinBox:hover, QSpinBox:hover {{
    border: 1px solid {BORDER_LIGHT_HEX};
    background-color: #101d26;
}}

QDoubleSpinBox:focus, QSpinBox:focus {{
    border: 1px solid {ACCENT_TEAL_HEX};
}}

QDoubleSpinBox:disabled, QSpinBox:disabled {{
    background-color: #080f14;
    color: #485b66;
    border: 1px solid #142028;
}}

QDoubleSpinBox::up-button, QSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid {BORDER_SUBTLE_HEX};
    border-bottom: 1px solid {BORDER_SUBTLE_HEX};
    border-top-right-radius: 5px;
}}

QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover {{
    background-color: #1e3542;
}}

QDoubleSpinBox::up-arrow, QSpinBox::up-arrow {{
    image: url({ARROW_UP_PATH});
    width: 8px;
    height: 5px;
}}

QDoubleSpinBox::down-button, QSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px;
    border-left: 1px solid {BORDER_SUBTLE_HEX};
    border-bottom-right-radius: 5px;
}}

QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {{
    background-color: #1e3542;
}}

QDoubleSpinBox::down-arrow, QSpinBox::down-arrow {{
    image: url({ARROW_DN_PATH});
    width: 8px;
    height: 5px;
}}

QComboBox {{
    background-color: #0b141a;
    border: 1px solid {BORDER_SUBTLE_HEX};
    border-radius: 6px;
    padding: 6px 28px 6px 10px;
    color: #ffffff;
    selection-background-color: {ACCENT_TEAL_HEX};
    selection-color: #07151a;
}}

QComboBox:hover {{
    border: 1px solid {ACCENT_TEAL_HEX};
    background-color: #101d26;
}}

QComboBox:focus {{
    border: 1px solid {ACCENT_TEAL_HEX};
}}

QComboBox:disabled {{
    background-color: #080f14;
    color: #485b66;
    border: 1px solid #142028;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
}}

QComboBox::down-arrow {{
    image: url({ARROW_DOWN_PATH});
    width: 10px;
    height: 7px;
    margin-right: 8px;
}}

QComboBox::down-arrow:disabled {{
    image: url({ARROW_DOWN_DISABLED_PATH});
}}

QComboBox QAbstractItemView {{
    background-color: #0b141a;
    color: #ffffff;
    selection-background-color: #16333c;
    selection-color: {ACCENT_TEAL_HEX};
    border: 1px solid {BORDER_SUBTLE_HEX};
}}

QLabel:disabled {{
    color: #485b66;
}}

QPushButton:disabled {{
    background-color: #0d151b;
    color: #485b66;
    border: 1px solid #142028;
}}

QScrollBar:vertical, QScrollBar:horizontal {{
    background-color: {BG_MAIN_HEX};
    border: none;
    width: 8px;
    height: 8px;
}}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background-color: {BORDER_SUBTLE_HEX};
    border-radius: 4px;
    min-height: 20px;
    min-width: 20px;
}}

QScrollBar::handle:hover {{
    background-color: {BORDER_LIGHT_HEX};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    background: none;
    border: none;
}}

QToolTip {{
    background-color: #111d25;
    color: #ffffff;
    border: 1px solid {BORDER_LIGHT_HEX};
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
}}

QScrollArea {{
    background: transparent;
    border: none;
}}
"""
