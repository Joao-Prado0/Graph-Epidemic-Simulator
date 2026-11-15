"""Gráficos em tempo real das curvas epidemiológicas (M5 — RF08, RF24).

Exibe as curvas dos compartimentos S, E, I, R e D com pyqtgraph, um marcador
vertical do dia atualmente selecionado e exportação da imagem em PNG.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pyqtgraph as pg
import pyqtgraph.exporters
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from epidemia.core.analysis.epidemic_metrics import extract_compartment_counts
from epidemia.ui.styles import (
    COLOR_HEX_DECEASED,
    COLOR_HEX_EXPOSED,
    COLOR_HEX_INFECTED,
    COLOR_HEX_RECOVERED_NAT,
    COLOR_HEX_SUSCEPTIBLE,
)

if TYPE_CHECKING:
    from epidemia.core.timeline.protocol import Timeline


class ChartsView(QWidget):
    """Visualizador das curvas S, E, I, R e D com pyqtgraph e marcador de dia."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Barra de ferramentas superior do gráfico
        top_bar = QHBoxLayout()
        title_lbl = QLabel("Evolução Temporal da População (S, E, I, R, D)")
        title_lbl.setStyleSheet("font-weight: bold; color: #90caf9;")
        top_bar.addWidget(title_lbl)

        top_bar.addStretch(1)

        btn_export = QPushButton("📷 Exportar PNG")
        btn_export.setToolTip("Exporta o gráfico atual como imagem PNG")
        btn_export.clicked.connect(self._on_export_clicked)
        top_bar.addWidget(btn_export)

        layout.addLayout(top_bar)

        # PlotWidget do pyqtgraph com tema escuro
        pg.setConfigOption("background", "#18191c")
        pg.setConfigOption("foreground", "#cccccc")
        pg.setConfigOption("antialias", True)

        self._plot_widget = pg.PlotWidget()
        self._plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self._plot_widget.setLabel("bottom", "Dia de Simulação")
        self._plot_widget.setLabel("left", "Indivíduos")
        self._plot_widget.addLegend(offset=(10, 10))

        # Criação das 5 curvas
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
            pen=pg.mkPen(color="#ffffff", width=1.5, style=Qt.PenStyle.DashLine),
        )
        self._plot_widget.addItem(self._day_line)

        layout.addWidget(self._plot_widget, stretch=1)

    def update_timeline_data(self, timeline: Timeline | None, current_day: int = 0) -> None:
        """Atualiza os pontos das 5 curvas a partir do ``Timeline``."""
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

        has_bytes = timeline.vertex_states(0) is not None

        for d in range(n_days):
            if has_bytes:
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

        self.set_current_day(current_day)

    def set_current_day(self, day: int) -> None:
        """Posiciona o marcador vertical no dia especificado."""
        self._day_line.setValue(day)

    def clear(self) -> None:
        """Limpa as curvas e reseta o marcador."""
        empty: list[int] = []
        self._curve_s.setData(empty, empty)
        self._curve_e.setData(empty, empty)
        self._curve_i.setData(empty, empty)
        self._curve_r.setData(empty, empty)
        self._curve_d.setData(empty, empty)
        self._day_line.setValue(0)

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
