"""Parâmetros imutáveis da simulação e tabela de níveis de intervenção (M3).

``SimulationConfig`` é congelado por construção (RN01, decisão A3). γ é a taxa
total de saída de I, informada pelo usuário; a mortalidade divide a saída entre
D e R (decisão A17). β não entra aqui: é calibrado depois (A14, A16).
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

from epidemia.core.errors import ParameterOutOfRangeError

LEVEL_NONE: Final[str] = "nenhum"
LEVEL_LOW: Final[str] = "baixo"
LEVEL_MEDIUM: Final[str] = "medio"
LEVEL_HIGH: Final[str] = "alto"

DEFAULT_VACCINE_EFFICACY: Final[float] = 0.8

SCENARIO_GLOBAL: Final[str] = "global"
SCENARIO_REGIONAL_EBOLA: Final[str] = "regional_ebola"
VALID_SCENARIOS: Final[frozenset[str]] = frozenset({SCENARIO_GLOBAL, SCENARIO_REGIONAL_EBOLA})


@dataclass(frozen=True, slots=True)
class InterventionParams:
    """Constantes de isolamento e vacinação de um nível (Modelagem 5, premissas)."""

    level: str
    isolation_daily_prob: float
    isolation_duration_days: int
    vaccination_start_day: int
    vaccination_daily_fraction: float
    vaccine_efficacy: float = DEFAULT_VACCINE_EFFICACY


INTERVENTION_TABLE: Final[dict[str, InterventionParams]] = {
    LEVEL_NONE: InterventionParams(LEVEL_NONE, 0.0, 0, 0, 0.0),
    LEVEL_LOW: InterventionParams(LEVEL_LOW, 0.05, 7, 180, 0.002),
    LEVEL_MEDIUM: InterventionParams(LEVEL_MEDIUM, 0.15, 10, 120, 0.005),
    LEVEL_HIGH: InterventionParams(LEVEL_HIGH, 0.30, 14, 60, 0.010),
}

_LEVEL_ALIASES: Final[dict[str, str]] = {
    "nenhum": LEVEL_NONE,
    "none": LEVEL_NONE,
    "baixo": LEVEL_LOW,
    "low": LEVEL_LOW,
    "medio": LEVEL_MEDIUM,
    "médio": LEVEL_MEDIUM,
    "medium": LEVEL_MEDIUM,
    "alto": LEVEL_HIGH,
    "high": LEVEL_HIGH,
}


def normalize_intervention_level(level: str) -> str:
    """Converte um nome de nível (pt ou en) para o nome canônico em português."""
    if not isinstance(level, str):
        raise ParameterOutOfRangeError(f"Nível de intervenção inválido: {level!r}.")
    canonical = _LEVEL_ALIASES.get(level.strip().lower())
    if canonical is None:
        valid = ", ".join(INTERVENTION_TABLE)
        raise ParameterOutOfRangeError(
            f"Nível de intervenção desconhecido: {level!r} (válidos: {valid})."
        )
    return canonical


def resolve_intervention_params(level: str | InterventionParams) -> InterventionParams:
    """Devolve os parâmetros de um nível (ou o próprio objeto, se já resolvido)."""
    if isinstance(level, InterventionParams):
        return level
    return INTERVENTION_TABLE[normalize_intervention_level(level)]


def _check_number(name: str, value: object, *, low: float, high: float | None = None) -> float:
    """Valida número finito real (não bool) em ``(low, ...)`` ou ``[low, high]``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ParameterOutOfRangeError(f"{name} deve ser numérico (recebido: {value!r}).")
    number = float(value)
    if not math.isfinite(number):
        raise ParameterOutOfRangeError(f"{name} deve ser finito (recebido: {value!r}).")
    if high is None:
        if number <= low:
            raise ParameterOutOfRangeError(f"{name} deve ser > {low} (recebido: {value!r}).")
    elif not (low <= number <= high):
        raise ParameterOutOfRangeError(
            f"{name} deve estar em [{low}, {high}] (recebido: {value!r})."
        )
    return number


def _check_int(name: str, value: object, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ParameterOutOfRangeError(
            f"{name} deve ser inteiro >= {minimum} (recebido: {value!r})."
        )
    return value


@dataclass(frozen=True)
class SimulationConfig:
    """Configuração imutável de uma simulação (RN01, RF01).

    Qualquer alteração exige uma nova configuração e um novo início.
    """

    seed: int = 42
    scenario: str = SCENARIO_GLOBAL
    r0: float = 2.5
    exit_rate_gamma: float = 0.1
    mortality: float = 0.02
    incubation_days: float = 4.0
    intervention_level: str = LEVEL_LOW
    patient_zero: tuple[int, ...] | None = None
    max_days: int = 365
    day_zero_threshold_m: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ParameterOutOfRangeError(f"seed deve ser inteiro (recebido: {self.seed!r}).")
        if self.scenario not in VALID_SCENARIOS:
            raise ParameterOutOfRangeError(
                f"Cenário desconhecido: {self.scenario!r} (válidos: {sorted(VALID_SCENARIOS)})."
            )
        _check_number("r0", self.r0, low=0.0)
        _check_number("exit_rate_gamma", self.exit_rate_gamma, low=0.0)
        _check_number("incubation_days", self.incubation_days, low=0.0)
        _check_number("mortality", self.mortality, low=0.0, high=1.0)
        _check_int("max_days", self.max_days, minimum=1)
        _check_int("day_zero_threshold_m", self.day_zero_threshold_m, minimum=1)
        object.__setattr__(
            self, "intervention_level", normalize_intervention_level(self.intervention_level)
        )
        if self.patient_zero is not None:
            object.__setattr__(
                self, "patient_zero", self._normalize_patient_zero(self.patient_zero)
            )

    @staticmethod
    def _normalize_patient_zero(value: Iterable[int]) -> tuple[int, ...]:
        if isinstance(value, (str, bytes)):
            raise ParameterOutOfRangeError("patient_zero deve ser uma sequência de inteiros.")
        vertices = tuple(value)
        if not vertices:
            raise ParameterOutOfRangeError("patient_zero não pode ser vazio (use None).")
        for u in vertices:
            _check_int("patient_zero (vértice)", u, minimum=0)
        return vertices

    @property
    def sigma(self) -> float:
        """Taxa de saída da incubação: 1 / incubation_days."""
        return 1.0 / self.incubation_days

    @property
    def gamma(self) -> float:
        """Taxa total de saída de I (alias de ``exit_rate_gamma``)."""
        return self.exit_rate_gamma

    @property
    def intervention_params(self) -> InterventionParams:
        """Constantes de isolamento e vacinação do nível configurado."""
        return INTERVENTION_TABLE[self.intervention_level]

    # Aliases em português (nomes da arquitetura v0.5), somente leitura.
    @property
    def contagio_r0(self) -> float:
        return self.r0

    @property
    def recuperacao_gamma(self) -> float:
        return self.exit_rate_gamma

    @property
    def mortalidade(self) -> float:
        return self.mortality

    @property
    def incubacao_dias(self) -> float:
        return self.incubation_days

    @property
    def nivel_intervencao(self) -> str:
        return self.intervention_level
