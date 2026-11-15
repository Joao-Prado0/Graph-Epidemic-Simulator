"""Testes unitários do controlador de reprodução (RF04, RF11)."""

from __future__ import annotations

import pytest

from epidemia.app.playback import PlaybackController
from epidemia.app.simulation_session import SimulationSession
from epidemia.core.epidemic.parameters import SimulationConfig
from epidemia.core.errors import ParameterOutOfRangeError
from tests.fixtures import create_synthetic_world


def test_playback_nao_altera_historico_ao_pausar_e_voltar():
    """Verifica que avançar, pausar e retroceder não altera o buffer nem os estados."""
    world = create_synthetic_world(total_vertices=60, seed=42)
    session = SimulationSession(world)
    config = SimulationConfig(
        seed=42,
        r0=2.2,
        exit_rate_gamma=0.2,
        mortality=0.04,
        incubation_days=3.0,
        intervention_level="baixo",
        max_days=30,
    )
    session.configure(config)
    session.start()

    for _ in range(8):
        session.run_day()

    timeline = session.timeline()
    dias_iniciais = timeline.days_available
    assert dias_iniciais == 9

    # Guarda cópia de todos os bytes gravados
    estados_originais = [timeline.vertex_states(d) for d in range(dias_iniciais)]

    player = PlaybackController(timeline)
    assert player.current_day == 0

    # Navega para frente, pausa, vai para o dia 5, depois para o dia 2
    player.play()
    assert player.is_playing
    player.set_day(5)
    assert player.current_day == 5

    player.step_backward()
    assert player.current_day == 4

    player.pause()
    assert not player.is_playing

    player.step_forward()
    assert player.current_day == 5

    # O histórico deve permanecer 100% idêntico
    assert timeline.days_available == dias_iniciais
    for d in range(dias_iniciais):
        assert timeline.vertex_states(d) == estados_originais[d]


def test_playback_velocidades_validas_e_invalidas():
    """Verifica validação de velocidades permitidas."""
    player = PlaybackController()
    for v in (1.0, 2.0, 5.0, 10.0):
        player.set_speed(v)
        assert player.speed == v

    with pytest.raises(ParameterOutOfRangeError):
        player.set_speed(3.0)

    with pytest.raises(ParameterOutOfRangeError):
        player.set_speed(0.5)


def test_playback_limites_e_advance_tick():
    """Verifica limites do slider e parada automática em advance_tick."""
    world = create_synthetic_world(total_vertices=60, seed=42)
    session = SimulationSession(world)
    session.configure(SimulationConfig(seed=42, max_days=10))
    session.start()
    session.run_day()
    session.run_day()

    timeline = session.timeline()
    player = PlaybackController(timeline)
    assert player.days_available == 3

    # Clamping
    assert player.set_day(99) == 2
    assert player.set_day(-5) == 0

    # Reprodução e parada automática
    player.set_day(1)
    player.play()
    assert player.advance_tick() is True
    assert player.current_day == 2

    # No fim, advance_tick pausa
    assert player.advance_tick() is False
    assert not player.is_playing
    assert player.is_at_end


def test_playback_reset():
    """Verifica reset do player."""
    player = PlaybackController()
    player.set_day(5)
    player.play()
    player.reset()
    assert player.current_day == 0
    assert not player.is_playing
