"""Fachada de aplicação para o fluxo de simulação SEIRD (M3 — Arquitetura 4.3).

``SimulationSession`` coordena o ciclo de vida da simulação sem depender de Qt:
recebe ``SimulationConfig``, calibra ``beta`` por bisseção antes da partida,
congela a configuração após ``start()`` (RN01), avança um dia por chamada em
``run_day()``, expõe a ``SimulationTimeline`` para a UI e descarta o buffer ao
reiniciar em ``reset()``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from epidemia.core.epidemic.calibration import CalibrationResult, calibrate_beta
from epidemia.core.epidemic.engine import DayRecord, EpidemicEngine
from epidemia.core.epidemic.parameters import SimulationConfig
from epidemia.core.errors import EpidemiaError, ParameterOutOfRangeError
from epidemia.core.graph.graph import Graph
from epidemia.core.seeds import SeedBook
from epidemia.core.timeline.buffer import SimulationTimeline, StateBuffer
from epidemia.core.timeline.protocol import CountryInfo


def _extract_graph(world_or_graph: Any) -> Graph:
    if isinstance(world_or_graph, Graph):
        return world_or_graph
    graph = getattr(world_or_graph, "graph", None)
    if isinstance(graph, Graph):
        return graph
    raise ParameterOutOfRangeError(
        "world deve ser uma instância de World (com atributo .graph) ou Graph."
    )


def _build_timeline(world_or_graph: Any, buffer: StateBuffer) -> SimulationTimeline:
    if hasattr(world_or_graph, "country_codes") and hasattr(world_or_graph, "vertex_country"):
        return SimulationTimeline.from_world(world_or_graph, buffer)

    graph = _extract_graph(world_or_graph)
    vertex_country = [
        graph.vertex_info(u).country_id if graph.has_vertex(u) else 0
        for u in range(graph.num_vertices)
    ]
    max_cid = max(vertex_country, default=0)
    countries = [
        CountryInfo(
            iso3=f"C{cid:02d}",
            name=f"Country {cid}",
            population=max(1, vertex_country.count(cid)),
            geometry=None,
        )
        for cid in range(max_cid + 1)
    ]
    return SimulationTimeline(buffer, vertex_country, countries)


class SimulationSession:
    """Sessão de simulação SEIRD consumida pela camada ``ui/`` (M5)."""

    def __init__(
        self,
        world: Any,
        config: SimulationConfig | None = None,
    ) -> None:
        self._world = world
        self._graph: Graph = _extract_graph(world)
        self._config: SimulationConfig | None = None
        self._seeds: SeedBook | None = None
        self._calibrated_beta: float | None = None
        self._calibration_result: CalibrationResult | None = None
        self._buffer: StateBuffer | None = None
        self._timeline: SimulationTimeline | None = None
        self._engine: EpidemicEngine | None = None
        self._started: bool = False

        if config is not None:
            self.configure(config)

    @property
    def world(self) -> Any:
        """Retorna o contêiner ``World`` (ou ``Graph``) associado à sessão."""
        return self._world

    @property
    def graph(self) -> Graph:
        """Retorna o ``Graph`` sobre o qual a sessão opera."""
        return self._graph

    @property
    def config(self) -> SimulationConfig:
        """Retorna a configuração ativa (levanta ``EpidemiaError`` se ausente)."""
        if self._config is None:
            raise EpidemiaError(
                "A sessão ainda não possui SimulationConfig. Chame configure() primeiro."
            )
        return self._config

    @property
    def calibrated_beta(self) -> float | None:
        """Retorna o valor de ``beta`` calibrado, ou ``None`` se ainda não calibrado."""
        return self._calibrated_beta

    @property
    def calibration_result(self) -> CalibrationResult | None:
        """Retorna o ``CalibrationResult`` completo da última calibração."""
        return self._calibration_result

    @property
    def is_started(self) -> bool:
        """Indica se a simulação já foi iniciada (configuração travada — RN01)."""
        return self._started

    @property
    def finished(self) -> bool:
        """Indica se a simulação atual atingiu a condição de parada."""
        if not self._started or self._engine is None:
            return False
        return self._engine.finished

    @property
    def current_day(self) -> int:
        """Retorna o dia atual da simulação (ou ``-1`` antes de ``start()``)."""
        if not self._started or self._engine is None:
            return -1
        return self._engine.current_day

    @property
    def patient_zero(self) -> tuple[int, ...]:
        """Retorna a tupla de vértices pacientes zero da execução atual."""
        if not self._started or self._engine is None:
            return ()
        return self._engine.patient_zero

    def configure(self, config: SimulationConfig) -> None:
        """Define a configuração da simulação antes do início (RN01)."""
        if self._started:
            raise EpidemiaError(
                "A configuração está congelada após o início da simulação (RN01). "
                "Chame reset() antes de reconfigurar."
            )
        if not isinstance(config, SimulationConfig):
            raise ParameterOutOfRangeError(
                "config deve ser uma instância de SimulationConfig."
            )
        self._config = config
        self._seeds = SeedBook(config.seed)
        self._calibrated_beta = None
        self._calibration_result = None

    def calibrate_beta(self) -> float:
        """Calibra ``beta`` por bisseção para o ``config.r0`` atual e retorna seu valor."""
        if self._started:
            raise EpidemiaError(
                "Não é permitido recalibrar beta com a simulação em andamento (RN01)."
            )
        cfg = self.config
        seeds = self._seeds if self._seeds is not None else SeedBook(cfg.seed)
        res = calibrate_beta(self._graph, cfg, seeds=seeds)
        self._calibration_result = res
        self._calibrated_beta = res.beta
        return res.beta

    def start(self, patient_zero: Sequence[int] | None = None) -> DayRecord:
        """Inicia a simulação no dia 0, congelando a configuração (RN01)."""
        cfg = self.config
        if self._calibrated_beta is None:
            self.calibrate_beta()

        assert self._calibrated_beta is not None
        self._seeds = SeedBook(cfg.seed)
        self._buffer = StateBuffer(self._graph.num_vertices)
        self._timeline = _build_timeline(self._world, self._buffer)
        self._engine = EpidemicEngine(
            self._graph,
            cfg,
            seeds=self._seeds,
            buffer=self._buffer,
            beta=self._calibrated_beta,
        )
        rec0 = self._engine.start(patient_zero=patient_zero)
        self._started = True
        return rec0

    def run_day(self) -> DayRecord:
        """Avança exatamente 1 dia de simulação e retorna o ``DayRecord``."""
        if not self._started or self._engine is None:
            raise EpidemiaError(
                "A sessão precisa ser iniciada com start() antes de chamar run_day()."
            )
        return self._engine.step()

    def timeline(self) -> SimulationTimeline:
        """Retorna a ``SimulationTimeline`` associada à execução atual."""
        if self._timeline is None:
            raise EpidemiaError(
                "A linha do tempo só está disponível após iniciar a sessão com start()."
            )
        return self._timeline

    def reset(self) -> None:
        """Descarta o buffer e o motor atuais e destrava a configuração (RN01)."""
        if self._buffer is not None:
            self._buffer.clear()
        self._engine = None
        self._buffer = None
        self._timeline = None
        self._started = False
        self._graph.reset_masks()
        if self._config is not None:
            self._seeds = SeedBook(self._config.seed)
