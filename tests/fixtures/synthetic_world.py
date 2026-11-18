"""Fixtures para testes do M5 e testes de integração."""

from __future__ import annotations

from typing import Any

from epidemia.world import (
    CountryInput,
    RouteInput,
    World,
    create_fallback_countries,
    create_fallback_routes,
    create_fallback_world,
)


def square_geojson(lon0: float, lat0: float, size: float = 6.0) -> dict[str, Any]:
    """Gera geometria GeoJSON para um polígono retangular simples."""
    ring = [
        (lon0, lat0),
        (lon0 + size, lat0),
        (lon0 + size, lat0 + size),
        (lon0, lat0 + size),
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def create_synthetic_countries() -> list[CountryInput]:
    """Retorna 5 países sintéticos para testes."""
    return create_fallback_countries()


def create_synthetic_routes() -> list[RouteInput]:
    """Retorna rotas sintéticas entre os países."""
    return create_fallback_routes()


def create_synthetic_world(
    total_vertices: int = 100,
    seed: int = 42,
) -> World:
    """Cria e retorna uma instância de World sintético para testes."""
    return create_fallback_world(total_vertices=total_vertices, seed=seed)
