"""Métricas e análises para o painel de resultados (M5 — RF14, RF16, RF17, RF18, RF19, RF20, RF21).

Consolida os indicadores epidemiológicos a partir do ``Timeline`` usando
``summarize_epidemic_series`` e ``estimate_effective_r0_from_series``, e provê
o cálculo de métricas e algoritmos de Teoria dos Grafos de M1 e M2
(BFS, DFS, componentes conexas, Dijkstra, Tarjan, grau, agrupamento local/global,
intermediação aproximada e comunidades por país) sem dependência de Qt.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from epidemia.core.analysis.bridges import find_bridges_and_articulation_points
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
    local_clustering_coefficient,
    vertex_degree,
)
from epidemia.core.errors import InvalidDatasetError, ParameterOutOfRangeError
from epidemia.core.graph.shortest_path import dijkstra
from epidemia.core.graph.traversal import bfs, connected_components, dfs
from epidemia.core.timeline.protocol import (
    STATE_D,
    STATE_E,
    STATE_I,
    STATE_R,
    STATE_S,
    decode_vertex_state,
    is_isolated_byte,
    is_vaccinated_byte,
)

if TYPE_CHECKING:
    from epidemia.core.epidemic.parameters import SimulationConfig
    from epidemia.core.graph.graph import GraphLike
    from epidemia.core.timeline.protocol import Timeline

_STATE_LABELS: dict[int, str] = {
    STATE_S: "S",
    STATE_E: "E",
    STATE_I: "I",
    STATE_R: "R",
    STATE_D: "D",
}


@dataclass(frozen=True)
class NetworkAnalysisResult:
    """Resultado estruturado da análise de redes para o painel (RF16, RF18, RF19, RF20)."""

    num_vertices: int
    avg_degree: float
    max_degree: int
    max_degree_vertex: int
    top_betweenness: list[tuple[int, float]]
    num_communities: int
    country_communities: dict[int, int]
    avg_clustering: float
    num_components: int = 0
    largest_component_size: int = 0
    num_bridges: int = 0
    num_articulation_points: int = 0
    top_bridges: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True, slots=True)
class ShortestEpidemicPathSummary:
    """Resultado do caminho epidemiológico mais provável entre dois países (RF16, RF17)."""

    source_iso3: str
    target_iso3: str
    source_vertex: int
    target_vertex: int
    reachable: bool
    vertex_path: tuple[int, ...]
    country_path: tuple[str, ...]
    effective_distance: float
    path_probability: float
    bfs_hops: int | None
    dfs_reachable_count: int


@dataclass(frozen=True, slots=True)
class VertexInspectionResult:
    """Métricas estruturais e estado epidemiológico de um vértice inspecionado (RF18, RF26)."""

    vertex_id: int
    iso3: str
    country_name: str
    degree: int
    local_clustering: float
    state_code: int
    state_name: str
    is_isolated: bool
    is_vaccinated: bool


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

    has_fast_counts = hasattr(timeline, "compartment_counts")
    has_vertex_states = timeline.vertex_states(0) is not None

    for d in range(n_days):
        if has_fast_counts:
            counts = timeline.compartment_counts(d)  # type: ignore[attr-defined]
            cum_cases.append(counts.cumulative_cases)
            deaths.append(counts.deceased)
            active_infected.append(counts.infected)
            exposed.append(counts.exposed)
        elif has_vertex_states:
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
    """Calcula métricas estruturais de rede de M1 e M2 (RF16, RF18, RF19, RF20).

    Executa:
    - Componentes conexas e Componente Gigante (M1 — RF16);
    - Pontes e pontos de articulação via algoritmo de Tarjan iterativo (M2 — RF20);
    - Graus de todos os vértices (média, máximo — M2 — RF18);
    - Intermediação aproximada por amostragem de ``sample_size`` fontes (Brandes — M2 — RF18);
    - Propagação de rótulos sobre o grafo contraído por país (M2 — RF19);
    - Coeficiente de agrupamento médio global (M2 — RF18).
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
            num_components=0,
            largest_component_size=0,
            num_bridges=0,
            num_articulation_points=0,
            top_bridges=(),
        )

    # 1. Componentes conexas (M1 — RF16)
    if hasattr(graph, "has_vertex"):
        comps = connected_components(graph)  # type: ignore[arg-type]
        num_comps = len(comps)
        largest_comp = len(comps[0]) if comps else 0
    else:
        num_comps = 1
        largest_comp = num_v

    # 2. Pontes e pontos de articulação de Tarjan (M2 — RF20)
    tarjan_res = find_bridges_and_articulation_points(graph)
    num_bridges = len(tarjan_res.bridges)
    num_art_points = len(tarjan_res.articulation_points)
    top_bridges = tuple(tarjan_res.bridges[:5])

    # 3. Graus (M2 — RF18)
    deg_map = degrees(graph)
    tot_deg = sum(deg_map.values())
    avg_deg = tot_deg / num_v if num_v > 0 else 0.0

    max_deg_vertex = max(deg_map.keys(), key=lambda v: deg_map[v], default=0)
    max_deg = deg_map.get(max_deg_vertex, 0)

    # 4. Intermediação aproximada (M2 — RF18)
    k_sample = min(max(1, sample_size), num_v)
    bet_map = betweenness_centrality(graph, k=k_sample, seed=seed, normalized=True)
    sorted_bet = sorted(bet_map.items(), key=lambda item: item[1], reverse=True)
    top_betweenness = sorted_bet[:5]

    # 5. Comunidades por propagação de rótulos no grafo contraído por país (M2 — RF19)
    num_countries = max(vertex_country, default=0) + 1 if vertex_country else 0
    contracted = contract_graph_by_country(
        graph,
        vertex_country,
        num_countries=num_countries,
    )
    comm_result = label_propagation_communities(contracted, seed=seed)
    country_comm = comm_result.vertex_community
    num_comm = len(comm_result.communities)

    # 6. Agrupamento médio (M2 — RF18)
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
        num_components=num_comps,
        largest_component_size=largest_comp,
        num_bridges=num_bridges,
        num_articulation_points=num_art_points,
        top_bridges=top_bridges,
    )


def _select_country_hub_vertex(world: Any, iso3: str) -> int:
    """Seleciona o vértice mais conectado (priorizando conexões internacionais) do país."""
    verts = world.vertices_of_country(iso3)
    if not verts:
        raise InvalidDatasetError(f"País {iso3!r} não possui vértices alocados no grafo.")

    graph = world.graph
    vertex_country = world.vertex_country

    def _score(u: int) -> tuple[int, int, int]:
        c_u = vertex_country[u]
        intl_deg = 0
        total_deg = 0
        for v in graph.neighbors(u):
            total_deg += 1
            if vertex_country[v] != c_u:
                intl_deg += 1
        return (intl_deg, total_deg, -u)

    return max(verts, key=_score)


def compute_shortest_epidemic_path(
    world: Any,
    source_iso3: str,
    target_iso3: str,
    *,
    beta: float | None = None,
) -> ShortestEpidemicPathSummary:
    """Calcula o caminho epidemiológico mais provável (Dijkstra RF17) e busca (BFS/DFS RF16).

    Executa os três algoritmos canônicos do Módulo 1 sobre o grafo global unificado:
    1. ``dijkstra`` sobre a distância efetiva ``-ln(p_uv)`` (Brockmann & Helbing);
    2. ``bfs`` para obter a menor distância topológica em saltos (hops);
    3. ``dfs`` iterativa para medir o alcance da componente conexa da origem.
    """
    if world is None:
        raise ParameterOutOfRangeError("world não pode ser None.")

    src_code = source_iso3.strip().upper()
    dst_code = target_iso3.strip().upper()

    s_vertex = _select_country_hub_vertex(world, src_code)
    t_vertex = s_vertex if src_code == dst_code else _select_country_hub_vertex(world, dst_code)

    sp_res = dijkstra(world.graph, s_vertex, target=t_vertex, beta=beta)
    bfs_res = bfs(world.graph, s_vertex)
    dfs_res = dfs(world.graph, s_vertex)

    v_path = tuple(sp_res.path_to(t_vertex))
    reachable = len(v_path) > 0

    country_seq: list[str] = []
    for u in v_path:
        c_code = world.country_of_vertex(u)
        if not country_seq or country_seq[-1] != c_code:
            country_seq.append(c_code)

    eff_dist = sp_res.distance_to(t_vertex)
    prob = sp_res.path_probability(t_vertex)
    hops = bfs_res.distances.get(t_vertex)

    return ShortestEpidemicPathSummary(
        source_iso3=src_code,
        target_iso3=dst_code,
        source_vertex=s_vertex,
        target_vertex=t_vertex,
        reachable=reachable,
        vertex_path=v_path,
        country_path=tuple(country_seq),
        effective_distance=eff_dist if math.isfinite(eff_dist) else math.inf,
        path_probability=prob,
        bfs_hops=hops,
        dfs_reachable_count=len(dfs_res.order),
    )


def inspect_vertex_metrics(
    world: Any,
    vertex_id: int,
    vertex_bytes: bytes | None = None,
) -> VertexInspectionResult:
    """Inspeciona o estado epidemiológico e métricas locais de um vértice (RF18, RF26)."""
    if world is None:
        raise ParameterOutOfRangeError("world não pode ser None.")

    iso3 = world.country_of_vertex(vertex_id)
    c_name = world.country_names.get(iso3, iso3)
    deg = vertex_degree(world.graph, vertex_id)
    clust = local_clustering_coefficient(world.graph, vertex_id)

    if vertex_bytes is not None and 0 <= vertex_id < len(vertex_bytes):
        raw_byte = vertex_bytes[vertex_id]
        st_code = decode_vertex_state(raw_byte)
        is_iso = is_isolated_byte(raw_byte)
        is_vac = is_vaccinated_byte(raw_byte)
    else:
        st_code = STATE_S
        is_iso = world.graph.is_vertex_isolated(vertex_id)
        is_vac = False

    st_name = _STATE_LABELS.get(st_code, "S")
    return VertexInspectionResult(
        vertex_id=vertex_id,
        iso3=iso3,
        country_name=c_name,
        degree=deg,
        local_clustering=clust,
        state_code=st_code,
        state_name=st_name,
        is_isolated=is_iso,
        is_vaccinated=is_vac,
    )
