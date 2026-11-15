"""Testes de integração da SimulationSession e sensibilidade das intervenções (M3)."""

from __future__ import annotations

import pytest

from epidemia.app import SimulationSession
from epidemia.core.epidemic import SimulationConfig
from epidemia.core.errors import EpidemiaError, ParameterOutOfRangeError
from epidemia.core.graph.graph import Graph
from epidemia.core.timeline import Timeline
from epidemia.world import CountryInput, RouteInput, World, build_world


def _square_geojson(lon0: float, lat0: float, size: float = 4.0) -> dict[str, object]:
    ring = [
        (lon0, lat0),
        (lon0 + size, lat0),
        (lon0 + size, lat0 + size),
        (lon0, lat0 + size),
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def _build_test_world(total_vertices: int = 120) -> World:
    countries = [
        CountryInput("BRA", "Brazil", 215_000_000, _square_geojson(-50.0, -15.0)),
        CountryInput("USA", "United States", 330_000_000, _square_geojson(-100.0, 35.0)),
        CountryInput("PRT", "Portugal", 10_300_000, _square_geojson(-9.0, 39.0)),
    ]
    routes = [
        RouteInput("BRA", "USA", 25),
        RouteInput("BRA", "PRT", 18),
        RouteInput("USA", "PRT", 20),
    ]
    return build_world(
        countries,
        routes,
        seed=42,
        total_vertices=total_vertices,
        min_vertices=10,
    )


def test_simulation_session_full_lifecycle_and_rn01_freeze() -> None:
    world = _build_test_world(total_vertices=60)
    cfg = SimulationConfig(
        seed=42,
        r0=2.5,
        exit_rate_gamma=0.14,
        mortality=0.05,
        incubation_days=3.0,
        intervention_level="medio",
        patient_zero=(0,),
        max_days=40,
    )
    session = SimulationSession(world, cfg)
    assert session.world is world
    assert session.graph is world.graph
    assert session.config == cfg
    assert not session.is_started
    assert not session.finished
    assert session.current_day == -1
    assert session.patient_zero == ()
    assert session.calibrated_beta is None

    beta = session.calibrate_beta()
    assert beta > 0.0
    assert session.calibrated_beta == pytest.approx(beta)
    assert session.calibration_result is not None

    rec0 = session.start()
    assert rec0.day == 0
    assert session.is_started
    assert session.current_day == 0
    assert session.patient_zero == (0,)

    # RN01: configuração e calibração congeladas após start()
    with pytest.raises(EpidemiaError):
        session.configure(SimulationConfig(seed=99))
    with pytest.raises(EpidemiaError):
        session.calibrate_beta()

    tl = session.timeline()
    assert isinstance(tl, Timeline)
    assert tl.days_available == 1
    assert len(tl.countries) == 3

    for _ in range(10):
        rec = session.run_day()
        assert rec.counts.total_vertices == 60
        if session.finished:
            break

    assert tl.days_available >= 2
    assert tl.country_day_zero("BRA") == 0
    digest_run1 = tl._buffer.digest_sha256()

    # reset() descarta buffer e destrava a sessão mantendo determinismo
    session.reset()
    assert not session.is_started
    assert session.current_day == -1
    with pytest.raises(EpidemiaError):
        session.timeline()

    session.start()
    for _ in range(10):
        session.run_day()
        if session.finished:
            break
    assert session.timeline()._buffer.digest_sha256() == digest_run1

    # Após reset(), configure() volta a ser permitido
    session.reset()
    new_cfg = SimulationConfig(seed=100, r0=1.8)
    session.configure(new_cfg)
    assert session.config == new_cfg
    assert session.calibrated_beta is None


def test_simulation_session_standalone_graph_and_error_guards() -> None:
    g = Graph(12)
    for u in range(12):
        g.add_edge(u, (u + 1) % 12, weight=0.9)

    session = SimulationSession(g)
    with pytest.raises(EpidemiaError):
        _ = session.config
    with pytest.raises(EpidemiaError):
        session.run_day()
    with pytest.raises(EpidemiaError):
        session.timeline()
    with pytest.raises(ParameterOutOfRangeError):
        session.configure("invalido")  # type: ignore[arg-type]
    with pytest.raises(ParameterOutOfRangeError):
        SimulationSession(object())

    session.configure(SimulationConfig(seed=7, patient_zero=(0,)))
    session.start()
    session.run_day()
    assert session.timeline().days_available == 2


def test_intervention_levels_monotonic_impact_reduction() -> None:
    """Valida a sensibilidade dos níveis de intervenção (Modelagem 5):
    'nenhum' > 'baixo' > 'medio' > 'alto' em casos acumulados médios.
    """
    world = _build_test_world(total_vertices=120)
    fixed_beta = 0.14
    initial_patients = (
        world.vertices_of_country("BRA")[0],
        world.vertices_of_country("BRA")[1],
        world.vertices_of_country("USA")[0],
        world.vertices_of_country("USA")[1],
        world.vertices_of_country("PRT")[0],
        world.vertices_of_country("PRT")[1],
    )

    mean_cases_by_level: dict[str, float] = {}
    test_seeds = (10, 20, 30, 40, 50)
    for level in ("nenhum", "baixo", "medio", "alto"):
        total_cases = 0
        for s in test_seeds:
            cfg = SimulationConfig(
                seed=s,
                r0=3.0,
                exit_rate_gamma=0.08,
                mortality=0.02,
                incubation_days=2.5,
                intervention_level=level,
                patient_zero=initial_patients,
                max_days=140,
            )
            session = SimulationSession(world, cfg)
            session._calibrated_beta = fixed_beta
            session.start()
            while not session.finished and session.current_day < 140:
                rec = session.run_day()
            total_cases += rec.counts.cumulative_cases
        mean_cases_by_level[level] = total_cases / len(test_seeds)

    assert mean_cases_by_level["nenhum"] > mean_cases_by_level["baixo"]
    assert mean_cases_by_level["baixo"] > mean_cases_by_level["medio"]
    assert mean_cases_by_level["medio"] > mean_cases_by_level["alto"]
