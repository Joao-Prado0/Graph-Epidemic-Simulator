"""Testes unitários e de validação científica do EpidemicEngine (M3)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from epidemia.core.analysis.epidemic_metrics import (
    STATE_D,
    STATE_I,
    STATE_R,
)
from epidemia.core.epidemic.engine import EpidemicEngine
from epidemia.core.epidemic.model import (
    edge_infection_probability,
    exit_probability,
    progression_probability,
    solve_mean_field_seird,
)
from epidemia.core.epidemic.parameters import SimulationConfig
from epidemia.core.errors import (
    EpidemiaError,
    GraphError,
    ParameterOutOfRangeError,
    VertexNotFoundError,
)
from epidemia.core.graph.graph import Graph
from epidemia.core.timeline.buffer import StateBuffer
from epidemia.core.timeline.protocol import (
    decode_vertex_state,
    is_isolated_byte,
    is_vaccinated_byte,
)


def _complete_graph(n: int, weight: float = 1.0, beta: float = 0.08) -> Graph:
    g = Graph(n, beta=beta)
    for u in range(n):
        for v in range(u + 1, n):
            g.add_edge(u, v, weight=weight)
    return g


def test_engine_requires_start_before_step() -> None:
    g = Graph(4)
    engine = EpidemicEngine(g, SimulationConfig())
    assert not engine.finished
    assert engine.current_day == -1
    with pytest.raises(EpidemiaError):
        engine.step()


def test_engine_patient_zero_manual_and_random() -> None:
    g = _complete_graph(10)
    cfg = SimulationConfig(seed=99, patient_zero=(2, 5))
    engine = EpidemicEngine(g, cfg)
    rec0 = engine.start()
    assert rec0.day == 0
    assert engine.patient_zero == (2, 5)
    assert rec0.counts.infected == 2
    assert rec0.counts.susceptible == 8
    assert rec0.counts.total_vertices == 10

    # Argumento explícito em start() sobrescreve config.patient_zero
    rec0_override = engine.start(patient_zero=[7])
    assert engine.patient_zero == (7,)
    assert rec0_override.counts.infected == 1
    assert decode_vertex_state(engine.buffer.vertex_states(0)[7]) == STATE_I

    # Sorteio aleatório determinístico quando patient_zero é None
    cfg_rand = SimulationConfig(seed=42)
    eng_a = EpidemicEngine(g, cfg_rand)
    eng_b = EpidemicEngine(g, cfg_rand)
    eng_a.start()
    eng_b.start()
    assert eng_a.patient_zero == eng_b.patient_zero
    assert len(eng_a.patient_zero) == 1


def test_engine_accepts_world_like_container() -> None:
    g = _complete_graph(5)
    world_stub = SimpleNamespace(graph=g)
    engine = EpidemicEngine(world_stub, SimulationConfig(patient_zero=(0,)))
    rec = engine.start()
    assert rec.counts.total_vertices == 5
    assert engine.graph is g


def test_engine_empty_graph_no_edges_never_spreads() -> None:
    """Caso de referência 2 (Modelagem 11.1): grafo sem arestas não propaga."""
    g = Graph(20, beta=0.5)
    cfg = SimulationConfig(
        seed=7,
        exit_rate_gamma=0.3,
        mortality=0.0,
        incubation_days=2.0,
        intervention_level="nenhum",
        patient_zero=(0,),
    )
    engine = EpidemicEngine(g, cfg)
    engine.start()
    while not engine.finished:
        rec = engine.step()
        assert rec.new_exposed == 0
        assert rec.counts.exposed == 0
        assert rec.counts.susceptible == 19
        assert rec.counts.total_vertices == 20

    final_counts = engine.buffer.compartment_counts(engine.current_day)
    assert final_counts.susceptible == 19
    assert final_counts.recovered_natural == 1
    assert final_counts.infected == 0


def test_engine_conservation_invariant_and_determinism_by_hash() -> None:
    """Critérios F1 e F2 (RN03): S+E+I+R+D=N em todo passo e mesmo hash para mesma semente."""
    cfg = SimulationConfig(
        seed=2026,
        r0=2.8,
        exit_rate_gamma=0.12,
        mortality=0.1,
        incubation_days=3.0,
        intervention_level="alto",
        max_days=80,
    )

    def run_once() -> StateBuffer:
        g = _complete_graph(60, weight=0.2, beta=0.06)
        eng = EpidemicEngine(g, cfg)
        eng.start()
        for _ in range(80):
            rec = eng.step()
            assert rec.counts.total_vertices == 60
            if eng.finished:
                break
        return eng.buffer

    buf1 = run_once()
    buf2 = run_once()
    assert buf1.days_available == buf2.days_available
    assert buf1.digest_sha256() == buf2.digest_sha256()


def test_engine_isolated_vertex_can_die_and_releases_isolation_flag() -> None:
    g = _complete_graph(4, beta=0.5)
    cfg = SimulationConfig(
        seed=12,
        exit_rate_gamma=50.0,  # saída de I quase certa no 1º passo
        mortality=1.0,  # 100% de letalidade ao sair de I
        incubation_days=2.0,
        intervention_level="alto",
        patient_zero=(0,),
    )
    engine = EpidemicEngine(g, cfg)
    engine.start()
    g.set_vertex_isolated(0, True)
    rec = engine.step()
    assert rec.counts.deceased == 1
    assert rec.counts.susceptible == 3  # isolado não contaminou ninguém antes de morrer
    byte0 = engine.buffer.vertex_states(1)[0]
    assert decode_vertex_state(byte0) == STATE_D
    assert not is_isolated_byte(byte0)


def test_engine_records_vaccinated_flag_in_buffer() -> None:
    g = Graph(30)
    cfg = SimulationConfig(
        seed=5,
        exit_rate_gamma=0.01,
        mortality=0.0,
        incubation_days=5.0,
        intervention_level="alto",  # vacinação começa no dia 60
        patient_zero=(0,),
        max_days=70,
    )
    engine = EpidemicEngine(g, cfg)
    engine.start()
    for _ in range(65):
        engine.step()

    day_bytes = engine.buffer.vertex_states(engine.current_day)
    # No grafo sem arestas, qualquer R nos vértices 1..29 veio exclusivamente de vacina
    vaccinated_r = [
        u
        for u in range(1, 30)
        if decode_vertex_state(day_bytes[u]) == STATE_R and is_vaccinated_byte(day_bytes[u])
    ]
    assert len(vaccinated_r) >= 1


def test_reference_case_complete_graph_within_5_percent_of_mean_field_peak() -> None:
    """Critério F1 (Modelagem 11.1): pico simulado dentro de 5% da solução numérica."""
    n = 400
    initial_i = 10
    beta = 0.0025
    incubation_days = 1.5
    gamma = 0.12

    cfg = SimulationConfig(
        seed=101,
        r0=3.0,
        exit_rate_gamma=gamma,
        mortality=0.0,
        incubation_days=incubation_days,
        intervention_level="nenhum",
        patient_zero=tuple(range(initial_i)),
        max_days=120,
    )
    g = _complete_graph(n, weight=1.0, beta=beta)
    engine = EpidemicEngine(g, cfg, beta=beta)
    engine.start()
    while not engine.finished and engine.current_day < 120:
        engine.step()

    sim_peak = max(c.infected for c in engine.buffer.compartment_series())

    ref = solve_mean_field_seird(
        population=n,
        initial_infected=initial_i,
        edge_probability=edge_infection_probability(1.0, beta),
        incubation_progression=progression_probability(incubation_days),
        exit_probability_value=exit_probability(gamma),
        mortality=0.0,
        days=120,
    )
    rel_error = abs(sim_peak - ref.peak_infected) / ref.peak_infected
    assert rel_error <= 0.05


def test_engine_constructor_and_patient_zero_validations() -> None:
    with pytest.raises(ParameterOutOfRangeError):
        EpidemicEngine(object(), SimulationConfig())
    with pytest.raises(GraphError):
        EpidemicEngine(Graph(0), SimulationConfig())
    with pytest.raises(ParameterOutOfRangeError):
        EpidemicEngine(Graph(3), SimulationConfig(), beta=0.0)
    with pytest.raises(ParameterOutOfRangeError):
        EpidemicEngine(Graph(3), SimulationConfig(), buffer=StateBuffer(2))

    eng = EpidemicEngine(Graph(3), SimulationConfig())
    with pytest.raises(VertexNotFoundError):
        eng.start(patient_zero=[99])
    with pytest.raises(ParameterOutOfRangeError):
        eng.start(patient_zero=[])
    with pytest.raises(ParameterOutOfRangeError):
        eng.start(patient_zero=[True])  # type: ignore[list-item]
