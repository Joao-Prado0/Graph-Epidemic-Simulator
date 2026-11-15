"""Leis de transição do modelo SEIRD por passo diário (M3).

Todas as taxas viram probabilidade pela forma exponencial ``1 - exp(-taxa)``,
que mantém o resultado entre 0 e 1 (Modelagem 4.2, C1 e C2). Este módulo é puro:
não sorteia nada. Quem sorteia é o motor (``engine``).

Também traz a solução determinística de referência, em campo médio sobre um
grafo completo, usada para validar o motor (critério F1, Modelagem 11.1).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from epidemia.core.errors import ParameterOutOfRangeError
from epidemia.core.graph.weights import transmission_probability


def _check_rate(name: str, rate: float, *, positive: bool) -> float:
    if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(rate):
        raise ParameterOutOfRangeError(f"{name} deve ser numérico e finito (recebido: {rate!r}).")
    if rate < 0.0 or (positive and rate == 0.0):
        bound = "> 0" if positive else ">= 0"
        raise ParameterOutOfRangeError(f"{name} deve ser {bound} (recebido: {rate!r}).")
    return float(rate)


def rate_to_daily_probability(rate: float) -> float:
    """Converte uma taxa diária em probabilidade: ``1 - exp(-rate)``. Complexidade: O(1)."""
    return 1.0 - math.exp(-_check_rate("rate", rate, positive=False))


def progression_probability(incubation_days: float) -> float:
    """P(E -> I) = ``1 - exp(-sigma)``, com ``sigma = 1 / incubation_days``."""
    days = _check_rate("incubation_days", incubation_days, positive=True)
    return rate_to_daily_probability(1.0 / days)


def exit_probability(exit_rate_gamma: float) -> float:
    """P(saída de I) = ``1 - exp(-gamma)``, com gamma a taxa total de saída de I (A17)."""
    return rate_to_daily_probability(_check_rate("exit_rate_gamma", exit_rate_gamma, positive=True))


def edge_infection_probability(weight: float, beta: float) -> float:
    """P(I infectar um vizinho S por uma aresta ativa) = ``1 - exp(-beta * w)`` (M1)."""
    return transmission_probability(weight, beta)


@dataclass(frozen=True, slots=True)
class DeterministicTrajectory:
    """Série esperada (campo médio) de cada compartimento, do dia 0 ao último dia."""

    susceptible: tuple[float, ...]
    exposed: tuple[float, ...]
    infected: tuple[float, ...]
    recovered: tuple[float, ...]
    deceased: tuple[float, ...]

    @property
    def peak_infected(self) -> float:
        """Maior valor de I na série."""
        return max(self.infected)

    @property
    def peak_day(self) -> int:
        """Primeiro dia em que I atinge o pico."""
        return self.infected.index(self.peak_infected)


def solve_mean_field_seird(
    population: int,
    initial_infected: int,
    *,
    edge_probability: float,
    incubation_progression: float,
    exit_probability_value: float,
    mortality: float = 0.0,
    days: int = 200,
) -> DeterministicTrajectory:
    """Resolve o SEIRD em campo médio para um grafo completo de ``population`` vértices.

    Em um grafo completo, cada infeccioso tenta infectar cada suscetível com
    probabilidade ``edge_probability``, então um suscetível escapa de ``I``
    infecciosos com ``(1 - p) ** I``. As transições leem o estado do início do dia
    (atualização síncrona), como o motor. Complexidade: O(days).

    Parâmetros em probabilidades diárias: ``incubation_progression`` é P(E -> I) e
    ``exit_probability_value`` é P(saída de I).
    """
    if isinstance(population, bool) or not isinstance(population, int) or population < 1:
        raise ParameterOutOfRangeError(f"population deve ser inteiro >= 1: {population!r}.")
    if (
        isinstance(initial_infected, bool)
        or not isinstance(initial_infected, int)
        or not (1 <= initial_infected <= population)
    ):
        raise ParameterOutOfRangeError(
            f"initial_infected deve estar em [1, {population}]: {initial_infected!r}."
        )
    if isinstance(days, bool) or not isinstance(days, int) or days < 0:
        raise ParameterOutOfRangeError(f"days deve ser inteiro >= 0: {days!r}.")
    for name, value in (
        ("edge_probability", edge_probability),
        ("incubation_progression", incubation_progression),
        ("exit_probability_value", exit_probability_value),
        ("mortality", mortality),
    ):
        if not math.isfinite(value) or not (0.0 <= value <= 1.0):
            raise ParameterOutOfRangeError(f"{name} deve estar em [0, 1]: {value!r}.")

    s = float(population - initial_infected)
    e = 0.0
    i = float(initial_infected)
    r = 0.0
    d = 0.0
    series: tuple[list[float], ...] = ([s], [e], [i], [r], [d])
    escape_base = 1.0 - edge_probability

    for _ in range(days):
        new_exposed = s * (1.0 - escape_base**i)
        new_infected = e * incubation_progression
        leaving = i * exit_probability_value
        s -= new_exposed
        e += new_exposed - new_infected
        i += new_infected - leaving
        d += leaving * mortality
        r += leaving * (1.0 - mortality)
        for values, value in zip(series, (s, e, i, r, d), strict=True):
            values.append(value)

    return DeterministicTrajectory(*(tuple(values) for values in series))
