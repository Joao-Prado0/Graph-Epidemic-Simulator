"""Métricas epidemiológicas sobre séries temporais e buffer de estados (M2 — RF21).

Implementa o cálculo do R0 efetivo pela relação SEIR no crescimento inicial,
extração de contagens por compartimento a partir do byte de estado de cada
vértice (excluindo vacinados dos casos/recuperados naturais) e indicadores de
resumo da epidemia (pico de ativos, pico de novos casos diários, duração,
mortes e tamanho final).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

# Codificação do byte de vértice (Arquitetura, seção 4.1)
STATE_MASK = 0b0000_0111
STATE_S = 0
STATE_E = 1
STATE_I = 2
STATE_R = 3
STATE_D = 4

FLAG_ISOLATED = 1 << 3    # bit 3
FLAG_VACCINATED = 1 << 4  # bit 4


@dataclass(frozen=True)
class CompartmentCounts:
    """Contagens agregadas de um dia a partir dos bytes de estado dos vértices."""

    susceptible: int
    exposed: int
    infected: int
    recovered_natural: int
    recovered_vaccinated: int
    deceased: int
    isolated: int

    @property
    def total_recovered(self) -> int:
        """Total no compartimento R (naturais + vacinados)."""
        return self.recovered_natural + self.recovered_vaccinated

    @property
    def cumulative_cases(self) -> int:
        """Casos acumulados sintomáticos/naturais: I + R_natural + D (Modelagem 7.1)."""
        return self.infected + self.recovered_natural + self.deceased

    @property
    def total_vertices(self) -> int:
        """Soma de todos os compartimentos (invariante S + E + I + R + D = N)."""
        return (
            self.susceptible
            + self.exposed
            + self.infected
            + self.total_recovered
            + self.deceased
        )


@dataclass(frozen=True)
class EpidemicSummary:
    """Resumo consolidado de uma epidemia para o painel e comparação (RF21)."""

    peak_active_cases: int
    peak_active_day: int
    peak_daily_new_cases: int
    peak_daily_new_cases_day: int
    final_infected_count: int
    final_infected_fraction: float
    total_deaths: int
    mortality_fraction: float
    duration_days: int
    effective_r0: float | None = None


def extract_compartment_counts(vertex_bytes: bytes | bytearray | Sequence[int]) -> CompartmentCounts:
    """Extrai as contagens de cada compartimento e flags a partir dos bytes do dia.

    Segue a codificação da Arquitetura (seção 4.1):
    - bits 0..2: estado (0=S, 1=E, 2=I, 3=R, 4=D)
    - bit 3: flag de isolado
    - bit 4: flag de vacinado (distingue R vacinado de R natural)

    Complexidade: O(V).
    """
    s = e = i = r_nat = r_vac = d = iso = 0
    for b in vertex_bytes:
        state = b & STATE_MASK
        if b & FLAG_ISOLATED:
            iso += 1

        if state == STATE_S:
            s += 1
        elif state == STATE_E:
            e += 1
        elif state == STATE_I:
            i += 1
        elif state == STATE_R:
            if b & FLAG_VACCINATED:
                r_vac += 1
            else:
                r_nat += 1
        elif state == STATE_D:
            d += 1
        else:
            raise ValueError(f"Estado epidemiológico inválido nos bits 0..2: {state}")

    return CompartmentCounts(
        susceptible=s,
        exposed=e,
        infected=i,
        recovered_natural=r_nat,
        recovered_vaccinated=r_vac,
        deceased=d,
        isolated=iso,
    )


def daily_new_cases(cumulative_cases: Sequence[int]) -> list[int]:
    """Calcula a série de novos casos por dia a partir da série acumulada (I + R + D).

    No dia 0, os novos casos correspondem ao valor inicial ``cumulative_cases[0]``.
    Nos dias seguintes, ``max(0, C[t] - C[t - 1])``.

    Complexidade: O(T), onde T é o número de dias.
    """
    if not cumulative_cases:
        return []
    result = [max(0, int(cumulative_cases[0]))]
    for t in range(1, len(cumulative_cases)):
        diff = int(cumulative_cases[t]) - int(cumulative_cases[t - 1])
        result.append(max(0, diff))
    return result


def estimate_effective_r0_seir(
    i_start: float,
    i_end: float,
    days_elapsed: int | float,
    sigma: float,
    gamma: float,
) -> float:
    """Estima o R0 efetivo pela taxa de crescimento exponencial na forma SEIR.

    Fórmula (Modelagem, seção 6.1 e RF21):
        ``r = ln(I_t / I_0) / t``
        ``R0 = (1 + r / sigma) * (1 + r / gamma)``

    Parâmetros:
        i_start: Contagem de infectados (ou casos na fase inicial) no início da janela.
        i_end: Contagem ao fim da janela de crescimento.
        days_elapsed: Intervalo de dias ``t > 0`` entre as duas medições.
        sigma: Taxa de saída da incubação (``1 / incubacao_dias > 0``).
        gamma: Taxa total de saída do compartimento infeccioso (``> 0``).
    """
    if days_elapsed <= 0:
        raise ValueError(f"days_elapsed deve ser positivo: {days_elapsed}")
    if sigma <= 0 or gamma <= 0:
        raise ValueError(f"sigma ({sigma}) e gamma ({gamma}) devem ser positivos.")
    if i_start <= 0 or i_end <= 0:
        raise ValueError(f"i_start ({i_start}) e i_end ({i_end}) devem ser positivos.")

    r = math.log(i_end / i_start) / days_elapsed
    r0 = (1.0 + r / sigma) * (1.0 + r / gamma)
    return max(0.0, r0)


def estimate_effective_r0_from_series(
    infected_series: Sequence[int | float],
    sigma: float,
    gamma: float,
    *,
    start_day: int | None = None,
    end_day: int | None = None,
) -> float | None:
    """Estima o R0 efetivo diretamente a partir de uma série temporal de infectados.

    Se ``start_day`` não for informado, usa o primeiro dia com valor positivo.
    Se ``end_day`` não for informado, usa o dia de pico (desde que posterior a
    ``start_day`` e com crescimento positivo). Retorna ``None`` se não houver
    janela válida de crescimento para estimar.
    """
    if sigma <= 0 or gamma <= 0:
        raise ValueError(f"sigma ({sigma}) e gamma ({gamma}) devem ser positivos.")
    if len(infected_series) < 2:
        return None

    t0 = start_day
    if t0 is None:
        for idx, val in enumerate(infected_series):
            if val > 0:
                t0 = idx
                break
    if t0 is None or not (0 <= t0 < len(infected_series)) or infected_series[t0] <= 0:
        return None

    t1 = end_day
    if t1 is None:
        # Escolhe o primeiro dia do valor máximo a partir de t0
        best_day = t0
        best_val = infected_series[t0]
        for idx in range(t0 + 1, len(infected_series)):
            if infected_series[idx] > best_val:
                best_val = infected_series[idx]
                best_day = idx
        t1 = best_day

    if t1 <= t0 or t1 >= len(infected_series) or infected_series[t1] <= 0:
        return None

    return estimate_effective_r0_seir(
        i_start=float(infected_series[t0]),
        i_end=float(infected_series[t1]),
        days_elapsed=t1 - t0,
        sigma=sigma,
        gamma=gamma,
    )


def summarize_epidemic_series(
    cumulative_cases: Sequence[int],
    deaths: Sequence[int],
    population: int,
    *,
    active_infected: Sequence[int] | None = None,
    exposed: Sequence[int] | None = None,
    sigma: float | None = None,
    gamma: float | None = None,
) -> EpidemicSummary:
    """Calcula os indicadores consolidados do painel (RF21) a partir das séries.

    Funciona tanto para o fluxo de simulação (em que ``active_infected`` e
    ``exposed`` estão disponíveis) quanto para o fluxo real (em que existem
    apenas acumulados ``cumulative_cases`` e ``deaths``).
    """
    if population <= 0:
        raise ValueError(f"A população total deve ser positiva: {population}")
    n_days = len(cumulative_cases)
    if len(deaths) != n_days:
        raise ValueError("cumulative_cases e deaths devem ter o mesmo comprimento.")
    if active_infected is not None and len(active_infected) != n_days:
        raise ValueError("active_infected deve ter o mesmo comprimento de cumulative_cases.")
    if exposed is not None and len(exposed) != n_days:
        raise ValueError("exposed deve ter o mesmo comprimento de cumulative_cases.")

    if n_days == 0:
        return EpidemicSummary(
            peak_active_cases=0,
            peak_active_day=0,
            peak_daily_new_cases=0,
            peak_daily_new_cases_day=0,
            final_infected_count=0,
            final_infected_fraction=0.0,
            total_deaths=0,
            mortality_fraction=0.0,
            duration_days=0,
            effective_r0=None,
        )

    new_cases = daily_new_cases(cumulative_cases)
    peak_new = max(new_cases)
    peak_new_day = new_cases.index(peak_new)

    if active_infected is not None:
        peak_active = max(active_infected)
        peak_active_day = list(active_infected).index(peak_active)
    else:
        peak_active = peak_new
        peak_active_day = peak_new_day

    final_cases = int(cumulative_cases[-1])
    final_deaths = int(deaths[-1])

    # Duração: último dia com E + I > 0 (simulação) ou último dia com novos casos > 0 (fluxo real)
    duration = 0
    if active_infected is not None:
        for day in range(n_days):
            e_day = int(exposed[day]) if exposed is not None else 0
            if int(active_infected[day]) + e_day > 0:
                duration = day
    else:
        for day, nc in enumerate(new_cases):
            if nc > 0:
                duration = day

    eff_r0: float | None = None
    if sigma is not None and gamma is not None:
        series_for_r0 = active_infected if active_infected is not None else cumulative_cases
        eff_r0 = estimate_effective_r0_from_series(series_for_r0, sigma=sigma, gamma=gamma)

    return EpidemicSummary(
        peak_active_cases=int(peak_active),
        peak_active_day=peak_active_day,
        peak_daily_new_cases=int(peak_new),
        peak_daily_new_cases_day=peak_new_day,
        final_infected_count=final_cases,
        final_infected_fraction=final_cases / population,
        total_deaths=final_deaths,
        mortality_fraction=final_deaths / population,
        duration_days=duration,
        effective_r0=eff_r0,
    )
