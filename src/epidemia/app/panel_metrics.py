"""Métricas e análises para o painel de resultados (M5 — RF14, RF18, RF19, RF21).

Consolida os indicadores epidemiológicos a partir do ``Timeline`` usando
``summarize_epidemic_series`` e ``estimate_effective_r0_from_series``, e provê
o cálculo de métricas de rede (grau, intermediação aproximada e comunidades por país)
sem dependência de Qt.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from epidemia.core.analysis.communities import (
    contract_graph_by_country,
    label_propagation_communities,
)
from epidemia.core.analysis.epidemic_metrics import (
    EpidemicSummary,
    extract_compartment_counts,
    summarize_epidemic_series,
)
from epidemia.core.analysis.metrics import (
    average_clustering_coefficient,
    betweenness_centrality,
    degrees,
)
from epidemia.core.errors import ParameterOutOfRangeError

if TYPE_CHECKING:
    from epidemia.core.epidemic.parameters import SimulationConfig
    from epidemia.core.graph.graph import GraphLike
    from epidemia.core.timeline.protocol import Timeline


@dataclass(frozen=True)
class NetworkAnalysisResult:
    """Resultado estruturado da análise de redes para o painel (RF18, RF19)."""

    num_vertices: int
    avg_degree: float
    max_degree: int
    max_degree_vertex: int
    top_betweenness: list[tuple[int, float]]
    num_communities: int
    country_communities: dict[int, int]
    avg_clustering: float
    comparison_metric_status: str = "indisponível nesta etapa (M4)"


def compute_epidemic_summary_from_timeline(
    timeline: Timeline,
    config: SimulationConfig | None = None,
) -> EpidemicSummary:
    """Extrai as séries do ``Timeline`` e calcula o resumo consolidado da epidemia.

    Garante consistência direta com ``summarize_epidemic_series`` (RF21).
    """
    if timeline is None:
        raise ParameterOutOfRangeError("timeline não pode ser None.")

    n_days = timeline.days_available
    if n_days <= 0:
        return EpidemicSummary(
            peak_active_cases=0,
            peak_active_day=0,
            peak_daily_new_cases=0,
            peak_daily_new_cases_day=0,
            final_infected_count=0,
            final_infected_fraction=0.0,
            total_deaths=0,
            mortality_fraction=0.0,
            duration_days=0,
            effective_r0=None,
        )

    cum_cases: list[int] = []
    deaths: list[int] = []
    active_infected: list[int] = []
    exposed: list[int] = []

    has_vertex_states = timeline.vertex_states(0) is not None

    for d in range(n_days):
        if has_vertex_states:
            v_bytes = timeline.vertex_states(d)
            assert v_bytes is not None
            counts = extract_compartment_counts(v_bytes)
            cum_cases.append(counts.cumulative_cases)
            deaths.append(counts.deceased)
            active_infected.append(counts.infected)
            exposed.append(counts.exposed)
        else:
            country_counts = timeline.country_counts(d)
            tot_cases = sum(c.cases for c in country_counts)
            tot_deaths = sum(c.deaths for c in country_counts)
            tot_active = sum(c.active for c in country_counts)
            cum_cases.append(tot_cases)
            deaths.append(tot_deaths)
            active_infected.append(tot_active)
            exposed.append(0)

    population = timeline.num_vertices
    if population <= 0:
        population = max(1, sum(c.population for c in timeline.countries))

    sigma: float | None = None
    gamma: float | None = None
    if config is not None:
        if config.incubation_days > 0:
            sigma = 1.0 / float(config.incubation_days)
        if config.exit_rate_gamma > 0:
            gamma = float(config.exit_rate_gamma)

    return summarize_epidemic_series(
        cumulative_cases=cum_cases,
        deaths=deaths,
        population=population,
        active_infected=active_infected,
        exposed=exposed,
        sigma=sigma,
        gamma=gamma,
    )


def compute_network_analysis(
    graph: GraphLike,
    vertex_country: Sequence[int],
    *,
    sample_size: int = 50,
    seed: int = 42,
    compute_clustering: bool = True,
) -> NetworkAnalysisResult:
    """Calcula métricas de centralidade, agrupamento e comunidades (RF18, RF19).

    Executa:
    - Graus de todos os vértices (média, máximo);
    - Intermediação aproximada por amostragem de ``sample_size`` fontes (Brandes);
    - Propagação de rótulos sobre o grafo contraído por país;
    - Coeficiente de agrupamento médio global.
    """
    if graph is None:
        raise ParameterOutOfRangeError("graph não pode ser None.")

    num_v = graph.num_vertices
    if num_v == 0:
        return NetworkAnalysisResult(
            num_vertices=0,
            avg_degree=0.0,
            max_degree=0,
            max_degree_vertex=-1,
            top_betweenness=[],
            num_communities=0,
            country_communities={},
            avg_clustering=0.0,
        )

    # 1. Graus
    deg_map = degrees(graph)
    tot_deg = sum(deg_map.values())
    avg_deg = tot_deg / num_v if num_v > 0 else 0.0

    max_deg_vertex = max(deg_map.keys(), key=lambda v: deg_map[v], default=0)
    max_deg = deg_map.get(max_deg_vertex, 0)

    # 2. Intermediação aproximada
    k_sample = min(max(1, sample_size), num_v)
    bet_map = betweenness_centrality(graph, k=k_sample, seed=seed, normalized=True)
    sorted_bet = sorted(bet_map.items(), key=lambda item: item[1], reverse=True)
    top_betweenness = sorted_bet[:5]

    # 3. Comunidades por propagação de rótulos no grafo contraído por país
    num_countries = max(vertex_country, default=0) + 1 if vertex_country else 0
    contracted = contract_graph_by_country(
        graph,
        vertex_country,
        num_countries=num_countries,
    )
    comm_result = label_propagation_communities(contracted, seed=seed)
    country_comm = comm_result.vertex_community
    num_comm = len(comm_result.communities)

    # 4. Agrupamento médio
    avg_clust = 0.0
    if compute_clustering:
        avg_clust = average_clustering_coefficient(graph)

    return NetworkAnalysisResult(
        num_vertices=num_v,
        avg_degree=avg_deg,
        max_degree=max_deg,
        max_degree_vertex=max_deg_vertex,
        top_betweenness=top_betweenness,
        num_communities=num_comm,
        country_communities=country_comm,
        avg_clustering=avg_clust,
    )
