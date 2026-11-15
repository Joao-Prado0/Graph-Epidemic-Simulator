"""Testes de SimulationConfig e da tabela de níveis de intervenção (M3)."""

from __future__ import annotations

import dataclasses

import pytest

from epidemia.core.epidemic.parameters import (
    INTERVENTION_TABLE,
    InterventionParams,
    SimulationConfig,
    normalize_intervention_level,
    resolve_intervention_params,
)
from epidemia.core.errors import ParameterOutOfRangeError


def test_defaults_and_derived_values() -> None:
    cfg = SimulationConfig()
    assert cfg.seed == 42 and cfg.scenario == "global"
    assert cfg.sigma == pytest.approx(0.25)
    assert cfg.gamma == cfg.exit_rate_gamma
    assert cfg.intervention_params.level == "baixo"


def test_config_is_frozen() -> None:
    cfg = SimulationConfig()
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.r0 = 3.0  # type: ignore[misc]
    assert dataclasses.replace(cfg, r0=3.0).r0 == 3.0  # nova config é possível


def test_portuguese_aliases() -> None:
    cfg = SimulationConfig(r0=3.0, exit_rate_gamma=0.2, mortality=0.1, incubation_days=2.0)
    assert cfg.contagio_r0 == 3.0
    assert cfg.recuperacao_gamma == 0.2
    assert cfg.mortalidade == 0.1
    assert cfg.incubacao_dias == 2.0
    assert cfg.nivel_intervencao == "baixo"


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("low", "baixo"),
        ("MEDIUM", "medio"),
        ("médio", "medio"),
        (" High ", "alto"),
        ("none", "nenhum"),
        ("alto", "alto"),
    ],
)
def test_level_normalization(given: str, expected: str) -> None:
    assert normalize_intervention_level(given) == expected
    assert SimulationConfig(intervention_level=given).intervention_level == expected


def test_intervention_table_matches_modelagem() -> None:
    low, mid, high = (INTERVENTION_TABLE[k] for k in ("baixo", "medio", "alto"))
    assert (low.isolation_daily_prob, low.isolation_duration_days) == (0.05, 7)
    assert (mid.isolation_daily_prob, mid.isolation_duration_days) == (0.15, 10)
    assert (high.isolation_daily_prob, high.isolation_duration_days) == (0.30, 14)
    assert (low.vaccination_start_day, low.vaccination_daily_fraction) == (180, 0.002)
    assert (mid.vaccination_start_day, mid.vaccination_daily_fraction) == (120, 0.005)
    assert (high.vaccination_start_day, high.vaccination_daily_fraction) == (60, 0.010)
    assert all(p.vaccine_efficacy == 0.8 for p in INTERVENTION_TABLE.values())
    none = INTERVENTION_TABLE["nenhum"]
    assert none.isolation_daily_prob == 0.0 and none.vaccination_daily_fraction == 0.0


def test_levels_are_monotonic_in_intensity() -> None:
    order = [INTERVENTION_TABLE[k] for k in ("baixo", "medio", "alto")]
    for a, b in zip(order, order[1:], strict=False):
        assert a.isolation_daily_prob < b.isolation_daily_prob
        assert a.isolation_duration_days < b.isolation_duration_days
        assert a.vaccination_start_day > b.vaccination_start_day
        assert a.vaccination_daily_fraction < b.vaccination_daily_fraction


def test_resolve_intervention_params() -> None:
    custom = InterventionParams("x", 0.1, 3, 5, 0.1)
    assert resolve_intervention_params(custom) is custom
    assert resolve_intervention_params("alto") is INTERVENTION_TABLE["alto"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"seed": 1.5},
        {"seed": True},
        {"scenario": "marte"},
        {"r0": 0},
        {"r0": -1.0},
        {"r0": float("nan")},
        {"r0": "2"},
        {"exit_rate_gamma": 0},
        {"exit_rate_gamma": float("inf")},
        {"incubation_days": 0},
        {"mortality": -0.1},
        {"mortality": 1.1},
        {"intervention_level": "extremo"},
        {"intervention_level": 3},
        {"max_days": 0},
        {"day_zero_threshold_m": 0},
        {"patient_zero": ()},
        {"patient_zero": (-1,)},
        {"patient_zero": (1.5,)},
        {"patient_zero": "12"},
    ],
)
def test_invalid_values_raise(kwargs: dict[str, object]) -> None:
    with pytest.raises(ParameterOutOfRangeError):
        SimulationConfig(**kwargs)  # type: ignore[arg-type]


def test_mortality_bounds_are_inclusive() -> None:
    assert SimulationConfig(mortality=0.0).mortality == 0.0
    assert SimulationConfig(mortality=1.0).mortality == 1.0


def test_patient_zero_is_converted_to_tuple() -> None:
    cfg = SimulationConfig(patient_zero=[3, 5])  # type: ignore[arg-type]
    assert cfg.patient_zero == (3, 5)
    assert SimulationConfig().patient_zero is None


def test_regional_scenario_accepted() -> None:
    assert SimulationConfig(scenario="regional_ebola").scenario == "regional_ebola"
