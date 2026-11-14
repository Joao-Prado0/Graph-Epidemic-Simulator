"""Funções matemáticas de pesos, probabilidades e custos de arestas"""

from __future__ import annotations

import math
from typing import Final

from epidemia.core.errors import InvalidEdgeError, ParameterOutOfRangeError

MAX_TRANSMISSION_PROBABILITY: Final[float] = 0.999
DEFAULT_BETA: Final[float] = 0.08


def normalized_route_weight(routes: int, max_routes: int) -> float:
    """Calcula o peso normalizado ``w = ln(1 + routes) / ln(1 + max_routes)`` (Modelagem 2.5)."""
    if routes <= 0 or max_routes <= 0:
        raise InvalidEdgeError(
            f"routes ({routes}) e max_routes ({max_routes}) devem ser inteiros positivos."
        )
    if routes > max_routes:
        raise InvalidEdgeError(f"routes ({routes}) não pode exceder max_routes ({max_routes}).")
    return math.log1p(routes) / math.log1p(max_routes)


def transmission_probability(weight: float, beta: float = DEFAULT_BETA) -> float:
    """Calcula a probabilidade de transmissão ``p = 1 - exp(-beta * w)`` na aresta."""
    if weight <= 0.0 or not math.isfinite(weight):
        raise InvalidEdgeError(f"O peso da aresta deve ser finito e positivo: {weight}")
    if beta <= 0.0 or not math.isfinite(beta):
        raise ParameterOutOfRangeError(f"O parâmetro beta deve ser finito e positivo: {beta}")
    return 1.0 - math.exp(-beta * weight)


def effective_distance_cost(probability: float) -> float:
    """Calcula o custo de caminho ``-ln(min(p, 0.999))`` (Brockmann & Helbing, 2013)."""
    if probability <= 0.0 or probability > 1.0 or not math.isfinite(probability):
        raise InvalidEdgeError(
            f"A probabilidade de transmissão deve estar em (0, 1]: {probability}"
        )
    return -math.log(min(probability, MAX_TRANSMISSION_PROBABILITY))
travel_cost = effective_distance_cost