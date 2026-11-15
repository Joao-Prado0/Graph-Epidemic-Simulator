"""Contrato de leitura da linha do tempo e codificação do byte de vértice (M3).

Define a interface única ``Timeline`` consumida pelo player (M5) nos dois fluxos
(simulação e pandemias reais — Arquitetura 4.1, decisão A2) e as funções de
empacotamento do byte de cada vértice (A10):

- bits 0..2: estado (S=0, E=1, I=2, R=3, D=4);
- bit 3: flag de isolado;
- bit 4: flag de vacinado.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from epidemia.core.analysis.epidemic_metrics import (
    FLAG_ISOLATED,
    FLAG_VACCINATED,
    STATE_D,
    STATE_E,
    STATE_I,
    STATE_MASK,
    STATE_R,
    STATE_S,
    CompartmentCounts,
)
from epidemia.core.errors import ParameterOutOfRangeError

__all__ = [
    "FLAG_ISOLATED",
    "FLAG_VACCINATED",
    "STATE_D",
    "STATE_E",
    "STATE_I",
    "STATE_MASK",
    "STATE_R",
    "STATE_S",
    "CompartmentCounts",
    "CountryCounts",
    "CountryInfo",
    "Timeline",
    "decode_vertex_state",
    "encode_vertex_byte",
    "is_isolated_byte",
    "is_vaccinated_byte",
]


def encode_vertex_byte(state: int, *, isolated: bool = False, vaccinated: bool = False) -> int:
    """Empacota estado e flags em um único byte de vértice. Complexidade: O(1)."""
    if isinstance(state, bool) or not isinstance(state, int) or not (STATE_S <= state <= STATE_D):
        raise ParameterOutOfRangeError(f"Estado epidemiológico inválido: {state!r}.")
    value = state
    if isolated:
        value |= FLAG_ISOLATED
    if vaccinated:
        value |= FLAG_VACCINATED
    return value


def decode_vertex_state(byte_val: int) -> int:
    """Extrai o estado epidemiológico (bits 0..2) de um byte de vértice."""
    return byte_val & STATE_MASK


def is_isolated_byte(byte_val: int) -> bool:
    """Indica se a flag de isolado (bit 3) está ligada."""
    return bool(byte_val & FLAG_ISOLATED)


def is_vaccinated_byte(byte_val: int) -> bool:
    """Indica se a flag de vacinado (bit 4) está ligada."""
    return bool(byte_val & FLAG_VACCINATED)


@dataclass(frozen=True, slots=True)
class CountryInfo:
    """Metadados estáticos de um país para a reprodução (nome, ISO3, população, geometria)."""

    iso3: str
    name: str
    population: int
    geometry: Any = None


@dataclass(frozen=True, slots=True)
class CountryCounts:
    """Contagens de vértices por compartimento em um país, em um dia."""

    iso3: str
    susceptible: int = 0
    exposed: int = 0
    infected: int = 0
    recovered_natural: int = 0
    recovered_vaccinated: int = 0
    deceased: int = 0
    isolated: int = 0

    @property
    def total_recovered(self) -> int:
        """R total (naturais + vacinados)."""
        return self.recovered_natural + self.recovered_vaccinated

    @property
    def recovered(self) -> int:
        """R natural, sem vacinados (comparação com o SARS, Modelagem 7.1)."""
        return self.recovered_natural

    @property
    def cumulative_cases(self) -> int:
        """Casos acumulados I + R natural + D (exclui E e vacinados, Modelagem 7.1)."""
        return self.infected + self.recovered_natural + self.deceased

    @property
    def cases(self) -> int:
        """Alias de ``cumulative_cases``, na mesma forma do fluxo real."""
        return self.cumulative_cases

    @property
    def deaths(self) -> int:
        """Mortes acumuladas (D)."""
        return self.deceased

    @property
    def total_vertices(self) -> int:
        """Soma S + E + I + R + D (invariante de conservação, Modelagem 11.2)."""
        return self.susceptible + self.exposed + self.infected + self.total_recovered + self.deceased

    @property
    def dominant_state(self) -> int:
        """Estado com mais vértices no país (cor do polígono na simulação, Arquitetura 4.1).

        Em empate vence o estado de menor código.
        """
        by_state = (
            self.susceptible,
            self.exposed,
            self.infected,
            self.total_recovered,
            self.deceased,
        )
        return max(range(len(by_state)), key=lambda s: (by_state[s], -s))


@runtime_checkable
class Timeline(Protocol):
    """Histórico de estados já disponível para reprodução (simulação ou fluxo real)."""

    num_vertices: int
    vertex_country: Sequence[int]
    countries: Sequence[CountryInfo]

    @property
    def days_available(self) -> int:
        """Dias já gravados (cresce durante a simulação)."""
        ...

    def vertex_states(self, day: int) -> bytes | None:
        """Byte por vértice no dia (``None`` no fluxo real)."""
        ...

    def country_counts(self, day: int) -> Sequence[CountryCounts]:
        """Contagens por país no dia."""
        ...
