"""Tela Inicial da aplicação (M5 — RF25, Wireframe Tela 1).

Apresenta os dois fluxos principais do sistema (Simulação e Pandemias reais) em cards
visuais dedicados, além do atalho para carregamento prévio de configuração JSON.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from epidemia.ui.styles import (
    ACCENT_TEAL_HEX,
    BG_CARD_HEX,
    BORDER_SUBTLE_HEX,
    TEXT_MUTED_HEX,
    TEXT_PRIMARY_HEX,
    TEXT_SECONDARY_HEX,
)


class MiniNetworkPreview(QWidget):
    """Mini visual representativo de rede para o card de simulação."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(120)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()

        nodes = [
            (w * 0.15, h * 0.45, "#4cd7b4"),
            (w * 0.32, h * 0.20, "#4cd7b4"),
            (w * 0.48, h * 0.35, "#e53935"),  # Paciente zero / infectado
            (w * 0.65, h * 0.22, "#4cd7b4"),
            (w * 0.82, h * 0.50, "#4cd7b4"),
            (w * 0.35, h * 0.75, "#4cd7b4"),
            (w * 0.60, h * 0.70, "#4cd7b4"),
        ]

        edges = [
            (0, 1),
            (0, 5),
            (1, 2),
            (1, 3),
            (2, 3),
            (2, 5),
            (2, 6),
            (3, 4),
            (4, 6),
            (5, 6),
        ]

        pen_edge = QPen(QColor("#224647"), 1.5)
        painter.setPen(pen_edge)
        for u, v in edges:
            p1 = nodes[u]
            p2 = nodes[v]
            painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))

        for x, y, col in nodes:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(col)))
            r = 5 if col != "#e53935" else 6.5
            painter.drawEllipse(int(x - r), int(y - r), int(2 * r), int(2 * r))


class MiniHeatmapPreview(QWidget):
    """Mini visual de intensidade para o card de pandemias reais."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(120)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()

        blocks = [
            (w * 0.10, h * 0.25, 45, 30, "#cb181d"),
            (w * 0.22, h * 0.20, 70, 40, "#fb6a4a"),
            (w * 0.26, h * 0.55, 55, 45, "#fc9272"),
            (w * 0.46, h * 0.25, 40, 30, "#cb181d"),
            (w * 0.52, h * 0.40, 50, 45, "#ef3b2c"),
            (w * 0.65, h * 0.20, 80, 45, "#99000d"),
            (w * 0.72, h * 0.60, 55, 35, "#fcbba1"),
        ]

        for x, y, bw, bh, col in blocks:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(col)))
            painter.drawRoundedRect(int(x), int(y), int(bw), int(bh), 4, 4)


class StartScreen(QWidget):
    """Tela inicial com a seleção de fluxos e acesso à configuração (RF25)."""

    open_simulation = Signal()
    open_real_pandemics = Signal()
    load_config = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(40, 30, 40, 30)
        root_layout.setSpacing(28)
        root_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Cabeçalho central
        header_widget = QWidget(self)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(6)

        lbl_top = QLabel("LABORATÓRIO DE EPIDEMIOLOGIA")
        lbl_top.setStyleSheet(
            f"color: {ACCENT_TEAL_HEX}; font-size: 12px; font-weight: bold; letter-spacing: 2px;"
        )
        lbl_top.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(lbl_top)

        lbl_title = QLabel("Simulador de Epidemias em Redes")
        lbl_title.setStyleSheet(
            f"color: {TEXT_PRIMARY_HEX}; font-size: 32px; font-weight: bold;"
        )
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(lbl_title)

        lbl_sub = QLabel(
            "Explore como uma epidemia se propaga. Teste cenários, conecte evidências "
            "e descubra padrões."
        )
        lbl_sub.setStyleSheet(f"color: {TEXT_SECONDARY_HEX}; font-size: 14px;")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(lbl_sub)

        root_layout.addWidget(header_widget)

        # 2. Cards de Fluxos (Simulação e Pandemias Reais)
        cards_widget = QWidget(self)
        cards_layout = QHBoxLayout(cards_widget)
        cards_layout.setSpacing(24)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_sim = self._create_simulation_card()
        card_real = self._create_real_card()

        cards_layout.addWidget(card_sim)
        cards_layout.addWidget(card_real)

        root_layout.addWidget(cards_widget)

        # 3. Rodapé com Carregar Configuração JSON
        bottom_widget = QWidget(self)
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.setSpacing(8)

        btn_load_json = QPushButton("Carregar configuração JSON")
        btn_load_json.setMinimumWidth(260)
        btn_load_json.setStyleSheet(
            f"background-color: #16232b; color: {TEXT_PRIMARY_HEX}; "
            f"border: 1px solid {BORDER_SUBTLE_HEX}; padding: 10px 20px; font-size: 13px;"
        )
        btn_load_json.clicked.connect(self.load_config.emit)
        bottom_layout.addWidget(btn_load_json, alignment=Qt.AlignmentFlag.AlignCenter)

        lbl_hint = QLabel("Comece com um novo cenário ou retome um experimento salvo.")
        lbl_hint.setStyleSheet(f"color: {TEXT_MUTED_HEX}; font-size: 12px;")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.addWidget(lbl_hint)

        root_layout.addWidget(bottom_widget)

    def _create_simulation_card(self) -> QFrame:
        card = QFrame()
        card.setFixedSize(460, 360)
        card.setStyleSheet(
            f"background-color: {BG_CARD_HEX}; border: 1px solid {BORDER_SUBTLE_HEX}; "
            f"border-radius: 12px;"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Tag
        lbl_tag = QLabel("EXPERIMENTE")
        lbl_tag.setStyleSheet(
            f"color: {ACCENT_TEAL_HEX}; border: 1px solid {ACCENT_TEAL_HEX}; "
            f"border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: bold;"
        )
        lbl_tag.setFixedHeight(22)
        layout.addWidget(lbl_tag, alignment=Qt.AlignmentFlag.AlignLeft)

        # Preview de rede
        layout.addWidget(MiniNetworkPreview())

        # Título e texto
        lbl_title = QLabel("Simulação")
        lbl_title.setStyleSheet(
            f"color: {TEXT_PRIMARY_HEX}; font-size: 22px; font-weight: bold; border: none;"
        )
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Configure a doença e assista à propagação.\n"
            "Ajuste parâmetros e observe a dinâmica da rede."
        )
        lbl_desc.setStyleSheet(
            f"color: {TEXT_SECONDARY_HEX}; font-size: 13px; border: none;"
        )
        layout.addWidget(lbl_desc)

        layout.addStretch(1)

        btn_open = QPushButton("Abrir fluxo ->")
        btn_open.setObjectName("btnPrimary")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setFixedHeight(40)
        btn_open.clicked.connect(self.open_simulation.emit)
        layout.addWidget(btn_open)

        return card

    def _create_real_card(self) -> QFrame:
        card = QFrame()
        card.setFixedSize(460, 360)
        card.setStyleSheet(
            f"background-color: {BG_CARD_HEX}; border: 1px solid {BORDER_SUBTLE_HEX}; "
            f"border-radius: 12px;"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Tag
        lbl_tag = QLabel("DADOS HISTÓRICOS")
        lbl_tag.setStyleSheet(
            "color: #ffb300; border: 1px solid #ffb300; "
            "border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: bold;"
        )
        lbl_tag.setFixedHeight(22)
        layout.addWidget(lbl_tag, alignment=Qt.AlignmentFlag.AlignLeft)

        # Preview de mapa
        layout.addWidget(MiniHeatmapPreview())

        # Título e texto
        lbl_title = QLabel("Pandemias reais")
        lbl_title.setStyleSheet(
            f"color: {TEXT_PRIMARY_HEX}; font-size: 22px; font-weight: bold; border: none;"
        )
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Reproduza surtos históricos sobre o mesmo mapa.\n"
            "Compare trajetórias e intervenções no tempo."
        )
        lbl_desc.setStyleSheet(
            f"color: {TEXT_SECONDARY_HEX}; font-size: 13px; border: none;"
        )
        layout.addWidget(lbl_desc)

        layout.addStretch(1)

        btn_open = QPushButton("Abrir fluxo ->")
        btn_open.setObjectName("btnSecondary")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setFixedHeight(40)
        btn_open.clicked.connect(self.open_real_pandemics.emit)
        layout.addWidget(btn_open)

        return card
