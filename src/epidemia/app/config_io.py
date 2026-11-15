"""Serialização e desserialização de configurações de simulação (M5 — RF07).

Salva e carrega objetos ``SimulationConfig`` em formato JSON utilizando apenas
a biblioteca padrão, com validação rigorosa dos tipos e faixas de valores.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from epidemia.core.epidemic.parameters import SimulationConfig
from epidemia.core.errors import ParameterOutOfRangeError


def config_to_dict(config: SimulationConfig) -> dict[str, Any]:
    """Converte um ``SimulationConfig`` em dicionário serializável."""
    if not isinstance(config, SimulationConfig):
        raise ParameterOutOfRangeError("config deve ser uma instância de SimulationConfig.")

    return {
        "seed": config.seed,
        "scenario": config.scenario,
        "r0": float(config.r0),
        "exit_rate_gamma": float(config.exit_rate_gamma),
        "mortality": float(config.mortality),
        "incubation_days": float(config.incubation_days),
        "intervention_level": config.intervention_level,
        "patient_zero": list(config.patient_zero) if config.patient_zero is not None else None,
        "max_days": config.max_days,
        "day_zero_threshold_m": config.day_zero_threshold_m,
    }


def config_from_dict(data: Mapping[str, Any]) -> SimulationConfig:
    """Reconstrói e valida um ``SimulationConfig`` a partir de um mapeamento.

    Levanta ``ParameterOutOfRangeError`` se os dados forem inválidos ou violarem
    as restrições do modelo.
    """
    if not isinstance(data, Mapping):
        raise ParameterOutOfRangeError("Os dados de configuração devem ser um objeto/dicionário.")

    try:
        raw_seed = data.get("seed", 42)
        raw_scenario = data.get("scenario", "global")
        raw_r0 = data.get("r0", 2.5)
        raw_gamma = data.get("exit_rate_gamma", 0.1)
        raw_mortality = data.get("mortality", 0.02)
        raw_incubation = data.get("incubation_days", 4.0)
        raw_intervention = data.get("intervention_level", "baixo")
        raw_patient_zero = data.get("patient_zero")
        raw_max_days = data.get("max_days", 365)
        raw_threshold_m = data.get("day_zero_threshold_m", 1)

        patient_zero_tuple: tuple[int, ...] | None = None
        if raw_patient_zero is not None:
            if not isinstance(raw_patient_zero, (list, tuple)):
                raise ParameterOutOfRangeError("patient_zero deve ser uma lista de inteiros ou null.")
            patient_zero_tuple = tuple(int(x) for x in raw_patient_zero)

        return SimulationConfig(
            seed=int(raw_seed),
            scenario=str(raw_scenario),
            r0=float(raw_r0),
            exit_rate_gamma=float(raw_gamma),
            mortality=float(raw_mortality),
            incubation_days=float(raw_incubation),
            intervention_level=str(raw_intervention),
            patient_zero=patient_zero_tuple,
            max_days=int(raw_max_days),
            day_zero_threshold_m=int(raw_threshold_m),
        )
    except (ValueError, TypeError) as exc:
        raise ParameterOutOfRangeError(
            f"Erro ao processar valores de configuração: {exc}"
        ) from exc


def config_to_json(config: SimulationConfig, indent: int = 2) -> str:
    """Serializa um ``SimulationConfig`` em string JSON formatada."""
    data = config_to_dict(config)
    return json.dumps(data, indent=indent, ensure_ascii=False)


def config_from_json(json_str: str) -> SimulationConfig:
    """Desserializa e valida um ``SimulationConfig`` a partir de string JSON."""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ParameterOutOfRangeError(f"Arquivo JSON corrompido ou inválido: {exc}") from exc

    return config_from_dict(data)


def save_config(path: str | Path, config: SimulationConfig) -> None:
    """Grava o ``SimulationConfig`` no caminho especificado em formato JSON."""
    caminho = Path(path)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conteudo = config_to_json(config)
    caminho.write_text(conteudo, encoding="utf-8")


def load_config(path: str | Path) -> SimulationConfig:
    """Carrega e valida um ``SimulationConfig`` a partir de um arquivo JSON."""
    caminho = Path(path)
    if not caminho.exists():
        raise ParameterOutOfRangeError(f"Arquivo de configuração não encontrado: {path}")

    try:
        conteudo = caminho.read_text(encoding="utf-8")
    except OSError as exc:
        raise ParameterOutOfRangeError(
            f"Não foi possível ler o arquivo de configuração: {exc}"
        ) from exc

    return config_from_json(conteudo)
