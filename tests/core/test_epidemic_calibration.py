"""Testes unitários da calibração de beta por bisseção e fórmula de Newman (M3)."""

from __future__ import annotations

import pytest

from epidemia.core.epidemic import (
    CalibrationResult,
    SimulationConfig,
    calibrate_beta,
    measure_empirical_r0,
    newman_analytic_r0,
)
from epidemia.core.errors import ParameterOutOfRangeError
from epidemia.core.graph.graph import Graph
from epidemia.core.graph.weights import effective_distance_cost, transmission_probability
from epidemia.core.seeds import SeedBook


def _ring_chord_graph(n: int = 30, weight: float = 0.8) -> Graph:
    """Cria um grafo conexo regular de grau 4 (anel + cordas de passo 2)."""
    g = Graph(n)
    for u in range(n):
        g.add_edge(u, (u + 1) % n, weight=weight)
        g.add_edge(u, (u + 2) % n, weight=weight)
    return g


def test_newman_analytic_r0_properties() -> None:
    empty = Graph(10)
    assert newman_analytic_r0(empty, beta=0.2, gamma=0.1) == 0.0
    assert newman_analytic_r0(Graph(0), beta=0.2, gamma=0.1) == 0.0

    g = _ring_chord_graph(20, weight=1.0)
    r_low = newman_analytic_r0(g, beta=0.05, gamma=0.15)
    r_high = newman_analytic_r0(g, beta=0.25, gamma=0.15)
    assert 0.0 < r_low < r_high

    # Grafo regular de grau 4 tem (<k^2>/<k> - 1) = 4 - 1 = 3.0; logo R0_Newman <= 3.0
    assert r_high < 3.0

    # Maior taxa de saída gamma reduz o R0 analítico
    r_faster_recovery = newman_analytic_r0(g, beta=0.25, gamma=0.40)
    assert r_faster_recovery < r_high


def test_newman_analytic_r0_validation() -> None:
    g = _ring_chord_graph(10)
    with pytest.raises(ParameterOutOfRangeError):
        newman_analytic_r0(g, beta=0.0, gamma=0.1)
    with pytest.raises(ParameterOutOfRangeError):
        newman_analytic_r0(g, beta=0.1, gamma=-0.1)
    with pytest.raises(ParameterOutOfRangeError):
        newman_analytic_r0(g, beta=True, gamma=0.1)  # type: ignore[arg-type]


def test_measure_empirical_r0_monotonic_and_preserves_graph_state() -> None:
    g = _ring_chord_graph(25, weight=0.6)
    g.update_transmission_costs(0.123)
    g.set_vertex_isolated(0, True)

    cfg = SimulationConfig(seed=42, r0=2.5, exit_rate_gamma=0.14)
    seeds = SeedBook(cfg.seed)

    r1 = measure_empirical_r0(g, cfg, beta=0.02, seeds=seeds)
    r2 = measure_empirical_r0(g, cfg, beta=0.08, seeds=seeds)
    r3 = measure_empirical_r0(g, cfg, beta=0.20, seeds=seeds)

    assert 0.0 < r1 < r2 < r3
    # Estado original do grafo deve ser preservado após as simulações de teste
    assert g.beta == pytest.approx(0.123)
    assert g.is_vertex_isolated(0)


def test_measure_empirical_r0_empty_and_invalid() -> None:
    cfg = SimulationConfig()
    assert measure_empirical_r0(Graph(5), cfg, beta=0.1) == 0.0

    g = _ring_chord_graph(8)
    with pytest.raises(ParameterOutOfRangeError):
        measure_empirical_r0(g, cfg, beta=0.0)
    with pytest.raises(ParameterOutOfRangeError):
        measure_empirical_r0(g, cfg, beta=0.1, trials=0)
    with pytest.raises(ParameterOutOfRangeError):
        measure_empirical_r0(g, cfg, beta=0.1, horizon_days=0)


def test_calibrate_beta_converges_and_updates_graph_costs() -> None:
    g = _ring_chord_graph(30, weight=0.7)
    cfg_low = SimulationConfig(seed=77, r0=1.5, exit_rate_gamma=0.14)
    cfg_high = SimulationConfig(seed=77, r0=3.2, exit_rate_gamma=0.14)

    res_low = calibrate_beta(g, cfg_low, tolerance=0.05)
    assert isinstance(res_low, CalibrationResult)
    assert res_low.target_r0 == pytest.approx(1.5)
    assert res_low.measured_r0 == pytest.approx(1.5, abs=0.08)
    assert res_low.newman_r0 > 0.0
    assert res_low.iterations >= 1
    assert res_low.elapsed_ms >= 0.0

    # Verifica Decisão A16: custos de caminho -ln(p_ij) do grafo atualizados com best_beta
    assert g.beta == pytest.approx(res_low.beta)
    expected_cost = effective_distance_cost(transmission_probability(0.7, res_low.beta))
    assert g.edge_cost(0, 1) == pytest.approx(expected_cost)

    res_high = calibrate_beta(g, cfg_high, tolerance=0.05)
    assert res_high.measured_r0 == pytest.approx(3.2, abs=0.08)
    assert res_high.beta > res_low.beta


def test_calibrate_beta_on_empty_graph_and_validations() -> None:
    empty = Graph(6)
    cfg = SimulationConfig(r0=2.0)
    res = calibrate_beta(empty, cfg)
    assert res.measured_r0 == 0.0
    assert res.newman_r0 == 0.0
    assert res.iterations == 0

    g = _ring_chord_graph(10)
    with pytest.raises(ParameterOutOfRangeError):
        calibrate_beta(g, cfg, beta_min=0.0)
    with pytest.raises(ParameterOutOfRangeError):
        calibrate_beta(g, cfg, beta_min=0.5, beta_max=0.2)
    with pytest.raises(ParameterOutOfRangeError):
        calibrate_beta(g, cfg, max_iterations=0)
    with pytest.raises(ParameterOutOfRangeError):
        calibrate_beta(g, cfg, tolerance=0.0)
