"""Testes das leis de transição SEIRD e da solução de campo médio (M3)."""

from __future__ import annotations

import math

import pytest

from epidemia.core.epidemic.model import (
    edge_infection_probability,
    exit_probability,
    progression_probability,
    rate_to_daily_probability,
    solve_mean_field_seird,
)
from epidemia.core.errors import ParameterOutOfRangeError


def test_rate_to_probability_known_values() -> None:
    assert rate_to_daily_probability(0.0) == 0.0
    assert rate_to_daily_probability(1.0) == pytest.approx(1 - math.exp(-1))
    assert 0.0 < rate_to_daily_probability(50.0) <= 1.0  # nunca passa de 1


def test_progression_and_exit_probabilities() -> None:
    assert progression_probability(4.0) == pytest.approx(1 - math.exp(-0.25))
    assert exit_probability(0.22) == pytest.approx(1 - math.exp(-0.22))


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf"), True, "1"])
def test_progression_rejects_invalid(bad: object) -> None:
    with pytest.raises(ParameterOutOfRangeError):
        progression_probability(bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [0.0, -0.1, float("inf")])
def test_exit_rejects_invalid(bad: float) -> None:
    with pytest.raises(ParameterOutOfRangeError):
        exit_probability(bad)


def test_rate_rejects_negative() -> None:
    with pytest.raises(ParameterOutOfRangeError):
        rate_to_daily_probability(-0.5)


def test_edge_infection_probability_delegates_to_m1() -> None:
    assert edge_infection_probability(0.5, 0.4) == pytest.approx(1 - math.exp(-0.2))
    assert edge_infection_probability(1.0, 0.08) < edge_infection_probability(1.0, 0.16)


def test_mean_field_one_step_by_hand() -> None:
    # N=10, 1 infectado, p=0.1: novos expostos = 9 * (1 - 0.9) = 0.9
    t = solve_mean_field_seird(
        10,
        1,
        edge_probability=0.1,
        incubation_progression=0.5,
        exit_probability_value=0.4,
        mortality=0.25,
        days=1,
    )
    assert t.susceptible[1] == pytest.approx(9 - 0.9)
    assert t.exposed[1] == pytest.approx(0.9)
    assert t.infected[1] == pytest.approx(1 - 0.4)
    assert t.recovered[1] == pytest.approx(0.4 * 0.75)
    assert t.deceased[1] == pytest.approx(0.4 * 0.25)


def test_mean_field_conserves_population() -> None:
    t = solve_mean_field_seird(
        1000,
        5,
        edge_probability=0.002,
        incubation_progression=0.2,
        exit_probability_value=0.1,
        mortality=0.05,
        days=300,
    )
    for day in range(301):
        total = (
            t.susceptible[day]
            + t.exposed[day]
            + t.infected[day]
            + t.recovered[day]
            + t.deceased[day]
        )
        assert total == pytest.approx(1000)


def test_mean_field_no_transmission_without_edge_probability() -> None:
    t = solve_mean_field_seird(
        100,
        3,
        edge_probability=0.0,
        incubation_progression=0.5,
        exit_probability_value=0.3,
        days=50,
    )
    assert all(x == 0.0 for x in t.exposed)
    assert t.susceptible[-1] == 97
    assert t.infected[-1] < 1e-5


def test_mean_field_epidemic_peak_and_terminal_state() -> None:
    t = solve_mean_field_seird(
        1000,
        5,
        edge_probability=0.002,
        incubation_progression=0.3,
        exit_probability_value=0.1,
        days=400,
    )
    assert t.peak_infected > 50
    assert 0 < t.peak_day < 400
    assert t.susceptible[-1] < 1000 - 5  # houve epidemia
    assert t.deceased[-1] == 0.0  # mortalidade padrão 0


def test_mean_field_validations() -> None:
    kwargs = {
        "edge_probability": 0.1,
        "incubation_progression": 0.5,
        "exit_probability_value": 0.5,
    }
    with pytest.raises(ParameterOutOfRangeError):
        solve_mean_field_seird(0, 1, **kwargs)
    with pytest.raises(ParameterOutOfRangeError):
        solve_mean_field_seird(10, 0, **kwargs)
    with pytest.raises(ParameterOutOfRangeError):
        solve_mean_field_seird(10, 11, **kwargs)
    with pytest.raises(ParameterOutOfRangeError):
        solve_mean_field_seird(10, 1, days=-1, **kwargs)
    with pytest.raises(ParameterOutOfRangeError):
        solve_mean_field_seird(10, 1, mortality=1.5, **kwargs)
    with pytest.raises(ParameterOutOfRangeError):
        solve_mean_field_seird(10, 1, **{**kwargs, "edge_probability": 1.2})
