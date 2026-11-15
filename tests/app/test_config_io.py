"""Testes unitários de salvar e carregar configuração (RF07)."""

from __future__ import annotations

import pytest

from epidemia.app.config_io import (
    config_from_dict,
    config_from_json,
    load_config,
    save_config,
)
from epidemia.core.epidemic.parameters import SimulationConfig
from epidemia.core.errors import ParameterOutOfRangeError


def test_config_io_roundtrip(tmp_path):
    """Verifica que salvar e carregar uma configuração restaura o objeto idêntico."""
    orig = SimulationConfig(
        seed=123,
        scenario="global",
        r0=3.2,
        exit_rate_gamma=0.15,
        mortality=0.03,
        incubation_days=5.0,
        intervention_level="medio",
        patient_zero=(1, 5, 12),
        max_days=180,
        day_zero_threshold_m=2,
    )

    arquivo = tmp_path / "config.json"
    save_config(arquivo, orig)

    assert arquivo.exists()
    carregado = load_config(arquivo)
    assert carregado == orig


def test_config_from_dict_defaults():
    """Verifica que chaves omitidas usam os padrões do SimulationConfig."""
    cfg = config_from_dict({"r0": 1.8, "seed": 99})
    assert cfg.r0 == 1.8
    assert cfg.seed == 99
    assert cfg.scenario == "global"
    assert cfg.exit_rate_gamma == 0.1
    assert cfg.intervention_level == "baixo"


def test_config_invalid_json_raises_error(tmp_path):
    """Verifica que JSON com sintaxe inválida levanta ParameterOutOfRangeError."""
    arquivo = tmp_path / "malformed.json"
    arquivo.write_text("{esta_invalido: 123", encoding="utf-8")

    with pytest.raises(ParameterOutOfRangeError, match="Arquivo JSON corrompido"):
        load_config(arquivo)


def test_config_non_dict_raises_error():
    """Verifica que JSON contendo lista ou escalar levanta ParameterOutOfRangeError."""
    with pytest.raises(ParameterOutOfRangeError, match="devem ser um objeto/dicionário"):
        config_from_json("[1, 2, 3]")


def test_config_invalid_parameters_raise_error():
    """Verifica que parâmetros fora da faixa levantam ParameterOutOfRangeError."""
    with pytest.raises(ParameterOutOfRangeError):
        config_from_dict({"r0": -1.0})

    with pytest.raises(ParameterOutOfRangeError):
        config_from_dict({"intervention_level": "desconhecido"})

    with pytest.raises(ParameterOutOfRangeError):
        config_from_dict({"patient_zero": "não-é-lista"})


def test_config_file_not_found(tmp_path):
    """Verifica erro quando arquivo não existe."""
    inexistente = tmp_path / "nao_existe.json"
    with pytest.raises(ParameterOutOfRangeError, match="não encontrado"):
        load_config(inexistente)


def test_config_salva_e_carregada_produz_mesmo_buffer_hash(tmp_path):
    """Verifica o critério de aceitação: config salva e carregada produz o mesmo buffer hash."""
    import hashlib

    from epidemia.app.simulation_session import SimulationSession
    from tests.fixtures import create_synthetic_world

    orig_cfg = SimulationConfig(
        seed=777,
        scenario="global",
        r0=2.6,
        exit_rate_gamma=0.18,
        mortality=0.03,
        incubation_days=3.5,
        intervention_level="baixo",
        max_days=20,
    )

    # 1. Executa com config original
    world_a = create_synthetic_world(total_vertices=60, seed=777)
    session_a = SimulationSession(world_a)
    session_a.configure(orig_cfg)
    session_a.start()
    for _ in range(8):
        session_a.run_day()

    timeline_a = session_a.timeline()
    hasher_a = hashlib.sha256()
    for d in range(timeline_a.days_available):
        hasher_a.update(timeline_a.vertex_states(d))
    hash_a = hasher_a.hexdigest()

    # 2. Salva e recarrega
    cfg_file = tmp_path / "saved_cfg.json"
    save_config(cfg_file, orig_cfg)
    loaded_cfg = load_config(cfg_file)

    # 3. Executa com config carregada
    world_b = create_synthetic_world(total_vertices=60, seed=777)
    session_b = SimulationSession(world_b)
    session_b.configure(loaded_cfg)
    session_b.start()
    for _ in range(8):
        session_b.run_day()

    timeline_b = session_b.timeline()
    hasher_b = hashlib.sha256()
    for d in range(timeline_b.days_available):
        hasher_b.update(timeline_b.vertex_states(d))
    hash_b = hasher_b.hexdigest()

    assert hash_a == hash_b
