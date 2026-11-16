"""Fachada de aplicação para o fluxo de pandemias reais (M4 — Arquitetura 4.3).

Define a ``RealTimeline``, que implementa o protocolo central ``Timeline``
(core/timeline/protocol.py) permitindo que o player de reprodução do M5 exiba
as 4 pandemias históricas (COVID-19, Ebola, H1N1, SARS) sem dependência de Qt.
Provê também a classe ``RealSession``, que coordena a seleção do cenário e a
exposição dos metadados históricos.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from epidemia.core.errors import (
    EpidemiaError,
    InvalidDatasetError,
    ParameterOutOfRangeError,
)
from epidemia.core.timeline.protocol import (
    CountryCounts,
    CountryInfo,
    Timeline,
)
from epidemia.datasets.series import (
    PANDEMIC_COVID19,
    PANDEMIC_EBOLA,
    PANDEMIC_H1N1,
    PANDEMIC_SARS,
    SUPPORTED_PANDEMICS,
    DailyRecord,
    PandemicSeries,
    load_pandemic_series,
)

__all__ = [
    "DEFAULT_REAL_NUM_VERTICES",
    "RealCountryCounts",
    "RealSession",
    "RealTimeline",
]

DEFAULT_REAL_NUM_VERTICES: Final[int] = 8000


@dataclass(frozen=True, slots=True)
class RealCountryCounts(CountryCounts):
    """Contagens por país no fluxo de pandemias reais com propriedade ``active``."""

    @property
    def active(self) -> int:
        """Casos ativos no dia (equivalente a infected na representação SEIRD)."""
        return self.infected


class RealTimeline(Timeline):
    """Linha do tempo baseada em séries temporais de pandemias reais (RF11, RF12).

    Implementa a interface ``Timeline`` de forma somente-leitura. No fluxo real:
    - ``vertex_states(day)`` retorna sempre ``None`` (os vértices não têm estados
      estocásticos individuais no fluxo real, herdando a cor do polígono na UI);
    - ``country_counts(day)`` entrega as contagens acumuladas e ativas calculadas
      a partir da série histórica indexada pela ``PandemicSeries``.
    """

    def __init__(
        self,
        series: PandemicSeries,
        countries: Sequence[CountryInfo],
        vertex_country: Sequence[int] | None = None,
        num_vertices: int = DEFAULT_REAL_NUM_VERTICES,
    ) -> None:
        if not isinstance(series, PandemicSeries):
            raise ParameterOutOfRangeError(
                f"series deve ser uma instância de PandemicSeries, recebido: {type(series)!r}."
            )
        if not countries:
            raise InvalidDatasetError("A lista de países não pode ser vazia.")
        if num_vertices <= 0:
            raise ParameterOutOfRangeError(f"num_vertices deve ser > 0, recebido: {num_vertices}.")

        self._series = series
        self._countries = tuple(countries)
        self._iso_index: dict[str, int] = {c.iso3: idx for idx, c in enumerate(self._countries)}
        self._num_vertices = num_vertices

        if vertex_country is not None:
            self._vertex_country = tuple(vertex_country)
        else:
            # Se não fornecido, distribui uniformemente entre os países presentes
            m = len(self._countries)
            self._vertex_country = tuple(i % m for i in range(num_vertices))

        self._counts_cache: dict[int, tuple[CountryCounts, ...]] = {}

    @property
    def series(self) -> PandemicSeries:
        """Retorna a ``PandemicSeries`` subjacente."""
        return self._series

    @property
    def num_vertices(self) -> int:
        """Número total de vértices alocados para o cenário."""
        return self._num_vertices

    @property
    def vertex_country(self) -> Sequence[int]:
        """Vetor de mapeamento do índice do vértice para o índice do seu país."""
        return self._vertex_country

    @property
    def countries(self) -> Sequence[CountryInfo]:
        """Metadados estáticos de cada país presente no cenário."""
        return self._countries

    @property
    def days_available(self) -> int:
        """Quantidade de dias disponíveis na série histórica da pandemia."""
        return self._series.total_days

    def vertex_states(self, day: int) -> bytes | None:
        """Retorna None no fluxo real (estados estocásticos individuais não existem)."""
        return None

    def country_counts(self, day: int) -> tuple[CountryCounts, ...]:
        """Retorna as contagens de todos os países no dia informado."""
        if not (0 <= day < self.days_available):
            raise ParameterOutOfRangeError(
                f"Dia {day} fora da faixa disponível [0, {self.days_available - 1}]."
            )

        if day in self._counts_cache:
            return self._counts_cache[day]

        result_list: list[CountryCounts] = []
        for info in self._countries:
            rec: DailyRecord | None = self._series.get_record(info.iso3, day)
            if rec is not None:
                cases = rec.cases
                deaths = rec.deaths
                recov = rec.recovered if rec.recovered is not None else 0
                infected = max(0, cases - (deaths + recov))
                susceptible = max(0, info.population - cases) if info.population > 0 else 0
            else:
                cases = 0
                deaths = 0
                recov = 0
                infected = 0
                susceptible = info.population

            counts = RealCountryCounts(
                iso3=info.iso3,
                susceptible=susceptible,
                exposed=0,
                infected=infected,
                recovered_natural=recov,
                recovered_vaccinated=0,
                deceased=deaths,
                isolated=0,
            )
            result_list.append(counts)

        counts_tuple = tuple(result_list)
        self._counts_cache[day] = counts_tuple
        return counts_tuple

    def country_day_zero(
        self,
        country: int | str,
        *,
        threshold_m: int = 1,
        threshold_cases: int | None = None,
    ) -> int | None:
        """Retorna o dia zero em que o país atinge o limiar de casos acumulados (A18).

        Parameters
        ----------
        country : int | str
            Código ISO3 ou índice numérico do país.
        threshold_m : int
            Limiar em vértices equivalentes (default M = 1).
        threshold_cases : int | None
            Limiar absoluto explícito em casos. Se None, converte ``threshold_m``
            para casos proporcionalmente à população do país sobre o total de vértices.
        """
        if isinstance(country, str):
            code = country.strip().upper()
            if code not in self._iso_index:
                raise InvalidDatasetError(f"País {country!r} não encontrado na linha do tempo.")
            idx = self._iso_index[code]
        else:
            idx = country
            if not (0 <= idx < len(self._countries)):
                raise InvalidDatasetError(f"Índice de país inválido: {country!r}.")

        info = self._countries[idx]
        if threshold_cases is not None:
            target_cases = max(1, threshold_cases)
        else:
            if info.population > 0 and self.num_vertices > 0:
                target_cases = max(1, round(threshold_m * (info.population / self.num_vertices)))
            else:
                target_cases = max(1, threshold_m)

        for d in range(self.days_available):
            counts = self.country_counts(d)[idx]
            if counts.cumulative_cases >= target_cases:
                return d

        return None

    @classmethod
    def from_world(
        cls,
        world: Any,
        series: PandemicSeries,
    ) -> RealTimeline:
        """Constrói uma RealTimeline a partir de um objeto World (M1) e PandemicSeries."""
        country_codes: tuple[str, ...] = getattr(world, "country_codes", ())
        names: dict[str, str] = getattr(world, "country_names", {})
        populations: dict[str, int] = getattr(world, "country_populations", {})
        geometries: dict[str, Any] = getattr(world, "country_geometries", {})

        countries = tuple(
            CountryInfo(
                iso3=code,
                name=names.get(code, code),
                population=populations.get(code, 0),
                geometry=geometries.get(code),
            )
            for code in country_codes
        )
        vertex_country: Sequence[int] = getattr(world, "vertex_country", ())
        num_vertices = len(vertex_country) if vertex_country else DEFAULT_REAL_NUM_VERTICES

        return cls(
            series=series,
            countries=countries,
            vertex_country=vertex_country,
            num_vertices=num_vertices,
        )


class RealSession:
    """Fachada de aplicação para gerenciamento e reprodução de pandemias reais (M4)."""

    def __init__(
        self,
        processed_dir: Path | str | None = None,
        world: Any = None,
        countries: Sequence[CountryInfo] | None = None,
    ) -> None:
        self._processed_dir = Path(processed_dir) if processed_dir is not None else None
        self._world = world
        self._countries = tuple(countries) if countries is not None else None
        self._current_pandemic: str | None = None
        self._series: PandemicSeries | None = None
        self._timeline: RealTimeline | None = None

    @property
    def available_pandemics(self) -> tuple[str, ...]:
        """Pandemias históricas suportadas."""
        return SUPPORTED_PANDEMICS

    @property
    def current_pandemic(self) -> str | None:
        """Nome da pandemia selecionada atualmente."""
        return self._current_pandemic

    @property
    def is_loaded(self) -> bool:
        """Indica se há uma pandemia carregada pronta para reprodução."""
        return self._timeline is not None

    def load_pandemic(
        self,
        name: str,
        *,
        series: PandemicSeries | None = None,
        csv_path: Path | str | None = None,
    ) -> RealTimeline:
        """Carrega uma pandemia histórica e instancia a RealTimeline.

        Parameters
        ----------
        name : str
            Identificador da pandemia (ex.: "covid19", "ebola", "h1n1", "sars").
        series : PandemicSeries, optional
            Instância pré-carregada de PandemicSeries.
        csv_path : Path | str, optional
            Caminho para o CSV da pandemia. Se omitido, busca no diretório processed.
        """
        canonical = name.strip().lower()
        if canonical not in SUPPORTED_PANDEMICS:
            raise ParameterOutOfRangeError(
                f"Pandemia {name!r} não suportada. Opções: {SUPPORTED_PANDEMICS}."
            )

        if series is not None:
            loaded_series = series
        else:
            if csv_path is not None:
                p_path = Path(csv_path)
            elif self._processed_dir is not None:
                p_path = self._processed_dir / f"{canonical}.csv"
            else:
                raise EpidemiaError(
                    "Não foi fornecido csv_path, series nem processed_dir para a RealSession."
                )
            loaded_series = load_pandemic_series(p_path, canonical)

        if self._world is not None:
            timeline = RealTimeline.from_world(self._world, loaded_series)
        elif self._countries is not None:
            timeline = RealTimeline(loaded_series, self._countries)
        else:
            # Constrói CountryInfo sintético/básico a partir dos países da série
            countries_list = [
                CountryInfo(iso3=c, name=c, population=0, geometry=None)
                for c in loaded_series.countries
            ]
            timeline = RealTimeline(loaded_series, countries_list)

        self._current_pandemic = canonical
        self._series = loaded_series
        self._timeline = timeline
        return timeline

    def timeline(self) -> RealTimeline:
        """Retorna a ``RealTimeline`` ativa (levanta erro se nenhuma estiver carregada)."""
        if self._timeline is None:
            raise EpidemiaError(
                "Nenhuma pandemia carregada na RealSession. Chame load_pandemic() primeiro."
            )
        return self._timeline

    def metadata(self) -> dict[str, Any]:
        """Retorna um dicionário de metadados da pandemia carregada."""
        if self._series is None:
            return {}

        last_day = self._series.total_days - 1
        cases, deaths, recov = self._series.daily_totals(last_day)
        return {
            "name": self._series.name,
            "first_date": self._series.first_date,
            "last_date": self._series.last_date,
            "total_days": self._series.total_days,
            "total_countries": len(self._series.countries),
            "final_cumulative_cases": cases,
            "final_deaths": deaths,
            "final_recovered": recov,
        }

    def reset(self) -> None:
        """Reinicia a sessão, descarregando a linha do tempo atual."""
        self._current_pandemic = None
        self._series = None
        self._timeline = None
