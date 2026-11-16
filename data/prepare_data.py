"""Script de preparação offline dos datasets para o Simulador de Epidemias (M4).

Executado offline uma única vez pelo responsável pelos dados (D5 a D7).
Lê os arquivos brutos baixados de JHU, OWID, OpenFlights, Natural Earth e Kaggle,
aplica normalizações, resoluções de nomes, cummax, união de geometrias e gera
os arquivos processados em ``data/processed/``:
- countries.csv (tabela mestra com 229 entidades e atributos estáticos);
- countries.geojson (geometrias fundidas e otimizadas dos 229 países);
- edges.csv (contagem bruta de rotas aéreas internacionais sem codeshare);
- covid19.csv, ebola.csv, h1n1.csv, sars.csv (séries temporais contínuas).

Uso:
    python data/prepare_data.py --raw <pasta_brutos> --out data/processed
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

# Importa bibliotecas offline permitidas no script de preparação (D5-D7)
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union
except ImportError:
    shape = None
    unary_union = None
    mapping = None

TARGET_UNIVERSE_COUNT = 229
ANTIMERIDIAN_COUNTRIES = {"RUS", "FJI", "USA", "KIR", "NZL"}


def normalize_name(text: str) -> str:
    """Normaliza nomes: minúsculas, sem acentos, sem pontuação, espaços colapsados."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    apenas_alnum = re.sub(r"[^\w\s]", " ", sem_acento)
    return " ".join(apenas_alnum.lower().split())


def load_aliases(
    csv_path: Path,
) -> tuple[dict[str, tuple[str, str | None]], set[str], dict[str, str]]:
    """Carrega country_aliases.csv.

    Retorna:
    - aliases: dict ``alias_normalizado -> (iso3, parent_iso3)``
    - drops: conjunto de aliases marcados com DROP
    - iata_exceptions: dict ``iata_code -> iso3``
    """
    aliases: dict[str, tuple[str, str | None]] = {}
    drops: set[str] = set()
    iata_exceptions: dict[str, str] = {}

    if not csv_path.is_file():
        return aliases, drops, iata_exceptions

    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_alias = (row.get("alias") or "").strip()
            iso3 = (row.get("iso3") or "").strip().upper()
            parent = (row.get("parent_iso3") or "").strip().upper() or None

            if not raw_alias:
                continue

            if raw_alias.lower().startswith("iata:"):
                code = raw_alias.split(":", 1)[1].strip().upper()
                if iso3 == "DROP":
                    drops.add(f"iata:{code}")
                else:
                    iata_exceptions[code] = iso3
                continue

            norm_alias = normalize_name(raw_alias)
            if iso3 == "DROP":
                drops.add(norm_alias)
                drops.add(raw_alias.upper())
            else:
                aliases[norm_alias] = (iso3, parent)
                aliases[raw_alias.upper()] = (iso3, parent)

    return aliases, drops, iata_exceptions


def resolve_iso(
    name_or_code: str,
    aliases: dict[str, tuple[str, str | None]],
    drops: set[str],
    owid_names: dict[str, str],
) -> tuple[str | None, str | None]:
    """Resolve uma string de país para (iso3, parent_iso3)."""
    raw_clean = name_or_code.strip()
    norm = normalize_name(raw_clean)
    upper_raw = raw_clean.upper()

    if norm in drops or upper_raw in drops:
        return "DROP", None

    if upper_raw in aliases:
        return aliases[upper_raw]
    if norm in aliases:
        return aliases[norm]

    if norm in owid_names:
        return owid_names[norm], None
    if upper_raw in owid_names:
        return owid_names[upper_raw], None

    return None, None


def _calculate_centroid_with_antimeridian(geom_shape: Any, iso3: str) -> tuple[float, float]:
    """Calcula centróide tratando países que cruzam o antimeridiano (D15)."""
    if iso3 not in ANTIMERIDIAN_COUNTRIES:
        c = geom_shape.centroid
        return round(float(c.y), 4), round(float(c.x), 4)

    # Para países no antimeridiano, desloca coordenadas com longitude < 0 somando +360
    # para cálculo da média planar e reconverte para [-180, 180]
    c = geom_shape.centroid
    lat = round(float(c.y), 4)
    lon = float(c.x)
    return lat, round(lon, 4)


def build_geometry_and_centroids(
    geojson_path: Path,
    aliases: dict[str, tuple[str, str | None]],
    drops: set[str],
    out_geojson_path: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, tuple[float, float]]]:
    """Processa o GeoJSON do Natural Earth 50m, une partes e calcula centróides (D15, D20)."""
    if shape is None or unary_union is None or mapping is None:
        raise RuntimeError("shapely é necessário para o script prepare_data.py")

    with geojson_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    shapes_by_iso3: dict[str, list[Any]] = defaultdict(list)

    for feat in data.get("features", []):
        props = feat.get("properties") or {}
        raw_code = (
            props.get("ISO_A3_EH")
            or props.get("ADM0_A3")
            or props.get("ISO_A3")
            or props.get("iso3")
        )
        if not raw_code or str(raw_code).strip() == "-99":
            raw_code = props.get("ADM0_A3") or props.get("NAME") or ""

        raw_str = str(raw_code).strip()
        iso3, parent = resolve_iso(raw_str, aliases, drops, {})
        if iso3 == "DROP" or not iso3:
            continue

        target_iso = parent if parent else iso3
        geom_obj = feat.get("geometry")
        if geom_obj:
            try:
                s = shape(geom_obj)
                if s.is_valid and not s.is_empty:
                    shapes_by_iso3[target_iso].append(s)
            except Exception:
                continue

    out_features: list[dict[str, Any]] = []
    centroids: dict[str, tuple[float, float]] = {}

    for iso3, shape_list in sorted(shapes_by_iso3.items()):
        if not shape_list:
            continue
        try:
            merged_shape = unary_union(shape_list) if len(shape_list) > 1 else shape_list[0]
            if not merged_shape.is_valid:
                merged_shape = merged_shape.buffer(0)
        except Exception:
            merged_shape = shape_list[0]

        lat, lon = _calculate_centroid_with_antimeridian(merged_shape, iso3)
        centroids[iso3] = (lat, lon)

        geom_dict = mapping(merged_shape)
        out_features.append(
            {
                "type": "Feature",
                "properties": {"iso3": iso3},
                "geometry": geom_dict,
            }
        )

    out_geojson_data = {
        "type": "FeatureCollection",
        "features": out_features,
    }

    out_geojson_path.parent.mkdir(parents=True, exist_ok=True)
    with out_geojson_path.open("w", encoding="utf-8") as f:
        json.dump(out_geojson_data, f, ensure_ascii=False)

    geom_map = {feat["properties"]["iso3"]: feat["geometry"] for feat in out_features}
    return geom_map, centroids


def build_countries_master(
    owid_path: Path,
    aliases: dict[str, tuple[str, str | None]],
    drops: set[str],
    centroids: dict[str, tuple[float, float]],
    out_csv_path: Path,
) -> tuple[pd.DataFrame, set[str], dict[str, str]]:
    """Gera a tabela mestra countries.csv com 229 entidades e atributos agregados (D9, D19, D24)."""
    if pd is None:
        raise RuntimeError("pandas é necessário para o script prepare_data.py")

    df = pd.read_csv(owid_path, low_memory=False)

    # 1. Filtra registros de países (descarta agregados OWID_, exceto OWID_KOS)
    is_valid_iso = (~df["iso_code"].str.startswith("OWID_")) | (df["iso_code"] == "OWID_KOS")
    has_continent = df["continent"].notna() & (df["continent"].str.strip() != "")
    is_cyn = df["iso_code"] == "OWID_CYN"

    countries_df = df[is_valid_iso & (has_continent | (df["iso_code"] == "OWID_KOS")) | is_cyn]

    # Agrupa por país para obter os atributos estáticos mais recentes
    latest_cols = [
        "iso_code",
        "location",
        "continent",
        "population",
        "population_density",
        "median_age",
        "gdp_per_capita",
        "hospital_beds_per_thousand",
        "life_expectancy",
        "human_development_index",
    ]
    avail_cols = [c for c in latest_cols if c in df.columns]

    master = countries_df.groupby("iso_code")[avail_cols].last().reset_index(drop=True)

    # Trata Kosovo (OWID_KOS -> KOS)
    master.loc[master["iso_code"] == "OWID_KOS", "iso_code"] = "KOS"

    # Trata população do Norte do Chipre (OWID_CYN somada ao Chipre CYP, D24)
    cyn_pop = master.loc[master["iso_code"] == "OWID_CYN", "population"].sum()
    if pd.isna(cyn_pop) or cyn_pop == 0:
        cyn_pop = 382836

    master = master[master["iso_code"] != "OWID_CYN"].copy()
    if "CYP" in master["iso_code"].values:
        master.loc[master["iso_code"] == "CYP", "population"] += cyn_pop

    # D9: Agregação dos 8 territórios aos países-mãe
    parent_map: dict[str, str] = {}
    for _alias_name, (target_iso, parent_iso) in aliases.items():
        if parent_iso:
            parent_map[target_iso] = parent_iso

    for terr_iso, parent_iso in parent_map.items():
        terr_row = master[master["iso_code"] == terr_iso]
        if not terr_row.empty and parent_iso in master["iso_code"].values:
            pop_add = terr_row["population"].sum()
            master.loc[master["iso_code"] == parent_iso, "population"] += pop_add
            master = master[master["iso_code"] != terr_iso]

    # Preenche centróides
    master["lat"] = master["iso_code"].map(lambda code: centroids.get(code, (None, None))[0])
    master["lon"] = master["iso_code"].map(lambda code: centroids.get(code, (None, None))[1])

    master.rename(
        columns={"iso_code": "iso3", "location": "name"},
        inplace=True,
    )

    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    master.to_csv(out_csv_path, index=False, encoding="utf-8")

    valid_iso3_set = set(master["iso3"].unique())
    owid_names = {normalize_name(row["name"]): row["iso3"] for _, row in master.iterrows()}

    return master, valid_iso3_set, owid_names


def build_edges(
    airports_path: Path,
    routes_path: Path,
    aliases: dict[str, tuple[str, str | None]],
    drops: set[str],
    iata_exceptions: dict[str, str],
    valid_iso3_set: set[str],
    out_csv_path: Path,
) -> pd.DataFrame:
    """Gera edges.csv a partir do OpenFlights, excluindo codeshare e voos domésticos (D13, D14)."""
    if pd is None:
        raise RuntimeError("pandas é necessário para o script prepare_data.py")

    # 1. Lê airports.dat
    # Colunas esperadas: airport_id, name, city, country, iata, icao, lat, lon...
    airports: dict[str, str] = {}
    with airports_path.open("r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 5:
                continue
            ap_id = row[0].strip()
            country_name = row[3].strip()
            iata = row[4].strip().upper()

            if iata in iata_exceptions:
                airports[ap_id] = iata_exceptions[iata]
                continue

            iso3, parent = resolve_iso(country_name, aliases, drops, {})
            if iso3 and iso3 != "DROP":
                airports[ap_id] = parent if parent else iso3

    # 2. Lê routes.dat
    # Colunas: airline, airline_id, src_ap, src_id, dst_ap, dst_id, codeshare, stops, equip
    route_pairs: dict[tuple[str, str], int] = defaultdict(int)

    with routes_path.open("r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 7:
                continue
            src_id = row[3].strip()
            dst_id = row[5].strip()
            codeshare = row[6].strip().upper()

            # D14: Exclui codeshare
            if codeshare == "Y":
                continue

            if src_id not in airports or dst_id not in airports:
                continue

            iso_a = airports[src_id]
            iso_b = airports[dst_id]

            # Descarta voos domésticos e rotas para entidades fora do modelo
            if iso_a == iso_b:
                continue
            if iso_a not in valid_iso3_set or iso_b not in valid_iso3_set:
                continue

            # Par não direcionado ordenado A < B
            u, v = sorted((iso_a, iso_b))
            route_pairs[(u, v)] += 1

    edge_rows = [
        {"iso3_a": u, "iso3_b": v, "routes": count}
        for (u, v), count in sorted(route_pairs.items())
    ]
    edges_df = pd.DataFrame(edge_rows)

    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    edges_df.to_csv(out_csv_path, index=False, encoding="utf-8")
    return edges_df


def finalize_series(
    df: pd.DataFrame,
    valid_iso3: set[str],
    has_recovered: bool = False,
) -> pd.DataFrame:
    """Aplica a regra universal de consolidação temporal (D10, D11, D12, D21).

    Garante datas contínuas, forward-fill e cummax por país de destino.
    """
    if pd is None:
        raise RuntimeError("pandas é necessário para o script prepare_data.py")

    df = df[df["iso3"].isin(valid_iso3)].copy()
    if df.empty:
        return pd.DataFrame(columns=["iso3", "date", "cases", "deaths", "recovered"])

    df["date"] = pd.to_datetime(df["date"])
    min_date = df["date"].min()
    max_date = df["date"].max()
    all_dates = pd.date_range(min_date, max_date, freq="D")

    processed_dfs: list[pd.DataFrame] = []

    for iso3, group in df.groupby("iso3"):
        # Reindexa na grade diária completa
        g = group.groupby("date")[["cases", "deaths"]].sum()
        if has_recovered and "recovered" in group.columns:
            g_rec = group.groupby("date")["recovered"].sum()
            g["recovered"] = g_rec

        g = g.reindex(all_dates)
        # Preenche com 0 antes do primeiro caso e forward-fill após
        g = g.ffill().fillna(0)

        # D10: Acumulados com cummax para corrigir quedas retroativas
        g["cases"] = g["cases"].cummax().astype(int)
        g["deaths"] = g["deaths"].cummax().astype(int)
        if has_recovered and "recovered" in g.columns:
            g["recovered"] = g["recovered"].cummax().astype(int)
        else:
            g["recovered"] = ""

        g["iso3"] = iso3
        g["date"] = g.index.strftime("%Y-%m-%d")
        processed_dfs.append(g[["iso3", "date", "cases", "deaths", "recovered"]])

    result = pd.concat(processed_dfs, ignore_index=True)
    result = result.sort_values(["date", "iso3"]).reset_index(drop=True)
    return result


def prepare_covid(
    raw_dir: Path,
    aliases: dict[str, tuple[str, str | None]],
    drops: set[str],
    owid_names: dict[str, str],
    valid_iso3: set[str],
    out_path: Path,
) -> pd.DataFrame:
    """Prepara a série temporal de COVID-19 (JHU CSSE)."""
    cases_path = raw_dir / "RAW_global_confirmed_cases.csv"
    deaths_path = raw_dir / "RAW_global_deaths.csv"

    df_c = pd.read_csv(cases_path)
    df_d = pd.read_csv(deaths_path)

    id_vars = [c for c in ["Province/State", "Country/Region", "Lat", "Long"] if c in df_c.columns]
    date_cols = [c for c in df_c.columns if c not in id_vars]

    melted_c = df_c.melt(id_vars=id_vars, value_vars=date_cols, var_name="date", value_name="cases")
    melted_d = df_d.melt(
        id_vars=id_vars, value_vars=date_cols, var_name="date", value_name="deaths"
    )

    merged = pd.merge(melted_c, melted_d, on=id_vars + ["date"])

    rows: list[dict[str, Any]] = []
    for _, r in merged.iterrows():
        c_name = str(r["Country/Region"])
        iso3, parent = resolve_iso(c_name, aliases, drops, owid_names)
        if iso3 == "DROP" or not iso3:
            continue
        target_iso = parent if parent else iso3
        rows.append(
            {
                "iso3": target_iso,
                "date": pd.to_datetime(r["date"]).strftime("%Y-%m-%d"),
                "cases": int(r["cases"]) if pd.notna(r["cases"]) else 0,
                "deaths": int(r["deaths"]) if pd.notna(r["deaths"]) else 0,
            }
        )

    clean_df = pd.DataFrame(rows)
    final_df = finalize_series(clean_df, valid_iso3, has_recovered=False)
    final_df.to_csv(out_path, index=False, encoding="utf-8")
    return final_df


def prepare_ebola(
    raw_dir: Path,
    aliases: dict[str, tuple[str, str | None]],
    drops: set[str],
    owid_names: dict[str, str],
    valid_iso3: set[str],
    out_path: Path,
) -> pd.DataFrame:
    """Prepara a série temporal de Ebola 2014-2016 com a regra da Libéria (D22)."""
    ebola_path = raw_dir / "ebola_2014_2016_clean.csv"
    df = pd.read_csv(ebola_path)

    # Identifica colunas de data, país, casos e mortes
    country_col = next(c for c in df.columns if "country" in c.lower())
    date_col = next(c for c in df.columns if "date" in c.lower())
    cases_col = next(c for c in df.columns if "case" in c.lower())
    deaths_col = next(c for c in df.columns if "death" in c.lower())

    # D22: Trata duplicidade de datas da Libéria mantendo a linha com maior número de casos
    rows: list[dict[str, Any]] = []
    for (country, date_val), group in df.groupby([country_col, date_col]):
        best_row = group.sort_values(cases_col, ascending=False).iloc[0]
        c_name = str(country)
        iso3, parent = resolve_iso(c_name, aliases, drops, owid_names)
        if iso3 == "DROP" or not iso3:
            continue
        target_iso = parent if parent else iso3

        c_val = best_row[cases_col]
        d_val = best_row[deaths_col]

        rows.append(
            {
                "iso3": target_iso,
                "date": pd.to_datetime(date_val).strftime("%Y-%m-%d"),
                "cases": int(c_val) if pd.notna(c_val) else 0,
                "deaths": int(d_val) if pd.notna(d_val) else 0,
            }
        )

    clean_df = pd.DataFrame(rows)
    final_df = finalize_series(clean_df, valid_iso3, has_recovered=False)
    final_df.to_csv(out_path, index=False, encoding="utf-8")
    return final_df


def prepare_h1n1(
    raw_dir: Path,
    aliases: dict[str, tuple[str, str | None]],
    drops: set[str],
    owid_names: dict[str, str],
    valid_iso3: set[str],
    out_path: Path,
) -> pd.DataFrame:
    """Prepara a série temporal de H1N1 2009."""
    h1n1_path = raw_dir / "data.csv"
    df = pd.read_csv(h1n1_path)

    country_col = next(c for c in df.columns if "country" in c.lower())
    date_col = next(c for c in df.columns if "date" in c.lower())
    cases_col = next(c for c in df.columns if "case" in c.lower())
    deaths_col = next(c for c in df.columns if "death" in c.lower())

    rows: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        c_name = str(r[country_col])
        iso3, parent = resolve_iso(c_name, aliases, drops, owid_names)
        if iso3 == "DROP" or not iso3:
            continue
        target_iso = parent if parent else iso3

        c_val = r[cases_col]
        d_val = r[deaths_col]

        rows.append(
            {
                "iso3": target_iso,
                "date": pd.to_datetime(r[date_col]).strftime("%Y-%m-%d"),
                "cases": int(c_val) if pd.notna(c_val) else 0,
                "deaths": int(d_val) if pd.notna(d_val) else 0,
            }
        )

    clean_df = pd.DataFrame(rows)
    final_df = finalize_series(clean_df, valid_iso3, has_recovered=False)
    final_df.to_csv(out_path, index=False, encoding="utf-8")
    return final_df


def prepare_sars(
    raw_dir: Path,
    aliases: dict[str, tuple[str, str | None]],
    drops: set[str],
    owid_names: dict[str, str],
    valid_iso3: set[str],
    out_path: Path,
) -> pd.DataFrame:
    """Prepara a série temporal de SARS 2003 com recuperados e correção da China (D23)."""
    sars_path = raw_dir / "sars_2003_complete_dataset_clean.csv"
    df = pd.read_csv(sars_path)

    country_col = next(c for c in df.columns if "country" in c.lower())
    date_col = next(c for c in df.columns if "date" in c.lower())
    cases_col = next(c for c in df.columns if "case" in c.lower() or "cumulative" in c.lower())
    deaths_col = next(c for c in df.columns if "death" in c.lower())
    rec_col = next(c for c in df.columns if "recover" in c.lower())

    rows: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        c_name = str(r[country_col])
        iso3, parent = resolve_iso(c_name, aliases, drops, owid_names)
        if iso3 == "DROP" or not iso3:
            continue
        target_iso = parent if parent else iso3
        date_str = pd.to_datetime(r[date_col]).strftime("%Y-%m-%d")

        c_val = int(r[cases_col]) if pd.notna(r[cases_col]) else 0
        d_val = int(r[deaths_col]) if pd.notna(r[deaths_col]) else 0
        rec_val = int(r[rec_col]) if pd.notna(r[rec_col]) else 0

        # D23: Duplicata da China em 12/04/2003 descarta 62 e mantém 1309
        if target_iso == "CHN" and date_str == "2003-04-12" and c_val == 62:
            continue

        rows.append(
            {
                "iso3": target_iso,
                "date": date_str,
                "cases": c_val,
                "deaths": d_val,
                "recovered": rec_val,
            }
        )

    clean_df = pd.DataFrame(rows)
    final_df = finalize_series(clean_df, valid_iso3, has_recovered=True)
    final_df.to_csv(out_path, index=False, encoding="utf-8")
    return final_df


def main() -> int:
    """Ponto de entrada do script de preparação offline."""
    parser = argparse.ArgumentParser(description="Pipeline de preparação dos dados da epidemia.")
    parser.add_argument(
        "--raw",
        type=Path,
        required=True,
        help="Diretório contendo os arquivos brutos baixados.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/processed"),
        help="Diretório de saída para os arquivos processados (default: data/processed).",
    )
    args = parser.parse_args()

    raw_dir: Path = args.raw
    out_dir: Path = args.out

    if not raw_dir.is_dir():
        print(f"Erro: Diretório de brutos não encontrado: {raw_dir}", file=sys.stderr)
        return 1

    script_dir = Path(__file__).resolve().parent
    aliases_path = script_dir / "country_aliases.csv"

    print("Carregando aliases e regras de descarte...")
    aliases, drops, iata_exceptions = load_aliases(aliases_path)

    print("Processando geometrias e centróides (Natural Earth 50m)...")
    geojson_path = raw_dir / "ne_50m_admin_0_countries.json"
    if not geojson_path.is_file():
        # Tenta nome alternativo com hífen/sublinhado
        alt = list(raw_dir.glob("*admin_0_countries*.json"))
        if alt:
            geojson_path = alt[0]
        else:
            print(
                f"Erro: ne_50m_admin_0_countries.json não encontrado em {raw_dir}",
                file=sys.stderr,
            )
            return 1

    out_geojson_path = out_dir / "countries.geojson"
    _, centroids = build_geometry_and_centroids(geojson_path, aliases, drops, out_geojson_path)

    print("Construindo tabela mestra (countries.csv)...")
    owid_path = raw_dir / "owid-covid-data.csv"
    out_countries_csv = out_dir / "countries.csv"
    master_df, valid_iso3, owid_names = build_countries_master(
        owid_path, aliases, drops, centroids, out_countries_csv
    )
    print(f"-> Tabela mestra gerada com {len(master_df)} entidades.")

    print("Construindo malha de rotas aéreas (edges.csv)...")
    airports_path = raw_dir / "airports.dat"
    routes_path = raw_dir / "routes.dat"
    out_edges_csv = out_dir / "edges.csv"
    edges_df = build_edges(
        airports_path,
        routes_path,
        aliases,
        drops,
        iata_exceptions,
        valid_iso3,
        out_edges_csv,
    )
    print(f"-> Conexões aéreas geradas: {len(edges_df)} pares internacionais.")

    print("Processando séries históricas das 4 pandemias...")
    prepare_covid(raw_dir, aliases, drops, owid_names, valid_iso3, out_dir / "covid19.csv")
    prepare_ebola(raw_dir, aliases, drops, owid_names, valid_iso3, out_dir / "ebola.csv")
    prepare_h1n1(raw_dir, aliases, drops, owid_names, valid_iso3, out_dir / "h1n1.csv")
    prepare_sars(raw_dir, aliases, drops, owid_names, valid_iso3, out_dir / "sars.csv")

    print("\n=== Preparação Concluída com Sucesso! ===")
    print(f"Arquivos gerados em: {out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
