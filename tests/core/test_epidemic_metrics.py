"""Testes unitários das métricas epidemiológicas da série temporal (M2 — RF21)."""

from __future__ import annotations

import pytest

from epidemia.core.analysis import (
    FLAG_ISOLATED,
    FLAG_VACCINATED,
    STATE_D,
    STATE_E,
    STATE_I,
    STATE_R,
    STATE_S,
    daily_new_cases,
    estimate_effective_r0_from_series,
    estimate_effective_r0_seir,
    extract_compartment_counts,
    summarize_epidemic_series,
)


def test_extract_compartment_counts_distinguishes_vaccinated_and_isolated() -> None:
    # 6 vértices:
    # 0: S
    # 1: E
    # 2: I + isolado
    # 3: R natural
    # 4: R vacinado
    # 5: D
    day_bytes = bytearray(
        [
            STATE_S,
            STATE_E,
            STATE_I | FLAG_ISOLATED,
            STATE_R,
            STATE_R | FLAG_VACCINATED,
            STATE_D,
        ]
    )
    counts = extract_compartment_counts(day_bytes)
    assert counts.susceptible == 1
    assert counts.exposed == 1
    assert counts.infected == 1
    assert counts.recovered_natural == 1
    assert counts.recovered_vaccinated == 1
    assert counts.total_recovered == 2
    assert counts.deceased == 1
    assert counts.isolated == 1
    # Invariante S + E + I + R + D = N (Modelagem 11.2)
    assert counts.total_vertices == 6
    # Casos acumulados naturais = I + R_natural + D (exclui E e R_vacinado, Modelagem 7.1)
    assert counts.cumulative_cases == 3


def test_extract_compartment_counts_invalid_state_raises() -> None:
    with pytest.raises(ValueError):
        extract_compartment_counts(bytearray([7]))


def test_estimate_effective_r0_seir_h1n1_and_sars_calibration() -> None:
    # Caso de referência H1N1 da Modelagem (seção 6.1):
    # De 2.501 a 22.027 casos em 28 dias (08/05 a 05/06/2009),
    # incubação 1,4 dias (sigma = 1/1.4) e gamma = 0.22 -> R0 próximo de 1,5.
    sigma_h1n1 = 1.0 / 1.4
    gamma_h1n1 = 0.22
    r0_h1n1 = estimate_effective_r0_seir(
        i_start=2501,
        i_end=22027,
        days_elapsed=28,
        sigma=sigma_h1n1,
        gamma=gamma_h1n1,
    )
    assert r0_h1n1 == pytest.approx(1.5, rel=0.02)

    # Caso de referência SARS da Modelagem (seção 6.2):
    # De 1.634 a 3.186 casos em 14 dias (31/03 a 14/04/2003),
    # incubação 4,0 dias (sigma = 0.25) e gamma = 0.032 -> R0 próximo de 3,0.
    r0_sars = estimate_effective_r0_seir(
        i_start=1634,
        i_end=3186,
        days_elapsed=14,
        sigma=0.25,
        gamma=0.032,
    )
    assert r0_sars == pytest.approx(3.0, rel=0.02)


def test_estimate_effective_r0_validation() -> None:
    with pytest.raises(ValueError):
        estimate_effective_r0_seir(10, 20, 0, sigma=0.5, gamma=0.2)
    with pytest.raises(ValueError):
        estimate_effective_r0_seir(10, 20, 5, sigma=0.0, gamma=0.2)
    with pytest.raises(ValueError):
        estimate_effective_r0_seir(0, 20, 5, sigma=0.5, gamma=0.2)


def test_daily_new_cases_and_summarize_epidemic_series() -> None:
    # População N = 100
    # Dias 0..4:
    # Acumulados (I + R_nat + D): [2, 6, 18, 25, 25] -> novos por dia: [2, 4, 12, 7, 0]
    # Infectados ativos I:        [2, 5, 14, 10,  0] -> pico ativo = 14 no dia 2
    # Expostos E:                 [1, 3,  2,  0,  0] -> último dia com E+I > 0 é dia 3
    # Mortes D:                   [0, 0,  1,  2,  3]
    cumulative = [2, 6, 18, 25, 25]
    active = [2, 5, 14, 10, 0]
    exposed = [1, 3, 2, 0, 0]
    deaths = [0, 0, 1, 2, 3]

    assert daily_new_cases(cumulative) == [2, 4, 12, 7, 0]

    summary = summarize_epidemic_series(
        cumulative_cases=cumulative,
        deaths=deaths,
        population=100,
        active_infected=active,
        exposed=exposed,
        sigma=0.5,
        gamma=0.25,
    )
    assert summary.peak_active_cases == 14
    assert summary.peak_active_day == 2
    assert summary.peak_daily_new_cases == 12
    assert summary.peak_daily_new_cases_day == 2
    assert summary.final_infected_count == 25
    assert summary.final_infected_fraction == pytest.approx(0.25)
    assert summary.total_deaths == 3
    assert summary.mortality_fraction == pytest.approx(0.03)
    assert summary.duration_days == 3
    assert summary.effective_r0 is not None and summary.effective_r0 > 1.0


def test_summarize_empty_series() -> None:
    summary = summarize_epidemic_series([], [], population=100)
    assert summary.peak_active_cases == 0
    assert summary.final_infected_count == 0
    assert summary.effective_r0 is None
    assert estimate_effective_r0_from_series([5], sigma=0.5, gamma=0.2) is None
