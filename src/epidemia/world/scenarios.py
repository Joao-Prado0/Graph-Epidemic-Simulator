"""Cenários de alocação do grafo unificado: global e regional (Modelagem 10 / B3, B4).

No cenário regional (ex.: Ebola 2014–2016), os países que atingem ao menos
``min_cases`` (10) casos acumulados nos primeiros ``window_days`` (60) dias
a partir do dia 0 do surto recebem o orçamento proporcional de vértices,
enquanto os demais países ficam fixados no piso ``n_min = 12``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from epidemia.core.errors import ParameterOutOfRangeError

SCENARIO_GLOBAL: Final[str] = "global"
SCENARIO_REGIONAL_EBOLA: Final[str] = "regional_ebola"

DEFAULT_REGIONAL_WINDOW_DAYS: Final[int] = 60
DEFAULT_REGIONAL_MIN_CASES: Final[int] = 10
DEFAULT_EBOLA_FOCUS_COUNTRIES: Final[frozenset[str]] = frozenset({"GIN", "LBR", "SLE"})


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    """Especificação imutável de um cenário de construção do grafo global."""

    name: str = SCENARIO_GLOBAL
    focus_countries: frozenset[str] | None = None
    window_days: int = DEFAULT_REGIONAL_WINDOW_DAYS
    min_cases: int = DEFAULT_REGIONAL_MIN_CASES

    @property
    def is_regional(self) -> bool:
        """Retorna ``True`` se o cenário restringe o orçamento a países-foco."""
        return self.focus_countries is not None


def detect_regional_focus_countries(
    daily_cases_by_country: Mapping[str, Sequence[int]],
    *,
    window_days: int = DEFAULT_REGIONAL_WINDOW_DAYS,
    min_cases: int = DEFAULT_REGIONAL_MIN_CASES,
) -> frozenset[str]:
    """Identifica os países que atingem ``min_cases`` nos primeiros ``window_days`` dias.

    Cada série em ``daily_cases_by_country[iso3]`` representa os casos acumulados
    a partir do dia 0 do surto (índice 0 = dia 0, ..., índice ``window_days``).
    """
    if window_days < 0:
        raise ParameterOutOfRangeError(f"window_days não pode ser negativo: {window_days}")
    if min_cases < 1:
        raise ParameterOutOfRangeError(f"min_cases deve ser >= 1: {min_cases}")

    focus: set[str] = set()
    max_index = window_days + 1
    for iso3, series in daily_cases_by_country.items():
        window = series[:max_index]
        if any(cases >= min_cases for cases in window):
            focus.add(iso3)

    return frozenset(focus)


def resolve_scenario(
    scenario: str | ScenarioSpec = SCENARIO_GLOBAL,
    *,
    daily_cases_by_country: Mapping[str, Sequence[int]] | None = None,
    window_days: int = DEFAULT_REGIONAL_WINDOW_DAYS,
    min_cases: int = DEFAULT_REGIONAL_MIN_CASES,
) -> ScenarioSpec:
    """Normaliza um nome ou objeto ``ScenarioSpec`` para uso no construtor do mundo."""
    if isinstance(scenario, ScenarioSpec):
        return scenario

    norm = scenario.strip().lower()
    if norm == SCENARIO_GLOBAL:
        return ScenarioSpec(
            name=SCENARIO_GLOBAL,
            focus_countries=None,
            window_days=window_days,
            min_cases=min_cases,
        )

    if norm in {SCENARIO_REGIONAL_EBOLA, "regional", "ebola"}:
        if daily_cases_by_country is not None:
            focus = detect_regional_focus_countries(
                daily_cases_by_country,
                window_days=window_days,
                min_cases=min_cases,
            )
        else:
            focus = DEFAULT_EBOLA_FOCUS_COUNTRIES
        return ScenarioSpec(
            name=SCENARIO_REGIONAL_EBOLA,
            focus_countries=focus,
            window_days=window_days,
            min_cases=min_cases,
        )

    raise ParameterOutOfRangeError(f"Cenário desconhecido: {scenario!r}")
