"""Diálogo de exportação de dados e gráficos (M5 — RF08; Tela 13).

Permite ao usuário selecionar formatos (CSV e/ou PNG), escolher o diretório de destino,
acompanhar o progresso da exportação e visualizar o status detalhado por arquivo.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from epidemia.app.export import export_timeline_csv
from epidemia.core.errors import EpidemiaError
from epidemia.ui.styles import (
    ACCENT_TEAL_HEX,
    BORDER_SUBTLE_HEX,
    TEXT_MUTED_HEX,
    TEXT_PRIMARY_HEX,
)

if TYPE_CHECKING:
    from epidemia.core.timeline.protocol import Timeline
    from epidemia.ui.charts_view import ChartsView


class ExportDialog(QDialog):
    """Diálogo modal para exportação de dados em CSV e gráficos em PNG (Tela 13)."""

    def __init__(
        self,
        timeline: Timeline | None,
        charts_view: ChartsView | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._timeline = timeline
        self._charts_view = charts_view
        self._output_dir = Path.cwd() / "exports"

        self.setWindowTitle("Exportar Dados da Simulação")
        self.setMinimumWidth(520)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Cabeçalho
        header = QVBoxLayout()
        header.setSpacing(4)
        lbl_title = QLabel("Exportar Resultados")
        lbl_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {TEXT_PRIMARY_HEX};")
        lbl_subtitle = QLabel(
            "Selecione os formatos e o diretório de destino para exportação dos dados."
        )
        lbl_subtitle.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED_HEX};")
        header.addWidget(lbl_title)
        header.addWidget(lbl_subtitle)
        layout.addLayout(header)

        # 1. Grupo de Formatos
        grp_formats = QGroupBox("Formatos de exportação")
        formats_layout = QVBoxLayout(grp_formats)
        formats_layout.setSpacing(10)

        # CSV Checkbox
        self._chk_csv = QCheckBox("Exportar CSV (séries por dia e por compartimento)")
        self._chk_csv.setChecked(True)
        lbl_csv_sub = QLabel("  Arquivo series_temporais.csv com contagens de S, E, I, R, D.")
        lbl_csv_sub.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED_HEX};")

        # PNG Checkbox
        self._chk_png = QCheckBox("Exportar imagem dos gráficos (PNG)")
        self._chk_png.setChecked(True)
        lbl_png_sub = QLabel("  Arquivo curvas_epidemicas.png com resolução das curvas.")
        lbl_png_sub.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED_HEX};")

        formats_layout.addWidget(self._chk_csv)
        formats_layout.addWidget(lbl_csv_sub)
        formats_layout.addWidget(self._chk_png)
        formats_layout.addWidget(lbl_png_sub)
        layout.addWidget(grp_formats)

        # 2. Grupo de Diretório de Destino
        grp_dir = QGroupBox("Diretório de saída")
        dir_layout = QVBoxLayout(grp_dir)
        dir_layout.setSpacing(6)

        pick_box = QHBoxLayout()
        self._edit_dir = QLineEdit(str(self._output_dir))
        self._btn_browse = QPushButton("Selecionar pasta...")
        self._btn_browse.setObjectName("btnSecondary")
        self._btn_browse.clicked.connect(self._on_browse_clicked)

        pick_box.addWidget(self._edit_dir, stretch=1)
        pick_box.addWidget(self._btn_browse)
        dir_layout.addLayout(pick_box)
        layout.addWidget(grp_dir)

        # 3. Grupo de Progresso e Status
        grp_status = QGroupBox("Progresso")
        status_layout = QVBoxLayout(grp_status)
        status_layout.setSpacing(8)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(14)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(
            f"QProgressBar {{ background-color: #0b141a; border: 1px solid {BORDER_SUBTLE_HEX};"
            f"  border-radius: 4px; }}"
            f"QProgressBar::chunk {{ background-color: {ACCENT_TEAL_HEX}; border-radius: 3px; }}"
        )
        status_layout.addWidget(self._progress_bar)

        status_box = QFrame()
        status_box.setStyleSheet(
            f"background-color: #0b141a; border: 1px solid {BORDER_SUBTLE_HEX};"
            f"border-radius: 6px; padding: 8px;"
        )
        box_layout = QVBoxLayout(status_box)
        box_layout.setSpacing(4)

        self._lbl_status_csv = QLabel("series_temporais.csv: Aguardando")
        self._lbl_status_csv.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED_HEX};")
        self._lbl_status_png = QLabel("curvas_epidemicas.png: Aguardando")
        self._lbl_status_png.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED_HEX};")

        box_layout.addWidget(self._lbl_status_csv)
        box_layout.addWidget(self._lbl_status_png)
        status_layout.addWidget(status_box)

        layout.addWidget(grp_status)

        # Rodapé de Ações
        footer = QHBoxLayout()
        footer.setSpacing(8)

        self._btn_close = QPushButton("Fechar")
        self._btn_close.setObjectName("btnSecondary")
        self._btn_close.clicked.connect(self.reject)

        self._btn_open_folder = QPushButton("Abrir pasta")
        self._btn_open_folder.setObjectName("btnSecondary")
        self._btn_open_folder.setEnabled(False)
        self._btn_open_folder.clicked.connect(self._on_open_folder_clicked)

        self._btn_export = QPushButton("Exportar")
        self._btn_export.setObjectName("btnPrimary")
        self._btn_export.clicked.connect(self._on_export_clicked)

        footer.addWidget(self._btn_close)
        footer.addWidget(self._btn_open_folder)
        footer.addStretch(1)
        footer.addWidget(self._btn_export)

        layout.addLayout(footer)

    def _on_browse_clicked(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self,
            "Selecionar pasta de destino",
            self._edit_dir.text(),
        )
        if chosen:
            self._output_dir = Path(chosen)
            self._edit_dir.setText(str(self._output_dir))

    def _on_open_folder_clicked(self) -> None:
        target_path = Path(self._edit_dir.text())
        if target_path.exists():
            QDesktopServices.openUrl(target_path.as_uri())

    def _on_export_clicked(self) -> None:
        export_csv = self._chk_csv.isChecked()
        export_png = self._chk_png.isChecked()

        if not export_csv and not export_png:
            QMessageBox.information(
                self,
                "Nenhum formato selecionado",
                "Selecione ao menos um formato para exportação (CSV ou PNG).",
            )
            return

        if self._timeline is None or self._timeline.days_available == 0:
            QMessageBox.warning(
                self,
                "Sem dados gravados",
                "Não há dados de simulação gravados para exportar.",
            )
            return

        dest_dir = Path(self._edit_dir.text().strip())
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Erro ao criar pasta",
                f"Não foi possível criar o diretório de destino:\n{exc}",
            )
            return

        total_tasks = int(export_csv) + int(export_png)
        completed_tasks = 0

        self._btn_export.setEnabled(False)
        self._progress_bar.setValue(10)

        # 1. Exporta CSV
        if export_csv:
            csv_path = dest_dir / "series_temporais.csv"
            try:
                days_exported = export_timeline_csv(self._timeline, csv_path)
                self._lbl_status_csv.setText(
                    f"series_temporais.csv: Concluído ({days_exported} dias gravados)"
                )
                self._lbl_status_csv.setStyleSheet(
                    f"font-size: 12px; color: {ACCENT_TEAL_HEX}; font-weight: bold;"
                )
                completed_tasks += 1
                self._progress_bar.setValue(int(completed_tasks / total_tasks * 100))
            except EpidemiaError as exc:
                self._lbl_status_csv.setText(f"series_temporais.csv: Erro ({exc})")
                self._lbl_status_csv.setStyleSheet("font-size: 12px; color: #ef5350;")
            except Exception as exc:  # noqa: BLE001
                self._lbl_status_csv.setText(f"series_temporais.csv: Falha ({exc})")
                self._lbl_status_csv.setStyleSheet("font-size: 12px; color: #ef5350;")

        # 2. Exporta PNG
        if export_png:
            png_path = dest_dir / "curvas_epidemicas.png"
            if self._charts_view is not None:
                try:
                    self._charts_view.export_image(png_path)
                    self._lbl_status_png.setText("curvas_epidemicas.png: Concluído")
                    self._lbl_status_png.setStyleSheet(
                        f"font-size: 12px; color: {ACCENT_TEAL_HEX}; font-weight: bold;"
                    )
                    completed_tasks += 1
                    self._progress_bar.setValue(int(completed_tasks / total_tasks * 100))
                except Exception as exc:  # noqa: BLE001
                    self._lbl_status_png.setText(f"curvas_epidemicas.png: Erro ({exc})")
                    self._lbl_status_png.setStyleSheet("font-size: 12px; color: #ef5350;")
            else:
                self._lbl_status_png.setText("curvas_epidemicas.png: Gráfico não disponível")
                self._lbl_status_png.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED_HEX};")

        self._btn_export.setEnabled(True)
        self._btn_open_folder.setEnabled(True)
        if completed_tasks == total_tasks:
            self._progress_bar.setValue(100)
            QMessageBox.information(
                self,
                "Exportação Concluída",
                f"Arquivos exportados com sucesso para:\n{dest_dir}",
            )
