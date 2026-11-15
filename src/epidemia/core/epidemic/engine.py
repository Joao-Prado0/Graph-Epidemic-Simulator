"""Motor de simulação epidemiológica SEIRD em passos diários (M3 — Arquitetura 4.2).

O motor não conhece Qt nem tempo de parede: cada chamada a ``step()`` avança
exatamente um dia de simulação, verifica o invariante de conservação
``S + E + I + R + D = N`` (F1), grava o snapshot de bytes no ``StateBuffer`` e
retorna o resumo diário ``DayRecord``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final

from epidemia.core.analysis.epidemic_metrics import (
    FLAG_ISOLATED,
    FLAG_VACCINATED,
    STATE_D,
    STATE_E,
    STATE_I,
    STATE_R,
    STATE_S,
    CompartmentCounts,
)
from epidemia.core.epidemic.interventions import (
    apply_daily_isolation,
    apply_daily_vaccination,
    release_isolation,
)
from epidemia.core.epidemic.model import (
    edge_infection_probability,
    exit_probability,
    progression_probability,
)
from epidemia.core.epidemic.parameters import SimulationConfig
from epidemia.core.errors import (
    EpidemiaError,
    GraphError,
    ParameterOutOfRangeError,
    VertexNotFoundError,
)
from epidemia.core.graph.graph import Graph
from epidemia.core.seeds import (
    SUBSYSTEM_ISOLATION,
    SUBSYSTEM_PATIENT_ZERO,
    SUBSYSTEM_VACCINATION,
    SeedBook,
)
from epidemia.core.timeline.buffer import StateBuffer

SUBSYSTEM_TRANSITIONS: Final[str] = "seird_transitions"


def _extract_graph(world_or_graph: Any) -> Graph:
    """Obtém a instância de ``Graph`` a partir de um ``Graph`` ou ``World``."""
    if isinstance(world_or_graph, Graph):
        return world_or_graph
    graph = getattr(world_or_graph, "graph", None)
    if isinstance(graph, Graph):
        return graph
    raise ParameterOutOfRangeError(
        "EpidemicEngine requer uma instância de Graph ou um objeto World contendo '.graph'."
    )


@dataclass(frozen=True, slots=True)
class DayRecord:
    """Resumo de um passo diário retornado por ``start()`` e ``step()``."""

    day: int
    counts: CompartmentCounts
    new_exposed: int = 0
    new_infected: int = 0
    new_recovered_natural: int = 0
    new_vaccinated: int = 0
    new_deaths: int = 0
    new_isolated: int = 0


class EpidemicEngine:
    """Motor estocástico discreto SEIRD sobre grafo com máscara de isolamento."""

    def __init__(
        self,
        world: Any,
        config: SimulationConfig,
        seeds: SeedBook | None = None,
        buffer: StateBuffer | None = None,
        *,
        beta: float | None = None,
    ) -> None:
        graph = _extract_graph(world)
        if graph.num_vertices <= 0:
            raise GraphError("O grafo deve possuir ao menos 1 vértice para simulação.")

        resolved_beta = float(graph.beta if beta is None else beta)
        if resolved_beta <= 0.0 or not math.isfinite(resolved_beta):
            raise ParameterOutOfRangeError(
                f"O parâmetro beta deve ser finito e positivo: {resolved_beta!r}."
            )

        if buffer is not None and buffer.num_vertices != graph.num_vertices:
            raise ParameterOutOfRangeError(
                f"O StateBuffer tem {buffer.num_vertices} vértices, mas o grafo tem "
                f"{graph.num_vertices}."
            )

        self._world = world
        self._graph: Graph = graph
        self._config: SimulationConfig = config
        self._seeds: SeedBook = seeds if seeds is not None else SeedBook(config.seed)
        self._buffer: StateBuffer = (
            buffer if buffer is not None else StateBuffer(graph.num_vertices)
        )
        self._beta: float = resolved_beta

        self._p_progression: float = progression_probability(config.incubation_days)
        self._p_exit: float = exit_probability(config.exit_rate_gamma)
        self._prob_cache: dict[float, float] = {}

        n = graph.num_vertices
        self._states: bytearray = bytearray(n)
        self._vaccinated: bytearray = bytearray(n)
        self._isolation_remaining: list[int] = [0] * n
        self._patient_zero: tuple[int, ...] = ()
        self._current_day: int = -1
        self._started: bool = False

        self._rng_pz = self._seeds.rng(SUBSYSTEM_PATIENT_ZERO)
        self._rng_iso = self._seeds.rng(SUBSYSTEM_ISOLATION)
        self._rng_vac = self._seeds.rng(SUBSYSTEM_VACCINATION)
        self._rng_model = self._seeds.rng(SUBSYSTEM_TRANSITIONS)

    @property
    def graph(self) -> Graph:
        """Grafo sobre o qual a simulação é executada."""
        return self._graph

    @property
    def config(self) -> SimulationConfig:
        """Configuração imutável da simulação."""
        return self._config

    @property
    def buffer(self) -> StateBuffer:
        """Buffer de estados gravados dia a dia."""
        return self._buffer

    @property
    def beta(self) -> float:
        """Taxa de transmissão por aresta usada pelo motor."""
        return self._beta

    @property
    def current_day(self) -> int:
        """Dia atual da simulação (``-1`` antes de ``start()``)."""
        return self._current_day

    @property
    def patient_zero(self) -> tuple[int, ...]:
        """Vértices escolhidos como paciente(s) zero no início da simulação."""
        return self._patient_zero

    @property
    def finished(self) -> bool:
        """Indica se a simulação terminou (sem expostos/infectados ou atingiu ``max_days``)."""
        if not self._started or self._current_day < 0:
            return False
        if self._current_day >= self._config.max_days:
            return True
        counts = self._buffer.compartment_counts(self._current_day)
        return (counts.exposed + counts.infected) == 0

    def _resolve_patient_zero(self, patient_zero: Sequence[int] | None) -> tuple[int, ...]:
        present = list(self._graph.vertices())
        if not present:
            raise GraphError("O grafo não possui vértices presentes para escolher paciente zero.")

        chosen = patient_zero if patient_zero is not None else self._config.patient_zero
        if chosen is None:
            return (self._rng_pz.choice(present),)

        if isinstance(chosen, (str, bytes)) or len(chosen) == 0:
            raise ParameterOutOfRangeError(
                "patient_zero deve ser uma sequência não vazia de índices de vértices."
            )

        unique: list[int] = []
        seen: set[int] = set()
        for u in chosen:
            if isinstance(u, bool) or not isinstance(u, int):
                raise ParameterOutOfRangeError(f"Índice de paciente zero inválido: {u!r}.")
            if not self._graph.has_vertex(u):
                raise VertexNotFoundError(f"Paciente zero {u} não existe no grafo.")
            if u not in seen:
                seen.add(u)
                unique.append(u)
        return tuple(unique)

    def _pack_snapshot(self) -> bytearray:
        """Empacota estado e flags de cada vértice em um ``bytearray`` do dia."""
        n = self._graph.num_vertices
        snapshot = bytearray(n)
        states = self._states
        vaccinated = self._vaccinated
        graph = self._graph
        for u in range(n):
            val = states[u]
            if graph.is_vertex_isolated(u):
                val |= FLAG_ISOLATED
            if vaccinated[u]:
                val |= FLAG_VACCINATED
            snapshot[u] = val
        return snapshot

    def _record_current_day(
        self,
        *,
        new_exposed: int = 0,
        new_infected: int = 0,
        new_recovered_natural: int = 0,
        new_vaccinated: int = 0,
        new_deaths: int = 0,
        new_isolated: int = 0,
    ) -> DayRecord:
        snapshot = self._pack_snapshot()
        day_idx = self._buffer.append_day(snapshot)
        counts = self._buffer.compartment_counts(day_idx)
        if counts.total_vertices != self._graph.num_vertices:
            raise EpidemiaError(
                f"Violação do invariante S+E+I+R+D=N no dia {day_idx}: "
                f"{counts.total_vertices} != {self._graph.num_vertices}."
            )
        return DayRecord(
            day=day_idx,
            counts=counts,
            new_exposed=new_exposed,
            new_infected=new_infected,
            new_recovered_natural=new_recovered_natural,
            new_vaccinated=new_vaccinated,
            new_deaths=new_deaths,
            new_isolated=new_isolated,
        )

    def start(self, patient_zero: Sequence[int] | None = None) -> DayRecord:
        """Inicializa o dia 0 com o(s) paciente(s) zero em ``I`` e grava no buffer (RF03)."""
        self._buffer.clear()
        self._graph.reset_masks()

        self._rng_pz = self._seeds.rng(SUBSYSTEM_PATIENT_ZERO)
        self._rng_iso = self._seeds.rng(SUBSYSTEM_ISOLATION)
        self._rng_vac = self._seeds.rng(SUBSYSTEM_VACCINATION)
        self._rng_model = self._seeds.rng(SUBSYSTEM_TRANSITIONS)

        n = self._graph.num_vertices
        self._states = bytearray([STATE_S] * n)
        self._vaccinated = bytearray(n)
        self._isolation_remaining = [0] * n

        pz = self._resolve_patient_zero(patient_zero)
        for u in pz:
            self._states[u] = STATE_I

        self._patient_zero = pz
        self._current_day = 0
        self._started = True

        return self._record_current_day(new_infected=len(pz))

    def step(self) -> DayRecord:
        """Avança um dia de simulação de forma síncrona em O(V + E) e grava no buffer."""
        if not self._started:
            raise EpidemiaError("O motor precisa ser iniciado com start() antes de chamar step().")

        self._current_day += 1
        params = self._config.intervention_params

        new_isolated = apply_daily_isolation(
            self._graph,
            self._states,
            self._isolation_remaining,
            params,
            self._rng_iso,
        )
        new_vaccinated = apply_daily_vaccination(
            self._states,
            self._vaccinated,
            self._current_day,
            params,
            self._rng_vac,
        )

        # Retrato congelado do início das transições SEIRD (atualização síncrona)
        prev_states = bytes(self._states)
        graph = self._graph
        rng = self._rng_model
        beta = self._beta
        prob_cache = self._prob_cache

        new_exposed = 0
        new_infected = 0
        new_recovered_natural = 0
        new_deaths = 0

        # 1. Contágio (S -> E) através de arestas ativas a partir dos vértices em I
        for u, state_u in enumerate(prev_states):
            if state_u != STATE_I or graph.is_vertex_isolated(u):
                continue
            for v in graph.neighbors(u, only_active=True):
                if self._states[v] != STATE_S:
                    continue
                w = graph.edge_weight(u, v)
                p_edge = prob_cache.get(w)
                if p_edge is None:
                    p_edge = edge_infection_probability(w, beta)
                    prob_cache[w] = p_edge
                if rng.random() < p_edge:
                    self._states[v] = STATE_E
                    new_exposed += 1

        # 2. Fim da incubação (E -> I) e saída de infeccioso (I -> D ou I -> R)
        p_prog = self._p_progression
        p_exit = self._p_exit
        mortality = self._config.mortality

        for u, state_u in enumerate(prev_states):
            if state_u == STATE_E:
                if rng.random() < p_prog:
                    self._states[u] = STATE_I
                    new_infected += 1
            elif state_u == STATE_I and rng.random() < p_exit:
                if rng.random() < mortality:
                    self._states[u] = STATE_D
                    new_deaths += 1
                    if self._isolation_remaining[u] > 0 or graph.is_vertex_isolated(u):
                        release_isolation(graph, self._isolation_remaining, u)
                else:
                    self._states[u] = STATE_R
                    new_recovered_natural += 1

        return self._record_current_day(
            new_exposed=new_exposed,
            new_infected=new_infected,
            new_recovered_natural=new_recovered_natural,
            new_vaccinated=new_vaccinated,
            new_deaths=new_deaths,
            new_isolated=new_isolated,
        )
