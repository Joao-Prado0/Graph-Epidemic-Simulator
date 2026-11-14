"""Grade espacial 2D para construção da Rede Geométrica Aleatória em O(V + E) (RF02).

Evita a comparação quadrática O(V^2) de todos os pares de vértices de um país
ao particionar o plano em células quadradas de lado igual ao raio de conexão ``r``.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from typing import Final

from epidemia.core.errors import ParameterOutOfRangeError
from epidemia.world.allocation import effective_average_degree

DEFAULT_TARGET_AVG_DEGREE: Final[float] = 8.0


def connection_radius(
    area: float,
    num_vertices: int,
    *,
    target_avg_degree: float = DEFAULT_TARGET_AVG_DEGREE,
) -> float:
    """Calcula o raio geométrico ``r = sqrt(d_ef / (pi * rho))`` (Modelagem 2.4).

    Onde ``rho = num_vertices / area`` é a densidade espacial de vértices no país
    e ``d_ef = min(target_avg_degree, num_vertices - 1)``.
    """
    if area <= 0.0 or not math.isfinite(area):
        raise ParameterOutOfRangeError(f"A área do país deve ser finita e positiva: {area}")
    if num_vertices < 0:
        raise ParameterOutOfRangeError(f"num_vertices não pode ser negativo: {num_vertices}")
    if num_vertices <= 1:
        return 0.0

    d_ef = effective_average_degree(target_avg_degree, num_vertices)
    density = num_vertices / area
    return math.sqrt(d_ef / (math.pi * density))


def spatial_grid_edges(
    positions: Sequence[tuple[float, float]],
    radius: float,
) -> list[tuple[int, int]]:
    """Encontra todos os pares ``(u, v)`` com ``u < v`` e distância euclidiana ``<= radius``.

    Algoritmo:
    1. Insere cada vértice ``u`` na célula ``(floor(x / r), floor(y / r))``.
    2. Para cada vértice ``u``, inspeciona apenas os vértices ``v > u`` situados
       na própria célula e nas 8 células adjacentes (vizinhança 3x3).

    Complexidade de tempo esperada: O(V + E) para distribuição espacial uniforme.
    Complexidade de espaço: O(V).
    """
    if radius < 0.0 or not math.isfinite(radius):
        raise ParameterOutOfRangeError(f"O raio de conexão deve ser finito e >= 0: {radius}")

    n = len(positions)
    if n <= 1 or radius == 0.0:
        return []

    r_sq = radius * radius
    grid: dict[tuple[int, int], list[int]] = defaultdict(list)

    for u, (x, y) in enumerate(positions):
        cell = (int(math.floor(x / radius)), int(math.floor(y / radius)))
        grid[cell].append(u)

    edges: list[tuple[int, int]] = []
    for u, (xu, yu) in enumerate(positions):
        cx = int(math.floor(xu / radius))
        cy = int(math.floor(yu / radius))

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neighbor_cell = grid.get((cx + dx, cy + dy))
                if not neighbor_cell:
                    continue
                for v in neighbor_cell:
                    if v <= u:
                        continue
                    xv, yv = positions[v]
                    dist_sq = (xu - xv) * (xu - xv) + (yu - yv) * (yu - yv)
                    if dist_sq <= r_sq:
                        edges.append((u, v))

    edges.sort()
    return edges
