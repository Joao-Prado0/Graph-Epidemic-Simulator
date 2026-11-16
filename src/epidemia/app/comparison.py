"""Comparação científica entre curvas simuladas e séries pandêmicas reais (M4 — RF14).

Implementa a avaliação quantitativa entre o modelo estocástico SEIRD e as séries
históricas (Modelagem 7 / Responsabilidades M4):
- Alinhamento temporal pelo Dia 0 a partir de limiar de M vértices / casos equivalentes;
- Normalização de grandezas por fração da população do cenário ou do país;
- Grandezas comparadas: casos acumulados (I + R_natural + D), óbitos (D) e recuperados (R no SARS);
- Métricas:
  1. Erro Quadrático Médio (MSE e RMSE) das trajetórias acumuladas no intervalo comum;
  2. Diferença no dia do pico de novos casos diários (Δt_pico = t_pico,sim - t_pico,real);
  3. Diferença na magnitude do pico de novos casos diários;
  4. Diferença no tamanho final da epidemia (ΔS_inf = S_inf,sim - S_inf,real).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from epidemia.core.analysis.epidemic_metrics import extract_compartment_counts
from epidemia.core.errors import ParameterOutOfRangeError

if TYPE_CHECKING:
    from epidemia.core.timeline.protocol import Timeline

__all__ = [
    "ComparisonResult",
    "compare_simulation_to_real",
]


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """Resultado estruturado da comparação científica simulado vs real (RF14)."""

    aligned_days: int
    sim_day_zero: int
    real_day_zero: int
    cases_mse: float
    cases_rmse: float
    deaths_mse: float
    deaths_rmse: float
    recovered_mse: float | None
    recovered_rmse: float | None
    peak_day_difference: int
    sim_peak_day: int
    real_peak_day: int
    peak_magnitude_difference: float
    sim_peak_magnitude: float
    real_peak_magnitude: float
    final_size_difference: float
    sim_final_size: float
    real_final_size: float
    country_code: str | None = None

    def formatted_summary(self) -> str:
        """Sumário conciso para exibição em painel ou barra de status."""
        if self.aligned_days <= 0:
            return "Comparação RF14: Sem intervalo comum de dados alinhados."

        delta_peak_sign = "+" if self.peak_day_difference > 0 else ""
        delta_peak_str = f"{delta_peak_sign}{self.peak_day_difference}d"

        delta_size_sign = "+" if self.final_size_difference > 0 else ""
        delta_size_str = f"{delta_size_sign}{self.final_size_difference * 100:.2f}%"

        parts = [
            f"RMSE casos: {self.cases_rmse * 100:.2f}%",
            f"Δ dia pico: {delta_peak_str}",
            f"Δ tamanho final: {delta_size_str}",
        ]
        if self.recovered_rmse is not None:
            parts.append(f"RMSE rec: {self.recovered_rmse * 100:.2f}%")

        scope_str = f"[{self.country_code}] " if self.country_code else "[Global] "
        return scope_str + " | ".join(parts)

    def detailed_report(self) -> str:
        """Relatório analítico completo para inclusão em documentos técnicos."""
        rec_rmse_val = self.recovered_rmse * 100 if self.recovered_rmse is not None else 0.0
        rec_mse_val = self.recovered_mse if self.recovered_mse is not None else 0.0
        rec_str = (
            f"  - RMSE Recuperados: {rec_rmse_val:.4f}% (MSE: {rec_mse_val:.6e})\n"
            if self.recovered_rmse is not None
            else "  - Recuperados: Não disponíveis nesta fonte histórica.\n"
        )
        return (
            f"=== Relatório de Comparação Simulado × Real (RF14) ===\n"
            f"Âmbito: {self.country_code or 'Global (todos os países)'}\n"
            f"Dias de sobreposição: {self.aligned_days} dias\n"
            f"Dia 0 (Simulação): d={self.sim_day_zero} | Dia 0 (Real): d={self.real_day_zero}\n"
            f"\n1. Erro de Trajetória Acumulada (fração da população):\n"
            f"  - RMSE Casos Acumulados: {self.cases_rmse * 100:.4f}% (MSE: {self.cases_mse:.6e})\n"
            f"  - RMSE Óbitos: {self.deaths_rmse * 100:.4f}% (MSE: {self.deaths_mse:.6e})\n"
            f"{rec_str}"
            f"\n2. Dinâmica do Pico de Novos Casos Diários:\n"
            f"  - Dia do pico (Simulado): dia {self.sim_peak_day} pós-Dia 0\n"
            f"  - Dia do pico (Real): dia {self.real_peak_day} pós-Dia 0\n"
            f"  - Diferença de tempo (Δt_pico): {self.peak_day_difference:+d} dias\n"
            f"  - Taxa máx diária (Simulada): {self.sim_peak_magnitude * 100:.3f}%/dia\n"
            f"  - Taxa máx diária (Real): {self.real_peak_magnitude * 100:.3f}%/dia\n"
            f"  - Diferença de magnitude: {self.peak_magnitude_difference * 100:+.3f}%/dia\n"
            f"\n3. Tamanho Final da Epidemia:\n"
            f"  - Fração final infectada (Simulada): {self.sim_final_size * 100:.2f}%\n"
            f"  - Fração final infectada (Real): {self.real_final_size * 100:.2f}%\n"
            f"  - Diferença no tamanho final (ΔS_inf): {self.final_size_difference * 100:+.2f}%\n"
        )


def _extract_timeline_series(
    timeline: Timeline,
    country_code: str | None = None,
) -> tuple[list[int], list[int], list[int | None], int]:
    """Extrai séries de casos, mortes, recuperados e a população de referência."""
    n_days = timeline.days_available
    cum_cases: list[int] = []
    deaths: list[int] = []
    recovered: list[int | None] = []

    target_idx: int | None = None
    if country_code is not None:
        code_clean = country_code.strip().upper()
        for idx, c in enumerate(timeline.countries):
            if c.iso3 == code_clean:
                target_idx = idx
                break
        if target_idx is None:
            raise ParameterOutOfRangeError(
                f"País {country_code!r} não encontrado na linha do tempo."
            )

    has_states = n_days > 0 and timeline.vertex_states(0) is not None

    if country_code is None and has_states:
        # Extração otimizada global direto do StateBuffer
        for d in range(n_days):
            raw = timeline.vertex_states(d)
            assert raw is not None
            counts = extract_compartment_counts(raw)
            cum_cases.append(counts.cumulative_cases)
            deaths.append(counts.deceased)
            recovered.append(counts.recovered_natural)
        pop = timeline.num_vertices
    else:
        # Extração via country_counts (funciona tanto para simulação quanto real)
        for d in range(n_days):
            cc = timeline.country_counts(d)
            if target_idx is not None:
                c = cc[target_idx]
                cum_cases.append(c.cumulative_cases)
                deaths.append(c.deaths)
                recovered.append(c.recovered)
            else:
                tot_c = sum(c.cumulative_cases for c in cc)
                tot_d = sum(c.deaths for c in cc)
                tot_r = sum(c.recovered for c in cc)
                cum_cases.append(tot_c)
                deaths.append(tot_d)
                recovered.append(tot_r)

        if target_idx is not None:
            c_info = timeline.countries[target_idx]
            pop = c_info.population if c_info.population > 0 else timeline.num_vertices
        else:
            tot_pop = sum(c.population for c in timeline.countries)
            pop = tot_pop if tot_pop > 0 else timeline.num_vertices

    return cum_cases, deaths, recovered, max(1, pop)


def _find_day_zero(series: list[int], threshold: int) -> int:
    """Encontra o primeiro índice de dia onde a série atinge ou supera o limiar."""
    for d, val in enumerate(series):
        if val >= threshold:
            return d
    return 0


def compare_simulation_to_real(
    sim_timeline: Timeline,
    real_timeline: Timeline,
    *,
    country: str | None = None,
    threshold_m: int = 1,
) -> ComparisonResult:
    """Compara as trajetórias do modelo simulado contra a pandemia real (RF14).

    Parameters
    ----------
    sim_timeline : Timeline
        Linha do tempo gerada pela simulação SEIRD (M3).
    real_timeline : Timeline
        Linha do tempo baseada na série de pandemia histórica (M4).
    country : str | None, optional
        Código ISO3 para comparação específica de um país. Se None, avalia o
        cenário agregado global.
    threshold_m : int, optional
        Limiar de vértices para detecção do Dia 0 na simulação (default M = 1).
        No fluxo real, é convertido proporcionalmente à população do cenário.

    Returns
    -------
    ComparisonResult
        Objeto com métricas de erro MSE/RMSE, defasagem de pico e tamanho final.
    """
    if sim_timeline is None or real_timeline is None:
        raise ParameterOutOfRangeError("As duas timelines devem ser fornecidas para comparar.")

    sim_cases, sim_deaths, sim_rec, sim_pop = _extract_timeline_series(sim_timeline, country)
    real_cases, real_deaths, real_rec, real_pop = _extract_timeline_series(real_timeline, country)

    if not sim_cases or not real_cases:
        return ComparisonResult(
            aligned_days=0,
            sim_day_zero=0,
            real_day_zero=0,
            cases_mse=0.0,
            cases_rmse=0.0,
            deaths_mse=0.0,
            deaths_rmse=0.0,
            recovered_mse=None,
            recovered_rmse=None,
            peak_day_difference=0,
            sim_peak_day=0,
            real_peak_day=0,
            peak_magnitude_difference=0.0,
            sim_peak_magnitude=0.0,
            real_peak_magnitude=0.0,
            final_size_difference=0.0,
            sim_final_size=0.0,
            real_final_size=0.0,
            country_code=country,
        )

    # 1. Alinhamento pelo Dia 0
    sim_threshold = max(1, threshold_m)
    # Converte limiar de vértices para casos reais proporcionais à população
    real_threshold = max(1, round(threshold_m * (real_pop / sim_pop)))

    d0_sim = _find_day_zero(sim_cases, sim_threshold)
    d0_real = _find_day_zero(real_cases, real_threshold)

    # 2. Janela comum de sobreposição temporal
    sim_avail = len(sim_cases) - d0_sim
    real_avail = len(real_cases) - d0_real
    t_common = min(sim_avail, real_avail)

    if t_common <= 0:
        return ComparisonResult(
            aligned_days=0,
            sim_day_zero=d0_sim,
            real_day_zero=d0_real,
            cases_mse=0.0,
            cases_rmse=0.0,
            deaths_mse=0.0,
            deaths_rmse=0.0,
            recovered_mse=None,
            recovered_rmse=None,
            peak_day_difference=0,
            sim_peak_day=0,
            real_peak_day=0,
            peak_magnitude_difference=0.0,
            sim_peak_magnitude=0.0,
            real_peak_magnitude=0.0,
            final_size_difference=0.0,
            sim_final_size=0.0,
            real_final_size=0.0,
            country_code=country,
        )

    # 3. Trajetórias normalizadas no intervalo comum
    norm_sim_cases = [sim_cases[d0_sim + k] / sim_pop for k in range(t_common)]
    norm_real_cases = [real_cases[d0_real + k] / real_pop for k in range(t_common)]

    norm_sim_deaths = [sim_deaths[d0_sim + k] / sim_pop for k in range(t_common)]
    norm_real_deaths = [real_deaths[d0_real + k] / real_pop for k in range(t_common)]

    # MSE e RMSE de casos e mortes
    cases_mse = (
        sum((s - r) ** 2 for s, r in zip(norm_sim_cases, norm_real_cases, strict=False))
        / t_common
    )
    cases_rmse = math.sqrt(cases_mse)

    deaths_mse = (
        sum((s - r) ** 2 for s, r in zip(norm_sim_deaths, norm_real_deaths, strict=False))
        / t_common
    )
    deaths_rmse = math.sqrt(deaths_mse)

    # Recuperados (opcional, quando disponível na série real)
    has_real_rec = any(r is not None and r > 0 for r in real_rec)
    recovered_mse: float | None = None
    recovered_rmse: float | None = None
    if has_real_rec:
        norm_sim_rec = [
            (sim_rec[d0_sim + k] or 0) / sim_pop for k in range(t_common)
        ]
        norm_real_rec = [
            (real_rec[d0_real + k] or 0) / real_pop for k in range(t_common)
        ]
        recovered_mse = (
            sum(
                (s - r) ** 2
                for s, r in zip(norm_sim_rec, norm_real_rec, strict=False)
            )
            / t_common
        )
        recovered_rmse = math.sqrt(recovered_mse)

    # 4. Dinâmica do pico de novos casos diários
    daily_new_sim = [norm_sim_cases[0]]
    daily_new_real = [norm_real_cases[0]]
    for k in range(1, t_common):
        daily_new_sim.append(max(0.0, norm_sim_cases[k] - norm_sim_cases[k - 1]))
        daily_new_real.append(max(0.0, norm_real_cases[k] - norm_real_cases[k - 1]))

    sim_peak_day = max(range(t_common), key=lambda k: daily_new_sim[k])
    real_peak_day = max(range(t_common), key=lambda k: daily_new_real[k])
    sim_peak_mag = daily_new_sim[sim_peak_day]
    real_peak_mag = daily_new_real[real_peak_day]

    peak_day_diff = sim_peak_day - real_peak_day
    peak_mag_diff = sim_peak_mag - real_peak_mag

    # 5. Tamanho final da epidemia no encerramento da sobreposição
    sim_final = norm_sim_cases[-1]
    real_final = norm_real_cases[-1]
    final_diff = sim_final - real_final

    return ComparisonResult(
        aligned_days=t_common,
        sim_day_zero=d0_sim,
        real_day_zero=d0_real,
        cases_mse=cases_mse,
        cases_rmse=cases_rmse,
        deaths_mse=deaths_mse,
        deaths_rmse=deaths_rmse,
        recovered_mse=recovered_mse,
        recovered_rmse=recovered_rmse,
        peak_day_difference=peak_day_diff,
        sim_peak_day=sim_peak_day,
        real_peak_day=real_peak_day,
        peak_magnitude_difference=peak_mag_diff,
        sim_peak_magnitude=sim_peak_mag,
        real_peak_magnitude=real_peak_mag,
        final_size_difference=final_diff,
        sim_final_size=sim_final,
        real_final_size=real_final,
        country_code=country,
    )
