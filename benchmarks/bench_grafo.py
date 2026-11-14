"""Benchmark de desempenho dos algoritmos de grafos e comparação com NetworkX (M2).

Executa medições de tempo (em milissegundos) e verificação de equivalência entre
os algoritmos próprios de ``epidemia.core.analysis`` e o ``networkx`` nos tamanhos
de referência da modelagem (1.000, 5.000, 10.000 e 50.000 vértices), além de
medir o custo por passo O(V + E) para apoiar a definição de N_total e d_medio.

Observação: ``benchmarks/`` é o único diretório em que ``networkx`` é permitido
(RNF01, RNF02 e RNF09).
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from epidemia.core.analysis import (
    average_clustering_coefficient,
    average_degree,
    betweenness_centrality,
    find_bridges_and_articulation_points,
    label_propagation_communities,
)

DEFAULT_SIZES = (1_000, 5_000, 10_000, 50_000)
QUICK_SIZES = (500, 1_000, 2_500)


class BenchmarkGraph:
    """Representação em lista de adjacência para o benchmark comparativo."""

    def __init__(self, num_vertices: int) -> None:
        self._num_vertices = num_vertices
        self._adj: list[list[int]] = [[] for _ in range(num_vertices)]

    @property
    def num_vertices(self) -> int:
        return self._num_vertices

    def add_edge(self, u: int, v: int) -> None:
        if u == v:
            return
        self._adj[u].append(v)
        self._adj[v].append(u)

    def neighbors(self, u: int) -> Iterator[int]:
        return iter(self._adj[u])


@dataclass(frozen=True)
class BenchmarkRow:
    """Linha de resultado comparativo para um tamanho de grafo e algoritmo."""

    num_vertices: int
    num_edges: int
    algorithm: str
    own_time_ms: float
    nx_time_ms: float
    speed_ratio: float
    verified: bool


def generate_test_graphs(
    num_vertices: int,
    avg_degree: int = 8,
    seed: int = 42,
) -> tuple[BenchmarkGraph, nx.Graph, int]:
    """Gera um grafo aleatório esparso determinístico nas duas estruturas."""
    rng = random.Random(seed + num_vertices)
    own_graph = BenchmarkGraph(num_vertices)
    nx_graph = nx.Graph()
    nx_graph.add_nodes_from(range(num_vertices))

    target_edges = (num_vertices * avg_degree) // 2
    edges_added: set[tuple[int, int]] = set()

    # Garante uma espinha dorsal com anel + pontes para exercitar Tarjan e agrupamento
    limit_ring = max(2, int(num_vertices * 0.9))
    for u in range(limit_ring - 1):
        edge = (u, u + 1)
        edges_added.add(edge)
        own_graph.add_edge(u, u + 1)
        nx_graph.add_edge(u, u + 1)

    while len(edges_added) < target_edges:
        u = rng.randrange(num_vertices)
        # Mistura conexões locais (triângulos) e conexões de longo alcance (rotas)
        if rng.random() < 0.65:
            offset = rng.randint(1, max(2, avg_degree))
            v = (u + offset) % num_vertices
        else:
            v = rng.randrange(num_vertices)
        if u == v:
            continue
        edge = (min(u, v), max(u, v))
        if edge not in edges_added:
            edges_added.add(edge)
            own_graph.add_edge(edge[0], edge[1])
            nx_graph.add_edge(edge[0], edge[1])

    return own_graph, nx_graph, len(edges_added)


def simulate_epidemic_step_traversal(
    graph: BenchmarkGraph,
    beta: float = 0.08,
    seed: int = 42,
) -> int:
    """Simula o custo O(V + E) de um passo diário de transmissão sobre o grafo."""
    rng = random.Random(seed)
    n = graph.num_vertices
    # 5% inicialmente infectados (estado 2) e demais suscetíveis (estado 0)
    states = bytearray(2 if rng.random() < 0.05 else 0 for _ in range(n))
    p_transmit = 1.0 - math.exp(-beta)
    new_exposed = 0

    for u in range(n):
        if states[u] == 2:
            for v in graph.neighbors(u):
                if states[v] == 0 and rng.random() < p_transmit:
                    new_exposed += 1
    return new_exposed


def run_benchmark_for_size(
    num_vertices: int,
    *,
    avg_degree: int = 8,
    betweenness_k: int = 25,
    include_exact_betweennessMaxN: int = 1_000,
    seed: int = 42,
) -> tuple[list[BenchmarkRow], float]:
    """Executa a bateria de algoritmos para um tamanho ``num_vertices``."""
    own_g, nx_g, num_edges = generate_test_graphs(
        num_vertices=num_vertices,
        avg_degree=avg_degree,
        seed=seed,
    )
    rows: list[BenchmarkRow] = []

    # 1. Grau médio
    t0 = time.perf_counter()
    deg_own = average_degree(own_g)
    t_own = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    deg_nx = sum(d for _, d in nx_g.degree()) / num_vertices
    t_nx = (time.perf_counter() - t0) * 1000.0
    rows.append(
        BenchmarkRow(
            num_vertices=num_vertices,
            num_edges=num_edges,
            algorithm="Grau médio O(V+E)",
            own_time_ms=t_own,
            nx_time_ms=t_nx,
            speed_ratio=t_own / max(t_nx, 1e-6),
            verified=math.isclose(deg_own, deg_nx, rel_tol=1e-9),
        )
    )

    # 2. Coeficiente de agrupamento médio global
    t0 = time.perf_counter()
    clust_own = average_clustering_coefficient(own_g)
    t_own = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    clust_nx = nx.average_clustering(nx_g)
    t_nx = (time.perf_counter() - t0) * 1000.0
    rows.append(
        BenchmarkRow(
            num_vertices=num_vertices,
            num_edges=num_edges,
            algorithm="Agrupamento médio O(sum k_v^2)",
            own_time_ms=t_own,
            nx_time_ms=t_nx,
            speed_ratio=t_own / max(t_nx, 1e-6),
            verified=math.isclose(clust_own, clust_nx, rel_tol=1e-6, abs_tol=1e-9),
        )
    )

    # 3. Tarjan: pontes e pontos de articulação
    t0 = time.perf_counter()
    tarjan_own = find_bridges_and_articulation_points(own_g)
    t_own = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    bridges_nx = sorted((min(u, v), max(u, v)) for u, v in nx.bridges(nx_g))
    art_nx = set(nx.articulation_points(nx_g))
    t_nx = (time.perf_counter() - t0) * 1000.0
    rows.append(
        BenchmarkRow(
            num_vertices=num_vertices,
            num_edges=num_edges,
            algorithm="Tarjan (pontes + artic.) O(V+E)",
            own_time_ms=t_own,
            nx_time_ms=t_nx,
            speed_ratio=t_own / max(t_nx, 1e-6),
            verified=(
                tarjan_own.bridges == bridges_nx and tarjan_own.articulation_points == art_nx
            ),
        )
    )

    # 4. Propagação de rótulos (comunidades)
    t0 = time.perf_counter()
    comm_own = label_propagation_communities(own_g, seed=seed, max_iterations=30)
    t_own = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    comm_nx = list(nx.algorithms.community.label_propagation_communities(nx_g))
    t_nx = (time.perf_counter() - t0) * 1000.0
    total_nodes_own = sum(len(c) for c in comm_own.communities)
    total_nodes_nx = sum(len(c) for c in comm_nx)
    rows.append(
        BenchmarkRow(
            num_vertices=num_vertices,
            num_edges=num_edges,
            algorithm="Propagação de rótulos (comun.)",
            own_time_ms=t_own,
            nx_time_ms=t_nx,
            speed_ratio=t_own / max(t_nx, 1e-6),
            verified=(total_nodes_own == num_vertices == total_nodes_nx),
        )
    )

    # 5. Intermediação aproximada por amostragem de fontes
    k_eff = min(betweenness_k, num_vertices)
    t0 = time.perf_counter()
    bc_own = betweenness_centrality(own_g, k=k_eff, seed=seed)
    t_own = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    bc_nx = nx.betweenness_centrality(nx_g, k=k_eff, seed=seed)
    t_nx = (time.perf_counter() - t0) * 1000.0
    rows.append(
        BenchmarkRow(
            num_vertices=num_vertices,
            num_edges=num_edges,
            algorithm=f"Intermediação aprox. (k={k_eff})",
            own_time_ms=t_own,
            nx_time_ms=t_nx,
            speed_ratio=t_own / max(t_nx, 1e-6),
            verified=(len(bc_own) == len(bc_nx) == num_vertices),
        )
    )

    # 6. Intermediação exata apenas até include_exact_betweennessMaxN (Modelagem, seção 8 / E4)
    if num_vertices <= include_exact_betweennessMaxN:
        t0 = time.perf_counter()
        bc_exact_own = betweenness_centrality(own_g, k=None)
        t_own = (time.perf_counter() - t0) * 1000.0

        t0 = time.perf_counter()
        bc_exact_nx = nx.betweenness_centrality(nx_g, k=None)
        t_nx = (time.perf_counter() - t0) * 1000.0
        max_diff = max(abs(bc_exact_own[u] - bc_exact_nx[u]) for u in range(num_vertices))
        rows.append(
            BenchmarkRow(
                num_vertices=num_vertices,
                num_edges=num_edges,
                algorithm="Intermediação exata O(V*E)",
                own_time_ms=t_own,
                nx_time_ms=t_nx,
                speed_ratio=t_own / max(t_nx, 1e-6),
                verified=(max_diff < 1e-7),
            )
        )

    # Passo diário de contágio O(V + E)
    t0 = time.perf_counter()
    simulate_epidemic_step_traversal(own_g, seed=seed)
    step_ms = (time.perf_counter() - t0) * 1000.0

    return rows, step_ms


def format_markdown_table(rows: list[BenchmarkRow]) -> str:
    """Formata os resultados em tabela Markdown pronta para o relatório."""
    header = (
        "| Vértices (V) | Arestas (E) | Algoritmo | Próprio (ms) | NetworkX (ms) "
        "| Razão (Próprio/NX) | Verificado |\n"
        "|---:|---:|---|---:|---:|---:|:---:|"
    )
    lines = [header]
    for r in rows:
        status = "OK" if r.verified else "FALHA"
        lines.append(
            f"| {r.num_vertices:,} | {r.num_edges:,} | {r.algorithm} | "
            f"{r.own_time_ms:.2f} | {r.nx_time_ms:.2f} | {r.speed_ratio:.2f}x | {status} |"
        )
    return "\n".join(lines)


def save_csv(rows: list[BenchmarkRow], path: Path) -> None:
    """Salva os resultados do benchmark em arquivo CSV."""
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "num_vertices",
                "num_edges",
                "algorithm",
                "own_time_ms",
                "nx_time_ms",
                "speed_ratio",
                "verified",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r.num_vertices,
                    r.num_edges,
                    r.algorithm,
                    f"{r.own_time_ms:.4f}",
                    f"{r.nx_time_ms:.4f}",
                    f"{r.speed_ratio:.4f}",
                    r.verified,
                ]
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark dos algoritmos de grafos (M2) vs. NetworkX."
    )
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=list(DEFAULT_SIZES),
        help="Tamanhos de grafo V a testar (padrão: 1000 5000 10000 50000).",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Executa uma versão rápida com grafos menores (500, 1000, 2500).",
    )
    parser.add_argument(
        "--avg-degree",
        type=int,
        default=8,
        help="Grau médio alvo d_barra (padrão: 8, dentro da faixa 6..10).",
    )
    parser.add_argument(
        "--betweenness-k",
        type=int,
        default=25,
        help="Número de fontes amostradas na intermediação aproximada (padrão: 25).",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Caminho opcional para exportar os resultados em CSV.",
    )
    args = parser.parse_args()

    sizes = list(QUICK_SIZES) if args.quick else list(args.sizes)
    all_rows: list[BenchmarkRow] = []
    step_times: list[tuple[int, int, float]] = []

    for v in sizes:
        rows, step_ms = run_benchmark_for_size(
            v,
            avg_degree=args.avg_degree,
            betweenness_k=args.betweenness_k,
        )
        all_rows.extend(rows)
        num_edges = rows[0].num_edges if rows else 0
        step_times.append((v, num_edges, step_ms))

    print("\n### Comparação de Desempenho: Implementação Própria vs. NetworkX\n")
    print(format_markdown_table(all_rows))

    print("\n### Tempo por Passo Diário de Simulação O(V + E)\n")
    print("| Vértices (V) | Arestas (E) | Tempo por passo (ms) |")
    print("|---:|---:|---:|")
    for v, e, ms in step_times:
        print(f"| {v:,} | {e:,} | {ms:.2f} |")

    if args.csv is not None:
        save_csv(all_rows, args.csv)
        print(f"\nResultados exportados para: {args.csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
