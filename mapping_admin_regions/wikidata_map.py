"""
wikidata_map.py
===============
Enriches a pipe-delimited gazetteer CSV with Wikidata QIDs and external
authority identifiers (GeoNames, Getty TGN, iDAI.gazetteer, OSM relation).

Administrative levels currently supported:
  LAND       — sovereign state / country
  BUNDESLAND — German federal state or Polish voivodeship
  KREIS      — German Landkreis/kreisfreie Stadt or Polish powiat

Matching strategy
-----------------
* LAND and BUNDESLAND: one global SPARQL call per level builds a label index;
  rapidfuzz token_sort_ratio then matches locally.
* KREIS: one SPARQL call per Bundesland (scoped via wdt:P131) keeps result
  sets small and avoids timeouts. No transitive property traversal (P279*).
* Known problem cases (abbreviations, dissolved districts, labelling
  inconsistencies) are handled via ALIASES and OVERRIDES dictionaries at the
  top of the file — no QIDs are ever guessed by the script itself.

External identifiers retrieved via Wikidata as a hub
------------------------------------------------------
  P1566  GeoNames geographic identifier
  P1667  Getty Thesaurus of Geographic Names (TGN)
  P8217  iDAI.gazetteer (German Archaeological Institute)
  P402   OpenStreetMap relation ID

Outputs (written to the same directory as this script)
------------------------------------------------------
  *_mapped.csv   Full input CSV with enrichment columns appended.
  *_report.csv   One row per unique value per level; useful for QA review.
                 Rows are sorted by match score ascending so uncertain
                 matches appear at the top.

Dependencies
------------
    pip install pandas requests rapidfuzz

This script is structured so that each top-level section can be converted
directly into a Jupyter Notebook cell. The suggested cell order matches the
section headers below.
"""

# =============================================================================
# SECTION 1 — IMPORTS AND CONFIGURATION
# =============================================================================
# All parameters that a user might want to adjust are collected here.
# Edit this section before running; no other part of the file needs changing
# for routine use.

import csv
import pathlib
import re
import time
from typing import Optional

import pandas as pd
import requests
from rapidfuzz import fuzz, process

# --- File paths --------------------------------------------------------------

INPUT_FILE = "fst_standortanalysen_ref.csv"  # pipe-delimited input
OUTPUT_FILE = "fst_standortanalysen_ref_mapped.csv"
REPORT_FILE = "fst_standortanalysen_ref_report.csv"
OUTPUT_SEP = ","  # separator for output CSVs

HERE = pathlib.Path(__file__).parent  # resolved to notebook dir later

# --- SPARQL ------------------------------------------------------------------

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
# Wikidata's fair-use policy requires a descriptive User-Agent string.
USER_AGENT = "fst_standortanalysen_wikidata_mapper/1.0 (your-email@example.com)"
SPARQL_TIMEOUT = 45  # seconds; per-Bundesland queries are lightweight
REQUEST_DELAY = 1.0  # seconds between successive SPARQL calls (be polite)

# --- Fuzzy matching thresholds (0.0 – 1.0) -----------------------------------

FUZZY_THRESHOLD = 0.85  # LAND and BUNDESLAND
KREIS_FUZZY_THRESHOLD = 0.75  # Lower because Wikidata labels often carry
# extra prefixes (e.g. "Powiat Teltow-Fläming")

# --- BUNDESLAND normalisation ------------------------------------------------
# Aliases  : applied before fuzzy matching (lowercase key → replacement string)
# Overrides: bypass fuzzy matching entirely; QIDs confirmed by manual lookup
# Strip    : regex prefixes removed from raw values before matching

BUNDESLAND_ALIASES: dict[str, str] = {
    "mvp": "Mecklenburg-Vorpommern",  # common abbreviation in source data
}

BUNDESLAND_OVERRIDES: dict[str, dict] = {
    # "Woj. Śląskie" strips to "Śląskie"; fuzzy collision with "Dolnośląskie".
    # Q54181 confirmed manually; OSM relation 224462 added manually.
    "śląskie": {
        "qid": "Q54181",
        "geonames": "3337497",
        "osm_relation": "224462",
        "label": "śląskie",
        "source": "override",
    },
}

BUNDESLAND_STRIP_PREFIXES: list[str] = [
    r"^woj\.\s*",  # Polish voivodeships: "Woj. Dolnośląskie" → "Dolnośląskie"
]

# --- KREIS normalisation -----------------------------------------------------

KREIS_ALIASES: dict[str, str] = {
    "sommerda": "Sömmerda",  # typo in source data
    "pow. gorẃski": "Górowski",  # encoding artefact in source data
}

# All QIDs below have been confirmed by manual Wikidata lookup.
# Groups:
#   (a) Wikidata label lacks "Landkreis" prefix that KREIS_STRIP_PREFIXES removes
#   (b) Source data uses a short or old name; Wikidata uses the full current name
#   (c) Dissolved/historical districts that no longer exist as current admin units
#   (d) Polish powiats where the adjective form in source data mismatches Wikidata
#   (e) German Kreise confirmed after low fuzzy scores caused by Wikidata altLabels
KREIS_OVERRIDES: dict[str, dict] = {
    # (a) Label prefix mismatch
    "harz": {"qid": "Q6087", "label": "Landkreis Harz", "source": "override"},
    "börde": {"qid": "Q6064", "label": "Landkreis Börde", "source": "override"},
    # (b) Short or old name in source data
    "rügen": {"qid": "Q2909", "label": "Vorpommern-Rügen", "source": "override"},
    "weimarer land": {"qid": "Q7879", "label": "Weimarer Land", "source": "override"},
    "gotha": {"qid": "Q7869", "label": "Landkreis Gotha", "source": "override"},
    "görlitz": {"qid": "Q6317", "label": "Landkreis Görlitz", "source": "override"},
    "sömmerda": {"qid": "Q7865", "label": "Landkreis Sömmerda", "source": "override"},
    "leipzig": {"qid": "Q17953", "label": "Leipzig", "source": "override"},
    "brandenburg": {
        "qid": "Q3931",
        "label": "Brandenburg an der Havel",
        "source": "override",
    },
    "brandenburg (havel)": {
        "qid": "Q3931",
        "label": "Brandenburg an der Havel",
        "source": "override",
    },
    # (c) Dissolved/historical districts — mapped to successor or historical item
    "leipzig-land": {
        "qid": "Q1323208",
        "label": "Landkreis Leipzig-Land",
        "source": "override",
    },
    "jessen": {"qid": "Q6075", "label": "Landkreis Jessen", "source": "override"},
    "hoyerswerda": {
        "qid": "Q571947",
        "label": "Landkreis Hoyerswerda",
        "source": "override",
    },
    # (d) Polish powiats: adjective form in source data vs. Wikidata noun form
    "powiat gryfiński": {
        "qid": "Q326895",
        "label": "Powiat Gryfiński",
        "source": "override",
    },
    "powiat słupecki": {
        "qid": "Q133257",
        "label": "Powiat Słupecki",
        "source": "override",
    },
    "powiat miński": {"qid": "Q947536", "label": "Powiat Miński", "source": "override"},
    "powiat szczeciński": {
        "qid": "Q558696",
        "label": "Powiat Szczeciński",
        "source": "override",
    },
    "powiat szczecińska": {
        "qid": "Q558408",
        "label": "Powiat Szczecinecki",
        "source": "override",
    },
    "powiat krosno odrzańskie": {
        "qid": "Q317835",
        "label": "Powiat Krośnieński",
        "source": "override",
    },
    "powiat gorzów wielkopolski": {
        "qid": "Q104731",
        "label": "Gorzów Wielkopolski",
        "source": "override",
    },
    "powiat górowski": {
        "qid": "Q636757",
        "label": "Powiat Górowski",
        "source": "override",
    },
    "powiat kościański": {
        "qid": "Q133188",
        "label": "Powiat Kościański",
        "source": "override",
    },
    "powiat poznański": {
        "qid": "Q101575",
        "label": "Powiat Poznański",
        "source": "override",
    },
    # (e) German Kreise with Wikidata altLabels that depressed fuzzy scores
    "teltow-fläming": {
        "qid": "Q6146",
        "label": "Landkreis Teltow-Fläming",
        "source": "override",
    },
    "mansfeld-südharz": {
        "qid": "Q6092",
        "label": "Landkreis Mansfeld-Südharz",
        "source": "override",
    },
    "anhalt-bitterfeld": {
        "qid": "Q6071",
        "label": "Landkreis Anhalt-Bitterfeld",
        "source": "override",
    },
}

KREIS_STRIP_PREFIXES: list[str] = [
    r"^landkreis\s+",  # "Landkreis Harz"    → "Harz"    → hits override
    r"^kreis\s+",  # "Kreis Rügen"        → "Rügen"   → hits override
]
# Polish powiats: replace "pow. X" with "Powiat X" to match Wikidata rdfs:labels
KREIS_POW_REPLACE = re.compile(r"^pow\.\s*", re.IGNORECASE)


# =============================================================================
# SECTION 2 — SHARED UTILITIES
# =============================================================================
# Low-level helpers used throughout the pipeline: SPARQL execution, index
# construction, and the MatchResult type that carries all enrichment data.

# MatchResult tuple layout (indices used throughout the script):
#   0  qid           Wikidata Q-identifier
#   1  geonames      GeoNames numeric ID          (P1566)
#   2  matchLabel    Label matched in Wikidata
#   3  matchScore    Confidence 0.0 – 1.0
#   4  matchReason   Human-readable explanation
#   5  tgn           Getty TGN identifier         (P1667)
#   6  idai          iDAI.gazetteer identifier    (P8217)
#   7  osm_relation  OpenStreetMap relation ID    (P402)
MatchResult = tuple[
    Optional[str],  # qid
    Optional[str],  # geonames
    Optional[str],  # matched label
    Optional[float],  # score 0.0–1.0
    str,  # reason
    Optional[str],  # tgn
    Optional[str],  # idai
    Optional[str],  # osm_relation
]

NO_MATCH: MatchResult = (None, None, None, None, "Not processed", None, None, None)


def sparql_query(query: str) -> list[dict]:
    """Execute a SPARQL SELECT against the Wikidata endpoint.

    Returns a list of row dicts with string values, one per result binding.
    Raises requests.HTTPError on non-2xx responses.
    """
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
    """Extract a Q-identifier string from a full Wikidata entity URI."""
    return uri.rsplit("/", 1)[-1]


def build_index(rows: list[dict]) -> dict[str, dict]:
    """Build a lowercase-keyed label index from SPARQL result rows.

    Rows sharing the same label key are *merged* rather than overwritten so
    that external identifiers (GeoNames, TGN, IDAI, OSM) are accumulated
    across all rows for the same item — Wikidata returns one row per label
    variant, so a single item may appear in many rows.

    rdfs:label takes precedence over skos:altLabel as the display label.
    p131 / p131up store the direct and one-level-up administrative parent
    QIDs for use as a Bundesland-scoping filter during KREIS matching.
    """
    index: dict[str, dict] = {}
    for row in rows:
        key = row["label"].strip().lower()
        if key not in index:
            index[key] = {
                "qid": qid_from_uri(row["item"]),
                "label": row["label"].strip(),
                "geonames": None,
                "tgn": None,
                "idai": None,
                "osm_relation": None,
                "source": row.get("labelType", "unknown"),
                "p131": qid_from_uri(row["p131"]) if "p131" in row else None,
                "p131up": qid_from_uri(row["p131up"]) if "p131up" in row else None,
            }
        entry = index[key]
        # Accumulate external IDs from every row for this label key
        for field in ("geonames", "tgn", "idai", "osm_relation"):
            if entry[field] is None and row.get(field):
                entry[field] = row[field]
        # Prefer rdfs:label as canonical display label
        if row.get("labelType") == "rdfs:label":
            entry["source"] = "rdfs:label"
            entry["label"] = row["label"].strip()
    return index


# =============================================================================
# SECTION 3 — WIKIDATA INDEX FETCHERS
# =============================================================================
# One function per administrative level. Each issues a focused SPARQL query
# and returns a label index built by build_index().
#
# External identifier properties fetched alongside every label:
#   P1566  GeoNames | P1667  Getty TGN | P8217  iDAI.gazetteer | P402  OSM


def fetch_country_index() -> dict[str, dict]:
    """Fetch sovereign states, historical countries, and federated states.

    Wikidata classes queried:
      Q6256    sovereign state
      Q3024240 historical country  (covers DDR, Deutsches Reich, etc.)
      Q179164  federated state     (covers Bundesländer if needed later)

    Labels are fetched in German only (lang=de).
    """
    query = """
SELECT DISTINCT ?item ?label ?labelType ?geonames ?tgn ?idai ?osm_relation WHERE {
  VALUES ?class { wd:Q6256 wd:Q3024240 wd:Q179164 }
  ?item wdt:P31 ?class .
  { ?item rdfs:label ?label .   FILTER(LANG(?label)="de") BIND("rdfs:label"    AS ?labelType) }
  UNION
  { ?item skos:altLabel ?label . FILTER(LANG(?label)="de") BIND("skos:altLabel" AS ?labelType) }
  OPTIONAL { ?item wdt:P1566 ?geonames . }
  OPTIONAL { ?item wdt:P1667 ?tgn . }
  OPTIONAL { ?item wdt:P8217 ?idai . }
  OPTIONAL { ?item wdt:P402  ?osm_relation . }
}"""
    print("Fetching country index...", flush=True)
    rows = sparql_query(query)
    print(f"  {len(rows)} entries.")
    return build_index(rows)


def fetch_bundesland_index() -> dict[str, dict]:
    """Fetch German federal states and Polish voivodeships.

    Wikidata classes queried:
      Q1221156  Land in Deutschland (German federal state)
      Q150093   voivodeship of Poland

    Labels are fetched in German and Polish (lang=de,pl).
    """
    query = """
SELECT DISTINCT ?item ?label ?labelType ?geonames ?tgn ?idai ?osm_relation WHERE {
  VALUES ?class { wd:Q1221156 wd:Q150093 }
  ?item wdt:P31 ?class .
  { ?item rdfs:label ?label .   FILTER(LANG(?label) IN ("de","pl")) BIND("rdfs:label"    AS ?labelType) }
  UNION
  { ?item skos:altLabel ?label . FILTER(LANG(?label) IN ("de","pl")) BIND("skos:altLabel" AS ?labelType) }
  OPTIONAL { ?item wdt:P1566 ?geonames . }
  OPTIONAL { ?item wdt:P1667 ?tgn . }
  OPTIONAL { ?item wdt:P8217 ?idai . }
  OPTIONAL { ?item wdt:P402  ?osm_relation . }
}"""
    print("Fetching Bundesland/Voivodeship index...", flush=True)
    rows = sparql_query(query)
    print(f"  {len(rows)} entries.")
    return build_index(rows)


def fetch_kreis_index_for_bundesland(bl_qid: str, bl_name: str) -> dict[str, dict]:
    """Fetch all current administrative districts within a given Bundesland.

    Scoped by wdt:P131 (located in administrative territorial entity) pointing
    directly to *bl_qid*. This keeps result sets small (~500–3000 rows per
    Bundesland after label expansion) and avoids SPARQL timeout risks.

    Dissolved items are excluded via MINUS { ?item wdt:P582 [] } (end date).
    Short labels (≤3 chars) are filtered to exclude vehicle registration codes
    (KFZ-Kennzeichen) that appear as skos:altLabels in Wikidata.

    Labels are fetched in German and Polish (lang=de,pl) to cover both
    German Landkreise and Polish powiats in the same query pattern.
    """
    query = f"""
SELECT DISTINCT ?item ?label ?labelType ?geonames ?tgn ?idai ?osm_relation WHERE {{
  ?item wdt:P131 wd:{bl_qid} .
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
  OPTIONAL {{ ?item wdt:P1667 ?tgn . }}
  OPTIONAL {{ ?item wdt:P8217 ?idai . }}
  OPTIONAL {{ ?item wdt:P402  ?osm_relation . }}
}}
"""
    print(f"  [{bl_name} / {bl_qid}]  querying Wikidata...", flush=True)
    rows = sparql_query(query)
    print(f"    {len(rows)} entries retrieved.")
    time.sleep(REQUEST_DELAY)
    return build_index(rows)


# =============================================================================
# SECTION 4 — NORMALISATION AND FUZZY MATCHING
# =============================================================================
# Label normalisation (strip prefixes, apply aliases, check overrides) runs
# before any SPARQL index is consulted. The fuzzy_lookup function then
# searches the pre-built index using rapidfuzz token_sort_ratio, optionally
# scoped to a specific Bundesland via the stored P131 value.


def _normalise(
    raw: str,
    strip_prefixes: list[str],
    aliases: dict[str, str],
    overrides: dict[str, dict],
) -> tuple[str, str, Optional[dict]]:
    """Generic normalisation pipeline shared by all administrative levels.

    Steps applied in order:
      1. Strip known prefixes (regex, case-insensitive)
      2. Apply manual alias (e.g. abbreviation → full name)
      3. Check direct override (bypasses fuzzy matching entirely)

    Returns (normalised_value, human_readable_notes, override_entry_or_None).
    """
    notes: list[str] = []
    value = raw.strip()
    for pat in strip_prefixes:
        stripped = re.sub(pat, "", value, flags=re.IGNORECASE).strip()
        if stripped != value:
            notes.append(f"stripped -> '{stripped}'")
            value = stripped
    alias = aliases.get(value.lower())
    if alias:
        notes.append(f"alias '{value}' -> '{alias}'")
        value = alias
    override = overrides.get(value.lower())
    if override:
        notes.append(f"override -> QID={override['qid']}")
    return value, "; ".join(notes), override


def normalise_bundesland(raw: str) -> tuple[str, str, Optional[dict]]:
    return _normalise(
        raw, BUNDESLAND_STRIP_PREFIXES, BUNDESLAND_ALIASES, BUNDESLAND_OVERRIDES
    )


def normalise_kreis(raw: str) -> tuple[str, str, Optional[dict]]:
    # Replace "pow. X" with "Powiat X" before general normalisation so that
    # override keys (e.g. "powiat głogówski") and Wikidata labels match.
    value = KREIS_POW_REPLACE.sub("Powiat ", raw.strip())
    return _normalise(value, KREIS_STRIP_PREFIXES, KREIS_ALIASES, KREIS_OVERRIDES)


def fuzzy_lookup(
    name: str,
    index: dict[str, dict],
    normalisation_note: str = "",
    threshold: float = FUZZY_THRESHOLD,
    filter_p131: Optional[str] = None,
) -> MatchResult:
    """Match *name* against *index* using rapidfuzz token_sort_ratio.

    token_sort_ratio is word-order independent, which tolerates label
    variants such as "Bundesrepublik Deutschland" vs "Deutschland".

    filter_p131
        If provided, restricts candidates to index entries whose stored
        p131 or p131up value matches this Bundesland QID. Falls back
        to the full index if the filtered subset is empty (safety net for
        items whose immediate P131 parent is a Regierungsbezirk rather
        than the Bundesland itself).

    Returns a MatchResult tuple; all external ID fields will be None for
    below-threshold or no-candidate results.
    """
    query_str = name.strip().lower()

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
        return None, None, None, None, "No candidates in index", None, None, None

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
            None,
            None,
            None,
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

    return (
        entry["qid"],
        entry.get("geonames"),
        entry["label"],
        score,
        " | ".join(parts),
        entry.get("tgn"),
        entry.get("idai"),
        entry.get("osm_relation"),
    )


# =============================================================================
# SECTION 5 — LEVEL PROCESSORS
# =============================================================================
# process_level handles LAND and BUNDESLAND (global index, one pass).
# process_kreis handles the KREIS level (per-Bundesland index, scoped pass).
# Both return a cache dict and a list of report rows.

# Column suffixes written to the output CSV for every administrative level
RESULT_SUFFIXES = [
    "QID",
    "GeoNames",
    "matchLabel",
    "matchScore",
    "matchReason",
    "TGN",
    "IDAI",
    "OSM_Relation",
]


def _build_override_result(raw: str, override: dict, note: str) -> MatchResult:
    """Construct a MatchResult from an override dict entry."""
    return (
        override["qid"],
        override.get("geonames"),
        override["label"],
        1.0,
        f"Direct override | '{raw}' -> QID={override['qid']}"
        + (f" | [{note}]" if note else ""),
        override.get("tgn"),
        override.get("idai"),
        override.get("osm_relation"),
    )


def _result_to_report_row(level: str, raw: str, v: MatchResult) -> dict:
    """Convert a MatchResult tuple to a flat report-CSV row dict."""
    return {
        "level": level,
        "input_value": raw,
        "QID": v[0],
        "GeoNames": v[1],
        "matchLabel": v[2],
        "matchScore": v[3],
        "matchReason": v[4],
        "TGN": v[5],
        "IDAI": v[6],
        "OSM_Relation": v[7],
    }


def process_level(
    df: pd.DataFrame,
    col: str,
    index: dict[str, dict],
    normalise_fn=None,
) -> tuple[dict[str, MatchResult], list[dict]]:
    """Match all unique values in *col* against a pre-built label index.

    Used for LAND and BUNDESLAND where a single global index covers all rows.
    Override entries are resolved before the fuzzy lookup is attempted.
    """
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
        result: MatchResult = (
            _build_override_result(raw, override, note)
            if override
            else fuzzy_lookup(normalised, index, normalisation_note=note)
        )
        cache[raw] = result

        qid, geonames, matched_label, score, *_ = result
        status = "OK" if qid else "NO MATCH"
        score_str = f"{score:.2f}" if score is not None else "n/a"
        print(
            f"  [{status:8s}] {raw!r:35s}  QID={str(qid):10s}  "
            f"GeoNames={str(geonames):12s}  score={score_str}  "
            f"matched='{matched_label}'"
        )

    report_rows = [_result_to_report_row(col, raw, v) for raw, v in cache.items()]
    return cache, report_rows


def process_kreis(df: pd.DataFrame) -> tuple[dict[str, MatchResult], list[dict]]:
    """Match KREIS values using a separate SPARQL index per Bundesland.

    Grouping by BUNDESLAND_QID (already resolved in a prior step) scopes
    each SPARQL query via wdt:P131, keeping result sets small and preventing
    cross-Bundesland name collisions (e.g. multiple cities named "Görlitz").

    KREIS values whose BUNDESLAND_QID could not be resolved are skipped and
    flagged in the report CSV.
    """
    pairs = (
        df[["KREIS", "BUNDESLAND", "BUNDESLAND_QID"]]
        .dropna(subset=["BUNDESLAND_QID"])
        .drop_duplicates()
    )
    by_bl = pairs.groupby(["BUNDESLAND_QID", "BUNDESLAND"])

    print(
        f"\nMatching {df['KREIS'].nunique()} unique KREIS value(s) across "
        f"{len(by_bl)} Bundesland group(s) (threshold={KREIS_FUZZY_THRESHOLD})...\n"
    )

    cache: dict[str, MatchResult] = {}

    for (bl_qid, bl_name), grp in by_bl:
        kreis_index = fetch_kreis_index_for_bundesland(bl_qid, bl_name)

        for raw in grp["KREIS"].dropna().unique():
            if raw in cache:
                continue  # already resolved via an earlier Bundesland group
            normalised, note, override = normalise_kreis(raw)
            result: MatchResult = (
                _build_override_result(raw, override, note)
                if override
                else fuzzy_lookup(
                    normalised,
                    kreis_index,
                    normalisation_note=note,
                    threshold=KREIS_FUZZY_THRESHOLD,
                )
            )
            cache[raw] = result

            qid, geonames, matched_label, score, *_ = result
            status = "OK" if qid else "NO MATCH"
            score_str = f"{score:.2f}" if score is not None else "n/a"
            print(
                f"    [{status:8s}] {raw!r:35s}  QID={str(qid):10s}  "
                f"GeoNames={str(geonames):12s}  score={score_str}  "
                f"matched='{matched_label}'"
            )

    # Flag any KREIS rows where BUNDESLAND_QID was unavailable for scoping
    for raw in df["KREIS"].dropna().unique():
        if raw not in cache:
            cache[raw] = (
                None,
                None,
                None,
                None,
                "Skipped: no BUNDESLAND_QID available for scoping",
                None,
                None,
                None,
            )

    report_rows = [_result_to_report_row("KREIS", raw, v) for raw, v in cache.items()]
    return cache, report_rows


# =============================================================================
# SECTION 6 — MAIN PIPELINE
# =============================================================================
# Orchestrates the full enrichment run: load CSV → match each level →
# write outputs → print coverage summary.


def _append_columns(
    df: pd.DataFrame, prefix: str, cache: dict[str, MatchResult]
) -> None:
    """Append RESULT_SUFFIXES columns for one administrative level to *df* in place."""
    for i, suffix in enumerate(RESULT_SUFFIXES):
        df[f"{prefix}_{suffix}"] = df[prefix].map(
            lambda x, i=i: cache.get(x, NO_MATCH)[i]
        )


def _print_summary(
    df: pd.DataFrame,
    land_cache: dict,
    bl_cache: dict,
    kreis_cache: dict,
) -> None:
    """Print a per-level, per-country coverage table to stdout."""

    def _land_of(col: str, raw: str) -> str:
        rows = df[df[col] == raw]["LAND"].dropna()
        return rows.iloc[0] if len(rows) else "?"

    def _stats(subset: dict) -> tuple:
        matched = sum(1 for v in subset.values() if v[0] is not None)
        geo = sum(1 for v in subset.values() if v[1] is not None)
        tgn = sum(1 for v in subset.values() if len(v) > 5 and v[5] is not None)
        idai = sum(1 for v in subset.values() if len(v) > 6 and v[6] is not None)
        osm = sum(1 for v in subset.values() if len(v) > 7 and v[7] is not None)
        return len(subset), matched, len(subset) - matched, geo, tgn, idai, osm

    print(f"\nRows: {len(df)}\n")
    header = (
        f"  {'level':<12s}  {'scope':<6s}  {'unique':>6s}  {'matched':>7s}"
        f"  {'no_match':>8s}  {'GeoNames':>9s}  {'TGN':>6s}  {'IDAI':>6s}  {'OSM':>6s}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))

    for level, cache, col in [
        ("LAND", land_cache, "LAND"),
        ("BUNDESLAND", bl_cache, "BUNDESLAND"),
        ("KREIS", kreis_cache, "KREIS"),
    ]:
        for scope in ("DE", "PL", "total"):
            if scope == "total":
                subset = cache
            else:
                land_val = "Deutschland" if scope == "DE" else "Polen"
                subset = {
                    k: v for k, v in cache.items() if _land_of(col, k) == land_val
                }
                if not subset:
                    continue
            n, matched, no_match, geo, tgn, idai, osm = _stats(subset)
            lbl = level if scope == "DE" else ""
            print(
                f"  {lbl:<12s}  {scope:<6s}  {n:>6d}  {matched:>7d}"
                f"  {no_match:>8d}  {geo:>9d}  {tgn:>6d}  {idai:>6d}  {osm:>6d}"
            )
            if scope == "total":
                print()


def main() -> None:
    # --- Load input ----------------------------------------------------------
    input_path = HERE / INPUT_FILE
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path, sep="|", dtype=str, quotechar='"', encoding="utf-8")
    df.columns = df.columns.str.strip()

    for col in ("LAND", "BUNDESLAND", "KREIS"):
        if col not in df.columns:
            raise ValueError(f"Column '{col}' missing. Available: {list(df.columns)}")

    all_report: list[dict] = []

    # --- LAND ----------------------------------------------------------------
    country_index = fetch_country_index()
    land_cache, land_report = process_level(df, "LAND", country_index)
    all_report.extend(land_report)
    _append_columns(df, "LAND", land_cache)

    # --- BUNDESLAND ----------------------------------------------------------
    bl_index = fetch_bundesland_index()
    bl_cache, bl_report = process_level(
        df, "BUNDESLAND", bl_index, normalise_fn=normalise_bundesland
    )
    all_report.extend(bl_report)
    _append_columns(df, "BUNDESLAND", bl_cache)

    # --- KREIS ---------------------------------------------------------------
    kreis_cache, kreis_report = process_kreis(df)
    all_report.extend(kreis_report)
    _append_columns(df, "KREIS", kreis_cache)

    # --- Write mapped CSV ----------------------------------------------------
    out = HERE / OUTPUT_FILE
    df.to_csv(
        out,
        sep=OUTPUT_SEP,
        index=False,
        quoting=csv.QUOTE_ALL,
        encoding="utf-8",
        na_rep="",
    )
    print(f"\n[1/2] Mapped CSV:  {out}")

    # --- Write report CSV (sorted by score ascending for easy QA review) -----
    rep = HERE / REPORT_FILE
    pd.DataFrame(all_report).sort_values(
        ["level", "matchScore"], ascending=[True, True], na_position="first"
    ).to_csv(rep, sep=OUTPUT_SEP, index=False, quoting=csv.QUOTE_ALL, encoding="utf-8")
    print(f"[2/2] Report CSV:  {rep}")

    # --- Coverage summary ----------------------------------------------------
    _print_summary(df, land_cache, bl_cache, kreis_cache)


if __name__ == "__main__":
    main()
