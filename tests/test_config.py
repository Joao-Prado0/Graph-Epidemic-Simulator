"""Testes unitários para a resolução de caminhos de configuração (M5 — config.py)."""

from __future__ import annotations

import sys
from pathlib import Path

from epidemia.config import (
    BASE_DIR,
    COUNTRIES_GEOJSON,
    DATA_DIR,
    PROCESSED_DATA_DIR,
    get_base_dir,
    has_processed_data,
    has_real_geometries,
)


def test_config_paths_in_dev_environment() -> None:
    base = get_base_dir()
    assert base == BASE_DIR
    assert base.is_dir()
    assert (base / "src").is_dir()
    assert DATA_DIR == base / "data"
    assert PROCESSED_DATA_DIR == base / "data" / "processed"
    assert COUNTRIES_GEOJSON == PROCESSED_DATA_DIR / "countries.geojson"


def test_config_paths_frozen_simulation(monkeypatch, tmp_path: Path) -> None:
    fake_meipass = tmp_path / "meipass_temp"
    fake_meipass.mkdir()
    (fake_meipass / "data" / "processed").mkdir(parents=True)

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(fake_meipass), raising=False)

    base = get_base_dir()
    assert base == fake_meipass


def test_has_processed_data_and_geometries(monkeypatch, tmp_path: Path) -> None:
    # Em data/processed atual sem arquivos reais, deve ser False
    assert not has_processed_data()
    assert not has_real_geometries()

    # Com arquivos simulados
    fake_geojson = tmp_path / "countries.geojson"
    fake_geojson.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("epidemia.config.COUNTRIES_GEOJSON", fake_geojson)
    assert has_real_geometries()
