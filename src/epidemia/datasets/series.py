"""Leitor e indexador de séries temporais de pandemias históricas (M4 — datasets/series.py).

Provê a leitura e indexação em memória das séries temporais diárias processadas:
- ``covid19.csv``: COVID-19 (JHU / OMS);
- ``ebola.csv``: Surto de Ebola 2014–2016 na África Ocidental;
- ``h1n1.csv``: Pandemia de Gripe Suína A(H1N1) 2009;
- ``sars.csv``: Surto de SARS 2003 (único com dados de recuperados).

Esquema unificado dos arquivos (Modelagem 3.4 / Dados 6.2):
``iso3,date,cases,deaths,recovered``
onde ``date`` segue ISO 8601 (AAAA-MM-DD), e os valores numéricos são acumulados
não decrescentes. Em conformidade estrita com a regra de isolamento da camada
``datasets``, utiliza exclusivamente a biblioteca padrão do Python.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Final

__all__ = [
    "PANDEMIC_COVID19",
    "PANDEMIC_EBOLA",
    "PANDEMIC_H1N1",
    "PANDEMIC_SARS",
    "SUPPORTED_PANDEMICS",
    "DailyRecord",
    "PandemicSeries",
    "load_pandemic_series",
]

PANDEMIC_COVID19: Final[str] = "covid19"
PANDEMIC_EBOLA: Final[str] = "ebola"
PANDEMIC_H1N1: Final[str] = "h1n1"
PANDEMIC_SARS: Final[str] = "sars"

SUPPORTED_PANDEMICS: Final[tuple[str, ...]] = (
    PANDEMIC_COVID19,
    PANDEMIC_EBOLA,
    PANDEMIC_H1N1,
    PANDEMIC_SARS,
)


@dataclass(frozen=True, slots=True)
class DailyRecord:
    """Registro diário de casos, óbitos e recuperados acumulados de um país."""

    iso3: str
    date: str
    cases: int
    deaths: int
    recovered: int | None = None

    @property
    def cumulative_cases(self) -> int:
        """Alias para ``cases`` (casos acumulados I + R natural + D)."""
        return self.cases


@dataclass(frozen=True, slots=True)
class PandemicSeries:
    """Estrutura indexada em memória de uma série temporal pandêmica."""

    name: str
    dates: tuple[str, ...]
    countries: tuple[str, ...]
    first_date: str
    last_date: str
    total_days: int
    _by_country_date: dict[tuple[str, str], DailyRecord]
    _by_country_day: dict[tuple[str, int], DailyRecord]
    _by_country: dict[str, tuple[DailyRecord, ...]]

    def get_record(self, iso3: str, day_or_date: int | str) -> DailyRecord | None:
        """Retorna o registro do país por índice de dia (int) ou por data AAAA-MM-DD (str)."""
        code = iso3.strip().upper()
        if isinstance(day_or_date, int):
            return self._by_country_day.get((code, day_or_date))
        return self._by_country_date.get((code, str(day_or_date).strip()))

    def country_series(self, iso3: str) -> tuple[DailyRecord, ...]:
        """Retorna a série temporal completa ordenada de um país (ou tupla vazia)."""
        code = iso3.strip().upper()
        return self._by_country.get(code, ())

    def day_records(self, day: int) -> dict[str, DailyRecord]:
        """Retorna todos os registros dos países disponíveis no índice de dia informado."""
        result: dict[str, DailyRecord] = {}
        for c in self.countries:
            rec = self._by_country_day.get((c, day))
            if rec is not None:
                result[c] = rec
        return result

    def cumulative_cases_series(self, iso3: str) -> tuple[int, ...]:
        """Retorna a tupla de casos acumulados do país ao longo de todos os dias."""
        series = self.country_series(iso3)
        return tuple(r.cases for r in series)

    def deaths_series(self, iso3: str) -> tuple[int, ...]:
        """Retorna a tupla de óbitos acumulados do país ao longo de todos os dias."""
        series = self.country_series(iso3)
        return tuple(r.deaths for r in series)

    def recovered_series(self, iso3: str) -> tuple[int, ...] | None:
        """Retorna a tupla de recuperados acumulados (ou None se a série não contiver R)."""
        series = self.country_series(iso3)
        if not series or series[0].recovered is None:
            return None
        return tuple(r.recovered if r.recovered is not None else 0 for r in series)

    def daily_totals(self, day: int) -> tuple[int, int, int]:
        """Calcula os totais globais acumulados no dia: (casos, mortes, recuperados)."""
        tot_cases = 0
        tot_deaths = 0
        tot_rec = 0
        has_rec = False

        for c in self.countries:
            rec = self._by_country_day.get((c, day))
            if rec is not None:
                tot_cases += rec.cases
                tot_deaths += rec.deaths
                if rec.recovered is not None:
                    tot_rec += rec.recovered
                    has_rec = True

        return tot_cases, tot_deaths, tot_rec if has_rec else 0


def _parse_recovered(val: str | None) -> int | None:
    if val is None:
        return None
    val_clean = val.strip()
    if not val_clean:
        return None
    try:
        return int(float(val_clean))
    except ValueError:
        return None


def load_pandemic_series(path: Path | str, pandemic_name: str = "") -> PandemicSeries:
    """Carrega e indexa um arquivo de série temporal de pandemia histórica.

    Parameters
    ----------
    path : Path | str
        Caminho para o arquivo CSV da pandemia (ex.: ``covid19.csv``).
    pandemic_name : str, optional
        Identificador amigável da pandemia. Se vazio, infere a partir do nome do arquivo.

    Returns
    -------
    PandemicSeries
        Estrutura imutável contendo índices de acesso rápido e metadados.

    Raises
    ------
    FileNotFoundError
        Se o arquivo não existir.
    ValueError
        Se colunas obrigatórias estiverem ausentes ou formato for inválido.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Arquivo de série temporal não encontrado: {file_path}")

    name = pandemic_name.strip() if pandemic_name else file_path.stem.lower()

    records_list: list[DailyRecord] = []
    dates_set: set[str] = set()
    countries_set: set[str] = set()

    with file_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Arquivo CSV vazio ou sem cabeçalho: {file_path}")

        fieldnames = set(reader.fieldnames)
        required = {"iso3", "date", "cases", "deaths"}
        missing = required - fieldnames
        if missing:
            raise ValueError(f"Colunas obrigatórias ausentes em {file_path}: {sorted(missing)}")

        for row_idx, row in enumerate(reader, start=2):
            iso3 = (row.get("iso3") or "").strip().upper()
            date_str = (row.get("date") or "").strip()
            cases_str = (row.get("cases") or "").strip()
            deaths_str = (row.get("deaths") or "").strip()

            if not iso3:
                raise ValueError(f"Linha {row_idx} em {file_path} sem código iso3.")
            if not date_str:
                raise ValueError(f"Linha {row_idx} ({iso3}) em {file_path} sem data.")

            try:
                cases = int(float(cases_str)) if cases_str else 0
                deaths = int(float(deaths_str)) if deaths_str else 0
            except ValueError as err:
                raise ValueError(
                    f"Valor numérico inválido na linha {row_idx} ({iso3}, {date_str}): {err}"
                ) from err

            if cases < 0 or deaths < 0:
                raise ValueError(
                    f"Valores negativos na linha {row_idx}: cases={cases}, deaths={deaths}."
                )

            recovered = _parse_recovered(row.get("recovered"))
            if recovered is not None and recovered < 0:
                raise ValueError(f"Recuperados negativos na linha {row_idx}: {recovered}.")

            rec = DailyRecord(
                iso3=iso3,
                date=date_str,
                cases=cases,
                deaths=deaths,
                recovered=recovered,
            )
            records_list.append(rec)
            dates_set.add(date_str)
            countries_set.add(iso3)

    if not records_list:
        raise ValueError(f"O arquivo {file_path} não contém registros de dados.")

    sorted_dates = tuple(sorted(dates_set))
    sorted_countries = tuple(sorted(countries_set))
    date_to_day_idx = {d: idx for idx, d in enumerate(sorted_dates)}

    by_country_date: dict[tuple[str, str], DailyRecord] = {}
    by_country_day: dict[tuple[str, int], DailyRecord] = {}
    temp_by_country: dict[str, list[DailyRecord]] = {c: [] for c in sorted_countries}

    for rec in records_list:
        by_country_date[(rec.iso3, rec.date)] = rec
        day_idx = date_to_day_idx[rec.date]
        by_country_day[(rec.iso3, day_idx)] = rec
        temp_by_country[rec.iso3].append(rec)

    # Ordena a lista de cada país por data
    by_country: dict[str, tuple[DailyRecord, ...]] = {}
    for c, r_list in temp_by_country.items():
        by_country[c] = tuple(sorted(r_list, key=lambda r: r.date))

    return PandemicSeries(
        name=name,
        dates=sorted_dates,
        countries=sorted_countries,
        first_date=sorted_dates[0],
        last_date=sorted_dates[-1],
        total_days=len(sorted_dates),
        _by_country_date=by_country_date,
        _by_country_day=by_country_day,
        _by_country=by_country,
    )
