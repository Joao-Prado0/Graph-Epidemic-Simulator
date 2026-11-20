"""Gráficos em tempo real das curvas epidemiológicas (M5 — RF08, RF24; Tela 7).

Exibe as curvas dos compartimentos S, E, I, R e D com pyqtgraph, um marcador
vertical do dia atualmente selecionado, chips inferiores com percentuais e contagens
em formato pt-BR e botão para exportação em PNG.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pyqtgraph as pg
import pyqtgraph.exporters
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from epidemia.core.analysis.epidemic_metrics import extract_compartment_counts
from epidemia.ui.styles import (
    ACCENT_TEAL_HEX,
    BG_CARD_HEX,
    BG_MAIN_HEX,
    BORDER_SUBTLE_HEX,
    COLOR_HEX_DECEASED,
    COLOR_HEX_EXPOSED,
    COLOR_HEX_INFECTED,
    COLOR_HEX_RECOVERED_NAT,
    COLOR_HEX_SUSCEPTIBLE,
    TEXT_MUTED_HEX,
    TEXT_PRIMARY_HEX,
    TEXT_SECONDARY_HEX,
    format_number_br,
    format_percent_br,
)

if TYPE_CHECKING:
    from epidemia.core.timeline.protocol import Timeline


class CompartmentChip(QFrame):
    """Chip visual que exibe o compartimento com seu indicador de cor, contagem e %."""

    def __init__(
        self,
        name: str,
        color_hex: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._color_hex = color_hex

        self.setStyleSheet(
            f"CompartmentChip {{"
            f"  background-color: {BG_CARD_HEX};"
            f"  border: 1px solid {BORDER_SUBTLE_HEX};"
            f"  border-radius: 6px;"
            f"}}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        # Bolinha indicadora de cor
        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(
            f"background-color: {color_hex}; border-radius: 5px; min-width: 10px; max-width: 10px;"
        )
        layout.addWidget(dot)

        # Texto do compartimento
        self._lbl_name = QLabel(name)
        self._lbl_name.setStyleSheet(
            f"font-size: 11px; font-weight: bold; color: {TEXT_SECONDARY_HEX};"
        )
        layout.addWidget(self._lbl_name)

        # Valor (percentual e contagem)
        self._lbl_value = QLabel("--")
        self._lbl_value.setStyleSheet(
            f"font-size: 12px; font-weight: bold; color: {TEXT_PRIMARY_HEX};"
        )
        layout.addWidget(self._lbl_value)

    def set_counts(self, count: int, total: int) -> None:
        if total <= 0:
            self._lbl_value.setText("--")
            return
        pct_str = format_percent_br(count / total, decimals=1)
        cnt_str = format_number_br(count)
        self._lbl_value.setText(f"{pct_str} · {cnt_str}")


class ChartsView(QWidget):
    """Visualizador das curvas S, E, I, R e D com pyqtgraph, chips e exportação PNG (Tela 7)."""

    back_to_map_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._timeline: Timeline | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        compact_btn_qss = "QPushButton { padding: 3px 10px; font-size: 12px; min-height: 0px; }"

        # Barra de ferramentas superior (compacta e alinhada)
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self._btn_back_map = QPushButton("← Voltar ao mapa")
        self._btn_back_map.setObjectName("btnSecondary")
        self._btn_back_map.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_back_map.setFixedHeight(28)
        self._btn_back_map.setStyleSheet(compact_btn_qss)
        self._btn_back_map.clicked.connect(self.back_to_map_requested.emit)
        top_bar.addWidget(self._btn_back_map)

        header_text = QVBoxLayout()
        header_text.setSpacing(1)
        self._lbl_title = QLabel("Curvas em tempo real")
        self._lbl_title.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {TEXT_PRIMARY_HEX};"
        )
        self._lbl_subtitle = QLabel("Modelo SEIRD · Evolução diária da população")
        self._lbl_subtitle.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED_HEX};")
        header_text.addWidget(self._lbl_title)
        header_text.addWidget(self._lbl_subtitle)
        top_bar.addLayout(header_text)

        top_bar.addStretch(1)

        self._btn_reset_zoom = QPushButton("Ajustar gráfico")
        self._btn_reset_zoom.setObjectName("btnSecondary")
        self._btn_reset_zoom.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_reset_zoom.setFixedHeight(28)
        self._btn_reset_zoom.setStyleSheet(compact_btn_qss)
        self._btn_reset_zoom.setToolTip("Reajusta o enquadramento e o zoom do gráfico à tela")
        self._btn_reset_zoom.clicked.connect(self.reset_zoom)
        top_bar.addWidget(self._btn_reset_zoom)

        self._btn_export = QPushButton("Exportar PNG")
        self._btn_export.setObjectName("btnSecondary")
        self._btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_export.setFixedHeight(28)
        self._btn_export.setStyleSheet(compact_btn_qss)
        self._btn_export.setToolTip("Exportar gráfico atual como imagem PNG")
        self._btn_export.clicked.connect(self._on_export_clicked)
        top_bar.addWidget(self._btn_export)

        layout.addLayout(top_bar)

        # Configura pyqtgraph com fundo escuro e estilo elegante
        pg.setConfigOption("background", BG_MAIN_HEX)
        pg.setConfigOption("foreground", TEXT_SECONDARY_HEX)
        pg.setConfigOption("antialias", True)

        self._plot_widget = pg.PlotWidget()
        self._plot_widget.showGrid(x=True, y=True, alpha=0.15)
        self._plot_widget.setLabel("bottom", "Dia de Simulação")
        self._plot_widget.setLabel("left", "Indivíduos")
        self._plot_widget.addLegend(offset=(10, 10))

        # 5 curvas principais
        self._curve_s = self._plot_widget.plot(
            name="Suscetíveis (S)",
            pen=pg.mkPen(color=COLOR_HEX_SUSCEPTIBLE, width=2),
        )
        self._curve_e = self._plot_widget.plot(
            name="Expostos (E)",
            pen=pg.mkPen(color=COLOR_HEX_EXPOSED, width=2),
        )
        self._curve_i = self._plot_widget.plot(
            name="Infectados (I)",
            pen=pg.mkPen(color=COLOR_HEX_INFECTED, width=2),
        )
        self._curve_r = self._plot_widget.plot(
            name="Recuperados (R)",
            pen=pg.mkPen(color=COLOR_HEX_RECOVERED_NAT, width=2),
        )
        self._curve_d = self._plot_widget.plot(
            name="Óbitos (D)",
            pen=pg.mkPen(color=COLOR_HEX_DECEASED, width=2),
        )

        # Marcador vertical do dia selecionado
        self._day_line = pg.InfiniteLine(
            pos=0,
            angle=90,
            movable=False,
            pen=pg.mkPen(color=ACCENT_TEAL_HEX, width=1.5, style=Qt.PenStyle.DashLine),
        )
        self._plot_widget.addItem(self._day_line)

        layout.addWidget(self._plot_widget, stretch=1)

        # 5 Chips inferiores por compartimento (Tela 7)
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(8)

        self._chip_s = CompartmentChip("S · Suscetíveis", COLOR_HEX_SUSCEPTIBLE)
        self._chip_e = CompartmentChip("E · Expostos", COLOR_HEX_EXPOSED)
        self._chip_i = CompartmentChip("I · Infectados", COLOR_HEX_INFECTED)
        self._chip_r = CompartmentChip("R · Recuperados", COLOR_HEX_RECOVERED_NAT)
        self._chip_d = CompartmentChip("D · Mortos", COLOR_HEX_DECEASED)

        chips_layout.addWidget(self._chip_s)
        chips_layout.addWidget(self._chip_e)
        chips_layout.addWidget(self._chip_i)
        chips_layout.addWidget(self._chip_r)
        chips_layout.addWidget(self._chip_d)

        layout.addLayout(chips_layout)

    def set_back_button_visible(self, visible: bool) -> None:
        """Habilita ou esconde o botão 'Voltar ao mapa' dependendo da navegação."""
        self._btn_back_map.setVisible(visible)

    def update_timeline_data(self, timeline: Timeline | None, current_day: int = 0) -> None:
        """Atualiza os pontos das 5 curvas a partir do ``Timeline``."""
        self._timeline = timeline
        if timeline is None or timeline.days_available <= 0:
            self.clear()
            return

        n_days = timeline.days_available
        days = list(range(n_days))

        s_vals: list[int] = []
        e_vals: list[int] = []
        i_vals: list[int] = []
        r_vals: list[int] = []
        d_vals: list[int] = []

        has_fast_counts = hasattr(timeline, "compartment_counts")
        has_bytes = timeline.vertex_states(0) is not None

        for d in range(n_days):
            if has_fast_counts:
                counts = timeline.compartment_counts(d)  # type: ignore[attr-defined]
                s_vals.append(counts.susceptible)
                e_vals.append(counts.exposed)
                i_vals.append(counts.infected)
                r_vals.append(counts.total_recovered)
                d_vals.append(counts.deceased)
            elif has_bytes:
                v_bytes = timeline.vertex_states(d)
                assert v_bytes is not None
                counts = extract_compartment_counts(v_bytes)
                s_vals.append(counts.susceptible)
                e_vals.append(counts.exposed)
                i_vals.append(counts.infected)
                r_vals.append(counts.total_recovered)
                d_vals.append(counts.deceased)
            else:
                c_counts = timeline.country_counts(d)
                s_vals.append(sum(c.susceptible for c in c_counts))
                e_vals.append(0)
                i_vals.append(sum(c.active for c in c_counts))
                r_vals.append(sum(c.recovered for c in c_counts))
                d_vals.append(sum(c.deaths for c in c_counts))

        self._curve_s.setData(days, s_vals)
        self._curve_e.setData(days, e_vals)
        self._curve_i.setData(days, i_vals)
        self._curve_r.setData(days, r_vals)
        self._curve_d.setData(days, d_vals)

        if s_vals:
            tot = s_vals[0] + e_vals[0] + i_vals[0] + r_vals[0] + d_vals[0]
            self._lbl_subtitle.setText(
                f"Modelo SEIRD · {format_number_br(tot)} indivíduos · {n_days} dias registrados"
            )

        self.set_current_day(current_day)

    def set_current_day(self, day: int) -> None:
        """Posiciona o marcador vertical no dia especificado e atualiza os chips."""
        self._day_line.setValue(day)

        if self._timeline is None or day < 0 or day >= self._timeline.days_available:
            return

        if hasattr(self._timeline, "compartment_counts"):
            counts = self._timeline.compartment_counts(day)  # type: ignore[attr-defined]
            tot = counts.total_vertices
            self._chip_s.set_counts(counts.susceptible, tot)
            self._chip_e.set_counts(counts.exposed, tot)
            self._chip_i.set_counts(counts.infected, tot)
            self._chip_r.set_counts(counts.total_recovered, tot)
            self._chip_d.set_counts(counts.deceased, tot)
            return

        has_bytes = self._timeline.vertex_states(0) is not None
        if has_bytes:
            v_bytes = self._timeline.vertex_states(day)
            if v_bytes is not None:
                counts = extract_compartment_counts(v_bytes)
                tot = counts.total_vertices
                self._chip_s.set_counts(counts.susceptible, tot)
                self._chip_e.set_counts(counts.exposed, tot)
                self._chip_i.set_counts(counts.infected, tot)
                self._chip_r.set_counts(counts.total_recovered, tot)
                self._chip_d.set_counts(counts.deceased, tot)
        else:
            c_counts = self._timeline.country_counts(day)
            s = sum(c.susceptible for c in c_counts)
            i = sum(c.active for c in c_counts)
            r = sum(c.recovered for c in c_counts)
            d = sum(c.deaths for c in c_counts)
            tot = s + i + r + d
            self._chip_s.set_counts(s, tot)
            self._chip_e.set_counts(0, tot)
            self._chip_i.set_counts(i, tot)
            self._chip_r.set_counts(r, tot)
            self._chip_d.set_counts(d, tot)

    def clear(self) -> None:
        """Limpa as curvas e reseta o marcador e chips."""
        empty: list[int] = []
        self._curve_s.setData(empty, empty)
        self._curve_e.setData(empty, empty)
        self._curve_i.setData(empty, empty)
        self._curve_r.setData(empty, empty)
        self._curve_d.setData(empty, empty)
        self._day_line.setValue(0)
        self._chip_s.set_counts(0, 0)
        self._chip_e.set_counts(0, 0)
        self._chip_i.set_counts(0, 0)
        self._chip_r.set_counts(0, 0)
        self._chip_d.set_counts(0, 0)
        self._lbl_subtitle.setText("Modelo SEIRD · Evolução diária da população")

    def reset_zoom(self) -> None:
        """Reajusta automaticamente os eixos X e Y do gráfico para caber na tela."""
        self._plot_widget.enableAutoRange()
        self._plot_widget.autoRange()

    def export_image(self, file_path: str | Path) -> None:
        """Exporta o gráfico como arquivo de imagem PNG."""
        exporter = pg.exporters.ImageExporter(self._plot_widget.plotItem)
        exporter.export(str(file_path))

    def _on_export_clicked(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar gráfico como imagem",
            "curvas_epidemicas.png",
            "Imagens PNG (*.png)",
        )
        if path:
            self.export_image(path)
