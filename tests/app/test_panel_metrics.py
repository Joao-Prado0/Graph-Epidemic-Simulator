"""Testes unitários das métricas e resumos do painel (RF14, RF18, RF19, RF21)."""

from __future__ import annotations

from epidemia.app.panel_metrics import (
    compute_epidemic_summary_from_timeline,
    compute_network_analysis,
)
from epidemia.app.simulation_session import SimulationSession
from epidemia.core.analysis.epidemic_metrics import (
    extract_compartment_counts,
    summarize_epidemic_series,
)
from epidemia.core.epidemic.parameters import SimulationConfig
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
    """Verifica cálculo de graus, intermediação aproximada e comunidades por país."""
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
    assert "indisponível" in res.comparison_metric_status
