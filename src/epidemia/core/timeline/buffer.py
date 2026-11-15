"""Buffer de histórico de estados (append-only) e ``SimulationTimeline`` (M3).

O motor grava um ``bytes`` por dia (um byte por vértice, ver ``protocol``) e só
depois anuncia o dia; a interface lê apenas dias já gravados (Arquitetura 7,
decisões E2 e A5). Cada dia é guardado como ``bytes`` imutável, então nem a
thread da interface nem código externo conseguem alterar o passado.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any, Final

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
    extract_compartment_counts,
)
from epidemia.core.errors import InvalidDatasetError, ParameterOutOfRangeError
from epidemia.core.timeline.protocol import CountryCounts, CountryInfo

DEFAULT_DAY_ZERO_VERTEX_THRESHOLD: Final[int] = 1


def _is_int(value: object) -> bool:
    """Inteiro de verdade (``bool`` não vale)."""
    return isinstance(value, int) and not isinstance(value, bool)


class StateBuffer:
    """Histórico somente de acréscimo: um snapshot imutável de ``bytes`` por dia."""

    def __init__(self, num_vertices: int) -> None:
        if not _is_int(num_vertices) or num_vertices <= 0:
            raise ParameterOutOfRangeError(
                f"num_vertices deve ser inteiro positivo: {num_vertices!r}"
            )
        self._num_vertices = num_vertices
        self._snapshots: list[bytes] = []
        self._counts: list[CompartmentCounts] = []
        self._generation = 0

    @property
    def num_vertices(self) -> int:
        """Quantidade de vértices por dia."""
        return self._num_vertices

    @property
    def days_available(self) -> int:
        """Dias já gravados."""
        return len(self._snapshots)

    @property
    def generation(self) -> int:
        """Contador incrementado a cada ``clear()`` (invalida caches de leitores)."""
        return self._generation

    def append_day(self, states: bytes | bytearray | Sequence[int]) -> int:
        """Grava um novo dia e devolve seu índice. Complexidade: O(V).

        Valida o tamanho e todos os estados (via ``extract_compartment_counts``).
        O dia só fica visível depois de totalmente gravado.
        """
        snapshot = bytes(states)
        if len(snapshot) != self._num_vertices:
            raise ParameterOutOfRangeError(
                f"O dia deve ter {self._num_vertices} bytes (recebido: {len(snapshot)})."
            )
        try:
            counts = extract_compartment_counts(snapshot)
        except ValueError as exc:
            raise ParameterOutOfRangeError(str(exc)) from exc
        # Contagens primeiro: leitores só enxergam o dia quando ``_snapshots`` cresce.
        self._counts.append(counts)
        self._snapshots.append(snapshot)
        return len(self._snapshots) - 1

    def _check_day(self, day: int) -> None:
        if not _is_int(day) or not (0 <= day < len(self._snapshots)):
            raise ParameterOutOfRangeError(
                f"Dia {day!r} indisponível (dias gravados: {len(self._snapshots)})."
            )

    def vertex_states(self, day: int) -> bytes:
        """Bytes dos vértices no dia. Complexidade: O(1)."""
        self._check_day(day)
        return self._snapshots[day]

    def compartment_counts(self, day: int) -> CompartmentCounts:
        """Contagens globais do dia (calculadas na gravação). Complexidade: O(1)."""
        self._check_day(day)
        return self._counts[day]

    def compartment_series(self) -> list[CompartmentCounts]:
        """Cópia da série de contagens globais dos dias gravados."""
        return list(self._counts[: len(self._snapshots)])

    def digest_sha256(self) -> str:
        """SHA-256 de todos os dias, em ordem (teste de determinismo, RN03 e F2)."""
        h = hashlib.sha256()
        for snapshot in self._snapshots:
            h.update(snapshot)
        return h.hexdigest()

    def clear(self) -> None:
        """Descarta o histórico (reiniciar descarta o buffer)."""
        self._snapshots = []
        self._counts = []
        self._generation += 1


class SimulationTimeline:
    """Implementação de ``Timeline`` para o fluxo de simulação, sobre um ``StateBuffer``."""

    def __init__(
        self,
        buffer: StateBuffer,
        vertex_country: Sequence[int],
        countries: Sequence[CountryInfo],
    ) -> None:
        if len(vertex_country) != buffer.num_vertices:
            raise InvalidDatasetError(
                f"vertex_country tem {len(vertex_country)} itens, mas o buffer tem "
                f"{buffer.num_vertices} vértices."
            )
        bad_index = vertex_country and (
            min(vertex_country) < 0 or max(vertex_country) >= len(countries)
        )
        if bad_index:
            raise InvalidDatasetError("vertex_country tem índice de país fora de 'countries'.")
        self._buffer = buffer
        self.num_vertices: int = buffer.num_vertices
        self.vertex_country: Sequence[int] = tuple(vertex_country)
        self.countries: Sequence[CountryInfo] = tuple(countries)
        self._iso_index = {c.iso3: i for i, c in enumerate(self.countries)}
        self._cache: dict[int, tuple[CountryCounts, ...]] = {}
        self._cache_generation = buffer.generation

    @classmethod
    def from_world(cls, world: Any, buffer: StateBuffer) -> SimulationTimeline:
        """Constrói a partir de um ``World`` (acesso por atributos, sem importar ``world``)."""
        countries = [
            CountryInfo(
                iso3=iso3,
                name=world.country_names[iso3],
                population=world.country_populations[iso3],
                geometry=world.country_geometries.get(iso3),
            )
            for iso3 in world.country_codes
        ]
        return cls(buffer, world.vertex_country, countries)

    @property
    def days_available(self) -> int:
        """Dias já gravados no buffer."""
        return self._buffer.days_available

    def vertex_states(self, day: int) -> bytes:
        """Bytes dos vértices no dia."""
        return self._buffer.vertex_states(day)

    def country_counts(self, day: int) -> tuple[CountryCounts, ...]:
        """Contagens por país no dia. O(V) na primeira consulta e O(1) no cache."""
        if self._cache_generation != self._buffer.generation:
            self._cache.clear()
            self._cache_generation = self._buffer.generation
        cached = self._cache.get(day)
        if cached is not None:
            return cached

        states = self._buffer.vertex_states(day)
        n_countries = len(self.countries)
        # por país: S, E, I, R natural, R vacinado, D, isolados
        acc = [[0] * 7 for _ in range(n_countries)]
        for byte_val, c_idx in zip(states, self.vertex_country, strict=True):
            row = acc[c_idx]
            state = byte_val & STATE_MASK
            if state == STATE_S:
                row[0] += 1
            elif state == STATE_E:
                row[1] += 1
            elif state == STATE_I:
                row[2] += 1
            elif state == STATE_R:
                row[4 if byte_val & FLAG_VACCINATED else 3] += 1
            elif state == STATE_D:
                row[5] += 1
            if byte_val & FLAG_ISOLATED:
                row[6] += 1

        result = tuple(
            CountryCounts(
                iso3=info.iso3,
                susceptible=r[0],
                exposed=r[1],
                infected=r[2],
                recovered_natural=r[3],
                recovered_vaccinated=r[4],
                deceased=r[5],
                isolated=r[6],
            )
            for info, r in zip(self.countries, acc, strict=True)
        )
        self._cache[day] = result
        return result

    def country_day_zero(
        self,
        country: int | str,
        *,
        threshold_m: int = DEFAULT_DAY_ZERO_VERTEX_THRESHOLD,
    ) -> int | None:
        """Primeiro dia em que o país atinge ``threshold_m`` vértices com casos (A18).

        Conta I + R natural + D (casos acumulados). Devolve ``None`` se nunca atingir.
        """
        if not _is_int(threshold_m) or threshold_m < 1:
            raise ParameterOutOfRangeError(f"threshold_m deve ser inteiro >= 1: {threshold_m!r}")
        if isinstance(country, str):
            if country not in self._iso_index:
                raise InvalidDatasetError(f"País {country!r} não encontrado na linha do tempo.")
            idx = self._iso_index[country]
        else:
            idx = country
            if not (0 <= idx < len(self.countries)):
                raise InvalidDatasetError(f"Índice de país inválido: {country!r}.")
        for day in range(self.days_available):
            if self.country_counts(day)[idx].cumulative_cases >= threshold_m:
                return day
        return None
