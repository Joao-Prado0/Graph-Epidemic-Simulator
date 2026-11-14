"""Derivação determinística de sementes aleatórias por subsistema
Garante que cada subsistema estocástico (rede, paciente zero, isolamento,
vacinação, propagação de rótulos e calibração de beta) possua uma sequência
pseudoaleatória própria, reproduzível entre diferentes execuções do Python e
isolada dos demais subsistemas.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Final

from epidemia.core.errors import ParameterOutOfRangeError

SUBSYSTEM_NETWORK: Final[str] = "network"
SUBSYSTEM_PATIENT_ZERO: Final[str] = "patient_zero"
SUBSYSTEM_ISOLATION: Final[str] = "isolation"
SUBSYSTEM_VACCINATION: Final[str] = "vaccination"
SUBSYSTEM_LABELS: Final[str] = "labels"
SUBSYSTEM_CALIBRATION: Final[str] = "calibration"

KNOWN_SUBSYSTEMS: Final[frozenset[str]] = frozenset(
    {
        SUBSYSTEM_NETWORK,
        SUBSYSTEM_PATIENT_ZERO,
        SUBSYSTEM_ISOLATION,
        SUBSYSTEM_VACCINATION,
        SUBSYSTEM_LABELS,
        SUBSYSTEM_CALIBRATION,
    }
)


def derive_subsystem_seed(global_seed: int, subsystem: str) -> int:
    """Deriva uma semente inteira de 64 bits de forma determinística via SHA-256.
    Nunca utiliza ``hash()`` embutido do Python, pois este sofre randomização
    por sessão do interpretador (PYTHONHASHSEED).
    Complexidade: O(1).
    """

    if not isinstance(global_seed, int) or isinstance(global_seed, bool):
        raise ParameterOutOfRangeError(
            f"A semente global deve ser um inteiro (recebido: {global_seed!r})."
        )

    normalized = subsystem.strip().lower()
    if not normalized:
        raise ParameterOutOfRangeError("O nome do subsistema não pode ser vazio.")

    payload = f"{global_seed}:{normalized}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


@dataclass(frozen=True)
class SeedBook:
    """Catálogo imutável de sementes e geradores pseudoaleatórios por subsistema."""

    global_seed: int = 42

    def __post_init__(self) -> None:
        if not isinstance(self.global_seed, int) or isinstance(self.global_seed, bool):
            raise ParameterOutOfRangeError(
                f"global_seed deve ser um inteiro (recebido: {self.global_seed!r})."
            )

    def seed_for(self, subsystem: str) -> int:
        """Retorna a semente inteira de 64 bits derivada para ``subsystem``."""
        return derive_subsystem_seed(self.global_seed, subsystem)
    derive_seed = derive_subsystem_seed

    def rng(self, subsystem: str) -> random.Random:
        """Cria uma nova instância isolada de ``random.Random`` para ``subsystem``."""
        return random.Random(self.seed_for(subsystem))
