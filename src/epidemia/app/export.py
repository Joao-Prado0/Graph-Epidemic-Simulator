"""Exportação de dados da linha do tempo da simulação (M5 — RF08).

Gera arquivos CSV consolidados a partir de um objeto ``Timeline``, com exatamente
uma linha por dia gravado e colunas para cada compartimento:
S, E, I, R natural, R vacinado, D, isolados e total.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

from epidemia.core.analysis.epidemic_metrics import extract_compartment_counts
from epidemia.core.errors import ParameterOutOfRangeError

if TYPE_CHECKING:
    from epidemia.core.timeline.protocol import Timeline

CSV_HEADER = [
    "dia",
    "S",
    "E",
    "I",
    "R_natural",
    "R_vacinado",
    "D",
    "isolados",
    "total",
]


def export_timeline_csv(
    timeline: Timeline,
    path: str | Path,
    *,
    delimiter: str = ",",
) -> int:
    """Exporta os dias já gravados do ``Timeline`` para um arquivo CSV.

    Cada linha representa um dia de simulação (0 .. days_available - 1) com:
    - dia: índice do dia (0, 1, 2, ...)
    - S: suscetíveis
    - E: expostos
    - I: infectados ativos
    - R_natural: recuperados naturalmente (sem vacina)
    - R_vacinado: recuperados imunizados por vacina
    - D: óbitos acumulados
    - isolados: indivíduos atualmente isolados
    - total: soma de todos os compartimentos (invariante N)

    Retorna o número de dias exportados.
    """
    if timeline is None:
        raise ParameterOutOfRangeError("timeline não pode ser None.")

    caminho = Path(path)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    n_dias = timeline.days_available
    linhas_exportadas = 0

    with caminho.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(CSV_HEADER)

        for dia in range(n_dias):
            v_bytes = timeline.vertex_states(dia)
            if v_bytes is not None:
                counts = extract_compartment_counts(v_bytes)
                writer.writerow(
                    [
                        dia,
                        counts.susceptible,
                        counts.exposed,
                        counts.infected,
                        counts.recovered_natural,
                        counts.recovered_vaccinated,
                        counts.deceased,
                        counts.isolated,
                        counts.total_vertices,
                    ]
                )
            else:
                # Fallback para timelines sem bytes de vértice individuais (agregado)
                country_counts = timeline.country_counts(dia)
                tot_s = sum(c.susceptible for c in country_counts)
                tot_i = sum(c.active for c in country_counts)
                tot_rec = sum(c.recovered for c in country_counts)
                tot_d = sum(c.deaths for c in country_counts)
                tot_e = 0
                tot_r_nat = tot_rec
                tot_r_vac = 0
                tot_iso = 0
                total = tot_s + tot_i + tot_rec + tot_d
                writer.writerow(
                    [dia, tot_s, tot_e, tot_i, tot_r_nat, tot_r_vac, tot_d, tot_iso, total]
                )

            linhas_exportadas += 1

    return linhas_exportadas
