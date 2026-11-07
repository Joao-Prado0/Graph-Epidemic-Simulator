"""Testes estáticos das regras de dependência entre camadas (Arquitetura, seção 5).

Regras verificadas via AST:
- `core` não importa `PySide6`, `pyqtgraph`, `pandas`, `networkx`, nem nada de
  `app`, `world`, `datasets` ou `ui`.
- `datasets` não importa `PySide6`, `pyqtgraph`, `pandas`, `networkx`, nem nada de
  `core`, `world`, `app` ou `ui`.
- `world` não importa `PySide6`, `pyqtgraph`, `pandas`, `networkx`, nem nada de
  `app` ou `ui`.
- `app` não importa `ui`, `PySide6`, `pyqtgraph`, `pandas` nem `networkx`.
"""

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PACOTE_EPIDEMIA = RAIZ / "src" / "epidemia"


def _extrair_modulos_importados(arquivo: Path) -> set[str]:
    """Retorna o conjunto de módulos raiz ou subpacotes de `epidemia` importados no arquivo."""
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
    importados: set[str] = set()

    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                importados.add(alias.name)
        elif isinstance(no, ast.ImportFrom) and no.module:
            importados.add(no.module)

    return importados


def _viola_proibicao(modulo_importado: str, proibidos: set[str]) -> str | None:
    """Verifica se `modulo_importado` corresponde a algum pacote ou camada proibida."""
    partes = modulo_importado.split(".")
    raiz = partes[0]
    if raiz in proibidos:
        return raiz
    if raiz == "epidemia" and len(partes) > 1 and partes[1] in proibidos:
        return f"epidemia.{partes[1]}"
    return None


def _verificar_camada(camada: str, proibidos: set[str]) -> list[str]:
    pasta = PACOTE_EPIDEMIA / camada
    violacoes: list[str] = []
    if not pasta.exists():
        return violacoes

    for arquivo in pasta.rglob("*.py"):
        for mod in sorted(_extrair_modulos_importados(arquivo)):
            alvo = _viola_proibicao(mod, proibidos)
            if alvo is not None:
                rel = arquivo.relative_to(RAIZ)
                violacoes.append(f"{rel} importa '{mod}' (proibido em '{camada}': {alvo})")
    return violacoes


def test_core_isolado_de_camadas_superiores_e_ui():
    proibidos = {
        "PySide6",
        "pyqtgraph",
        "pandas",
        "networkx",
        "shapely",
        "app",
        "world",
        "datasets",
        "ui",
    }
    assert _verificar_camada("core", proibidos) == []


def test_datasets_usa_apenas_stdlib():
    proibidos = {
        "PySide6",
        "pyqtgraph",
        "pandas",
        "networkx",
        "shapely",
        "core",
        "world",
        "app",
        "ui",
    }
    assert _verificar_camada("datasets", proibidos) == []


def test_world_nao_depende_de_app_nem_ui():
    proibidos = {
        "PySide6",
        "pyqtgraph",
        "pandas",
        "networkx",
        "shapely",
        "app",
        "ui",
    }
    assert _verificar_camada("world", proibidos) == []


def test_app_nao_depende_de_ui_nem_qt():
    proibidos = {
        "PySide6",
        "pyqtgraph",
        "pandas",
        "networkx",
        "shapely",
        "ui",
    }
    assert _verificar_camada("app", proibidos) == []
