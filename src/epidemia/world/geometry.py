"""Operações geométricas puras na biblioteca padrão (Decisão A11 / Modelagem 2.4 e 3.3).

Implementa leitura de anéis de polígonos GeoJSON (Polygon e MultiPolygon),
cálculo de área planar (fórmula de Shoelace), teste ponto-em-polígono por
Ray Casting e sorteio determinístico de coordenadas dentro do país.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from epidemia.core.errors import InvalidDatasetError

Point2D = tuple[float, float]
Ring = list[Point2D]
PolygonRings = tuple[Ring, list[Ring]]
BBox = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class CountryGeometry:
    """Geometria consolidada de um país a partir do GeoJSON processado."""

    iso3: str
    polygons: list[PolygonRings]
    bbox: BBox
    area: float
    centroid: Point2D


def ring_signed_area(ring: Sequence[Point2D]) -> float:
    """Calcula a área com sinal de um anel fechado pela fórmula do Cadarço (Shoelace).

    Complexidade: O(K), onde K é o número de vértices do anel.
    """
    n = len(ring)
    if n < 3:
        return 0.0
    area2 = 0.0
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        area2 += x1 * y2 - x2 * y1
    return 0.5 * area2


def polygon_area(exterior: Sequence[Point2D], holes: Sequence[Sequence[Point2D]] = ()) -> float:
    """Retorna a área planar positiva de um polígono descontando seus buracos."""
    ext_area = abs(ring_signed_area(exterior))
    holes_area = sum(abs(ring_signed_area(h)) for h in holes)
    return max(0.0, ext_area - holes_area)


def ring_bbox(ring: Sequence[Point2D]) -> BBox:
    """Retorna a caixa envolvente ``(min_lon, min_lat, max_lon, max_lat)`` de um anel."""
    if not ring:
        raise InvalidDatasetError("Anel geométrico vazio.")
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    return (min(lons), min(lats), max(lons), max(lats))


def point_in_ring(lon: float, lat: float, ring: Sequence[Point2D]) -> bool:
    """Verifica se ``(lon, lat)`` está dentro do anel via Ray Casting (Jordan).

    Dispara uma semirreta horizontal para a direita (+infinito em longitude)
    e alterna o estado sempre que cruza uma aresta do polígono.

    Complexidade: O(K), onde K é o número de pontos do anel.
    """
    inside = False
    n = len(ring)
    if n < 3:
        return False

    x1, y1 = ring[-1]
    for i in range(n):
        x2, y2 = ring[i]
        # Verifica se a ordenada lat está entre as extremidades y1 e y2
        if (y1 > lat) != (y2 > lat):
            x_intersect = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
            if lon < x_intersect:
                inside = not inside
        x1, y1 = x2, y2

    return inside


def point_in_polygon(
    lon: float,
    lat: float,
    exterior: Sequence[Point2D],
    holes: Sequence[Sequence[Point2D]] = (),
) -> bool:
    """Retorna ``True`` se o ponto pertence ao anel exterior e não cai em nenhum buraco."""
    if not point_in_ring(lon, lat, exterior):
        return False
    for hole in holes:
        if point_in_ring(lon, lat, hole):
            return False
    return True


def extract_polygons_from_geojson(geometry: Mapping[str, Any]) -> list[PolygonRings]:
    """Extrai a lista de ``(exterior, holes)`` de um objeto geometry GeoJSON."""
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates")
    if not coords:
        raise InvalidDatasetError(f"Geometria GeoJSON sem coordenadas: {geometry!r}")

    polygons: list[PolygonRings] = []
    if geom_type == "Polygon":
        raw_polys = [coords]
    elif geom_type == "MultiPolygon":
        raw_polys = coords
    else:
        raise InvalidDatasetError(f"Tipo de geometria GeoJSON não suportado: {geom_type!r}")

    for raw_poly in raw_polys:
        if not raw_poly or not raw_poly[0]:
            continue
        exterior: Ring = [(float(pt[0]), float(pt[1])) for pt in raw_poly[0]]
        holes: list[Ring] = [
            [(float(pt[0]), float(pt[1])) for pt in ring] for ring in raw_poly[1:] if ring
        ]
        polygons.append((exterior, holes))

    if not polygons:
        raise InvalidDatasetError("Nenhum polígono válido encontrado na geometria GeoJSON.")
    return polygons


def build_country_geometry(iso3: str, geometry: Mapping[str, Any]) -> CountryGeometry:
    """Constrói ``CountryGeometry`` calculando área total, bbox e centroide ponderado."""
    polygons = extract_polygons_from_geojson(geometry)
    min_lon = math.inf
    min_lat = math.inf
    max_lon = -math.inf
    max_lat = -math.inf
    total_area = 0.0
    weighted_lon = 0.0
    weighted_lon_shifted = 0.0
    weighted_lat = 0.0

    for exterior, holes in polygons:
        bx0, by0, bx1, by1 = ring_bbox(exterior)
        min_lon = min(min_lon, bx0)
        min_lat = min(min_lat, by0)
        max_lon = max(max_lon, bx1)
        max_lat = max(max_lat, by1)

        p_area = polygon_area(exterior, holes)
        if p_area <= 0.0:
            p_area = 1e-9
        total_area += p_area
        cx = 0.5 * (bx0 + bx1)
        cy = 0.5 * (by0 + by1)
        weighted_lon += cx * p_area
        weighted_lon_shifted += (cx + 360.0 if cx < 0.0 else cx) * p_area
        weighted_lat += cy * p_area

    if max_lon - min_lon > 180.0:
        mean_lon = weighted_lon_shifted / total_area
        if mean_lon > 180.0:
            mean_lon -= 360.0
    else:
        mean_lon = weighted_lon / total_area
    centroid: Point2D = (mean_lon, weighted_lat / total_area)
    return CountryGeometry(
        iso3=iso3,
        polygons=polygons,
        bbox=(min_lon, min_lat, max_lon, max_lat),
        area=total_area,
        centroid=centroid,
    )


def sample_points_in_polygons(
    polygons: Sequence[PolygonRings],
    count: int,
    rng: random.Random,
    *,
    max_attempts_per_point: int = 500,
) -> list[Point2D]:
    """Sorteia ``count`` pontos ``(lon, lat)`` dentro dos polígonos usando ``rng``.

    Escolhe cada parte de um ``MultiPolygon`` com probabilidade proporcional à
    sua área planar e aplica amostragem por rejeição na caixa envolvente da parte.
    """
    if count <= 0:
        return []
    if not polygons:
        raise InvalidDatasetError("Lista de polígonos vazia para sorteio de pontos.")

    part_bboxes: list[BBox] = []
    part_weights: list[float] = []
    total_w = 0.0
    for exterior, holes in polygons:
        part_bboxes.append(ring_bbox(exterior))
        w = max(polygon_area(exterior, holes), 1e-9)
        total_w += w
        part_weights.append(total_w)

    points: list[Point2D] = []
    for _ in range(count):
        placed = False
        for _attempt in range(max_attempts_per_point):
            # Escolhe qual polígono do país recebe a tentativa proporcionalmente à área
            pick = rng.uniform(0.0, total_w)
            part_idx = 0
            for idx, cum_w in enumerate(part_weights):
                if pick <= cum_w:
                    part_idx = idx
                    break

            exterior, holes = polygons[part_idx]
            min_lon, min_lat, max_lon, max_lat = part_bboxes[part_idx]
            lon = rng.uniform(min_lon, max_lon)
            lat = rng.uniform(min_lat, max_lat)

            if point_in_polygon(lon, lat, exterior, holes):
                points.append((lon, lat))
                placed = True
                break

        if not placed:
            # Fallback determinístico para microestados com polígonos degenerados
            exterior, _ = polygons[0]
            min_lon, min_lat, max_lon, max_lat = part_bboxes[0]
            cx = 0.5 * (min_lon + max_lon) + rng.uniform(-1e-4, 1e-4)
            cy = 0.5 * (min_lat + max_lat) + rng.uniform(-1e-4, 1e-4)
            points.append((cx, cy))

    return points
