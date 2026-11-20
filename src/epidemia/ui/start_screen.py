"""Tela Inicial da aplicação (M5 — RF25, Wireframe Tela 1).

Apresenta os dois fluxos principais do sistema (Simulação e Pandemias reais) em cards
visuais dedicados, além do atalho para carregamento prévio de configuração JSON.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
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
    RESOURCES_DIR,
    TEXT_MUTED_HEX,
    TEXT_PRIMARY_HEX,
    TEXT_SECONDARY_HEX,
)


class MiniNetworkPreview(QWidget):
    """Mini visual representativo de rede com gradientes e propagação para o card de simulação."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(120)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())

        # Verifica se há imagem externa customizada fornecida pelo usuário
        custom_img = Path(RESOURCES_DIR) / "card_simulation.png"
        if custom_img.is_file():
            pix = QPixmap(str(custom_img))
            if not pix.isNull():
                scaled = pix.scaled(
                    int(w),
                    int(h),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                painter.drawPixmap(0, 0, scaled)
                return

        # Fundo sutil com gradiente radial
        grad_bg = QRadialGradient(w * 0.5, h * 0.5, w * 0.45)
        grad_bg.setColorAt(0.0, QColor(22, 45, 52, 120))
        grad_bg.setColorAt(1.0, QColor(17, 29, 37, 0))
        painter.fillRect(0, 0, int(w), int(h), grad_bg)

        # Rede com perspectiva e nós em múltiplos compartimentos SEIR
        nodes = [
            (w * 0.12, h * 0.65, "#4cd7b4", 4.5),
            (w * 0.22, h * 0.32, "#4cd7b4", 5.0),
            (w * 0.38, h * 0.22, "#26c6da", 4.5),
            (w * 0.50, h * 0.48, "#e53935", 7.5),  # Paciente Zero (Infectado)
            (w * 0.62, h * 0.24, "#ffb300", 5.0),  # Exposto
            (w * 0.78, h * 0.38, "#4cd7b4", 4.5),
            (w * 0.88, h * 0.68, "#26c6da", 5.0),  # Vacinado / Recuperado
            (w * 0.32, h * 0.78, "#4cd7b4", 4.5),
            (w * 0.68, h * 0.75, "#ffb300", 5.0),
            (w * 0.50, h * 0.88, "#4cd7b4", 4.0),
        ]

        edges = [
            (0, 1),
            (0, 7),
            (1, 2),
            (1, 3),
            (1, 7),
            (2, 3),
            (2, 4),
            (3, 4),
            (3, 7),
            (3, 8),
            (4, 5),
            (4, 8),
            (5, 6),
            (5, 8),
            (6, 8),
            (7, 9),
            (8, 9),
            (3, 9),
        ]

        # Arestas da rede
        for u, v in edges:
            p1 = nodes[u]
            p2 = nodes[v]
            is_inf = u == 3 or v == 3
            col = QColor(229, 57, 53, 90) if is_inf else QColor(42, 102, 89, 130)
            width = 1.6 if is_inf else 1.2
            painter.setPen(QPen(col, width))
            painter.drawLine(QPointF(p1[0], p1[1]), QPointF(p2[0], p2[1]))

        # Halo de dispersão em torno do paciente zero
        halo = QRadialGradient(nodes[3][0], nodes[3][1], 24)
        halo.setColorAt(0.0, QColor(229, 57, 53, 90))
        halo.setColorAt(0.5, QColor(229, 57, 53, 30))
        halo.setColorAt(1.0, QColor(229, 57, 53, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(halo)
        painter.drawEllipse(QPointF(nodes[3][0], nodes[3][1]), 24, 24)

        # Nós com borda e preenchimento SEIR
        for x, y, col, r in nodes:
            painter.setPen(QPen(QColor("#0b141a"), 1.5))
            painter.setBrush(QBrush(QColor(col)))
            painter.drawEllipse(QPointF(x, y), r, r)


class MiniHeatmapPreview(QWidget):
    """Mini visual de intensidade com mapa coroplético térmico para pandemias reais."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(120)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())

        # Verifica se há imagem externa customizada fornecida pelo usuário
        custom_img = Path(RESOURCES_DIR) / "card_pandemics.png"
        if custom_img.is_file():
            pix = QPixmap(str(custom_img))
            if not pix.isNull():
                scaled = pix.scaled(
                    int(w),
                    int(h),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                painter.drawPixmap(0, 0, scaled)
                return

        # Fundo térmico sutil
        grad_bg = QRadialGradient(w * 0.5, h * 0.5, w * 0.45)
        grad_bg.setColorAt(0.0, QColor(32, 20, 24, 100))
        grad_bg.setColorAt(1.0, QColor(17, 29, 37, 0))
        painter.fillRect(0, 0, int(w), int(h), grad_bg)

        # Linhas pontilhadas do grid geográfico
        painter.setPen(QPen(QColor("#1a2933"), 1, Qt.PenStyle.DotLine))
        for y_pct in (0.28, 0.52, 0.76):
            painter.drawLine(15, int(h * y_pct), int(w - 15), int(h * y_pct))

        # Silhuetas dos continentes (polígonos simplificados em estilo dashboard de inteligência)
        continents = [
            # América do Norte
            [
                (w * 0.14, h * 0.22),
                (w * 0.28, h * 0.20),
                (w * 0.30, h * 0.38),
                (w * 0.20, h * 0.48),
                (w * 0.12, h * 0.35),
            ],
            # América do Sul
            [
                (w * 0.24, h * 0.54),
                (w * 0.32, h * 0.56),
                (w * 0.28, h * 0.84),
                (w * 0.22, h * 0.74),
            ],
            # Europa
            [
                (w * 0.44, h * 0.22),
                (w * 0.54, h * 0.20),
                (w * 0.52, h * 0.36),
                (w * 0.42, h * 0.34),
            ],
            # África
            [
                (w * 0.44, h * 0.42),
                (w * 0.56, h * 0.42),
                (w * 0.54, h * 0.74),
                (w * 0.46, h * 0.70),
            ],
            # Ásia
            [
                (w * 0.58, h * 0.18),
                (w * 0.82, h * 0.20),
                (w * 0.84, h * 0.46),
                (w * 0.68, h * 0.52),
                (w * 0.56, h * 0.38),
            ],
            # Oceania
            [
                (w * 0.76, h * 0.66),
                (w * 0.86, h * 0.66),
                (w * 0.84, h * 0.82),
                (w * 0.74, h * 0.80),
            ],
        ]

        painter.setPen(QPen(QColor("#1f3342"), 1.2))
        painter.setBrush(QBrush(QColor("#14222c")))
        for poly in continents:
            path = QPainterPath()
            path.moveTo(poly[0][0], poly[0][1])
            for pt in poly[1:]:
                path.lineTo(pt[0], pt[1])
            path.closeSubpath()
            painter.drawPath(path)

        # Focos de calor de surtos históricos com gradiente radial térmico
        hotspots = [
            (w * 0.70, h * 0.36, 32.0, "#ef5350"),  # Ásia (COVID-19 / SARS)
            (w * 0.48, h * 0.28, 26.0, "#e53935"),  # Europa (Milão / H1N1)
            (w * 0.25, h * 0.32, 28.0, "#ff7043"),  # América do Norte
            (w * 0.27, h * 0.65, 22.0, "#ff9800"),  # América do Sul
            (w * 0.50, h * 0.54, 20.0, "#e53935"),  # África Ocidental (Ebola)
        ]

        painter.setPen(Qt.PenStyle.NoPen)
        for hx, hy, rad, col_hex in hotspots:
            spot = QRadialGradient(hx, hy, rad)
            base = QColor(col_hex)
            spot.setColorAt(0.0, QColor(base.red(), base.green(), base.blue(), 180))
            spot.setColorAt(0.4, QColor(base.red(), base.green(), base.blue(), 90))
            spot.setColorAt(1.0, QColor(base.red(), base.green(), base.blue(), 0))
            painter.setBrush(spot)
            painter.drawEllipse(QPointF(hx, hy), rad, rad)
            # Núcleo pontual do epicentro
            core_col = QColor("#ffffff" if col_hex == "#e53935" else col_hex)
            painter.setBrush(QBrush(core_col))
            painter.drawEllipse(QPointF(hx, hy), 2.5, 2.5)


class StartScreen(QWidget):
    """Tela inicial com a seleção de fluxos e acesso à configuração (RF25)."""

    open_simulation = Signal()
    open_real_pandemics = Signal()
    load_config = Signal()

    # Aliases semânticos
    simulation_requested = open_simulation
    real_pandemics_requested = open_real_pandemics
    load_config_requested = load_config

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
        lbl_title.setStyleSheet(f"color: {TEXT_PRIMARY_HEX}; font-size: 32px; font-weight: bold;")
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
        btn_load_json.setObjectName("btnLoadConfig")
        btn_load_json.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_load_json.setMinimumWidth(260)
        btn_load_json.setFixedHeight(40)
        btn_load_json.clicked.connect(self.load_config.emit)
        bottom_layout.addWidget(btn_load_json, alignment=Qt.AlignmentFlag.AlignCenter)

        lbl_hint = QLabel("Comece com um novo cenário ou retome um experimento salvo.")
        lbl_hint.setStyleSheet(f"color: {TEXT_MUTED_HEX}; font-size: 12px;")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.addWidget(lbl_hint)

        root_layout.addWidget(bottom_widget)

    def _create_simulation_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("cardSim")
        card.setFixedSize(460, 360)
        card.setStyleSheet(
            f"QFrame#cardSim {{ background-color: {BG_CARD_HEX}; "
            f"border: 1px solid {BORDER_SUBTLE_HEX}; border-radius: 12px; }}"
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
        lbl_desc.setStyleSheet(f"color: {TEXT_SECONDARY_HEX}; font-size: 13px; border: none;")
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
        card.setObjectName("cardReal")
        card.setFixedSize(460, 360)
        card.setStyleSheet(
            f"QFrame#cardReal {{ background-color: {BG_CARD_HEX}; "
            f"border: 1px solid {BORDER_SUBTLE_HEX}; border-radius: 12px; }}"
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
        lbl_desc.setStyleSheet(f"color: {TEXT_SECONDARY_HEX}; font-size: 13px; border: none;")
        layout.addWidget(lbl_desc)

        layout.addStretch(1)

        btn_open = QPushButton("Abrir fluxo ->")
        btn_open.setObjectName("btnPrimary")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setFixedHeight(40)
        btn_open.clicked.connect(self.open_real_pandemics.emit)
        layout.addWidget(btn_open)

        return card
