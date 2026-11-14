"""Subpacote de construção do grafo global unificado e cenários (M1)."""

from epidemia.world.allocation import (
    DEFAULT_ALPHA,
    DEFAULT_MIN_VERTICES,
    DEFAULT_TOTAL_VERTICES,
    allocate_vertices,
    effective_average_degree,
)
from epidemia.world.builder import (
    DEFAULT_K_MAX,
    DEFAULT_ROUTE_SCALE,
    INTERNAL_EDGE_WEIGHT,
    WorldCache,
    build_world,
    route_edge_multiplicity,
)
from epidemia.world.geometry import (
    CountryGeometry,
    build_country_geometry,
    extract_polygons_from_geojson,
    point_in_polygon,
    point_in_ring,
    polygon_area,
    ring_bbox,
    ring_signed_area,
    sample_points_in_polygons,
)
from epidemia.world.scenarios import (
    DEFAULT_EBOLA_FOCUS_COUNTRIES,
    DEFAULT_REGIONAL_MIN_CASES,
    DEFAULT_REGIONAL_WINDOW_DAYS,
    SCENARIO_GLOBAL,
    SCENARIO_REGIONAL_EBOLA,
    ScenarioSpec,
    detect_regional_focus_countries,
    resolve_scenario,
)
from epidemia.world.spatial_grid import (
    DEFAULT_TARGET_AVG_DEGREE,
    connection_radius,
    spatial_grid_edges,
)
from epidemia.world.world import CountryInput, RouteInput, World

__all__ = [
    "CountryGeometry",
    "CountryInput",
    "DEFAULT_ALPHA",
    "DEFAULT_EBOLA_FOCUS_COUNTRIES",
    "DEFAULT_K_MAX",
    "DEFAULT_MIN_VERTICES",
    "DEFAULT_REGIONAL_MIN_CASES",
    "DEFAULT_REGIONAL_WINDOW_DAYS",
    "DEFAULT_ROUTE_SCALE",
    "DEFAULT_TARGET_AVG_DEGREE",
    "DEFAULT_TOTAL_VERTICES",
    "INTERNAL_EDGE_WEIGHT",
    "RouteInput",
    "SCENARIO_GLOBAL",
    "SCENARIO_REGIONAL_EBOLA",
    "ScenarioSpec",
    "World",
    "WorldCache",
    "allocate_vertices",
    "build_country_geometry",
    "build_world",
    "connection_radius",
    "detect_regional_focus_countries",
    "effective_average_degree",
    "extract_polygons_from_geojson",
    "point_in_polygon",
    "point_in_ring",
    "polygon_area",
    "resolve_scenario",
    "ring_bbox",
    "ring_signed_area",
    "route_edge_multiplicity",
    "sample_points_in_polygons",
    "spatial_grid_edges",
]
