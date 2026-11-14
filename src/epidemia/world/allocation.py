"""Alocação iterativa de vértices por país com piso e maior resto (Modelagem 2.3 e 10).

Garante que a soma dos vértices alocados seja exatamente ``total_vertices``
(8.000 por padrão), que todo país receba ao menos ``min_vertices`` (12) e que
a distribuição respeite a proporcionalidade sublinear ``p_i ** alpha``.
"""

from __future__ import annotations

import math
from collections.abc import Collection, Mapping
from typing import Final

from epidemia.core.errors import InvalidDatasetError, ParameterOutOfRangeError

DEFAULT_TOTAL_VERTICES: Final[int] = 8000
DEFAULT_MIN_VERTICES: Final[int] = 12
DEFAULT_ALPHA: Final[float] = 0.5


def effective_average_degree(target_avg_degree: float, num_country_vertices: int) -> float:
    """Retorna o grau médio efetivo ``min(d_bar, n_i - 1)`` (Modelagem 2.4)."""
    if target_avg_degree <= 0.0 or not math.isfinite(target_avg_degree):
        raise ParameterOutOfRangeError(
            f"O grau médio alvo deve ser finito e positivo: {target_avg_degree}"
        )
    if num_country_vertices <= 1:
        return 0.0
    return min(float(target_avg_degree), float(num_country_vertices - 1))


def _apply_largest_remainder(
    quotas: Mapping[str, float],
    populations: Mapping[str, int],
    remaining_budget: int,
) -> dict[str, int]:
    """Arredonda cotas fracionárias pelo Método do Maior Resto (Hamilton).

    Desempata de forma determinística por maior população e código ISO3 em ordem alfabética.
    """
    floors: dict[str, int] = {}
    remainders: list[tuple[float, int, str]] = []
    floor_sum = 0

    for iso3, q in quotas.items():
        f_val = int(math.floor(q))
        floors[iso3] = f_val
        floor_sum += f_val
        remainders.append((q - f_val, populations[iso3], iso3))

    remainders.sort(key=lambda item: (-item[0], -item[1], item[2]))
    leftover = remaining_budget - floor_sum

    rounded: dict[str, int] = {}
    for idx, (_, _, iso3) in enumerate(remainders):
        bonus = 1 if idx < leftover else 0
        rounded[iso3] = floors[iso3] + bonus
    return rounded


def allocate_vertices(
    populations: Mapping[str, int],
    *,
    total_vertices: int = DEFAULT_TOTAL_VERTICES,
    min_vertices: int = DEFAULT_MIN_VERTICES,
    alpha: float = DEFAULT_ALPHA,
    focus_countries: Collection[str] | None = None,
) -> dict[str, int]:
    """Aloca exatamente ``total_vertices`` entre os países de ``populations``.

    Procedimento iterativo (Modelagem 2.3):
    1. No cenário regional (``focus_countries`` informado), países fora do foco
       são fixados diretamente em ``min_vertices``.
    2. Calcula a cota proporcional a ``p_i ** alpha`` sobre o orçamento restante
       para os países ainda livres.
    3. Países cuja cota ficar abaixo de ``min_vertices`` são fixados no piso e
       removidos do conjunto livre, descontando do orçamento.
    4. Quando nenhum país livre ficar abaixo do piso, arredonda pelo método do
       maior resto (Hamilton) via ``_apply_largest_remainder``.

    Complexidade de tempo: O(M^2) no pior caso (em prática 2 a 4 iterações, O(M log M)).
    Complexidade de espaço: O(M), onde M é o número de países.
    """
    num_countries = len(populations)
    if num_countries == 0:
        raise InvalidDatasetError("O mapeamento de populações não pode ser vazio.")
    if min_vertices < 1:
        raise ParameterOutOfRangeError(f"min_vertices deve ser >= 1: {min_vertices}")
    if total_vertices < num_countries * min_vertices:
        raise ParameterOutOfRangeError(
            f"total_vertices ({total_vertices}) é insuficiente para garantir o piso "
            f"min_vertices ({min_vertices}) em {num_countries} países "
            f"(mínimo necessário: {num_countries * min_vertices})."
        )
    if alpha <= 0.0 or not math.isfinite(alpha):
        raise ParameterOutOfRangeError(f"alpha deve ser finito e positivo: {alpha}")

    weights: dict[str, float] = {}
    for iso3, pop in populations.items():
        if pop <= 0:
            raise InvalidDatasetError(f"População inválida para o país {iso3!r}: {pop}")
        weights[iso3] = float(pop) ** alpha

    allocated: dict[str, int] = {}
    remaining_budget = total_vertices

    if focus_countries is not None:
        focus_set = set(focus_countries) & set(populations.keys())
        if not focus_set:
            raise ParameterOutOfRangeError(
                "Nenhum país de focus_countries está presente em populations."
            )
        free: set[str] = set()
        for iso3 in populations:
            if iso3 in focus_set:
                free.add(iso3)
            else:
                allocated[iso3] = min_vertices
                remaining_budget -= min_vertices
    else:
        free = set(populations.keys())

    # Laço iterativo de piso
    quotas: dict[str, float] = {}
    while free:
        total_weight = sum(weights[iso3] for iso3 in free)
        quotas = {iso3: remaining_budget * (weights[iso3] / total_weight) for iso3 in free}

        below_floor = [iso3 for iso3, q in quotas.items() if q < min_vertices]
        if not below_floor:
            break

        for iso3 in below_floor:
            allocated[iso3] = min_vertices
            remaining_budget -= min_vertices
            free.remove(iso3)

    # Se todos os países livres foram fixados no piso e ainda sobrou orçamento
    if not free and remaining_budget > 0:
        free = set(populations.keys())
        total_weight = sum(weights[iso3] for iso3 in free)
        quotas = {
            iso3: allocated[iso3] + remaining_budget * (weights[iso3] / total_weight)
            for iso3 in free
        }
        remaining_budget = total_vertices - sum(v for k, v in allocated.items() if k not in free)

    if free:
        active_quotas = {iso3: quotas[iso3] for iso3 in free}
        allocated.update(_apply_largest_remainder(active_quotas, populations, remaining_budget))

    return allocated
