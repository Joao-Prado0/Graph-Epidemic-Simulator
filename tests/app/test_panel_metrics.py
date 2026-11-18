"""Testes unitários das métricas e resumos do painel (RF14, RF18, RF19, RF21)."""

from __future__ import annotations

from epidemia.app.panel_metrics import (
    compute_epidemic_summary_from_timeline,
    compute_network_analysis,
    compute_shortest_epidemic_path,
    inspect_vertex_metrics,
)
from epidemia.app.simulation_session import SimulationSession
from epidemia.core.analysis.epidemic_metrics import (
    extract_compartment_counts,
    summarize_epidemic_series,
)
from epidemia.core.epidemic.parameters import SimulationConfig
from epidemia.core.timeline.protocol import encode_vertex_byte
from tests.fixtures import create_synthetic_world


def test_painel_consistente_com_summarize_epidemic_series():
    """Verifica que o painel produz resultado idêntico a summarize_epidemic_series."""
    world = create_synthetic_world(total_vertices=80, seed=42)
    session = SimulationSession(world)
    config = SimulationConfig(
        seed=42,
        r0=2.8,
        exit_rate_gamma=0.2,
        mortality=0.04,
        incubation_days=3.0,
        intervention_level="baixo",
        max_days=30,
    )
    session.configure(config)
    session.start()

    for _ in range(12):
        session.run_day()

    timeline = session.timeline()

    # 1. Resumo via função do painel
    summary_painel = compute_epidemic_summary_from_timeline(timeline, config)

    # 2. Resumo calculado manualmente pela série direta
    cum_cases = []
    deaths = []
    active_i = []
    exposed = []
    for d in range(timeline.days_available):
        counts = extract_compartment_counts(timeline.vertex_states(d))
        cum_cases.append(counts.cumulative_cases)
        deaths.append(counts.deceased)
        active_i.append(counts.infected)
        exposed.append(counts.exposed)

    summary_direto = summarize_epidemic_series(
        cumulative_cases=cum_cases,
        deaths=deaths,
        population=80,
        active_infected=active_i,
        exposed=exposed,
        sigma=1.0 / 3.0,
        gamma=0.2,
    )

    assert summary_painel == summary_direto
    assert summary_painel.peak_active_cases > 0
    assert summary_painel.duration_days > 0


def test_analise_de_rede_painel():
    """Verifica cálculo de componentes (M1), Tarjan (M2), graus, intermediação e comunidades."""
    world = create_synthetic_world(total_vertices=60, seed=42)
    res = compute_network_analysis(
        world.graph,
        world.vertex_country,
        sample_size=20,
        seed=42,
        compute_clustering=True,
    )

    assert res.num_vertices == 60
    assert res.avg_degree > 0
    assert res.max_degree >= res.avg_degree
    assert len(res.top_betweenness) <= 5
    assert res.num_communities >= 1
    assert len(res.country_communities) > 0
    assert res.avg_clustering >= 0.0
    assert res.num_components >= 2  # TUV é isolado no mundo sintético
    assert 0 < res.largest_component_size <= 60
    assert res.num_bridges >= 0
    assert res.num_articulation_points >= 0


def test_caminho_minimo_epidemiologico_dijkstra_bfs_dfs():
    """Verifica integración de Dijkstra (RF17), BFS e DFS (RF16) entre países no painel."""
    world = create_synthetic_world(total_vertices=60, seed=42)

    # Entre países conectados por rota aérea (BRA -> LBR)
    path_ok = compute_shortest_epidemic_path(world, "BRA", "LBR", beta=0.4)
    assert path_ok.reachable is True
    assert path_ok.source_iso3 == "BRA"
    assert path_ok.target_iso3 == "LBR"
    assert path_ok.country_path[0] == "BRA"
    assert path_ok.country_path[-1] == "LBR"
    assert path_ok.effective_distance > 0.0
    assert 0.0 < path_ok.path_probability <= 1.0
    assert path_ok.bfs_hops is not None and path_ok.bfs_hops >= 1
    assert path_ok.dfs_reachable_count > 10

    # Entre país conectado (BRA) e país sem rota aérea (TUV)
    path_unreach = compute_shortest_epidemic_path(world, "BRA", "TUV", beta=0.4)
    assert path_unreach.reachable is False
    assert path_unreach.vertex_path == ()
    assert path_unreach.path_probability == 0.0
    assert path_unreach.bfs_hops is None


def test_inspecao_de_vertice_metricas_locais():
    """Verifica inspeção de vértice com grau e agrupamento local (RF18, RF26)."""
    world = create_synthetic_world(total_vertices=60, seed=42)
    raw = bytearray(60)
    raw[0] = encode_vertex_byte(2, isolated=True, vaccinated=False)

    info = inspect_vertex_metrics(world, 0, bytes(raw))
    assert info.vertex_id == 0
    assert info.iso3 in world.country_codes
    assert info.degree >= 0
    assert 0.0 <= info.local_clustering <= 1.0
    assert info.state_code == 2
    assert info.state_name == "I"
    assert info.is_isolated is True
    assert info.is_vaccinated is False
