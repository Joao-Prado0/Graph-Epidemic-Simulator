"""Testes unitários para a hierarquia de erros e derivação de sementes (Passo 1 — M1)."""

from __future__ import annotations

import pytest

from epidemia.core.errors import (
    EpidemiaError,
    GraphError,
    InvalidDatasetError,
    InvalidEdgeError,
    ParameterOutOfRangeError,
    VertexNotFoundError,
)
from epidemia.core.seeds import (
    KNOWN_SUBSYSTEMS,
    SUBSYSTEM_ISOLATION,
    SUBSYSTEM_NETWORK,
    SeedBook,
    derive_subsystem_seed,
)


def test_hierarquia_de_excecoes_do_dominio() -> None:
    """Todas as exceções específicas devem herdar de EpidemiaError."""
    assert issubclass(ParameterOutOfRangeError, (EpidemiaError, ValueError))
    assert issubclass(GraphError, EpidemiaError)
    assert issubclass(VertexNotFoundError, (GraphError, KeyError))
    assert issubclass(InvalidEdgeError, (GraphError, ValueError))
    assert issubclass(InvalidDatasetError, EpidemiaError)


def test_derivacao_de_semente_eh_deterministica_e_64_bits() -> None:
    """Mesma semente global e mesmo subsistema produzem exatamente o mesmo inteiro."""
    s1 = derive_subsystem_seed(42, "network")
    s2 = derive_subsystem_seed(42, "  NETWORK ")
    assert s1 == s2
    assert 0 <= s1 < 2**64
    # Valor exato esperado do SHA-256("42:network")[:8] para garantir estabilidade entre máquinas
    assert s1 == 14426007215900259743


def test_subsistemas_distintos_geram_sementes_distintas() -> None:
    """Todos os subsistemas oficiais possuem sementes independentes para a mesma seed global."""
    book = SeedBook(global_seed=12345)
    seeds = {book.seed_for(sub) for sub in KNOWN_SUBSYSTEMS}
    assert len(seeds) == len(KNOWN_SUBSYSTEMS)


def test_isolamento_entre_geradores_de_subsistemas() -> None:
    """Consumir números no gerador de isolamento não afeta o gerador da rede."""
    book_a = SeedBook(global_seed=99)
    book_b = SeedBook(global_seed=99)

    rng_net_a = book_a.rng(SUBSYSTEM_NETWORK)
    rng_iso_a = book_a.rng(SUBSYSTEM_ISOLATION)
    # Consome 500 sorteios no subsistema de isolamento
    for _ in range(500):
        rng_iso_a.random()

    rng_net_b = book_b.rng(SUBSYSTEM_NETWORK)
    seq_a = [rng_net_a.random() for _ in range(20)]
    seq_b = [rng_net_b.random() for _ in range(20)]
    assert seq_a == seq_b


@pytest.mark.parametrize("invalid_seed", [True, False, 3.14, "42", None])
def test_semente_global_invalida_levanta_erro(invalid_seed: object) -> None:
    """Sementes não inteiras (incluindo bool) devem levantar ParameterOutOfRangeError."""
    with pytest.raises(ParameterOutOfRangeError):
        SeedBook(global_seed=invalid_seed)  # type: ignore[arg-type]


def test_subsistema_vazio_levanta_erro() -> None:
    """Subsistema em branco deve levantar ParameterOutOfRangeError."""
    book = SeedBook(42)
    with pytest.raises(ParameterOutOfRangeError):
        book.seed_for("   ")
