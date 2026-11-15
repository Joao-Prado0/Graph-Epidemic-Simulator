"""Testes dos contratos da linha do tempo e da codificação do byte de vértice (M3)."""

from __future__ import annotations

import pytest

from epidemia.core.errors import ParameterOutOfRangeError
from epidemia.core.timeline.protocol import (
    FLAG_ISOLATED,
    FLAG_VACCINATED,
    STATE_D,
    STATE_E,
    STATE_I,
    STATE_R,
    STATE_S,
    CountryCounts,
    CountryInfo,
    Timeline,
    decode_vertex_state,
    encode_vertex_byte,
    is_isolated_byte,
    is_vaccinated_byte,
)


@pytest.mark.parametrize("state", [STATE_S, STATE_E, STATE_I, STATE_R, STATE_D])
@pytest.mark.parametrize("isolated", [False, True])
@pytest.mark.parametrize("vaccinated", [False, True])
def test_encode_decode_roundtrip(state: int, isolated: bool, vaccinated: bool) -> None:
    b = encode_vertex_byte(state, isolated=isolated, vaccinated=vaccinated)
    assert decode_vertex_state(b) == state
    assert is_isolated_byte(b) is isolated
    assert is_vaccinated_byte(b) is vaccinated


def test_encode_known_values() -> None:
    assert encode_vertex_byte(STATE_I, isolated=True) == 10  # 2 | 8
    assert encode_vertex_byte(STATE_R, vaccinated=True) == 19  # 3 | 16
    assert FLAG_ISOLATED == 8 and FLAG_VACCINATED == 16


@pytest.mark.parametrize("bad", [-1, 5, 7, True])
def test_encode_invalid_state_raises(bad: int) -> None:
    with pytest.raises(ParameterOutOfRangeError):
        encode_vertex_byte(bad)


def test_country_counts_properties() -> None:
    c = CountryCounts(
        iso3="BRA",
        susceptible=10,
        exposed=2,
        infected=3,
        recovered_natural=4,
        recovered_vaccinated=5,
        deceased=1,
        isolated=2,
    )
    assert c.total_recovered == 9
    assert c.recovered == 4
    assert c.cumulative_cases == 3 + 4 + 1  # exclui E e vacinados
    assert c.cases == c.cumulative_cases
    assert c.deaths == 1
    assert c.total_vertices == 10 + 2 + 3 + 9 + 1


def test_dominant_state_and_tie_break() -> None:
    assert CountryCounts("X", susceptible=1, infected=7).dominant_state == STATE_I
    assert CountryCounts("X", deceased=9, susceptible=2).dominant_state == STATE_D
    assert CountryCounts("X", recovered_natural=2, recovered_vaccinated=2).dominant_state == STATE_R
    # empate: vence o menor código (S)
    assert CountryCounts("X", susceptible=3, infected=3).dominant_state == STATE_S


def test_country_info_is_frozen() -> None:
    info = CountryInfo(iso3="BRA", name="Brazil", population=1)
    with pytest.raises(AttributeError):
        info.iso3 = "ARG"  # type: ignore[misc]


def test_timeline_protocol_is_runtime_checkable() -> None:
    class Fake:
        num_vertices = 1
        vertex_country = (0,)
        countries = (CountryInfo("BRA", "Brazil", 1),)

        @property
        def days_available(self) -> int:
            return 1

        def vertex_states(self, day: int) -> bytes | None:
            return b"\x00"

        def country_counts(self, day: int) -> tuple[CountryCounts, ...]:
            return (CountryCounts("BRA", susceptible=1),)

    assert isinstance(Fake(), Timeline)
    assert not isinstance(object(), Timeline)
