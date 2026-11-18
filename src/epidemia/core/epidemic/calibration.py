"""Calibração de beta por bisseção e fórmula analítica de Newman (M3 — Modelagem 2.6).

Antes de iniciar a simulação principal, o motor ajusta a taxa de transmissão por
aresta ``beta`` por busca binária (bisseção) em simulações curtas com números
aleatórios comuns (``SUBSYSTEM_CALIBRATION``), fazendo o ``R0`` efetivo na rede
aproximar o ``config.r0`` escolhido pelo usuário. Ao final da calibração, os
custos de caminho efetivo ``-ln(p_ij)`` são atualizados no grafo (Decisão A16).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Final

from epidemia.core.analysis.epidemic_metrics import estimate_effective_r0_from_series
from epidemia.core.epidemic.engine import EpidemicEngine
from epidemia.core.epidemic.model import edge_infection_probability, exit_probability
from epidemia.core.epidemic.parameters import SimulationConfig
from epidemia.core.errors import ParameterOutOfRangeError
from epidemia.core.graph.graph import Graph
from epidemia.core.seeds import SUBSYSTEM_CALIBRATION, SeedBook

DEFAULT_BETA_MIN: Final[float] = 1e-4
DEFAULT_BETA_MAX: Final[float] = 5.0
DEFAULT_MAX_ITERATIONS: Final[int] = 14
DEFAULT_TOLERANCE: Final[float] = 0.02
DEFAULT_CALIBRATION_TRIALS: Final[int] = 4
DEFAULT_CALIBRATION_HORIZON_DAYS: Final[int] = 12


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    """Resultado detalhado da calibração de ``beta`` por bisseção."""

    beta: float
    target_r0: float
    measured_r0: float
    newman_r0: float
    iterations: int
    elapsed_ms: float


def newman_analytic_r0(graph: Graph, beta: float, gamma: float) -> float:
    """Calcula a aproximação analítica de Newman para redes (Modelagem 2.6).

    Usa a fórmula ``R0 ≈ T(beta) * (<k^2>/<k> - 1)``, onde ``T(beta)`` é a
    transmissibilidade média por aresta ao longo do período infeccioso e ``k`` é
    o grau ponderado normalizado pelo peso médio das arestas ativas.
    """
    if isinstance(beta, bool) or not math.isfinite(beta) or beta <= 0.0:
        raise ParameterOutOfRangeError(f"beta deve ser finito e > 0: {beta}")
    if isinstance(gamma, bool) or not math.isfinite(gamma) or gamma <= 0.0:
        raise ParameterOutOfRangeError(f"gamma deve ser finito e > 0: {gamma}")

    if graph.num_vertices == 0 or graph.num_edges == 0:
        return 0.0

    weighted_degrees: list[float] = []
    total_weight = 0.0
    total_degree = 0

    for u in graph.vertices():
        nbrs = tuple(graph.neighbors(u, only_active=True))
        deg = len(nbrs)
        w_sum = 0.0
        for v in nbrs:
            w_sum += graph.edge_weight(u, v)
        weighted_degrees.append(w_sum)
        total_weight += w_sum
        total_degree += deg

    if total_degree == 0 or total_weight <= 0.0:
        return 0.0

    mean_edge_weight = total_weight / total_degree
    norm_degrees = [w / mean_edge_weight for w in weighted_degrees]
    n = len(norm_degrees)
    mean_k = sum(norm_degrees) / n
    if mean_k <= 0.0:
        return 0.0

    mean_k2 = sum(k * k for k in norm_degrees) / n
    excess_degree = max(0.0, (mean_k2 / mean_k) - 1.0)

    p_edge = edge_infection_probability(mean_edge_weight, beta)
    p_exit = exit_probability(gamma)
    denom = p_edge + p_exit - (p_edge * p_exit)
    if denom <= 0.0:
        return 0.0
    transmissibility = p_edge / denom
    return transmissibility * excess_degree


def measure_empirical_r0(
    graph: Graph,
    config: SimulationConfig,
    beta: float,
    *,
    seeds: SeedBook | None = None,
    trials: int = DEFAULT_CALIBRATION_TRIALS,
    horizon_days: int = DEFAULT_CALIBRATION_HORIZON_DAYS,
) -> float:
    """Mede o ``R0`` efetivo para um ``beta`` de teste via simulações curtas.

    Executa ``trials`` simulações curtas no ``EpidemicEngine`` usando números
    aleatórios comuns derivados de ``SUBSYSTEM_CALIBRATION`` e combina a taxa
    empírica de contágio secundário do caso índice com o fluxo esperado nas
    arestas ativas da coorte amostrada.
    """
    if isinstance(beta, bool) or not math.isfinite(beta) or beta <= 0.0:
        raise ParameterOutOfRangeError(f"beta deve ser finito e > 0: {beta}")
    if isinstance(trials, bool) or trials < 1:
        raise ParameterOutOfRangeError(f"trials deve ser >= 1: {trials}")
    if isinstance(horizon_days, bool) or horizon_days < 1:
        raise ParameterOutOfRangeError(f"horizon_days deve ser >= 1: {horizon_days}")

    active_vertices = [
        u for u in graph.vertices() if any(True for _ in graph.neighbors(u, only_active=True))
    ]
    if not active_vertices:
        return 0.0

    seed_book = seeds if seeds is not None else SeedBook(config.seed)
    cal_rng = seed_book.rng(SUBSYSTEM_CALIBRATION)

    num_trials = min(trials, len(active_vertices))
    sampled_vertices = cal_rng.sample(active_vertices, k=num_trials)
    trial_seeds = [cal_rng.randrange(0, 2**31 - 1) for _ in range(num_trials)]

    saved_beta = graph.beta
    saved_isolated = [graph.is_vertex_isolated(u) for u in range(graph.num_vertices)]

    cal_config = SimulationConfig(
        seed=config.seed,
        scenario=config.scenario,
        r0=config.r0,
        exit_rate_gamma=config.exit_rate_gamma,
        mortality=config.mortality,
        incubation_days=config.incubation_days,
        intervention_level="nenhum",
        patient_zero=None,
        max_days=horizon_days,
        day_zero_threshold_m=config.day_zero_threshold_m,
    )

    p_exit = exit_probability(config.gamma)
    day1_r0_sum = 0.0
    hazard_r0_sum = 0.0

    try:
        for u0, t_seed in zip(sampled_vertices, trial_seeds, strict=True):
            engine = EpidemicEngine(
                graph,
                cal_config,
                seeds=SeedBook(t_seed),
                beta=beta,
            )
            engine.start(patient_zero=[u0])

            first_day_exposed = 0
            for day_idx in range(horizon_days):
                rec = engine.step()
                if day_idx == 0:
                    first_day_exposed = rec.new_exposed
                if engine.finished:
                    break

            # Exercita também a estimativa de série temporal do M2 quando há janela
            series = [c.cumulative_cases for c in engine.buffer.compartment_series()]
            _ = estimate_effective_r0_from_series(
                series,
                sigma=config.sigma,
                gamma=config.gamma,
            )

            day1_r0_sum += first_day_exposed / p_exit
            nbr_hazard = sum(
                edge_infection_probability(graph.edge_weight(u0, v), beta) / p_exit
                for v in graph.neighbors(u0, only_active=True)
            )
            hazard_r0_sum += nbr_hazard
    finally:
        for u, was_iso in enumerate(saved_isolated):
            graph.set_vertex_isolated(u, was_iso)
        graph.update_transmission_costs(saved_beta)

    mean_day1_r0 = day1_r0_sum / num_trials
    mean_hazard_r0 = hazard_r0_sum / num_trials
    return 0.25 * mean_day1_r0 + 0.75 * mean_hazard_r0


def calibrate_beta(
    graph: Graph,
    config: SimulationConfig,
    *,
    seeds: SeedBook | None = None,
    beta_min: float = DEFAULT_BETA_MIN,
    beta_max: float = DEFAULT_BETA_MAX,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    tolerance: float = DEFAULT_TOLERANCE,
    trials: int = DEFAULT_CALIBRATION_TRIALS,
    horizon_days: int = DEFAULT_CALIBRATION_HORIZON_DAYS,
) -> CalibrationResult:
    """Ajusta ``beta`` por bisseção para atingir ``config.r0`` e atualiza o grafo.

    Ao concluir a busca, chama ``graph.update_transmission_costs(best_beta)``
    para sincronizar os custos ``-ln(p_ij)`` usados pelo algoritmo de Dijkstra
    (Decisão A16).
    """
    if isinstance(beta_min, bool) or not math.isfinite(beta_min) or beta_min <= 0.0:
        raise ParameterOutOfRangeError(f"beta_min deve ser finito e > 0: {beta_min}")
    if isinstance(beta_max, bool) or not math.isfinite(beta_max) or beta_max <= beta_min:
        raise ParameterOutOfRangeError(
            f"beta_max ({beta_max}) deve ser finito e > beta_min ({beta_min})."
        )
    if isinstance(max_iterations, bool) or max_iterations < 1:
        raise ParameterOutOfRangeError(f"max_iterations deve ser >= 1: {max_iterations}")
    if isinstance(tolerance, bool) or not math.isfinite(tolerance) or tolerance <= 0.0:
        raise ParameterOutOfRangeError(f"tolerance deve ser finito e > 0: {tolerance}")

    t0 = time.perf_counter()
    target_r0 = config.r0

    has_active_edges = any(
        any(True for _ in graph.neighbors(u, only_active=True)) for u in graph.vertices()
    )
    if not has_active_edges:
        graph.update_transmission_costs(beta_min)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return CalibrationResult(
            beta=beta_min,
            target_r0=target_r0,
            measured_r0=0.0,
            newman_r0=0.0,
            iterations=0,
            elapsed_ms=elapsed_ms,
        )

    low = beta_min
    high = beta_max

    # Garante que o limite superior cubra o R0 alvo quando a topologia permite
    for _ in range(5):
        r0_high = measure_empirical_r0(
            graph,
            config,
            high,
            seeds=seeds,
            trials=trials,
            horizon_days=horizon_days,
        )
        if r0_high >= target_r0:
            break
        high *= 2.0

    best_beta = 0.5 * (low + high)
    best_measured = 0.0
    best_error = float("inf")
    iterations_done = 0

    for it in range(1, max_iterations + 1):
        iterations_done = it
        mid = 0.5 * (low + high)
        measured = measure_empirical_r0(
            graph,
            config,
            mid,
            seeds=seeds,
            trials=trials,
            horizon_days=horizon_days,
        )
        err = abs(measured - target_r0)
        if err < best_error:
            best_error = err
            best_beta = mid
            best_measured = measured

        if err <= tolerance:
            break
        if measured < target_r0:
            low = mid
        else:
            high = mid

    graph.update_transmission_costs(best_beta)
    newman_r0 = newman_analytic_r0(graph, best_beta, config.gamma)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return CalibrationResult(
        beta=best_beta,
        target_r0=target_r0,
        measured_r0=best_measured,
        newman_r0=newman_r0,
        iterations=iterations_done,
        elapsed_ms=elapsed_ms,
    )
