"""Thread de execução assíncrona da simulação (M5 — RNF03).

Executa a calibração de β, a inicialização e o avanço diário (run_day) em laço
fora da thread principal da interface gráfica, emitindo ``day_ready(int)`` a cada
dia concluído no buffer e respeitando pausa e cancelamento imediato.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QMutex, QMutexLocker, QThread, QWaitCondition, Signal

from epidemia.core.errors import EpidemiaError

if TYPE_CHECKING:
    from epidemia.app.simulation_session import SimulationSession


class SimulationThread(QThread):
    """Executa a simulação SEIRD desacoplada da interface."""

    day_ready = Signal(int)
    calibration_done = Signal(float)
    simulation_finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, session: SimulationSession | None = None, parent=None) -> None:
        super().__init__(parent)
        self._session: SimulationSession | None = session
        self._mutex = QMutex()
        self._pause_condition = QWaitCondition()
        self._is_paused: bool = False
        self._step_delay_ms: int = 10  # Pequena pausa para cooperar com o event loop

    def set_session(self, session: SimulationSession) -> None:
        """Associa uma nova sessão de simulação à thread."""
        with QMutexLocker(self._mutex):
            self._session = session

    @property
    def is_paused(self) -> bool:
        """Indica se a thread de cálculo está pausada."""
        with QMutexLocker(self._mutex):
            return self._is_paused

    def pause(self) -> None:
        """Pausa o laço de execução."""
        with QMutexLocker(self._mutex):
            self._is_paused = True

    def resume(self) -> None:
        """Retoma o laço de execução."""
        with QMutexLocker(self._mutex):
            self._is_paused = False
            self._pause_condition.wakeAll()

    def stop(self) -> None:
        """Interrompe a thread com segurança."""
        self.requestInterruption()
        self.resume()  # Acorda se estiver dormindo na condição de pausa

    def run(self) -> None:
        """Ponto de entrada da thread trabalhadora."""
        if self._session is None:
            return

        session = self._session

        try:
            # 1. Calibração de beta (se ainda não calibrado)
            if session.calibrated_beta is None:
                beta = session.calibrate_beta()
                self.calibration_done.emit(beta)

            if self.isInterruptionRequested():
                return

            # 2. Inicialização do dia 0 (se ainda não iniciado)
            if not session.is_started:
                session.start()
                self.day_ready.emit(session.current_day)

            # 3. Laço de avanço diário
            while not self.isInterruptionRequested() and not session.finished:
                # Trata pausa segura
                with QMutexLocker(self._mutex):
                    while self._is_paused and not self.isInterruptionRequested():
                        self._pause_condition.wait(self._mutex, 200)

                if self.isInterruptionRequested():
                    break

                session.run_day()
                self.day_ready.emit(session.current_day)

                if self._step_delay_ms > 0:
                    time.sleep(self._step_delay_ms / 1000.0)

            if not self.isInterruptionRequested() and session.finished:
                self.simulation_finished.emit()

        except EpidemiaError as exc:
            self.error_occurred.emit(str(exc))
        except Exception as exc:
            self.error_occurred.emit(f"Erro inesperado durante a simulação: {exc}")
