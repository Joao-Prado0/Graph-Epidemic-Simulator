"""Fixtures para testes do M5 e testes de integração."""

from __future__ import annotations

from typing import Any

from epidemia.world import CountryInput, RouteInput, World, build_world


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
    return [
        CountryInput("BRA", "Brasil", 215_000_000, square_geojson(-50.0, -15.0, 8.0)),
        CountryInput("GIN", "Guiné", 13_500_000, square_geojson(-12.0, 9.0, 4.0)),
        CountryInput("LBR", "Libéria", 5_200_000, square_geojson(-10.0, 5.0, 4.0)),
        CountryInput("SLE", "Serra Leoa", 8_400_000, square_geojson(-13.0, 7.0, 4.0)),
        CountryInput("TUV", "Tuvalu", 11_000, square_geojson(178.0, -8.0, 3.0)),
    ]


def create_synthetic_routes() -> list[RouteInput]:
    """Retorna rotas sintéticas entre os países."""
    return [
        RouteInput("BRA", "GIN", 15),
        RouteInput("GIN", "LBR", 6),
        RouteInput("LBR", "SLE", 10),
        RouteInput("SLE", "BRA", 4),
    ]


def create_synthetic_world(
    total_vertices: int = 100,
    seed: int = 42,
) -> World:
    """Cria e retorna uma instância de World sintético para testes."""
    countries = create_synthetic_countries()
    routes = create_synthetic_routes()
    return build_world(
        countries=countries,
        routes=routes,
        seed=seed,
        total_vertices=total_vertices,
        min_vertices=12,
    )
