"""Configurações globais e resolução de caminhos de dados do sistema (M5).

Garante localização correta dos dados processados tanto em ambiente de desenvolvimento
quanto quando o aplicativo é empacotado pelo PyInstaller (sys._MEIPASS quando frozen).
"""

from __future__ import annotations

import sys
from pathlib import Path


def get_base_dir() -> Path:
    """Retorna o diretório raiz da aplicação (ou o diretório temporário do PyInstaller)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # Em desenvolvimento: raiz do repositório (3 níveis acima de src/epidemia/config.py)
    return Path(__file__).resolve().parent.parent.parent


BASE_DIR: Path = get_base_dir()
DATA_DIR: Path = BASE_DIR / "data"
PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"

# Arquivos canônicos de entrada de dados
COUNTRIES_CSV: Path = PROCESSED_DATA_DIR / "countries.csv"
EDGES_CSV: Path = PROCESSED_DATA_DIR / "edges.csv"
COUNTRIES_GEOJSON: Path = PROCESSED_DATA_DIR / "countries.geojson"


def has_processed_data() -> bool:
    """Verifica se os arquivos essenciais de dados do M4 estão presentes."""
    return (
        COUNTRIES_CSV.is_file()
        and EDGES_CSV.is_file()
        and COUNTRIES_GEOJSON.is_file()
    )


def has_real_geometries() -> bool:
    """Verifica especificamente se o arquivo de geometrias reais countries.geojson existe."""
    return COUNTRIES_GEOJSON.is_file()
