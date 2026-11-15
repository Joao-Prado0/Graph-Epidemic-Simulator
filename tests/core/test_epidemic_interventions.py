"""Testes de isolamento e vacinação automáticos (M3)."""

from __future__ import annotations

import random

import pytest

from epidemia.core.analysis.epidemic_metrics import (
    STATE_D,
    STATE_E,
    STATE_I,
    STATE_R,
    STATE_S,
)
from epidemia.core.epidemic.interventions import (
    apply_daily_isolation,
    apply_daily_vaccination,
    release_isolation,
)
from epidemia.core.epidemic.parameters import INTERVENTION_TABLE, InterventionParams
from epidemia.core.errors import ParameterOutOfRangeError
from epidemia.core.graph.graph import Graph


def _path_graph(n: int) -> Graph:
    g = Graph(n)
    for u in range(n - 1):
        g.add_edge(u, u + 1, weight=1.0)
    return g


def test_isolation_masks_vertex_and_restores_same_edges() -> None:
    g = _path_graph(3)  # 0 - 1 - 2
    states = [STATE_S, STATE_I, STATE_S]
    remaining = [0, 0, 0]
    params = InterventionParams("t", 1.0, 3, 0, 0.0)
    edges_before = g.num_edges

    assert apply_daily_isolation(g, states, remaining, params, random.Random(1)) == 1
    assert g.is_vertex_isolated(1) and remaining[1] == 3
    assert list(g.neighbors(0)) == []  # vizinho não alcança o isolado
    assert list(g.neighbors(1)) == []
    assert g.num_edges == edges_before  # estrutura intacta

    states[1] = STATE_R  # deixa de ser I: só o prazo manda agora
    for _ in range(2):
        apply_daily_isolation(g, states, remaining, params, random.Random(1))
        assert g.is_vertex_isolated(1)
    apply_daily_isolation(g, states, remaining, params, random.Random(1))
    assert not g.is_vertex_isolated(1) and remaining[1] == 0
    assert sorted(g.neighbors(1)) == [0, 2]  # voltou com as mesmas arestas


def test_isolation_duration_and_no_reisolation_same_day() -> None:
    g = _path_graph(2)
    states = [STATE_I, STATE_S]
    remaining = [0, 0]
    params = InterventionParams("t", 1.0, 2, 0, 0.0)
    rng = random.Random(0)
    seen = []
    for _ in range(5):
        apply_daily_isolation(g, states, remaining, params, rng)
        seen.append(g.is_vertex_isolated(0))
    # isolado, isolado, liberado no dia, isolado de novo, isolado
    assert seen == [True, True, False, True, True]


def test_only_infectious_vertices_get_isolated() -> None:
    g = _path_graph(5)
    states = [STATE_S, STATE_E, STATE_R, STATE_D, STATE_I]
    remaining = [0] * 5
    params = InterventionParams("t", 1.0, 5, 0, 0.0)
    assert apply_daily_isolation(g, states, remaining, params, random.Random(3)) == 1
    assert [g.is_vertex_isolated(u) for u in range(5)] == [False, False, False, False, True]


def test_isolation_disabled_levels_do_nothing() -> None:
    g = _path_graph(3)
    states = [STATE_I] * 3
    remaining = [0] * 3
    none = INTERVENTION_TABLE["nenhum"]
    assert apply_daily_isolation(g, states, remaining, none, random.Random(1)) == 0
    assert not any(g.is_vertex_isolated(u) for u in range(3))


def test_isolation_rate_matches_probability() -> None:
    g = Graph(2000)
    states = [STATE_I] * 2000
    remaining = [0] * 2000
    params = InterventionParams("t", 0.30, 14, 0, 0.0)
    n = apply_daily_isolation(g, states, remaining, params, random.Random(7))
    assert 520 < n < 680  # esperado 600


def test_isolation_is_deterministic_per_seed() -> None:
    def run(seed: int) -> list[int]:
        g = Graph(300)
        remaining = [0] * 300
        params = InterventionParams("t", 0.3, 5, 0, 0.0)
        apply_daily_isolation(g, [STATE_I] * 300, remaining, params, random.Random(seed))
        return remaining

    assert run(5) == run(5)
    assert run(5) != run(6)


def test_release_isolation_helper() -> None:
    g = _path_graph(2)
    remaining = [4, 0]
    g.set_vertex_isolated(0, True)
    release_isolation(g, remaining, 0)
    assert remaining[0] == 0 and not g.is_vertex_isolated(0)


def test_isolation_size_mismatch_raises() -> None:
    with pytest.raises(ParameterOutOfRangeError):
        apply_daily_isolation(
            Graph(2), [STATE_S], [0, 0], INTERVENTION_TABLE["alto"], random.Random(1)
        )


def test_vaccination_waits_for_start_day() -> None:
    params = InterventionParams("t", 0.0, 0, 10, 1.0, 1.0)
    states = [STATE_S] * 4
    vaccinated = [0] * 4
    assert apply_daily_vaccination(states, vaccinated, 9, params, random.Random(1)) == 0
    assert states == [STATE_S] * 4
    assert apply_daily_vaccination(states, vaccinated, 10, params, random.Random(1)) == 4
    assert states == [STATE_R] * 4 and vaccinated == [1] * 4


def test_vaccination_only_changes_susceptibles() -> None:
    params = InterventionParams("t", 0.0, 0, 0, 1.0, 1.0)
    states = [STATE_S, STATE_E, STATE_I, STATE_R, STATE_D]
    vaccinated = [0] * 5
    assert apply_daily_vaccination(states, vaccinated, 0, params, random.Random(1)) == 1
    assert states == [STATE_R, STATE_E, STATE_I, STATE_R, STATE_D]
    assert vaccinated == [1, 0, 0, 0, 0]  # R natural segue sem a flag


def test_vaccination_zero_efficacy_or_fraction_keeps_everyone_susceptible() -> None:
    states = [STATE_S] * 50
    vaccinated = [0] * 50
    no_effect = InterventionParams("t", 0.0, 0, 0, 1.0, 0.0)
    assert apply_daily_vaccination(states, vaccinated, 5, no_effect, random.Random(1)) == 0
    assert states == [STATE_S] * 50
    none = INTERVENTION_TABLE["nenhum"]
    assert apply_daily_vaccination(states, vaccinated, 5, none, random.Random(1)) == 0


def test_vaccination_rate_is_fraction_times_efficacy() -> None:
    params = InterventionParams("t", 0.0, 0, 0, 0.5, 0.8)
    states = [STATE_S] * 5000
    vaccinated = [0] * 5000
    n = apply_daily_vaccination(states, vaccinated, 0, params, random.Random(11))
    assert 1850 < n < 2150  # esperado 2000 (0.5 * 0.8)
    assert sum(vaccinated) == n == states.count(STATE_R)


def test_vaccination_size_mismatch_raises() -> None:
    with pytest.raises(ParameterOutOfRangeError):
        apply_daily_vaccination([STATE_S], [0, 0], 0, INTERVENTION_TABLE["alto"], random.Random(1))
