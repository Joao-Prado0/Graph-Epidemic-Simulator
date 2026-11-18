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
import warnings
from collections import defaultdict
from datetime import date, datetime, timedelta
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
# Populações ausentes no OWID. Preenchidas só quando o valor está vazio.
POPULATION_OVERRIDES: dict[str, tuple[float, str]] = {
    "PCN": (47, "Pitcairn Islands, estimativa de 2021 (Wikipedia, verbete Pitcairn Islands)"),
}


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


def _ring_area_and_centroid(
    ring: list[Any],
    *,
    shift_antimeridian: bool,
) -> tuple[float, float, float]:
    """Calcula (área_absoluta, cx, cy) de um anel fechado pela fórmula de Shoelace."""
    pts = [
        (
            float(pt[0]) + (360.0 if shift_antimeridian and float(pt[0]) < 0.0 else 0.0),
            float(pt[1]),
        )
        for pt in ring
    ]
    n = len(pts)
    if n < 3:
        return 0.0, 0.0, 0.0

    area2 = 0.0
    cx6 = 0.0
    cy6 = 0.0
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        cross = x1 * y2 - x2 * y1
        area2 += cross
        cx6 += (x1 + x2) * cross
        cy6 += (y1 + y2) * cross

    if abs(area2) < 1e-12:
        avg_x = sum(p[0] for p in pts) / n
        avg_y = sum(p[1] for p in pts) / n
        return 1e-12, avg_x, avg_y

    area = 0.5 * area2
    cx = cx6 / (3.0 * area2)
    cy = cy6 / (3.0 * area2)
    return abs(area), cx, cy


def _calculate_centroid_with_antimeridian(geom_shape: Any, iso3: str) -> tuple[float, float]:
    """Calcula centróide (lat, lon) tratando países que cruzam o antimeridiano (D15).

    Aceita tanto objetos geométricos do Shapely quanto dicionários GeoJSON.
    Para países em ``ANTIMERIDIAN_COUNTRIES``, desloca longitudes negativas em +360°
    antes de calcular o centróide ponderado por área (Shoelace) e reconverte o
    resultado para o intervalo [-180, 180].
    """
    shift = iso3 in ANTIMERIDIAN_COUNTRIES

    if not shift and hasattr(geom_shape, "centroid") and not isinstance(geom_shape, dict):
        c = geom_shape.centroid
        return round(float(c.y), 4), round(float(c.x), 4)

    if isinstance(geom_shape, dict):
        geom_dict = geom_shape
    elif hasattr(geom_shape, "__geo_interface__"):
        geom_dict = geom_shape.__geo_interface__
    elif mapping is not None:
        geom_dict = mapping(geom_shape)
    else:
        raise TypeError(f"Geometria não suportada para cálculo de centróide: {type(geom_shape)!r}")

    g_type = geom_dict.get("type")
    coords = geom_dict.get("coordinates") or []
    polys = [coords] if g_type == "Polygon" else list(coords)

    total_area = 0.0
    weighted_lon = 0.0
    weighted_lat = 0.0

    for poly in polys:
        if not poly or not poly[0]:
            continue
        ext_area, cx, cy = _ring_area_and_centroid(poly[0], shift_antimeridian=shift)
        for hole in poly[1:]:
            if not hole:
                continue
            h_area, hcx, hcy = _ring_area_and_centroid(hole, shift_antimeridian=shift)
            if ext_area > h_area:
                cx = (cx * ext_area - hcx * h_area) / (ext_area - h_area)
                cy = (cy * ext_area - hcy * h_area) / (ext_area - h_area)
                ext_area -= h_area
        total_area += ext_area
        weighted_lon += cx * ext_area
        weighted_lat += cy * ext_area

    if total_area <= 0.0:
        return 0.0, 0.0

    lon = weighted_lon / total_area
    lat = weighted_lat / total_area
    if lon > 180.0:
        lon -= 360.0
    return round(float(lat), 4), round(float(lon), 4)


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
        if iso3 is None and len(raw_str) == 3 and raw_str.isalpha():
            iso3, parent = raw_str.upper(), None  # código ISO3 direto do Natural Earth
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

    # Preenche populações ausentes no OWID (só onde o valor está vazio)
    for code, (pop, _source) in POPULATION_OVERRIDES.items():
        mask = master["iso_code"] == code
        master.loc[mask & master["population"].isna(), "population"] = pop

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


def _find_raw_file(raw_dir: Path, filename: str) -> Path:
    """Localiza um arquivo bruto na raiz de ``raw_dir`` ou em subpastas."""
    direct = raw_dir / filename
    if direct.is_file():
        return direct
    matches = sorted(raw_dir.rglob(filename))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"Arquivo bruto '{filename}' não encontrado em {raw_dir}")


def _parse_flexible_date(val: Any) -> str:
    """Normaliza datas em formato YYYY-MM-DD ou M/D/YY (JHU) para ISO YYYY-MM-DD."""
    s = str(val).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    for fmt in ("%m/%d/%y", "%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date.fromisoformat(s[:10]).isoformat()


def _parse_int_safe(val: Any) -> int:
    """Converte string ou número (incluindo floats como '648.0') para int."""
    if val is None:
        return 0
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return 0
    return int(float(s))


def _write_csv_records(
    records: Any,
    columns: list[str],
    out_path: Path,
) -> Any:
    """Escreve registros (ou DataFrame) em CSV UTF-8."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if pd is not None and isinstance(records, pd.DataFrame):
        records.to_csv(out_path, index=False, encoding="utf-8")
        return records
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in records:
            writer.writerow({col: row.get(col, "") for col in columns})
    return records


def build_edges(
    airports_path: Path,
    routes_path: Path,
    aliases: dict[str, tuple[str, str | None]],
    drops: set[str],
    iata_exceptions: dict[str, str],
    valid_iso3_set: set[str],
    out_csv_path: Path,
    owid_names: dict[str, str] | None = None,
) -> Any:
    """Gera edges.csv a partir do OpenFlights, excluindo codeshare e voos domésticos (D13, D14)."""
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
                iso_ex = iata_exceptions[iata]
                _, parent_ex = aliases.get(iso_ex, (iso_ex, None))
                airports[ap_id] = parent_ex if parent_ex else iso_ex
                continue

            iso3, parent = resolve_iso(country_name, aliases, drops, owid_names or {})
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
        {"iso3_a": u, "iso3_b": v, "routes": count} for (u, v), count in sorted(route_pairs.items())
    ]
    out_obj = pd.DataFrame(edge_rows) if pd is not None else edge_rows
    return _write_csv_records(out_obj, ["iso3_a", "iso3_b", "routes"], out_csv_path)


def finalize_series(
    df: Any,
    valid_iso3: set[str],
    has_recovered: bool = False,
) -> Any:
    """Aplica a regra universal de consolidação temporal (D10, D11, D12, D21).

    Garante datas contínuas, forward-fill e cummax individual por série de origem
    (``origin_id``) antes de somar no país de destino (``iso3``, Decisão D21).
    Aceita tanto ``pandas.DataFrame`` quanto ``list[dict[str, Any]]``.
    """
    is_dataframe = pd is not None and isinstance(df, pd.DataFrame)
    if is_dataframe:
        records: list[dict[str, Any]] = df.to_dict("records")
    elif isinstance(df, list):
        records = list(df)
    else:
        raise TypeError("finalize_series espera pandas.DataFrame ou list[dict].")

    filtered = [r for r in records if str(r.get("iso3") or "") in valid_iso3]
    if not filtered:
        if is_dataframe:
            return pd.DataFrame(columns=["iso3", "date", "cases", "deaths", "recovered"])
        return []

    def _parse_iso_date(val: Any) -> date:
        s = str(val).strip()[:10]
        return date.fromisoformat(s)

    parsed_dates = [_parse_iso_date(r["date"]) for r in filtered]
    min_date = min(parsed_dates)
    max_date = max(parsed_dates)
    num_days = (max_date - min_date).days + 1
    date_strs = [(min_date + timedelta(days=i)).isoformat() for i in range(num_days)]
    date_to_idx = {d_str: idx for idx, d_str in enumerate(date_strs)}

    # Agrupa por (iso3_destino, origin_id) para aplicar D21:
    # cada território ou província sofre reindex + ffill + cummax antes da soma no país-mãe
    by_iso_and_origin: dict[str, dict[str, dict[int, tuple[int, int, int]]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for r, d_obj in zip(filtered, parsed_dates, strict=True):
        iso3 = str(r["iso3"])
        origin_id = str(r.get("origin_id") or iso3)
        d_idx = date_to_idx[d_obj.isoformat()]
        c_val = int(r.get("cases") or 0)
        d_val = int(r.get("deaths") or 0)
        rec_raw = r.get("recovered")
        rec_val = int(rec_raw) if (has_recovered and rec_raw not in (None, "")) else 0

        prev_c, prev_d, prev_r = by_iso_and_origin[iso3][origin_id].get(d_idx, (0, 0, 0))
        by_iso_and_origin[iso3][origin_id][d_idx] = (
            prev_c + c_val,
            prev_d + d_val,
            prev_r + rec_val,
        )

    out_rows: list[dict[str, Any]] = []
    for iso3 in sorted(by_iso_and_origin.keys()):
        origins_map = by_iso_and_origin[iso3]
        summed_cases = [0] * num_days
        summed_deaths = [0] * num_days
        summed_rec = [0] * num_days

        for _origin_id, day_map in origins_map.items():
            cur_c = 0
            cur_d = 0
            cur_r = 0
            max_c = 0
            max_d = 0
            max_r = 0
            for t in range(num_days):
                if t in day_map:
                    cur_c, cur_d, cur_r = day_map[t]
                # D10 + D11 + D12: ffill + cummax individual na série de origem
                if cur_c > max_c:
                    max_c = cur_c
                if cur_d > max_d:
                    max_d = cur_d
                if cur_r > max_r:
                    max_r = cur_r
                summed_cases[t] += max_c
                summed_deaths[t] += max_d
                summed_rec[t] += max_r

        # Garantia final de monotonicidade após a soma (D10)
        run_c = 0
        run_d = 0
        run_r = 0
        for t, d_str in enumerate(date_strs):
            run_c = max(run_c, summed_cases[t])
            run_d = max(run_d, summed_deaths[t])
            run_r = max(run_r, summed_rec[t])
            out_rows.append(
                {
                    "iso3": iso3,
                    "date": d_str,
                    "cases": run_c,
                    "deaths": run_d,
                    "recovered": run_r if has_recovered else "",
                }
            )

    out_rows.sort(key=lambda item: (item["date"], item["iso3"]))
    if is_dataframe:
        return pd.DataFrame(out_rows, columns=["iso3", "date", "cases", "deaths", "recovered"])
    return out_rows


def resolve_covid_row_iso(
    country_region: str,
    province_state: str | None,
    aliases: dict[str, tuple[str, str | None]],
    drops: set[str],
    owid_names: dict[str, str],
    valid_iso3: set[str],
) -> tuple[str | None, str | None]:
    """Resolve (target_iso3, origin_id) para uma linha do JHU CSSE (D9, D21).

    Prioriza ``Province/State`` quando esta corresponde a uma entidade autônoma
    em ``valid_iso3`` (ex.: ``Hong Kong -> HKG``, ``Greenland -> GRL``, ``Aruba -> ABW``)
    ou a um território fundido (ex.: ``Gibraltar -> GIB -> GBR``). Caso contrário,
    resolve por ``Country/Region`` preservando ``origin_id`` por província.
    """
    prov_clean = (province_state or "").strip()
    if prov_clean and prov_clean.lower() != "nan":
        prov_iso, prov_parent = resolve_iso(prov_clean, aliases, drops, owid_names)
        if prov_iso == "DROP":
            return "DROP", None
        if prov_iso is not None:
            target = prov_parent if prov_parent else prov_iso
            if target in valid_iso3:
                return target, prov_iso

    iso3, parent = resolve_iso(country_region, aliases, drops, owid_names)
    if iso3 == "DROP" or iso3 is None:
        return iso3, None
    target_iso = parent if parent else iso3
    origin_id = f"{iso3}:{prov_clean}" if prov_clean and prov_clean.lower() != "nan" else iso3
    return target_iso, origin_id


def prepare_covid(
    raw_dir: Path,
    aliases: dict[str, tuple[str, str | None]],
    drops: set[str],
    owid_names: dict[str, str],
    valid_iso3: set[str],
    out_path: Path,
) -> Any:
    """Prepara a série temporal de COVID-19 (JHU CSSE)."""
    cases_path = _find_raw_file(raw_dir, "RAW_global_confirmed_cases.csv")
    deaths_path = _find_raw_file(raw_dir, "RAW_global_deaths.csv")

    id_cols_set = {"Province/State", "Country/Region", "Lat", "Long"}
    with cases_path.open("r", encoding="utf-8", errors="replace") as fc:
        cases_rows = list(csv.DictReader(fc))
    with deaths_path.open("r", encoding="utf-8", errors="replace") as fd:
        deaths_rows = list(csv.DictReader(fd))

    if not cases_rows:
        return _write_csv_records([], ["iso3", "date", "cases", "deaths", "recovered"], out_path)

    date_cols = [c for c in cases_rows[0].keys() if c not in id_cols_set]
    date_iso_map = {col: _parse_flexible_date(col) for col in date_cols}

    deaths_by_key: dict[tuple[str, str], dict[str, str]] = {}
    for d_row in deaths_rows:
        key = (
            (d_row.get("Country/Region") or "").strip(),
            (d_row.get("Province/State") or "").strip(),
        )
        deaths_by_key[key] = d_row

    rows: list[dict[str, Any]] = []
    unresolved: set[str] = set()
    for c_row in cases_rows:
        c_name = (c_row.get("Country/Region") or "").strip()
        prov = (c_row.get("Province/State") or "").strip()
        target_iso, origin_id = resolve_covid_row_iso(
            c_name, prov, aliases, drops, owid_names, valid_iso3
        )
        if target_iso == "DROP":
            continue
        if not target_iso:
            unresolved.add(f"{c_name} ({prov})" if prov else c_name)
            continue

        d_row = deaths_by_key.get((c_name, prov), {})
        for col in date_cols:
            rows.append(
                {
                    "iso3": target_iso,
                    "origin_id": origin_id,
                    "date": date_iso_map[col],
                    "cases": _parse_int_safe(c_row.get(col)),
                    "deaths": _parse_int_safe(d_row.get(col)),
                }
            )

    if unresolved:
        warnings.warn(
            f"prepare_covid: nomes não resolvidos ignorados: {sorted(unresolved)}",
            stacklevel=2,
        )

    final_data = finalize_series(rows, valid_iso3, has_recovered=False)
    return _write_csv_records(
        final_data, ["iso3", "date", "cases", "deaths", "recovered"], out_path
    )


def prepare_ebola(
    raw_dir: Path,
    aliases: dict[str, tuple[str, str | None]],
    drops: set[str],
    owid_names: dict[str, str],
    valid_iso3: set[str],
    out_path: Path,
) -> Any:
    """Prepara a série temporal de Ebola 2014-2016 com a regra da Libéria (D22)."""
    ebola_path = _find_raw_file(raw_dir, "ebola_2014_2016_clean.csv")
    with ebola_path.open("r", encoding="utf-8", errors="replace") as f:
        raw_rows = list(csv.DictReader(f))

    if not raw_rows:
        return _write_csv_records([], ["iso3", "date", "cases", "deaths", "recovered"], out_path)

    cols = list(raw_rows[0].keys())
    country_col = next(c for c in cols if "country" in c.lower())
    date_col = next(c for c in cols if "date" in c.lower())
    cases_col = next(c for c in cols if "case" in c.lower())
    deaths_col = next(c for c in cols if "death" in c.lower())

    # D22: Trata duplicidade de datas da Libéria mantendo a linha com maior número de casos
    best_by_country_date: dict[tuple[str, str], tuple[int, int]] = {}
    for r in raw_rows:
        c_name = str(r.get(country_col) or "").strip()
        d_str = _parse_flexible_date(r.get(date_col))
        c_val = _parse_int_safe(r.get(cases_col))
        d_val = _parse_int_safe(r.get(deaths_col))
        key = (c_name, d_str)
        if key not in best_by_country_date or c_val > best_by_country_date[key][0]:
            best_by_country_date[key] = (c_val, d_val)

    rows: list[dict[str, Any]] = []
    unresolved: set[str] = set()
    for (c_name, d_str), (c_val, d_val) in best_by_country_date.items():
        iso3, parent = resolve_iso(c_name, aliases, drops, owid_names)
        if iso3 == "DROP":
            continue
        if not iso3:
            unresolved.add(c_name)
            continue
        target_iso = parent if parent else iso3
        rows.append(
            {
                "iso3": target_iso,
                "origin_id": iso3,
                "date": d_str,
                "cases": c_val,
                "deaths": d_val,
            }
        )

    if unresolved:
        warnings.warn(
            f"prepare_ebola: nomes não resolvidos ignorados: {sorted(unresolved)}",
            stacklevel=2,
        )

    final_data = finalize_series(rows, valid_iso3, has_recovered=False)
    return _write_csv_records(
        final_data, ["iso3", "date", "cases", "deaths", "recovered"], out_path
    )


def prepare_h1n1(
    raw_dir: Path,
    aliases: dict[str, tuple[str, str | None]],
    drops: set[str],
    owid_names: dict[str, str],
    valid_iso3: set[str],
    out_path: Path,
) -> Any:
    """Prepara a série temporal de H1N1 2009."""
    h1n1_path = _find_raw_file(raw_dir, "data.csv")
    with h1n1_path.open("r", encoding="utf-8", errors="replace") as f:
        raw_rows = list(csv.DictReader(f))

    if not raw_rows:
        return _write_csv_records([], ["iso3", "date", "cases", "deaths", "recovered"], out_path)

    cols = list(raw_rows[0].keys())
    country_col = next(c for c in cols if "country" in c.lower())
    date_col = next(c for c in cols if "date" in c.lower())
    cases_col = next(c for c in cols if "case" in c.lower())
    deaths_col = next(c for c in cols if "death" in c.lower())

    rows: list[dict[str, Any]] = []
    unresolved: set[str] = set()
    for r in raw_rows:
        c_name = str(r.get(country_col) or "").strip()
        iso3, parent = resolve_iso(c_name, aliases, drops, owid_names)
        if iso3 == "DROP":
            continue
        if not iso3:
            unresolved.add(c_name)
            continue
        target_iso = parent if parent else iso3

        rows.append(
            {
                "iso3": target_iso,
                "origin_id": iso3,
                "date": _parse_flexible_date(r.get(date_col)),
                "cases": _parse_int_safe(r.get(cases_col)),
                "deaths": _parse_int_safe(r.get(deaths_col)),
            }
        )

    if unresolved:
        warnings.warn(
            f"prepare_h1n1: nomes não resolvidos ignorados: {sorted(unresolved)}",
            stacklevel=2,
        )

    final_data = finalize_series(rows, valid_iso3, has_recovered=False)
    return _write_csv_records(
        final_data, ["iso3", "date", "cases", "deaths", "recovered"], out_path
    )


def prepare_sars(
    raw_dir: Path,
    aliases: dict[str, tuple[str, str | None]],
    drops: set[str],
    owid_names: dict[str, str],
    valid_iso3: set[str],
    out_path: Path,
) -> Any:
    """Prepara a série temporal de SARS 2003 com recuperados e correção da China (D23)."""
    sars_path = _find_raw_file(raw_dir, "sars_2003_complete_dataset_clean.csv")
    with sars_path.open("r", encoding="utf-8", errors="replace") as f:
        raw_rows = list(csv.DictReader(f))

    if not raw_rows:
        return _write_csv_records([], ["iso3", "date", "cases", "deaths", "recovered"], out_path)

    cols = list(raw_rows[0].keys())
    country_col = next(c for c in cols if "country" in c.lower())
    date_col = next(c for c in cols if "date" in c.lower())
    cases_col = next(c for c in cols if "case" in c.lower() or "cumulative" in c.lower())
    deaths_col = next(c for c in cols if "death" in c.lower())
    rec_col = next(c for c in cols if "recover" in c.lower())

    rows: list[dict[str, Any]] = []
    unresolved: set[str] = set()
    for r in raw_rows:
        c_name = str(r.get(country_col) or "").strip()
        iso3, parent = resolve_iso(c_name, aliases, drops, owid_names)
        if iso3 == "DROP":
            continue
        if not iso3:
            unresolved.add(c_name)
            continue
        target_iso = parent if parent else iso3
        date_str = _parse_flexible_date(r.get(date_col))

        c_val = _parse_int_safe(r.get(cases_col))
        d_val = _parse_int_safe(r.get(deaths_col))
        rec_val = _parse_int_safe(r.get(rec_col))

        # D23: Duplicata da China em 12/04/2003 descarta 62 e mantém 1309
        if target_iso == "CHN" and date_str == "2003-04-12" and c_val == 62:
            continue

        rows.append(
            {
                "iso3": target_iso,
                "origin_id": iso3,
                "date": date_str,
                "cases": c_val,
                "deaths": d_val,
                "recovered": rec_val,
            }
        )

    if unresolved:
        warnings.warn(
            f"prepare_sars: nomes não resolvidos ignorados: {sorted(unresolved)}",
            stacklevel=2,
        )

    final_data = finalize_series(rows, valid_iso3, has_recovered=True)
    return _write_csv_records(
        final_data, ["iso3", "date", "cases", "deaths", "recovered"], out_path
    )


def validate_processed_data(processed_dir: Path) -> list[str]:
    """Valida todos os invariantes estruturais dos arquivos em ``data/processed/``.

    Retorna uma lista de mensagens de erro (vazia se todos os invariantes passarem).
    """
    errors: list[str] = []
    countries_csv = processed_dir / "countries.csv"
    geojson_path = processed_dir / "countries.geojson"
    edges_csv = processed_dir / "edges.csv"

    if not countries_csv.is_file():
        return [f"Arquivo ausente: {countries_csv}"]

    valid_iso3: set[str] = set()
    centroids_csv: dict[str, tuple[float, float]] = {}
    with countries_csv.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            iso = (row.get("iso3") or "").strip()
            if not iso or iso in valid_iso3:
                errors.append(f"ISO3 inválido ou duplicado em countries.csv: {iso!r}")
            valid_iso3.add(iso)
            pop = float(row.get("population") or 0.0)
            if pop <= 0.0:
                errors.append(f"População não positiva para {iso}: {pop}")
            lat = float(row.get("lat") or 0.0)
            lon = float(row.get("lon") or 0.0)
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                errors.append(f"Centróide fora de faixa para {iso}: ({lat}, {lon})")
            centroids_csv[iso] = (lat, lon)

    # Verifica se Kiribati e Fiji estão na região do Pacífico (D15)
    if "KIR" in centroids_csv and not (
        centroids_csv["KIR"][1] > 150.0 or centroids_csv["KIR"][1] < -140.0
    ):
        errors.append(
            f"Centróide de KIR fora do Pacífico (D15 violada): lon={centroids_csv['KIR'][1]}"
        )
    if "FJI" in centroids_csv and centroids_csv["FJI"][1] < 170.0:
        errors.append(f"Centróide de FJI deslocado (D15 violada): lon={centroids_csv['FJI'][1]}")

    if not geojson_path.is_file():
        errors.append(f"Arquivo ausente: {geojson_path}")
    else:
        gj = json.loads(geojson_path.read_text(encoding="utf-8"))
        gj_isos = {feat["properties"]["iso3"] for feat in gj.get("features", [])}
        if gj_isos != valid_iso3:
            errors.append(
                f"Divergência de ISO3 entre countries.csv ({len(valid_iso3)}) e "
                f"countries.geojson ({len(gj_isos)})."
            )

    if not edges_csv.is_file():
        errors.append(f"Arquivo ausente: {edges_csv}")
    else:
        seen_pairs: set[tuple[str, str]] = set()
        with edges_csv.open("r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                u = (row.get("iso3_a") or "").strip()
                v = (row.get("iso3_b") or "").strip()
                routes = int(row.get("routes") or 0)
                if u not in valid_iso3 or v not in valid_iso3 or u >= v or routes <= 0:
                    errors.append(f"Aresta inválida em edges.csv: ({u}, {v}, {routes})")
                if (u, v) in seen_pairs:
                    errors.append(f"Aresta duplicada em edges.csv: ({u}, {v})")
                seen_pairs.add((u, v))

    for p_file in ("covid19.csv", "ebola.csv", "h1n1.csv", "sars.csv"):
        p_path = processed_dir / p_file
        if not p_path.is_file():
            errors.append(f"Arquivo de série ausente: {p_path}")
            continue
        prev_by_iso: dict[str, tuple[int, int]] = {}
        with p_path.open("r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                iso = row["iso3"]
                if iso not in valid_iso3:
                    errors.append(f"{p_file}: ISO3 fora do universo: {iso}")
                c_val = int(row["cases"])
                d_val = int(row["deaths"])
                prev_c, prev_d = prev_by_iso.get(iso, (0, 0))
                if c_val < prev_c or d_val < prev_d:
                    errors.append(f"{p_file}: queda não monotônica para {iso} em {row['date']}")
                prev_by_iso[iso] = (c_val, d_val)

    return errors


def main() -> int:
    """Ponto de entrada do script de preparação offline."""
    parser = argparse.ArgumentParser(description="Pipeline de preparação dos dados da epidemia.")
    parser.add_argument(
        "--raw",
        type=Path,
        required=False,
        help="Diretório contendo os arquivos brutos baixados.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/processed"),
        help="Diretório de saída para os arquivos processados (default: data/processed).",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Apenas valida os arquivos existentes em --out sem reprocessar os brutos.",
    )
    args = parser.parse_args()

    out_dir: Path = args.out
    if args.validate_only:
        errs = validate_processed_data(out_dir)
        if errs:
            for e in errs:
                print(f"[ERRO] {e}", file=sys.stderr)
            return 1
        print(f"Validação concluída com sucesso em: {out_dir.resolve()}")
        return 0

    raw_dir: Path | None = args.raw
    if raw_dir is None or not raw_dir.is_dir():
        print(f"Erro: Diretório de brutos não encontrado: {raw_dir}", file=sys.stderr)
        return 1

    script_dir = Path(__file__).resolve().parent
    aliases_path = script_dir / "country_aliases.csv"

    print("Carregando aliases e regras de descarte...")
    aliases, drops, iata_exceptions = load_aliases(aliases_path)

    print("Processando geometrias e centróides (Natural Earth 50m)...")
    out_geojson_path = out_dir / "countries.geojson"
    alt_json = list(raw_dir.rglob("*admin_0_countries*.json"))
    geojson_path = alt_json[0] if alt_json else raw_dir / "ne_50m_admin_0_countries.json"

    if geojson_path.is_file() and shape is not None:
        _, centroids = build_geometry_and_centroids(geojson_path, aliases, drops, out_geojson_path)
    elif out_geojson_path.is_file():
        print("-> Reutilizando countries.geojson existente e recalculando centróides (D15)...")
        gj_data = json.loads(out_geojson_path.read_text(encoding="utf-8"))
        centroids = {
            feat["properties"]["iso3"]: _calculate_centroid_with_antimeridian(
                feat["geometry"], feat["properties"]["iso3"]
            )
            for feat in gj_data.get("features", [])
        }
    else:
        print(
            f"Erro: ne_50m_admin_0_countries.json não encontrado em {raw_dir}",
            file=sys.stderr,
        )
        return 1

    print("Construindo tabela mestra (countries.csv)...")
    out_countries_csv = out_dir / "countries.csv"
    if pd is not None:
        owid_path = _find_raw_file(raw_dir, "owid-covid-data.csv")
        master_df, valid_iso3, owid_names = build_countries_master(
            owid_path, aliases, drops, centroids, out_countries_csv
        )
        print(f"-> Tabela mestra gerada com {len(master_df)} entidades.")
    elif out_countries_csv.is_file():
        with out_countries_csv.open("r", encoding="utf-8") as f:
            c_rows = list(csv.DictReader(f))
            fieldnames = list(c_rows[0].keys()) if c_rows else []
        for r in c_rows:
            iso = r["iso3"]
            if iso in centroids:
                r["lat"] = str(centroids[iso][0])
                r["lon"] = str(centroids[iso][1])
        _write_csv_records(c_rows, fieldnames, out_countries_csv)
        valid_iso3 = {r["iso3"] for r in c_rows}
        owid_names = {normalize_name(r["name"]): r["iso3"] for r in c_rows}
        print(f"-> Tabela mestra atualizada com {len(c_rows)} entidades.")
    else:
        print("Erro: pandas ausente e countries.csv não encontrado.", file=sys.stderr)
        return 1

    print("Construindo malha de rotas aéreas (edges.csv)...")
    airports_path = _find_raw_file(raw_dir, "airports.dat")
    routes_path = _find_raw_file(raw_dir, "routes.dat")
    out_edges_csv = out_dir / "edges.csv"
    edges_df = build_edges(
        airports_path,
        routes_path,
        aliases,
        drops,
        iata_exceptions,
        valid_iso3,
        out_edges_csv,
        owid_names=owid_names,
    )
    print(f"-> Conexões aéreas geradas: {len(edges_df)} pares internacionais.")

    print("Processando séries históricas das 4 pandemias...")
    prepare_covid(raw_dir, aliases, drops, owid_names, valid_iso3, out_dir / "covid19.csv")
    prepare_ebola(raw_dir, aliases, drops, owid_names, valid_iso3, out_dir / "ebola.csv")
    prepare_h1n1(raw_dir, aliases, drops, owid_names, valid_iso3, out_dir / "h1n1.csv")
    prepare_sars(raw_dir, aliases, drops, owid_names, valid_iso3, out_dir / "sars.csv")

    errs = validate_processed_data(out_dir)
    if errs:
        for e in errs:
            print(f"[ERRO DE VALIDAÇÃO] {e}", file=sys.stderr)
        return 1

    print("\n=== Preparação e Validação Concluídas com Sucesso! ===")
    print(f"Arquivos gerados em: {out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
