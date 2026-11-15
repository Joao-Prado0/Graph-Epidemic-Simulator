"""Controle de reprodução temporal da epidemia (M5 — RF04, RF11).

Gerencia a reprodução sobre uma ``Timeline`` já gravada:
dia atual, avanço passo a passo, retrocesso, pausa, play e multiplicadores de
velocidade (1x, 2x, 5x, 10x).

O ``PlaybackController`` nunca avança a simulação nem recalcula estados; ele
apenas navega pelos dados gravados na linha do tempo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from epidemia.core.errors import ParameterOutOfRangeError

if TYPE_CHECKING:
    from epidemia.core.timeline.protocol import CountryCounts, Timeline

VALID_SPEEDS: tuple[float, ...] = (1.0, 2.0, 5.0, 10.0)


class PlaybackController:
    """Controlador lógico de reprodução sobre o histórico da ``Timeline``."""

    def __init__(self, timeline: Timeline | None = None) -> None:
        self._timeline: Timeline | None = timeline
        self._current_day: int = 0
        self._is_playing: bool = False
        self._speed: float = 1.0

    @property
    def timeline(self) -> Timeline | None:
        """Retorna o ``Timeline`` atualmente associado."""
        return self._timeline

    def attach_timeline(self, timeline: Timeline) -> None:
        """Associa uma nova linha do tempo e posiciona no dia inicial."""
        self._timeline = timeline
        self._current_day = 0
        self._is_playing = False

    def detach_timeline(self) -> None:
        """Desconecta a linha do tempo e reseta o player."""
        self._timeline = None
        self._current_day = 0
        self._is_playing = False

    @property
    def days_available(self) -> int:
        """Retorna o total de dias gravados disponíveis para reprodução."""
        if self._timeline is None:
            return 0
        return self._timeline.days_available

    @property
    def current_day(self) -> int:
        """Retorna o índice do dia atualmente selecionado (0-indexed)."""
        return self._current_day

    @property
    def is_playing(self) -> bool:
        """Indica se a reprodução contínua está ativa."""
        return self._is_playing

    @property
    def speed(self) -> float:
        """Retorna o multiplicador de velocidade atual."""
        return self._speed

    @property
    def is_at_end(self) -> bool:
        """Indica se o dia atual é o último dia gravado disponível."""
        if self.days_available <= 0:
            return True
        return self._current_day >= self.days_available - 1

    def play(self) -> None:
        """Inicia a reprodução. Se estiver no último dia disponível, volta ao dia 0."""
        if self.days_available <= 0:
            self._is_playing = False
            return
        if self.is_at_end and self.days_available > 1:
            self._current_day = 0
        self._is_playing = True

    def pause(self) -> None:
        """Pausa a reprodução contínua."""
        self._is_playing = False

    def toggle_play(self) -> bool:
        """Alterna entre play e pausa, retornando o novo estado."""
        if self._is_playing:
            self.pause()
        else:
            self.play()
        return self._is_playing

    def set_speed(self, speed: float) -> None:
        """Define a velocidade de reprodução (1.0, 2.0, 5.0, 10.0)."""
        speed_float = float(speed)
        if speed_float not in VALID_SPEEDS:
            raise ParameterOutOfRangeError(
                f"Velocidade inválida: {speed}. Permitidas: {VALID_SPEEDS}."
            )
        self._speed = speed_float

    def set_day(self, day: int) -> int:
        """Define o dia atual da reprodução, respeitando os limites disponíveis."""
        target = int(day)
        if self.days_available <= 0:
            self._current_day = 0
            return 0

        max_day = max(0, self.days_available - 1)
        clamped = max(0, min(target, max_day))
        self._current_day = clamped
        return self._current_day

    def step_forward(self) -> int:
        """Avança exatamente 1 dia na reprodução (se disponível)."""
        if self.days_available <= 0:
            return 0
        if self._current_day < self.days_available - 1:
            self._current_day += 1
        return self._current_day

    def step_backward(self) -> int:
        """Recua exatamente 1 dia na reprodução."""
        if self._current_day > 0:
            self._current_day -= 1
        return self._current_day

    def advance_tick(self) -> bool:
        """Avança um passo automático durante a reprodução contínua.

        Retorna True se avançou, ou False se pausou por ter atingido o fim.
        """
        if not self._is_playing:
            return False

        if self._current_day < self.days_available - 1:
            self._current_day += 1
            return True

        # Fim dos dias gravados alcançado
        self.pause()
        return False

    def current_vertex_states(self) -> bytes | None:
        """Retorna os bytes de estado dos vértices no dia atual."""
        if self._timeline is None or self.days_available <= 0:
            return None
        return self._timeline.vertex_states(self._current_day)

    def current_country_counts(self) -> Sequence[CountryCounts]:
        """Retorna as contagens por país no dia atual."""
        if self._timeline is None or self.days_available <= 0:
            return ()
        return self._timeline.country_counts(self._current_day)

    def reset(self) -> None:
        """Reinicia o player para o dia inicial e pausa a reprodução."""
        self._current_day = 0
        self._is_playing = False
