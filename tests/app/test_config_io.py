"""Testes unitários de salvar e carregar configuração (RF07)."""

from __future__ import annotations

import pytest

from epidemia.app.config_io import (
    config_from_dict,
    config_from_json,
    config_to_dict,
    config_to_json,
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
