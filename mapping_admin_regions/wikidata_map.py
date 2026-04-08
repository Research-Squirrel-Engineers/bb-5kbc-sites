"""
wikidata_map.py
---------------
Maps LAND, BUNDESLAND, and KREIS columns from a pipe-delimited CSV to
Wikidata QIDs and GeoNames IDs via the Wikidata SPARQL endpoint.

Matching strategy:
  LAND       – global index of sovereign states          (1 SPARQL call)
  BUNDESLAND – global index of Bundeslaender/Voivodeships (1 SPARQL call)
  KREIS      – global index of ALL German Landkreise and Polish Powiats,
               fetched in one call, then filtered in Python by BUNDESLAND_QID
               via the stored P131 value.  No per-Bundesland queries, no
               P131+/P279* traversal -> no timeouts.

Outputs (same folder as this script):
  fst_standortanalysen_ref_mapped.csv
  fst_standortanalysen_ref_report.csv

Dependencies:
    pip install pandas requests rapidfuzz
"""

import csv
import pathlib
import re
import time
from typing import Optional

import pandas as pd
import requests
from rapidfuzz import fuzz, process

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

INPUT_FILE = "fst_standortanalysen_ref.csv"
OUTPUT_FILE = "fst_standortanalysen_ref_mapped.csv"
REPORT_FILE = "fst_standortanalysen_ref_report.csv"

OUTPUT_SEP = ","

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "fst_standortanalysen_wikidata_mapper/1.0 (your-email@example.com)"

FUZZY_THRESHOLD = 0.85  # used for LAND and BUNDESLAND
KREIS_FUZZY_THRESHOLD = 0.75  # lower: Wikidata labels often have extra prefixes
SPARQL_TIMEOUT = 45  # global index queries are heavier; 45s is safe
REQUEST_DELAY = 1.0

# ---------------------------------------------------------------------------
# NORMALISATION CONFIG
# ---------------------------------------------------------------------------

BUNDESLAND_ALIASES: dict[str, str] = {
    "mvp": "Mecklenburg-Vorpommern",
}
BUNDESLAND_OVERRIDES: dict[str, dict] = {
    "śląskie": {
        "qid": "Q54181",
        "geonames": "3337497",
        "label": "śląskie",
        "source": "override",
    },
}
BUNDESLAND_STRIP_PREFIXES = [r"^woj\.\s*"]

KREIS_ALIASES: dict[str, str] = {
    "sommerda": "Sömmerda",
    "pow. gorẃski": "Górowski",
}
KREIS_OVERRIDES: dict[str, dict] = {
    # Wikidata label lacks "Landkreis" prefix (stripped by KREIS_STRIP_PREFIXES)
    "harz": {
        "qid": "Q6087",
        "geonames": None,
        "label": "Landkreis Harz",
        "source": "override",
    },
    "börde": {
        "qid": "Q6064",
        "geonames": None,
        "label": "Landkreis Börde",
        "source": "override",
    },
    # Input has short/old name, Wikidata uses full current name
    "rügen": {
        "qid": "Q2909",
        "geonames": None,
        "label": "Vorpommern-Rügen",
        "source": "override",
    },
    "weimarer land": {
        "qid": "Q7879",
        "geonames": None,
        "label": "Weimarer Land",
        "source": "override",
    },
    "gotha": {
        "qid": "Q7869",
        "geonames": None,
        "label": "Landkreis Gotha",
        "source": "override",
    },
    "görlitz": {
        "qid": "Q6317",
        "geonames": None,
        "label": "Landkreis Görlitz",
        "source": "override",
    },
    "sömmerda": {
        "qid": "Q7865",
        "geonames": None,
        "label": "Landkreis Sömmerda",
        "source": "override",
    },
    "leipzig": {
        "qid": "Q17953",
        "geonames": None,
        "label": "Leipzig",
        "source": "override",
    },
    "brandenburg": {
        "qid": "Q3931",
        "geonames": None,
        "label": "Brandenburg an der Havel",
        "source": "override",
    },
    "brandenburg (havel)": {
        "qid": "Q3931",
        "geonames": None,
        "label": "Brandenburg an der Havel",
        "source": "override",
    },
    # Dissolved/historical kreise
    "leipzig-land": {
        "qid": "Q1323208",
        "geonames": None,
        "label": "Landkreis Leipzig-Land",
        "source": "override",
    },
    "jessen": {
        "qid": "Q6075",
        "geonames": None,
        "label": "Landkreis Jessen",
        "source": "override",
    },
    "hoyerswerda": {
        "qid": "Q571947",
        "geonames": None,
        "label": "Landkreis Hoyerswerda",
        "source": "override",
    },
    # Polish powiats: corrected wrong fuzzy matches
    "powiat gryfiński": {
        "qid": "Q326895",
        "geonames": None,
        "label": "Powiat Gryfiński",
        "source": "override",
    },
    "powiat słupecki": {
        "qid": "Q133257",
        "geonames": None,
        "label": "Powiat Słupecki",
        "source": "override",
    },
    "powiat miński": {
        "qid": "Q947536",
        "geonames": None,
        "label": "Powiat Miński",
        "source": "override",
    },
    "powiat szczeciński": {
        "qid": "Q558696",
        "geonames": None,
        "label": "Powiat Szczeciński",
        "source": "override",
    },
    "powiat szczecińska": {
        "qid": "Q558408",
        "geonames": None,
        "label": "Powiat Szczecinecki",
        "source": "override",
    },
    "powiat krosno odrzańskie": {
        "qid": "Q317835",
        "geonames": None,
        "label": "Powiat Krośnieński",
        "source": "override",
    },
    # German Kreise confirmed by user — altLabels in Wikidata caused low fuzzy scores
    "teltow-fläming": {
        "qid": "Q6146",
        "geonames": None,
        "label": "Landkreis Teltow-Fläming",
        "source": "override",
    },
    "mansfeld-südharz": {
        "qid": "Q6092",
        "geonames": None,
        "label": "Landkreis Mansfeld-Südharz",
        "source": "override",
    },
    "anhalt-bitterfeld": {
        "qid": "Q6071",
        "geonames": None,
        "label": "Landkreis Anhalt-Bitterfeld",
        "source": "override",
    },
    "powiat gorzów wielkopolski": {
        "qid": "Q104731",
        "geonames": None,
        "label": "Gorzów Wielkopolski",
        "source": "override",
    },
    # Confirmed by user — fuzzy score was < 1.0 due to adjective/noun form difference
    "powiat górowski": {
        "qid": "Q636757",
        "geonames": None,
        "label": "Powiat Górowski",
        "source": "override",
    },
    "powiat kościański": {
        "qid": "Q133188",
        "geonames": None,
        "label": "Powiat Kościański",
        "source": "override",
    },
    "powiat poznański": {
        "qid": "Q101575",
        "geonames": None,
        "label": "Powiat Poznański",
        "source": "override",
    },
}
KREIS_STRIP_PREFIXES = [
    r"^landkreis\s+",
    r"^kreis\s+",
]
# Polish powiats: replace 'pow. X' with 'Powiat X' to match Wikidata labels
KREIS_POW_REPLACE = re.compile(r"^pow\.\s*", re.IGNORECASE)

# Wikidata classes for Kreis-level entities — flat list, NO P279* needed.
# German district classes (state-specific subclasses included for precision)
KREIS_CLASSES_DE = " ".join(
    [
        "wd:Q106658",
        "wd:Q1176765",  # Landkreis (DE-specific + generic)
        "wd:Q1221157",
        "wd:Q22865",  # kreisfreie Stadt (DE-specific + generic)
        "wd:Q1799794",
        "wd:Q693039",  # Stadtkreis (DE-specific + generic)
        "wd:Q2197954",  # Landkreis in Brandenburg
        "wd:Q2280615",  # Landkreis in Sachsen
        "wd:Q2356285",  # Landkreis in Sachsen-Anhalt
        "wd:Q2360804",  # Landkreis in Thüringen
        "wd:Q2625595",  # kreisfreie Stadt in Sachsen
        "wd:Q2625596",  # kreisfreie Stadt in Sachsen-Anhalt
        "wd:Q2625597",  # kreisfreie Stadt in Thüringen
        "wd:Q2625598",  # kreisfreie Stadt in Brandenburg
    ]
)
KREIS_CLASSES_PL = " ".join(
    [
        "wd:Q181290",  # Powiat
        "wd:Q1697444",  # Stadtpowiat
    ]
)

# ---------------------------------------------------------------------------
# CORE HELPERS
# ---------------------------------------------------------------------------

HERE = pathlib.Path(__file__).parent

MatchResult = tuple[
    Optional[str],  # qid
    Optional[str],  # geonames
    Optional[str],  # matched label
    Optional[float],  # score 0.0-1.0
    str,  # reason
]

NO_MATCH: MatchResult = (None, None, None, None, "Not processed")


def sparql_query(query: str) -> list[dict]:
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": USER_AGENT,
    }
    response = requests.get(
        SPARQL_ENDPOINT,
        params={"query": query, "format": "json"},
        headers=headers,
        timeout=SPARQL_TIMEOUT,
    )
    response.raise_for_status()
    return [
        {k: v["value"] for k, v in row.items()}
        for row in response.json()["results"]["bindings"]
    ]


def qid_from_uri(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def build_index(rows: list[dict]) -> dict[str, dict]:
    """Lowercase-keyed index. Prefers GeoNames, then rdfs:label."""
    index: dict[str, dict] = {}
    for row in rows:
        key = row["label"].strip().lower()
        existing = index.get(key)
        is_better = (
            existing is None
            or ("geonames" in row and "geonames" not in existing)
            or (
                row.get("labelType") == "rdfs:label"
                and existing.get("source") != "rdfs:label"
            )
        )
        if is_better:
            index[key] = {
                "qid": qid_from_uri(row["item"]),
                "label": row["label"].strip(),
                "geonames": row.get("geonames"),
                "source": row.get("labelType", "unknown"),
                # P131 chain: direct parent + one level up (-> Bundesland)
                "p131": qid_from_uri(row["p131"]) if "p131" in row else None,
                "p131up": qid_from_uri(row["p131up"]) if "p131up" in row else None,
            }
    return index


# ---------------------------------------------------------------------------
# INDEX FETCHERS  (3 total, no per-Bundesland queries)
# ---------------------------------------------------------------------------


def fetch_country_index() -> dict[str, dict]:
    query = """
SELECT DISTINCT ?item ?label ?labelType ?geonames WHERE {
  VALUES ?class { wd:Q6256 wd:Q3024240 wd:Q179164 }
  ?item wdt:P31 ?class .
  { ?item rdfs:label ?label . FILTER(LANG(?label)="de") BIND("rdfs:label" AS ?labelType) }
  UNION
  { ?item skos:altLabel ?label . FILTER(LANG(?label)="de") BIND("skos:altLabel" AS ?labelType) }
  OPTIONAL { ?item wdt:P1566 ?geonames . }
}"""
    print("Fetching country index...", flush=True)
    rows = sparql_query(query)
    print(f"  {len(rows)} entries.")
    return build_index(rows)


def fetch_bundesland_index() -> dict[str, dict]:
    query = """
SELECT DISTINCT ?item ?label ?labelType ?geonames WHERE {
  VALUES ?class { wd:Q1221156 wd:Q150093 }
  ?item wdt:P31 ?class .
  { ?item rdfs:label ?label . FILTER(LANG(?label) IN ("de","pl")) BIND("rdfs:label" AS ?labelType) }
  UNION
  { ?item skos:altLabel ?label . FILTER(LANG(?label) IN ("de","pl")) BIND("skos:altLabel" AS ?labelType) }
  OPTIONAL { ?item wdt:P1566 ?geonames . }
}"""
    print("Fetching Bundesland/Voivodeship index...", flush=True)
    rows = sparql_query(query)
    print(f"  {len(rows)} entries.")
    return build_index(rows)


def fetch_kreis_index_for_bundesland(bl_qid: str, bl_name: str) -> dict[str, dict]:
    """
    Fetch all current administrative districts directly within *bl_qid*.

    No class filter — P131 scoping alone keeps the result set small (~10-40).
    MINUS { ?item wdt:P576 [] } excludes dissolved/historical items.
    FILTER(STRLEN > 3) excludes KFZ short codes.
    """
    query = f"""
SELECT DISTINCT ?item ?label ?labelType ?geonames WHERE {{
  ?item wdt:P131 wd:{bl_qid} .
  # Exclude items that have an end date (P582) - more precise than P576
  # P576 (dissolved) can exist on current items as admin reorganisation date
  MINUS {{ ?item wdt:P582 [] }}
  {{
    ?item rdfs:label ?label .
    FILTER(LANG(?label) IN ("de", "pl"))
    FILTER(STRLEN(?label) > 3)
    BIND("rdfs:label" AS ?labelType)
  }} UNION {{
    ?item skos:altLabel ?label .
    FILTER(LANG(?label) IN ("de", "pl"))
    FILTER(STRLEN(?label) > 4)
    BIND("skos:altLabel" AS ?labelType)
  }}
  OPTIONAL {{ ?item wdt:P1566 ?geonames . }}
}}
"""
    print(f"  [{bl_name} / {bl_qid}]  querying Wikidata...", flush=True)
    rows = sparql_query(query)
    print(f"    {len(rows)} entries retrieved.")
    time.sleep(REQUEST_DELAY)
    return build_index(rows)


def build_index(rows: list[dict]) -> dict[str, dict]:
    """Lowercase-keyed index. Prefers GeoNames, then rdfs:label."""
    index: dict[str, dict] = {}
    for row in rows:
        key = row["label"].strip().lower()
        existing = index.get(key)
        is_better = (
            existing is None
            or ("geonames" in row and "geonames" not in existing)
            or (
                row.get("labelType") == "rdfs:label"
                and existing.get("source") != "rdfs:label"
            )
        )
        if is_better:
            index[key] = {
                "qid": qid_from_uri(row["item"]),
                "label": row["label"].strip(),
                "geonames": row.get("geonames"),
                "source": row.get("labelType", "unknown"),
                # P131 chain: direct parent + one level up (-> Bundesland)
                "p131": qid_from_uri(row["p131"]) if "p131" in row else None,
                "p131up": qid_from_uri(row["p131up"]) if "p131up" in row else None,
            }
    return index


# ---------------------------------------------------------------------------
# INDEX FETCHERS  (3 total, no per-Bundesland queries)
# ---------------------------------------------------------------------------


def fetch_country_index() -> dict[str, dict]:
    query = """
SELECT DISTINCT ?item ?label ?labelType ?geonames WHERE {
  VALUES ?class { wd:Q6256 wd:Q3024240 wd:Q179164 }
  ?item wdt:P31 ?class .
  { ?item rdfs:label ?label . FILTER(LANG(?label)="de") BIND("rdfs:label" AS ?labelType) }
  UNION
  { ?item skos:altLabel ?label . FILTER(LANG(?label)="de") BIND("skos:altLabel" AS ?labelType) }
  OPTIONAL { ?item wdt:P1566 ?geonames . }
}"""
    print("Fetching country index...", flush=True)
    rows = sparql_query(query)
    print(f"  {len(rows)} entries.")
    return build_index(rows)


def fetch_bundesland_index() -> dict[str, dict]:
    query = """
SELECT DISTINCT ?item ?label ?labelType ?geonames WHERE {
  VALUES ?class { wd:Q1221156 wd:Q150093 }
  ?item wdt:P31 ?class .
  { ?item rdfs:label ?label . FILTER(LANG(?label) IN ("de","pl")) BIND("rdfs:label" AS ?labelType) }
  UNION
  { ?item skos:altLabel ?label . FILTER(LANG(?label) IN ("de","pl")) BIND("skos:altLabel" AS ?labelType) }
  OPTIONAL { ?item wdt:P1566 ?geonames . }
}"""
    print("Fetching Bundesland/Voivodeship index...", flush=True)
    rows = sparql_query(query)
    print(f"  {len(rows)} entries.")
    return build_index(rows)


def fetch_kreis_index_global() -> dict[str, dict]:
    """
    Fetch current German Kreise and Polish Powiats in two SPARQL calls.

    Key filters applied at query time:
      MINUS { ?item wdt:P576 [] }   – exclude dissolved/historical items
      FILTER(STRLEN(?label) > 2)    – exclude KFZ short codes (e.g. "RÜG")
      rdfs:label only for altLabel  – skos:altLabel used only as fallback,
                                      and only labels > 2 chars

    Each row stores wdt:P131 (direct admin parent) for Python-side
    Bundesland scoping.
    """

    def _fetch(classes: str, langs: str, label: str) -> list[dict]:
        query = f"""
SELECT DISTINCT ?item ?label ?labelType ?geonames ?p131 ?p131up WHERE {{
  VALUES ?class {{ {classes} }}
  ?item wdt:P31 ?class .
  MINUS {{ ?item wdt:P576 [] }}
  OPTIONAL {{ ?item wdt:P131 ?p131 . }}
  OPTIONAL {{ ?item wdt:P131/wdt:P131 ?p131up . }}
  {{
    ?item rdfs:label ?label .
    FILTER(LANG(?label) IN ({langs}))
    FILTER(STRLEN(?label) > 2)
    BIND("rdfs:label" AS ?labelType)
  }} UNION {{
    ?item skos:altLabel ?label .
    FILTER(LANG(?label) IN ({langs}))
    FILTER(STRLEN(?label) > 4)
    BIND("skos:altLabel" AS ?labelType)
  }}
  OPTIONAL {{ ?item wdt:P1566 ?geonames . }}
}}"""
        print(f"  Fetching {label}...", flush=True)
        rows = sparql_query(query)
        print(f"    {len(rows)} entries.")
        time.sleep(REQUEST_DELAY)
        return rows

    # Polish Powiats: Q856076 = powiat in Poland (more specific than Q181290)
    kreis_classes_pl = " ".join(
        [
            "wd:Q856076",  # powiat in Poland (current, specific)
            "wd:Q181290",  # powiat (generic fallback)
            "wd:Q1697444",  # city with powiat rights
        ]
    )

    print("Fetching global Kreis index (DE + PL)...", flush=True)
    rows_de = _fetch(KREIS_CLASSES_DE, '"de"', "German Kreise")
    rows_pl = _fetch(kreis_classes_pl, '"de","pl"', "Polish Powiats")
    return build_index(rows_de + rows_pl)


# ---------------------------------------------------------------------------
# NORMALISATION
# ---------------------------------------------------------------------------


def _normalise(
    raw: str,
    strip_prefixes: list[str],
    aliases: dict[str, str],
    overrides: dict[str, dict],
) -> tuple[str, str, Optional[dict]]:
    notes, value = [], raw.strip()
    for pat in strip_prefixes:
        s = re.sub(pat, "", value, flags=re.IGNORECASE).strip()
        if s != value:
            notes.append(f"stripped -> '{s}'")
            value = s
    alias = aliases.get(value.lower())
    if alias:
        notes.append(f"alias '{value}' -> '{alias}'")
        value = alias
    override = overrides.get(value.lower())
    if override:
        notes.append(f"override -> QID={override['qid']}")
    return value, "; ".join(notes), override


def normalise_bundesland(raw: str):
    return _normalise(
        raw, BUNDESLAND_STRIP_PREFIXES, BUNDESLAND_ALIASES, BUNDESLAND_OVERRIDES
    )


def normalise_kreis(raw: str):
    # Replace 'pow. X' with 'Powiat X' before general normalisation
    value = KREIS_POW_REPLACE.sub("Powiat ", raw.strip())
    return _normalise(value, KREIS_STRIP_PREFIXES, KREIS_ALIASES, KREIS_OVERRIDES)


# ---------------------------------------------------------------------------
# FUZZY LOOKUP
# ---------------------------------------------------------------------------


def fuzzy_lookup(
    name: str,
    index: dict[str, dict],
    normalisation_note: str = "",
    threshold: float = FUZZY_THRESHOLD,
    filter_p131: Optional[str] = None,
) -> MatchResult:
    """
    Match *name* against *index* using rapidfuzz token_sort_ratio.

    filter_p131: if given, restrict candidates to entries whose stored
                 P131 value matches this Bundesland QID.  Falls back to
                 the full index if the filtered subset is empty (safety net
                 for items that point to an intermediate P131 node).
    """
    query_str = name.strip().lower()

    # Build candidate pool scoped to Bundesland — filtered first, full fallback.
    # Check both direct P131 and one-level-up P131 to catch items whose
    # immediate parent is a Regierungsbezirk rather than the Bundesland.
    if filter_p131:
        filtered = {
            k: v
            for k, v in index.items()
            if v.get("p131") == filter_p131 or v.get("p131up") == filter_p131
        }
        candidates = filtered if filtered else index
        used_filter = bool(filtered)
    else:
        candidates = index
        used_filter = False

    result = process.extractOne(
        query_str, list(candidates.keys()), scorer=fuzz.token_sort_ratio
    )
    if result is None:
        return None, None, None, None, "No candidates in index"

    best_key, raw_score, _ = result
    score = round(raw_score / 100, 4)
    entry = candidates[best_key]

    if score < threshold:
        return (
            None,
            None,
            None,
            score,
            f"Best candidate '{entry['label']}' scored {score:.2f}, "
            f"below threshold {threshold}",
        )

    match_type = (
        "Exact match" if query_str == best_key else f"Fuzzy match (score={score:.2f})"
    )
    scope = f"P131={filter_p131}" if used_filter else "global index"
    parts = [
        f"{match_type} via {entry['source']} [{scope}]",
        f"'{name}' -> '{entry['label']}'",
    ]
    if normalisation_note:
        parts.append(f"[normalised: {normalisation_note}]")

    return entry["qid"], entry.get("geonames"), entry["label"], score, " | ".join(parts)


# ---------------------------------------------------------------------------
# PROCESS HELPERS
# ---------------------------------------------------------------------------


def process_level(
    df: pd.DataFrame,
    col: str,
    index: dict[str, dict],
    normalise_fn=None,
) -> tuple[dict[str, MatchResult], list[dict]]:
    unique_vals = df[col].dropna().unique().tolist()
    cache: dict[str, MatchResult] = {}

    print(
        f"\nMatching {len(unique_vals)} unique {col} value(s) "
        f"(threshold={FUZZY_THRESHOLD})...\n"
    )

    for raw in unique_vals:
        normalised, note, override = (
            normalise_fn(raw) if normalise_fn else (raw, "", None)
        )
        if override:
            result: MatchResult = (
                override["qid"],
                override.get("geonames"),
                override["label"],
                1.0,
                f"Direct override | '{raw}' -> QID={override['qid']}"
                + (f" | [{note}]" if note else ""),
            )
        else:
            result = fuzzy_lookup(normalised, index, normalisation_note=note)

        cache[raw] = result
        qid, geonames, matched_label, score, _ = result
        status = "OK" if qid else "NO MATCH"
        score_str = f"{score:.2f}" if score is not None else "n/a"
        print(
            f"  [{status:8s}] {raw!r:35s}  QID={str(qid):10s}  "
            f"GeoNames={str(geonames):12s}  score={score_str}  "
            f"matched='{matched_label}'"
        )

    report_rows = [
        {
            "level": col,
            "input_value": raw,
            "QID": v[0],
            "GeoNames": v[1],
            "matchLabel": v[2],
            "matchScore": v[3],
            "matchReason": v[4],
        }
        for raw, v in cache.items()
    ]
    return cache, report_rows


def process_kreis(df: pd.DataFrame) -> tuple[dict[str, MatchResult], list[dict]]:
    """
    Per-Bundesland KREIS lookup.
    Fetches one small index per unique BUNDESLAND_QID (P131 direct, no class
    filter, no P279*), then fuzzy-matches locally.
    Each query returns only ~10-40 items -> fast and timeout-safe.
    """
    # Group unique KREIS values by their BUNDESLAND_QID
    pairs = (
        df[["KREIS", "BUNDESLAND", "BUNDESLAND_QID"]]
        .dropna(subset=["BUNDESLAND_QID"])
        .drop_duplicates()
    )
    by_bl = pairs.groupby(["BUNDESLAND_QID", "BUNDESLAND"])

    total = df["KREIS"].nunique()
    print(
        f"\nMatching {total} unique KREIS value(s) across "
        f"{len(by_bl)} Bundesland group(s) (threshold={FUZZY_THRESHOLD})...\n"
    )

    cache: dict[str, MatchResult] = {}

    for (bl_qid, bl_name), grp in by_bl:
        kreise = grp["KREIS"].dropna().unique().tolist()
        kreis_index = fetch_kreis_index_for_bundesland(bl_qid, bl_name)

        for raw in kreise:
            if raw in cache:
                continue
            normalised, note, override = normalise_kreis(raw)

            if override:
                result: MatchResult = (
                    override["qid"],
                    override.get("geonames"),
                    override["label"],
                    1.0,
                    f"Direct override | '{raw}' -> QID={override['qid']}"
                    + (f" | [{note}]" if note else ""),
                )
            else:
                result = fuzzy_lookup(
                    normalised,
                    kreis_index,
                    normalisation_note=note,
                    threshold=KREIS_FUZZY_THRESHOLD,
                )

            cache[raw] = result
            qid, geonames, matched_label, score, _ = result
            status = "OK" if qid else "NO MATCH"
            score_str = f"{score:.2f}" if score is not None else "n/a"
            print(
                f"    [{status:8s}] {raw!r:35s}  QID={str(qid):10s}  "
                f"GeoNames={str(geonames):12s}  score={score_str}  "
                f"matched='{matched_label}'"
            )

    # Mark any KREIS without a BUNDESLAND_QID as skipped
    for raw in df["KREIS"].dropna().unique():
        if raw not in cache:
            cache[raw] = (
                None,
                None,
                None,
                None,
                "Skipped: no BUNDESLAND_QID available for scoping",
            )

    report_rows = [
        {
            "level": "KREIS",
            "input_value": raw,
            "QID": v[0],
            "GeoNames": v[1],
            "matchLabel": v[2],
            "matchScore": v[3],
            "matchReason": v[4],
        }
        for raw, v in cache.items()
    ]
    return cache, report_rows


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main() -> None:
    input_path = HERE / INPUT_FILE
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path, sep="|", dtype=str, quotechar='"', encoding="utf-8")
    df.columns = df.columns.str.strip()

    for col in ("LAND", "BUNDESLAND", "KREIS"):
        if col not in df.columns:
            raise ValueError(f"Column '{col}' missing. Available: {list(df.columns)}")

    all_report: list[dict] = []

    # -- LAND ----------------------------------------------------------------
    country_index = fetch_country_index()
    land_cache, land_report = process_level(df, "LAND", country_index)
    all_report.extend(land_report)
    for i, s in enumerate(
        ["QID", "GeoNames", "matchLabel", "matchScore", "matchReason"]
    ):
        df[f"LAND_{s}"] = df["LAND"].map(lambda x, i=i: land_cache.get(x, NO_MATCH)[i])

    # -- BUNDESLAND ----------------------------------------------------------
    bl_index = fetch_bundesland_index()
    bl_cache, bl_report = process_level(
        df, "BUNDESLAND", bl_index, normalise_fn=normalise_bundesland
    )
    all_report.extend(bl_report)
    for i, s in enumerate(
        ["QID", "GeoNames", "matchLabel", "matchScore", "matchReason"]
    ):
        df[f"BUNDESLAND_{s}"] = df["BUNDESLAND"].map(
            lambda x, i=i: bl_cache.get(x, NO_MATCH)[i]
        )

    # -- KREIS  (per-Bundesland index, direct P131, no class filter) ---------
    kreis_cache, kreis_report = process_kreis(df)
    all_report.extend(kreis_report)
    for i, s in enumerate(
        ["QID", "GeoNames", "matchLabel", "matchScore", "matchReason"]
    ):
        df[f"KREIS_{s}"] = df["KREIS"].map(
            lambda x, i=i: kreis_cache.get(x, NO_MATCH)[i]
        )

    # -- Write outputs -------------------------------------------------------
    out = HERE / OUTPUT_FILE
    df.to_csv(out, sep=OUTPUT_SEP, index=False, quoting=csv.QUOTE_ALL, encoding="utf-8")
    print(f"\n[1/2] Mapped CSV:  {out}")

    rep = HERE / REPORT_FILE
    pd.DataFrame(all_report).sort_values(
        ["level", "matchScore"], ascending=[True, True], na_position="first"
    ).to_csv(rep, sep=OUTPUT_SEP, index=False, quoting=csv.QUOTE_ALL, encoding="utf-8")
    print(f"[2/2] Report CSV:  {rep}")

    print(f"\nRows: {len(df)}")
    for level, cache in [
        ("LAND", land_cache),
        ("BUNDESLAND", bl_cache),
        ("KREIS", kreis_cache),
    ]:
        m = sum(1 for v in cache.values() if v[0] is not None)
        print(
            f"  {level:12s} unique={len(cache):3d}  matched={m}  no_match={len(cache)-m}"
        )


if __name__ == "__main__":
    main()
