import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]

# Liberado pelo professor em 03/11/2026 (Decisão D17).
NUMPY_LIBERADO = True


def _arquivos_que_importam(modulo: str) -> list[Path]:
    padrao = re.compile(rf"^\s*(import|from)\s+{modulo}\b", re.MULTILINE)
    return [
        arquivo
        for arquivo in (RAIZ / "src").rglob("*.py")
        if padrao.search(arquivo.read_text(encoding="utf-8"))
    ]


def test_networkx_nao_aparece_em_src():
    assert _arquivos_que_importam("networkx") == []


@pytest.mark.skipif(NUMPY_LIBERADO, reason="NumPy liberado pelo professor")
def test_numpy_nao_aparece_em_src():
    assert _arquivos_que_importam("numpy") == []
