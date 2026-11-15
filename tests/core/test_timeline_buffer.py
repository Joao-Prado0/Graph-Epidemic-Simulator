"""Testes do StateBuffer e do SimulationTimeline (M3)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from epidemia.core.errors import InvalidDatasetError, ParameterOutOfRangeError
from epidemia.core.timeline import (
    STATE_D,
    STATE_E,
    STATE_I,
    STATE_R,
    STATE_S,
    CountryInfo,
    SimulationTimeline,
    StateBuffer,
    Timeline,
    encode_vertex_byte,
)


def _day(*states: int) -> bytes:
    return bytes(states)


def test_buffer_append_and_read() -> None:
    buf = StateBuffer(3)
    assert buf.days_available == 0
    idx = buf.append_day(_day(STATE_S, STATE_I, STATE_S))
    assert idx == 0 and buf.days_available == 1
    buf.append_day(bytearray([STATE_E, STATE_I, STATE_R]))
    assert buf.vertex_states(0) == b"\x00\x02\x00"
    assert buf.compartment_counts(1).total_vertices == 3
    assert len(buf.compartment_series()) == 2


def test_buffer_snapshot_is_immutable_copy() -> None:
    buf = StateBuffer(2)
    mutable = bytearray([STATE_S, STATE_I])
    buf.append_day(mutable)
    mutable[0] = STATE_D  # mexer na origem não altera o histórico
    assert buf.vertex_states(0) == b"\x00\x02"
    assert isinstance(buf.vertex_states(0), bytes)


def test_buffer_validations() -> None:
    with pytest.raises(ParameterOutOfRangeError):
        StateBuffer(0)
    buf = StateBuffer(2)
    with pytest.raises(ParameterOutOfRangeError):
        buf.append_day(b"\x00")  # tamanho errado
    with pytest.raises(ParameterOutOfRangeError):
        buf.append_day(b"\x00\x07")  # estado inválido
    assert buf.days_available == 0  # falha não grava nada
    for bad in (0, -1, True):
        with pytest.raises(ParameterOutOfRangeError):
            buf.vertex_states(bad)  # type: ignore[arg-type]


def test_digest_is_deterministic_and_sensitive() -> None:
    a, b, c = StateBuffer(2), StateBuffer(2), StateBuffer(2)
    for buf in (a, b):
        buf.append_day(_day(0, 2))
        buf.append_day(_day(1, 2))
    c.append_day(_day(0, 2))
    c.append_day(_day(2, 2))
    assert a.digest_sha256() == b.digest_sha256()
    assert a.digest_sha256() != c.digest_sha256()
    assert len(a.digest_sha256()) == 64


def test_clear_resets_buffer() -> None:
    buf = StateBuffer(1)
    buf.append_day(_day(0))
    gen = buf.generation
    buf.clear()
    assert buf.days_available == 0 and buf.generation == gen + 1


def _timeline() -> tuple[StateBuffer, SimulationTimeline]:
    buf = StateBuffer(5)
    countries = [CountryInfo("AAA", "A", 100), CountryInfo("BBB", "B", 50)]
    vertex_country = [0, 0, 0, 1, 1]
    return buf, SimulationTimeline(buf, vertex_country, countries)


def test_timeline_country_counts_and_flags() -> None:
    buf, tl = _timeline()
    iso_inf = encode_vertex_byte(STATE_I, isolated=True)
    rec_vac = encode_vertex_byte(STATE_R, vaccinated=True)
    buf.append_day(_day(STATE_S, iso_inf, STATE_E, rec_vac, STATE_D))
    a, b = tl.country_counts(0)
    assert (a.iso3, a.susceptible, a.infected, a.exposed, a.isolated) == ("AAA", 1, 1, 1, 1)
    assert (b.recovered_vaccinated, b.recovered_natural, b.deceased) == (1, 0, 1)
    assert a.total_vertices == 3 and b.total_vertices == 2
    assert b.cumulative_cases == 1  # só D; R vacinado não conta
    assert tl.country_counts(0) is tl.country_counts(0)  # cache


def test_timeline_is_a_timeline_and_follows_buffer_growth() -> None:
    buf, tl = _timeline()
    assert isinstance(tl, Timeline)
    assert tl.days_available == 0
    buf.append_day(_day(0, 0, 0, 0, 0))
    assert tl.days_available == 1
    assert tl.vertex_states(0) == bytes(5)
    with pytest.raises(ParameterOutOfRangeError):
        tl.country_counts(1)


def test_timeline_cache_invalidated_after_clear() -> None:
    buf, tl = _timeline()
    buf.append_day(_day(2, 0, 0, 0, 0))
    assert tl.country_counts(0)[0].infected == 1
    buf.clear()
    buf.append_day(_day(0, 0, 0, 2, 2))
    assert tl.country_counts(0)[0].infected == 0
    assert tl.country_counts(0)[1].infected == 2


def test_country_day_zero() -> None:
    buf, tl = _timeline()
    buf.append_day(_day(0, 0, 0, 0, 0))
    buf.append_day(_day(2, 0, 0, 0, 0))  # A: 1 caso no dia 1
    buf.append_day(_day(2, 2, 0, 0, 0))  # A: 2 casos no dia 2
    assert tl.country_day_zero("AAA") == 1
    assert tl.country_day_zero(0, threshold_m=2) == 2
    assert tl.country_day_zero("BBB") is None
    with pytest.raises(InvalidDatasetError):
        tl.country_day_zero("ZZZ")
    with pytest.raises(InvalidDatasetError):
        tl.country_day_zero(9)
    with pytest.raises(ParameterOutOfRangeError):
        tl.country_day_zero("AAA", threshold_m=0)


def test_timeline_constructor_validations() -> None:
    buf = StateBuffer(2)
    countries = [CountryInfo("AAA", "A", 1)]
    with pytest.raises(InvalidDatasetError):
        SimulationTimeline(buf, [0], countries)
    with pytest.raises(InvalidDatasetError):
        SimulationTimeline(buf, [0, 1], countries)


def test_from_world_uses_world_attributes() -> None:
    world = SimpleNamespace(
        country_codes=("AAA", "BBB"),
        country_names={"AAA": "A", "BBB": "B"},
        country_populations={"AAA": 10, "BBB": 20},
        country_geometries={"AAA": "geom"},
        vertex_country=[0, 1, 1],
    )
    buf = StateBuffer(3)
    tl = SimulationTimeline.from_world(world, buf)
    assert [c.iso3 for c in tl.countries] == ["AAA", "BBB"]
    assert tl.countries[0].geometry == "geom" and tl.countries[1].geometry is None
    assert tl.countries[1].population == 20
    assert tuple(tl.vertex_country) == (0, 1, 1)
