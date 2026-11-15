"""Isolamento e vacinação automáticos (M3 — RF05 e RF06).

Isolamento: cada vértice I tem uma probabilidade diária de se isolar por alguns
dias. O isolamento liga a máscara do ``Graph`` (``set_vertex_isolated``), sem
alterar a estrutura; ao fim do prazo o vértice volta com as mesmas arestas (C3).

Vacinação: a partir do dia de início, uma fração diária dos suscetíveis é
vacinada; com probabilidade igual à eficácia o vértice vai para R com a flag de
vacinado, e senão permanece S (Modelagem 4.5).

As funções alteram os arrays do motor no lugar e recebem o gerador aleatório de
cada subsistema (``SeedBook.rng("isolation")`` e ``SeedBook.rng("vaccination")``).
Os vértices são percorridos em ordem de índice, para o resultado ser determinístico.
"""

from __future__ import annotations

import random
from collections.abc import MutableSequence, Sequence

from epidemia.core.analysis.epidemic_metrics import STATE_I, STATE_R, STATE_S
from epidemia.core.epidemic.parameters import InterventionParams
from epidemia.core.errors import ParameterOutOfRangeError
from epidemia.core.graph.graph import Graph


def release_isolation(graph: Graph, isolation_remaining: MutableSequence[int], u: int) -> None:
    """Encerra o isolamento de ``u`` (usado também quando o vértice morre). O(1)."""
    isolation_remaining[u] = 0
    graph.set_vertex_isolated(u, False)


def apply_daily_isolation(
    graph: Graph,
    states: Sequence[int],
    isolation_remaining: MutableSequence[int],
    params: InterventionParams,
    rng: random.Random,
) -> int:
    """Avança o isolamento em um dia e devolve quantos vértices se isolaram agora.

    1. Desconta um dia de quem está isolado; ao chegar a zero o vértice volta com as
       mesmas arestas e não pode se isolar de novo no mesmo dia.
    2. Cada vértice I não isolado se isola com ``isolation_daily_prob``, por
       ``isolation_duration_days`` dias.

    Complexidade: O(V).
    """
    if len(isolation_remaining) != len(states):
        raise ParameterOutOfRangeError("isolation_remaining e states devem ter o mesmo tamanho.")

    released_today: set[int] = set()
    for u, remaining in enumerate(isolation_remaining):
        if remaining > 0:
            isolation_remaining[u] = remaining - 1
            if remaining == 1:
                graph.set_vertex_isolated(u, False)
                released_today.add(u)

    if params.isolation_daily_prob <= 0.0 or params.isolation_duration_days <= 0:
        return 0

    newly_isolated = 0
    for u, state in enumerate(states):
        if state != STATE_I or isolation_remaining[u] > 0 or u in released_today:
            continue
        if rng.random() < params.isolation_daily_prob:
            isolation_remaining[u] = params.isolation_duration_days
            graph.set_vertex_isolated(u, True)
            newly_isolated += 1
    return newly_isolated


def apply_daily_vaccination(
    states: MutableSequence[int],
    vaccinated: MutableSequence[int],
    current_day: int,
    params: InterventionParams,
    rng: random.Random,
) -> int:
    """Vacina suscetíveis no dia ``current_day`` e devolve quantos foram imunizados.

    Antes de ``vaccination_start_day`` não faz nada. Depois, cada vértice S recebe a
    dose com ``vaccination_daily_fraction`` e a vacina funciona com
    ``vaccine_efficacy``: vai para R com ``vaccinated[u] = 1``. Como as duas
    escolhas são independentes, usa-se um único sorteio com a probabilidade
    ``fração * eficácia`` (mesma distribuição, metade do custo). Quem recebe a dose
    e a vacina falha continua S.

    Complexidade: O(V).
    """
    if len(vaccinated) != len(states):
        raise ParameterOutOfRangeError("vaccinated e states devem ter o mesmo tamanho.")
    if current_day < params.vaccination_start_day or params.vaccination_daily_fraction <= 0.0:
        return 0

    p_immunized = params.vaccination_daily_fraction * params.vaccine_efficacy
    newly_immunized = 0
    for u, state in enumerate(states):
        if state == STATE_S and rng.random() < p_immunized:
            states[u] = STATE_R
            vaccinated[u] = 1
            newly_immunized += 1
    return newly_immunized
