"""Barra de reprodução temporal (M5 — RF04, RF11).

Componente de interface com botões de play, pausa, retrocesso, avanço,
reinício, seletor de velocidades (1x, 2x, 5x, 10x) e slider de dias.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QWidget,
)

if TYPE_CHECKING:
    from epidemia.app.playback import PlaybackController


class PlayerBar(QWidget):
    """Barra horizontal com controles de reprodução e linha do tempo."""

    day_changed = Signal(int)
    reset_requested = Signal()

    def __init__(
        self,
        playback: PlaybackController,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._playback = playback

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer_tick)

        self._init_ui()
        self.update_state()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Botão Reiniciar
        self._btn_reset = QPushButton("↺ Reiniciar")
        self._btn_reset.setToolTip("Descarta a execução atual e volta ao início")
        self._btn_reset.clicked.connect(self._on_reset_clicked)
        layout.addWidget(self._btn_reset)

        # Botão Voltar 1 dia
        self._btn_back = QPushButton("⏮ -1d")
        self._btn_back.setToolTip("Volta um dia no histórico gravado")
        self._btn_back.clicked.connect(self._on_step_back)
        layout.addWidget(self._btn_back)

        # Botão Play / Pausa
        self._btn_play = QPushButton("▶ Reproduzir")
        self._btn_play.setObjectName("btnPrimary")
        self._btn_play.setToolTip("Inicia ou pausa a reprodução contínua")
        self._btn_play.clicked.connect(self._on_toggle_play)
        layout.addWidget(self._btn_play)

        # Botão Avançar 1 dia
        self._btn_forward = QPushButton("⏭ +1d")
        self._btn_forward.setToolTip("Avança um dia no histórico gravado")
        self._btn_forward.clicked.connect(self._on_step_forward)
        layout.addWidget(self._btn_forward)

        # Seletor de velocidade (1x, 2x, 5x, 10x)
        self._speed_group = QButtonGroup(self)
        self._speed_group.setExclusive(True)

        layout.addWidget(QLabel("Velocidade:"))
        for speed in (1.0, 2.0, 5.0, 10.0):
            label = f"×{int(speed)}"
            btn = QPushButton(label)
            btn.setCheckable(True)
            if speed == 1.0:
                btn.setChecked(True)
            btn.clicked.connect(lambda _, s=speed: self._on_speed_changed(s))
            self._speed_group.addButton(btn)
            layout.addWidget(btn)

        # Slider de dias
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 0)
        self._slider.setValue(0)
        self._slider.valueChanged.connect(self._on_slider_moved)
        layout.addWidget(self._slider, stretch=1)

        # Label do dia
        self._lbl_day = QLabel("Dia: 0 / 0")
        self._lbl_day.setMinimumWidth(100)
        self._lbl_day.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl_day)

    def _on_toggle_play(self) -> None:
        if self._playback.is_playing:
            self._playback.pause()
            self._timer.stop()
        else:
            self._playback.play()
            self._update_timer_interval()
            self._timer.start()
        self.update_state()

    def _on_step_back(self) -> None:
        day = self._playback.step_backward()
        self.update_state()
        self.day_changed.emit(day)

    def _on_step_forward(self) -> None:
        day = self._playback.step_forward()
        self.update_state()
        self.day_changed.emit(day)

    def _on_reset_clicked(self) -> None:
        self._playback.reset()
        self._timer.stop()
        self.update_state()
        self.reset_requested.emit()

    def _on_speed_changed(self, speed: float) -> None:
        self._playback.set_speed(speed)
        if self._playback.is_playing:
            self._update_timer_interval()

    def _update_timer_interval(self) -> None:
        # Base: 1x = 500ms por dia gravado; 10x = 50ms
        interval = max(30, int(500.0 / self._playback.speed))
        self._timer.setInterval(interval)

    def _on_slider_moved(self, value: int) -> None:
        if value != self._playback.current_day:
            day = self._playback.set_day(value)
            self._lbl_day.setText(f"Dia: {day} / {max(0, self._playback.days_available - 1)}")
            self.day_changed.emit(day)

    def _on_timer_tick(self) -> None:
        still_running = self._playback.advance_tick()
        self.update_state()
        self.day_changed.emit(self._playback.current_day)
        if not still_running:
            self._timer.stop()

    def update_state(self) -> None:
        """Sincroniza os widgets com o estado atual do PlaybackController."""
        max_day = max(0, self._playback.days_available - 1)
        cur_day = self._playback.current_day

        self._slider.blockSignals(True)
        self._slider.setRange(0, max_day)
        self._slider.setValue(cur_day)
        self._slider.blockSignals(False)

        self._lbl_day.setText(f"Dia: {cur_day} / {max_day}")

        if self._playback.is_playing:
            self._btn_play.setText("⏸ Pausar")
            self._btn_play.setObjectName("btnDanger")
        else:
            self._btn_play.setText("▶ Reproduzir")
            self._btn_play.setObjectName("btnPrimary")

        self._btn_play.style().unpolish(self._btn_play)
        self._btn_play.style().polish(self._btn_play)
