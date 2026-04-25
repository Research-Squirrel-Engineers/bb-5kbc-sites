"""
bb5kbc_lod_pipeline.py — Brandenburg 5000 BC Sites: CSV to Linked Open Data.

Reads `fst_wgs84_comma.csv` (the Schmidt 2026 site catalogue), applies the
modelling rules defined in `bb5kbc-modelling-rules.md`, and writes a single
Turtle file `bb5kbc-data.ttl` with all triples generated from the data. The
output is then validated against auto-generated SHACL shapes derived from
`bb5kbc-ontology.ttl`; the validation report is written separately, and the
pipeline does NOT abort on shape violations (warning-only mode).

Project layout (relative to repository root):
    rdf/        ← this script + bb5kbc-shapes.ttl + readme
    ontology/   ← bb5kbc-ontology.ttl
    data/       ← fst_wgs84_comma.csv  (read-only)
    dist/       ← generated output (bb5kbc-data.ttl, shacl-report.ttl, report.log)

Run from the rdf/ directory:
    python bb5kbc_lod_pipeline.py

Optional CLI flags:
    --strict        treat SHACL violations as errors (exit non-zero)
    --no-shacl      skip SHACL validation entirely
    --csv PATH      use a different CSV file
    --limit N       only process the first N rows (for testing)

Inspired by the structure of `Poseidon2LOD.py` (Mattis Schmidt, ArNO project),
adapted to bb5kbc's modelling rules: MD5-based hash URIs, FID-based site URIs,
British English comments, deterministic output, no per-row PROV activities
(one global pipeline activity instead).

Authors: Sophie C. Schmidt, Florian Thiery · Licence: CC BY 4.0
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import logging
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import (DCTERMS, FOAF, OWL, PROV, RDF, RDFS, SH, SKOS,
                               XSD)

# ---------------------------------------------------------------------------
# SECTION 1: Namespaces
# ---------------------------------------------------------------------------

# bb5kbc application ontology + data namespace
BB5KBC = Namespace("http://w3id.org/bb5kbc/ont/")
DATA = Namespace("http://w3id.org/bb5kbc/")

# Vocabularies referenced in the data
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
CRMSCI = Namespace("http://www.cidoc-crm.org/extensions/crmsci/")
FSL = Namespace("http://fuzzy-sl.squirrel.link/ontology/")
FSLWB = Namespace("https://fuzzy-sl.wikibase.cloud/entity/")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
SF = Namespace("http://www.opengis.net/ont/sf#")
TIME = Namespace("http://www.w3.org/2006/time#")
WD = Namespace("https://www.wikidata.org/entity/")
ORCID = Namespace("https://orcid.org/")

# Authority-file namespaces (used for external identifiers)
TGN = Namespace("http://vocab.getty.edu/tgn/")
IDAI = Namespace("http://gazetteer.dainst.org/place/")
OSM = Namespace("https://www.openstreetmap.org/relation/")


# ---------------------------------------------------------------------------
# SECTION 2: Configuration
# ---------------------------------------------------------------------------

# Fixed agent: the person who carried out the georeferencing for every site
SOPHIE_ORCID = URIRef("https://orcid.org/0000-0003-4696-2101")

# Fixed FSL Wikibase items used in the modelling
FSLWB_FINDSPOT = FSLWB["Q80"]               # P24 location type — every site
FSLWB_REPRESENTATIVE_POINT = FSLWB["Q126"]  # P33 point type — every geometry
FSLWB_HIGH = FSLWB["Q23"]                   # P5 certainty — genauigkeit_m = 0
FSLWB_MEDIUM = FSLWB["Q15"]                 # P5 certainty — 50–500 m
FSLWB_LOW = FSLWB["Q24"]                    # P5 certainty — 800–5000 m
FSLWB_DUBIOUS = FSLWB["Q113"]               # P5 certainty — 0,0 coordinate fault

# External identifier-type individuals (from the ontology)
EXT_ID_TYPES = {
    "wikidata":  BB5KBC["ExternalIdentifier_Wikidata"],
    "tgn":       BB5KBC["ExternalIdentifier_TGN"],
    "idai":      BB5KBC["ExternalIdentifier_iDAI"],
    "osm":       BB5KBC["ExternalIdentifier_OSM"],
    "periodo":   BB5KBC["ExternalIdentifier_PerioDo"],
}

# Multi-valued fundstellenart values that get split into multiple type nodes.
# Modelling rule 3, Sonderfall "Mehrwertige Fundstellenart": each component
# becomes its own deduplicated type node.
COMPOUND_FUNDSTELLENART = {
    "Siedlung und Grab":              [("Siedlung", "Q486972"), ("Grab", "Q173387")],
    "Kreisgrabenanlage und Siedlung": [("Kreisgrabenanlage", "Q1787688"), ("Siedlung", "Q486972")],
    "Siedlung, Brunnen":              [("Siedlung", "Q486972"), ("Brunnen", "Q43483")],
    "Siedlung, Kreisgrabenanlage":    [("Siedlung", "Q486972"), ("Kreisgrabenanlage", "Q1787688")],
}

# CSV-row-level data quality fixes. Applied during processing with a warning
# logged; the CSV file itself is never modified. Hopefully resolved upstream
# before final production runs.
DATING_END_FIXES = {
    "31":  "-4750",   # Eythra:    "+4750" → "-4750"  (typo, missing minus sign)
    "257": "-4344",   # Dyrotz 37: "+4344" → "-4344"
}

# CSV columns that are not yet populated but are part of the schema
# (for these we never attempt to read; documented for transparency)
EMPTY_COLUMNS = {"perio.do", "QID_publikation"}


# ---------------------------------------------------------------------------
# SECTION 3: Helpers
# ---------------------------------------------------------------------------

def setup_logger(log_path: Path) -> logging.Logger:
    """Configure a logger that writes to both console and a log file."""
    log = logging.getLogger("bb5kbc")
    log.setLevel(logging.INFO)
    log.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    fh.setFormatter(fmt)
    log.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)

    return log


def _empty(v) -> bool:
    """Treat None / NaN / '' / whitespace / 'nan' as empty."""
    if v is None:
        return True
    if isinstance(v, float) and pd.isna(v):
        return True
    s = str(v).strip()
    return s == "" or s.lower() == "nan"


def _norm_str(v) -> str:
    """Strip and normalise to str, return '' if empty."""
    return "" if _empty(v) else str(v).strip()


def _hash8(text: str) -> str:
    """First 8 characters of MD5(text utf-8). Used for deduplicated URIs."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:8]


def _lex_integer(v) -> str | None:
    """Canonical xsd:integer form, or None if not parseable."""
    if _empty(v):
        return None
    s = str(v).strip().replace(",", ".")
    try:
        return str(int(float(s)))
    except (ValueError, OverflowError):
        return None


def _lex_decimal(v) -> str | None:
    """Canonical xsd:decimal form, or None if not parseable. Comma → dot.

    Note: integer-valued inputs are kept without a decimal point (e.g. "100"
    rather than "100.0") for cleaner Turtle output.
    """
    if _empty(v):
        return None
    s = str(v).strip()
    m = re.search(r"[-+]?\d+(?:[.,]\d+)?", s)
    if not m:
        return None
    num = m.group(0).replace(",", ".")
    try:
        Decimal(num)
    except InvalidOperation:
        return None
    return num


def _wkt_point(x_str: str, y_str: str) -> str | None:
    """Build a 'POINT(lon lat)' WKT string from CSV x/y values.

    The CSV uses comma as decimal separator (German convention). x is longitude,
    y is latitude. Returns None for missing or 0,0 coordinates (modelling rule:
    0,0 → no geometry, certainty Q113 dubious instead).
    """
    lon = _lex_decimal(x_str)
    lat = _lex_decimal(y_str)
    if lon is None or lat is None:
        return None
    if Decimal(lon) == 0 and Decimal(lat) == 0:
        return None
    return f"POINT({lon} {lat})"


def _certainty_for_genauigkeit(genauigkeit_m: str, has_geometry: bool) -> URIRef:
    """Pick the FSL Wikibase certainty item based on accuracy in metres.

    Logic from the ontology:
        wgs84 = (0,0)        → Q113 dubious
        genauigkeit_m = 0    → Q23  high
        genauigkeit_m 50–500 → Q15  medium
        genauigkeit_m 800+   → Q24  low
    """
    if not has_geometry:
        return FSLWB_DUBIOUS
    n = _lex_decimal(genauigkeit_m)
    if n is None:
        return FSLWB_MEDIUM  # default if missing — should not happen
    val = Decimal(n)
    if val == 0:
        return FSLWB_HIGH
    if val < Decimal("500"):
        return FSLWB_MEDIUM
    return FSLWB_LOW


def _bind_namespaces(g: Graph) -> None:
    """Register all prefixes for readable Turtle output."""
    g.bind("bb5kbc", BB5KBC)
    g.bind("data", DATA)
    g.bind("crm", CRM)
    g.bind("crmsci", CRMSCI)
    g.bind("fsl", FSL)
    g.bind("fslwb", FSLWB)
    g.bind("geo", GEO)
    g.bind("sf", SF)
    g.bind("time", TIME)
    g.bind("wd", WD)
    g.bind("orcid", ORCID)
    g.bind("prov", PROV)
    g.bind("foaf", FOAF)
    g.bind("skos", SKOS)
    g.bind("dcterms", DCTERMS)


# ---------------------------------------------------------------------------
# SECTION 4: Triple builders
# ---------------------------------------------------------------------------
# Each builder adds triples for one bb5kbc class to the graph and returns the
# URI(s) it created (or an empty list if the value was missing). The orchestrator
# in main() chains them together using a `uri_dict` to share state across calls.

def _admin_node(g: Graph, label: str, klass: URIRef, prefix: str,
                tgn_id: str = "", idai_id: str = "", osm_id: str = "",
                wikidata_qid: str = "") -> URIRef:
    """Create or reuse an administrative-area node with optional external IDs.

    Used for Land, Bundesland, Kreis, Gemeinde — they all share the same
    pattern: hash-URI deduplicated by label, with up to four external
    identifiers attached.
    """
    uri = DATA[f"{prefix}_{_hash8(label)}"]

    # Triples are idempotent — adding the same triple twice is harmless in rdflib
    g.add((uri, RDF.type, klass))
    g.add((uri, RDFS.label, Literal(label, lang="de")))
    g.add((uri, SKOS.prefLabel, Literal(label, lang="de")))

    if tgn_id and not _empty(tgn_id):
        ext = TGN[str(tgn_id).strip()]
        g.add((uri, BB5KBC.hasExternalIdentifier, ext))
        g.add((ext, BB5KBC.hasExternalIdentifierType, EXT_ID_TYPES["tgn"]))

    if idai_id and not _empty(idai_id):
        ext = IDAI[str(idai_id).strip()]
        g.add((uri, BB5KBC.hasExternalIdentifier, ext))
        g.add((ext, BB5KBC.hasExternalIdentifierType, EXT_ID_TYPES["idai"]))

    if osm_id and not _empty(osm_id):
        ext = OSM[str(osm_id).strip()]
        g.add((uri, BB5KBC.hasExternalIdentifier, ext))
        g.add((ext, BB5KBC.hasExternalIdentifierType, EXT_ID_TYPES["osm"]))

    if wikidata_qid and not _empty(wikidata_qid):
        ext = WD[str(wikidata_qid).strip()]
        g.add((uri, BB5KBC.hasExternalIdentifier, ext))
        g.add((ext, BB5KBC.hasExternalIdentifierType, EXT_ID_TYPES["wikidata"]))

    return uri


def add_land_triples(g, row, uri_dict):
    """Land (country) — only Deutschland and Polen in the dataset."""
    label = _norm_str(row.get("land"))
    if not label:
        return []
    uri = _admin_node(
        g, label, BB5KBC.Land, "land",
        tgn_id=row.get("LAND_TGN", ""),
        idai_id=row.get("LAND_IDAI", ""),
        osm_id=row.get("LAND_OSM_Relation", ""),
    )
    return [uri]


def add_bundesland_triples(g, row, uri_dict):
    """Bundesland / Województwo. Linked upward to Land."""
    label = _norm_str(row.get("bundesland"))
    if not label:
        return []
    uri = _admin_node(
        g, label, BB5KBC.Bundesland, "bundesland",
        tgn_id=row.get("BL_TGN", ""),
        idai_id=row.get("BL_IDAI", ""),
        osm_id=row.get("BL_OSM_RELATION", ""),
    )
    for land_uri in uri_dict.get("Land", []):
        g.add((uri, BB5KBC.inLand, land_uri))
    return [uri]


def add_kreis_triples(g, row, uri_dict):
    """Kreis / Powiat. Linked upward to Bundesland."""
    label = _norm_str(row.get("kreis"))
    if not label:
        return []
    uri = _admin_node(
        g, label, BB5KBC.Kreis, "kreis",
        tgn_id=row.get("KREIS_TGN", ""),
        idai_id=row.get("KREIS_IDAI", ""),
        osm_id=row.get("KREIS_OSM_RELATION", ""),
    )
    for bl_uri in uri_dict.get("Bundesland", []):
        g.add((uri, BB5KBC.inBundesland, bl_uri))
    return [uri]


def add_gemeinde_triples(g, row, uri_dict):
    """Gemeinde / Gmina. Linked upward to Kreis."""
    label = _norm_str(row.get("gemeinde"))
    if not label:
        return []
    uri = _admin_node(
        g, label, BB5KBC.Gemeinde, "gemeinde",
        tgn_id=row.get("GEM_TGN", ""),
        idai_id=row.get("GEM_IDAI", ""),
        osm_id=row.get("GEM_OSM_RELATION", ""),
    )
    for kreis_uri in uri_dict.get("Kreis", []):
        g.add((uri, BB5KBC.inKreis, kreis_uri))
    return [uri]


def add_fundstelle_triples(g, row, uri_dict, log):
    """The site itself: FID-based URI, identifiers, label, links to admin areas."""
    fid = _norm_str(row.get("FID"))
    if not fid:
        log.warning(f"Row {row.name}: empty FID, skipping site creation")
        return []
    uri = DATA[f"site_{fid}"]
    g.add((uri, RDF.type, BB5KBC.Fundstelle))

    # Identifiers
    g.add((uri, BB5KBC.hatFID, Literal(fid, datatype=XSD.integer)))
    g.add((uri, DCTERMS.identifier, Literal(fid, datatype=XSD.integer)))

    if not _empty(row.get("fst_id")):
        g.add((uri, BB5KBC.hatFundstellenID, Literal(_norm_str(row["fst_id"]))))
    if not _empty(row.get("katalognr")):
        g.add((uri, BB5KBC.hatKatalognummer, Literal(_norm_str(row["katalognr"]))))

    # Labels
    name = _norm_str(row.get("fst_name"))
    if name:
        g.add((uri, RDFS.label, Literal(name, lang="de")))
        g.add((uri, SKOS.prefLabel, Literal(name, lang="de")))

    # Link to administrative containment (only the lowest non-empty level)
    for gemeinde_uri in uri_dict.get("Gemeinde", []):
        g.add((uri, BB5KBC.inGemeinde, gemeinde_uri))

    # Spatial accuracy
    gen_lex = _lex_decimal(row.get("genauigkeit_m"))
    if gen_lex is not None:
        g.add((uri, BB5KBC.hatGenauigkeit, Literal(gen_lex, datatype=XSD.decimal)))

    # Findspot location-type (constant for all sites)
    g.add((uri, FSL.hasLocationType, FSLWB_FINDSPOT))

    # Certainty derived from genauigkeit_m + presence of geometry
    wkt = _wkt_point(row.get("wgs84_x"), row.get("wgs84_y"))
    g.add((uri, FSL.certaintyLevel,
           _certainty_for_genauigkeit(row.get("genauigkeit_m", ""), wkt is not None)))

    return [uri]


def _typed_node(g: Graph, label: str, prefix: str, klass: URIRef,
                qid: str = "") -> URIRef:
    """Create or reuse a type node (Fundstellenart, Entdeckungsart, ...).

    Hash-URI based on the hash key (label or QID — caller decides via prefix).
    Adds rdfs:label and an optional Wikidata external identifier.
    """
    uri = DATA[f"{prefix}_{_hash8(label)}"]
    g.add((uri, RDF.type, klass))
    g.add((uri, RDFS.label, Literal(label, lang="de")))
    g.add((uri, SKOS.prefLabel, Literal(label, lang="de")))
    if qid and not _empty(qid):
        ext = WD[str(qid).strip()]
        g.add((uri, BB5KBC.hasExternalIdentifier, ext))
        g.add((ext, BB5KBC.hasExternalIdentifierType, EXT_ID_TYPES["wikidata"]))
    return uri


def add_fundstellenart_triples(g, row, uri_dict, log):
    """Site type. Multi-valued strings (e.g. 'Siedlung und Grab') are split."""
    label = _norm_str(row.get("fundstellenart"))
    qid = _norm_str(row.get("QID_fundstellenart"))
    if not label:
        return []

    sites = uri_dict.get("Fundstelle", [])
    if not sites:
        return []

    # Compound case — split into multiple type nodes
    if label in COMPOUND_FUNDSTELLENART:
        type_uris = []
        for component_label, component_qid in COMPOUND_FUNDSTELLENART[label]:
            t_uri = _typed_node(g, component_label, "fundstellenart",
                                BB5KBC.FundstellenartType, component_qid)
            for site in sites:
                g.add((site, BB5KBC.hatFundstellenart, t_uri))
            type_uris.append(t_uri)
        log.info(f"Row {row.name}: split fundstellenart '{label}' into "
                 f"{len(type_uris)} components")
        return type_uris

    # Single-valued: one type node, label = original CSV value (preserves '?')
    t_uri = _typed_node(g, label, "fundstellenart",
                        BB5KBC.FundstellenartType, qid)
    for site in sites:
        g.add((site, BB5KBC.hatFundstellenart, t_uri))
    return [t_uri]


def add_entdeckung_triples(g, row, uri_dict):
    """Discovery event + its type (skipped if no QID is present)."""
    label = _norm_str(row.get("entdeckung"))
    qid = _norm_str(row.get("QID_entdeckung"))
    sites = uri_dict.get("Fundstelle", [])
    if not label or not sites:
        return []

    fid = _norm_str(row.get("FID"))
    e_uri = DATA[f"site_{fid}_discovery"]
    g.add((e_uri, RDF.type, BB5KBC.Entdeckung))
    g.add((e_uri, RDFS.label, Literal(label, lang="de")))

    for site in sites:
        g.add((site, BB5KBC.wurdeEntdecktDurch, e_uri))

    # Discovery type — only if QID is set (rule: skip nodes without QID)
    if qid:
        t_uri = _typed_node(g, label, "entdeckungsart",
                            BB5KBC.EntdeckungsartType, qid)
        g.add((e_uri, BB5KBC.hatEntdeckungsart, t_uri))

    return [e_uri]


def add_publikation_triples(g, row, uri_dict):
    """Publication node referenced by `publikation_arch` + optional Wikidata QID."""
    label = _norm_str(row.get("publikation_arch"))
    qid = _norm_str(row.get("QID_publikation"))
    sites = uri_dict.get("Fundstelle", [])
    if not label or not sites:
        return []

    p_uri = DATA[f"pub_{_hash8(label)}"]
    g.add((p_uri, RDF.type, BB5KBC.Publikation))
    g.add((p_uri, RDFS.label, Literal(label, lang="de")))

    if qid:
        ext = WD[qid]
        g.add((p_uri, BB5KBC.hasExternalIdentifier, ext))
        g.add((ext, BB5KBC.hasExternalIdentifierType, EXT_ID_TYPES["wikidata"]))

    for site in sites:
        g.add((site, BB5KBC.hatPublikation, p_uri))
    return [p_uri]


def add_kulturelle_zuordnung_triples(g, row, uri_dict):
    """Cultural assignment node + the Kulturgruppe it points to.

    URI strategy: culture_{hash} where hash is the kultur-value hash. This
    means all sites with the same Kulturgruppe share the same KulturelleZuordnung
    *for the dataset as a whole* — which is the intended deduplication.
    """
    kultur = _norm_str(row.get("kultur"))
    sites = uri_dict.get("Fundstelle", [])
    if not kultur or not sites:
        return []

    kultur_uri = DATA[f"kultur_{_hash8(kultur)}"]
    g.add((kultur_uri, RDF.type, BB5KBC.Kulturgruppe))
    g.add((kultur_uri, RDFS.label, Literal(kultur, lang="de")))

    # Kulturgruppe-level perio.do is empty in current CSV (column = "perio.do")
    if "perio.do" in row.index and not _empty(row.get("perio.do")):
        ext = URIRef(_norm_str(row["perio.do"]))
        g.add((kultur_uri, BB5KBC.hasExternalIdentifier, ext))
        g.add((ext, BB5KBC.hasExternalIdentifierType, EXT_ID_TYPES["periodo"]))

    zuordnung_uri = DATA[f"culture_{_hash8(kultur)}"]
    g.add((zuordnung_uri, RDF.type, BB5KBC.KulturelleZuordnung))
    g.add((zuordnung_uri, BB5KBC.hatKulturgruppe, kultur_uri))

    for site in sites:
        g.add((site, BB5KBC.hatKulturelleZuordnung, zuordnung_uri))

    return [zuordnung_uri]


def add_datierung_triples(g, row, uri_dict, log):
    """Per-site dating node, attached to the kulturelle Zuordnung.

    Hard-coded fixes for known data errors in dating_end (FID 31, 257) — these
    are applied with a logged warning and should be removed once the CSV is
    corrected upstream.
    """
    zuordnung = uri_dict.get("KulturelleZuordnung", [])
    if not zuordnung:
        return []

    fid = _norm_str(row.get("FID"))
    kultur = _norm_str(row.get("kultur"))
    # URI follows mapping: derived from the KulturelleZuordnung hash + "_dating"
    d_uri = DATA[f"culture_{_hash8(kultur)}_dating"]
    g.add((d_uri, RDF.type, BB5KBC.Datierung))
    # Dual anchoring (CRM E52 + OWL Time Interval) flows from the ontology;
    # we only add the bb5kbc:Datierung type here.

    # Apply known dating_end fixes
    raw_end = _norm_str(row.get("dating_end"))
    if fid in DATING_END_FIXES and raw_end == DATING_END_FIXES[fid].lstrip("-"):
        # Original value is the positive variant; replace with the corrected one
        log.warning(f"Row FID={fid}: dating_end '{raw_end}' looks like a typo "
                    f"(missing minus sign). Corrected to '{DATING_END_FIXES[fid]}'. "
                    f"Please fix in the CSV.")
        raw_end = DATING_END_FIXES[fid]

    start_lex = _lex_integer(row.get("dating_start"))
    end_lex = _lex_integer(raw_end)
    if start_lex is not None:
        g.add((d_uri, BB5KBC.datierungStart, Literal(start_lex, datatype=XSD.integer)))
    if end_lex is not None:
        g.add((d_uri, BB5KBC.datierungEnd, Literal(end_lex, datatype=XSD.integer)))

    # Certainty descriptions (free text)
    for csv_col, prop in [
        ("dating_certainty_start", BB5KBC.datierungSicherheitStart),
        ("dating_certainty_end",   BB5KBC.datierungSicherheitEnd),
        ("dating_certainty_range", BB5KBC.datierungSicherheitRange),
    ]:
        v = _norm_str(row.get(csv_col))
        if v:
            g.add((d_uri, prop, Literal(v)))

    # Dating method (Wikidata QID; deduplicated by QID hash)
    method_qid = _norm_str(row.get("dating_method"))
    if method_qid:
        m_uri = DATA[f"datmethode_{_hash8(method_qid)}"]
        g.add((m_uri, RDF.type, BB5KBC.DatierungsMethodeType))
        g.add((m_uri, BB5KBC.hasExternalIdentifier, WD[method_qid]))
        g.add((WD[method_qid], BB5KBC.hasExternalIdentifierType,
               EXT_ID_TYPES["wikidata"]))
        g.add((d_uri, BB5KBC.datierungMethode, m_uri))

    # Perio.do match (variable predicate based on dating_perio.do_match)
    perio_uri = _norm_str(row.get("dating_perio.do"))
    perio_match = _norm_str(row.get("dating_perio.do_match"))
    if perio_uri:
        match_prop = {
            "exactMatch":   SKOS.exactMatch,
            "closeMatch":   SKOS.closeMatch,
            "relatedMatch": SKOS.relatedMatch,
        }.get(perio_match, SKOS.relatedMatch)  # default if missing
        if not perio_match:
            log.info(f"Row FID={fid}: dating_perio.do present but no match level "
                     f"specified — defaulting to skos:relatedMatch.")
        g.add((d_uri, match_prop, URIRef(perio_uri)))

    # Link to the KulturelleZuordnung (one per row)
    for z_uri in zuordnung:
        g.add((z_uri, BB5KBC.hatDatierung, d_uri))

    return [d_uri]


def add_scherbe_triples(g, row, uri_dict):
    """Sherds (1-n Wikidata QIDs, separated by '|')."""
    raw = _norm_str(row.get("sherd"))
    sites = uri_dict.get("Fundstelle", [])
    if not raw or not sites:
        return []

    sherd_uris = []
    for qid in (q.strip() for q in raw.split("|") if q.strip()):
        s_uri = DATA[f"sherd_{_hash8(qid)}"]
        g.add((s_uri, RDF.type, BB5KBC.Scherbe))
        g.add((s_uri, BB5KBC.hasExternalIdentifier, WD[qid]))
        g.add((WD[qid], BB5KBC.hasExternalIdentifierType, EXT_ID_TYPES["wikidata"]))
        for site in sites:
            g.add((site, BB5KBC.hatScherbe, s_uri))
        sherd_uris.append(s_uri)
    return sherd_uris


def add_georeferenzierung_triples(g, row, uri_dict):
    """Georeferencing activity + sf:Point geometry. FSL Wikibase pattern."""
    sites = uri_dict.get("Fundstelle", [])
    if not sites:
        return []

    fid = _norm_str(row.get("FID"))
    a_uri = DATA[f"site_{fid}_activity"]
    g.add((a_uri, RDF.type, BB5KBC.GeoreferenzierungsAktivitaet))
    g.add((a_uri, RDFS.label,
           Literal(f"Georeferenzierung von Fundstelle {fid}", lang="de")))

    # Sources, methods (FSL properties — kept direct per modelling decision)
    quelle = _norm_str(row.get("quelle_georef"))
    if quelle:
        g.add((a_uri, FSL.hasReference, Literal(quelle)))   # P25 string
    qid_quelle = _norm_str(row.get("QID_quelle_georef"))
    if qid_quelle:
        g.add((a_uri, FSL.hasReference, WD[qid_quelle]))    # P31 URI

    methode = _norm_str(row.get("methode"))
    if methode:
        m_uri = DATA[f"methode_{_hash8(methode)}"]
        g.add((m_uri, RDF.type, FSL.MethodType))
        g.add((m_uri, RDFS.label, Literal(methode, lang="de")))
        g.add((a_uri, FSL.methodUsed, m_uri))               # P7

    quellentyp = _norm_str(row.get("quellen_typ"))
    if quellentyp:
        q_uri = DATA[f"quellentyp_{_hash8(quellentyp)}"]
        g.add((q_uri, RDF.type, FSL.SourceType))
        g.add((q_uri, RDFS.label, Literal(quellentyp, lang="de")))
        g.add((a_uri, FSL.hasSourceType, q_uri))            # P6
        g.add((a_uri, FSL.hasSourceTypeDetail, q_uri))      # P16

    methodenbeschr = _norm_str(row.get("methodenbeschr"))
    if methodenbeschr:
        g.add((a_uri, FSL.activityDesc, Literal(methodenbeschr)))   # P15

    # Fixed agent (Sophie)
    g.add((a_uri, FSL.georeferencingBy, SOPHIE_ORCID))      # P14
    g.add((a_uri, PROV.wasAssociatedWith, SOPHIE_ORCID))

    # Link from site to activity (typed subproperty of prov:wasGeneratedBy)
    for site in sites:
        g.add((site, BB5KBC.wurdeGeoreferenziertDurch, a_uri))

    # Geometry (only if coordinates are valid and not 0,0)
    wkt = _wkt_point(row.get("wgs84_x"), row.get("wgs84_y"))
    if wkt is not None:
        geom_uri = DATA[f"site_{fid}_geom"]
        g.add((geom_uri, RDF.type, SF.Point))
        g.add((geom_uri, GEO.asWKT, Literal(wkt, datatype=GEO.wktLiteral)))
        g.add((geom_uri, FSL.hasPointType, FSLWB_REPRESENTATIVE_POINT))   # P33
        for site in sites:
            g.add((site, GEO.hasGeometry, geom_uri))
            g.add((site, FSL.representativeGeometry, geom_uri))

    return [a_uri]


def add_fixed_individuals(g):
    """Add the fixed individuals (Sophie + FSL Wikibase items + ext-id types).

    These are referenced from data rows but defined in the ontology. Adding
    them to the data graph too makes the data file self-explanatory when read
    in isolation (e.g. for SHACL validation against shapes that test types).
    """
    g.add((SOPHIE_ORCID, RDF.type, FOAF.Person))
    g.add((SOPHIE_ORCID, RDFS.label, Literal("Sophie C. Schmidt")))
    g.add((SOPHIE_ORCID, SKOS.prefLabel, Literal("Sophie C. Schmidt")))




# ---------------------------------------------------------------------------
# SECTION 5: SHACL shapes generator
# ---------------------------------------------------------------------------

def generate_shacl_shapes(ontology_path: Path) -> Graph:
    """Generate SHACL shapes from the bb5kbc ontology.

    Strategy:
    1. For every bb5kbc:* class, declare a sh:NodeShape with sh:targetClass.
    2. For each bb5kbc owl:ObjectProperty whose domain is a bb5kbc class, add
       a sh:property constraint with sh:path + sh:class (= range).
    3. For each bb5kbc owl:DatatypeProperty whose domain is a bb5kbc class,
       add a sh:property constraint with sh:path + sh:datatype (= range).
    4. For Fundstelle: add a hard rule that hatFID is required (minCount 1).

    The generated shapes are kept conservative: cardinality constraints are
    only emitted where we are confident (e.g. mandatory FID, single
    KulturelleZuordnung). All other shapes are advisory.

    The output graph is self-contained — it can be saved and used independently.
    """
    onto = Graph()
    onto.parse(str(ontology_path), format="turtle")

    shapes = Graph()
    _bind_namespaces(shapes)
    shapes.bind("sh", SH)

    # Shapes namespace
    SHAPES_NS = Namespace("http://w3id.org/bb5kbc/shapes/")
    shapes.bind("shape", SHAPES_NS)

    # Header
    shapes_meta = SHAPES_NS[""]
    shapes.add((shapes_meta, RDF.type, OWL.Ontology))
    shapes.add((shapes_meta, DCTERMS.title,
                Literal("bb5kbc SHACL shapes (auto-generated)", lang="en")))
    shapes.add((shapes_meta, DCTERMS.description,
                Literal("Generated from bb5kbc-ontology.ttl by "
                        "bb5kbc_lod_pipeline.py. Do not edit manually — "
                        "regenerate from the ontology instead.", lang="en")))
    shapes.add((shapes_meta, DCTERMS.creator, Literal("Sophie C. Schmidt")))
    shapes.add((shapes_meta, DCTERMS.creator, Literal("Florian Thiery")))

    # Collect bb5kbc classes
    bb_classes = set()
    for c in onto.subjects(RDF.type, OWL.Class):
        if str(c).startswith(str(BB5KBC)):
            bb_classes.add(c)

    # Collect bb5kbc properties with domain + range
    bb_obj_props = []
    bb_dt_props = []
    for p in onto.subjects(RDF.type, OWL.ObjectProperty):
        if not str(p).startswith(str(BB5KBC)):
            continue
        domains = list(onto.objects(p, RDFS.domain))
        ranges = list(onto.objects(p, RDFS.range))
        if not domains or not ranges:
            continue
        # Skip the catch-all hasExternalIdentifier (domain owl:Thing)
        if str(domains[0]) == str(OWL.Thing):
            continue
        bb_obj_props.append((p, domains[0], ranges[0]))
    for p in onto.subjects(RDF.type, OWL.DatatypeProperty):
        if not str(p).startswith(str(BB5KBC)):
            continue
        domains = list(onto.objects(p, RDFS.domain))
        ranges = list(onto.objects(p, RDFS.range))
        if not domains or not ranges:
            continue
        bb_dt_props.append((p, domains[0], ranges[0]))

    # Build one NodeShape per class
    for cls in sorted(bb_classes, key=str):
        local = str(cls).replace(str(BB5KBC), "")
        shape_uri = SHAPES_NS[local + "Shape"]
        shapes.add((shape_uri, RDF.type, SH.NodeShape))
        shapes.add((shape_uri, SH.targetClass, cls))
        shapes.add((shape_uri, RDFS.label,
                    Literal(f"Shape for bb5kbc:{local}", lang="en")))

        # Object property constraints whose domain is this class
        for p, dom, rng in bb_obj_props:
            if dom != cls:
                continue
            from rdflib import BNode
            constraint = BNode()
            shapes.add((shape_uri, SH.property, constraint))
            shapes.add((constraint, SH.path, p))
            shapes.add((constraint, SH["class"], rng))
            shapes.add((constraint, SH.severity, SH.Warning))

        # Datatype property constraints whose domain is this class
        for p, dom, rng in bb_dt_props:
            if dom != cls:
                continue
            from rdflib import BNode
            constraint = BNode()
            shapes.add((shape_uri, SH.property, constraint))
            shapes.add((constraint, SH.path, p))
            shapes.add((constraint, SH.datatype, rng))
            shapes.add((constraint, SH.severity, SH.Warning))

    # Mandatory rule: every Fundstelle must have a hatFID
    fid_constraint = SHAPES_NS["FundstelleShape_hatFID_required"]
    fundstelle_shape = SHAPES_NS["FundstelleShape"]
    shapes.add((fundstelle_shape, SH.property, fid_constraint))
    shapes.add((fid_constraint, SH.path, BB5KBC.hatFID))
    shapes.add((fid_constraint, SH.minCount, Literal(1, datatype=XSD.integer)))
    shapes.add((fid_constraint, SH.maxCount, Literal(1, datatype=XSD.integer)))
    shapes.add((fid_constraint, SH.datatype, XSD.integer))
    shapes.add((fid_constraint, SH.severity, SH.Violation))
    shapes.add((fid_constraint, RDFS.label,
                Literal("Every Fundstelle must have exactly one hatFID.", lang="en")))

    return shapes


# ---------------------------------------------------------------------------
# SECTION 6: Main orchestrator
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--csv", default=None,
                   help="Path to CSV file (default: ../data/fst_wgs84_comma.csv)")
    p.add_argument("--ontology", default=None,
                   help="Path to bb5kbc ontology .ttl (default: ../ontology/bb5kbc-ontology.ttl)")
    p.add_argument("--out-dir", default=None,
                   help="Output directory (default: ../dist)")
    p.add_argument("--limit", type=int, default=None,
                   help="Process only the first N CSV rows (debugging)")
    p.add_argument("--strict", action="store_true",
                   help="Fail on SHACL violations (default: warn only)")
    p.add_argument("--no-shacl", action="store_true",
                   help="Skip SHACL validation entirely")
    return p.parse_args()


def main():
    args = parse_args()

    # ----- Path setup --------------------------------------------------------
    script_dir = Path(__file__).resolve().parent
    root = script_dir.parent

    csv_path = Path(args.csv) if args.csv else root / "data" / "fst_wgs84_comma.csv"
    ontology_path = Path(args.ontology) if args.ontology else root / "ontology" / "bb5kbc-ontology.ttl"
    out_dir = Path(args.out_dir) if args.out_dir else root / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_data = out_dir / "bb5kbc-data.ttl"
    out_shapes = script_dir / "bb5kbc-shapes.ttl"   # shapes live alongside the script
    out_report = out_dir / "shacl-report.ttl"
    out_log = out_dir / "report.log"

    # ----- Logger ------------------------------------------------------------
    log = setup_logger(out_log)
    log.info("=" * 70)
    log.info("bb5kbc LOD pipeline — start")
    log.info("=" * 70)
    log.info(f"CSV input:        {csv_path}")
    log.info(f"Ontology input:   {ontology_path}")
    log.info(f"Data output:      {out_data}")
    log.info(f"SHACL shapes:     {out_shapes}")
    log.info(f"SHACL report:     {out_report}")
    log.info(f"Log file:         {out_log}")
    log.info("")

    # ----- Read CSV ----------------------------------------------------------
    if not csv_path.exists():
        log.error(f"CSV not found: {csv_path}")
        return 1
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, na_values=[])
    log.info(f"Loaded CSV: {len(df)} rows, {len(df.columns)} columns")

    if args.limit is not None:
        df = df.head(args.limit)
        log.info(f"Limited to first {len(df)} rows (--limit)")

    # ----- Build data graph --------------------------------------------------
    g = Graph()
    _bind_namespaces(g)

    add_fixed_individuals(g)

    log.info("Processing rows ...")
    rows_processed = 0
    rows_skipped = 0
    for index, row in df.iterrows():
        # Skip rows with no FID — cannot be uniquely identified
        if _empty(row.get("FID")):
            log.warning(f"Row {index}: empty FID — skipping entire row")
            rows_skipped += 1
            continue

        uri_dict = {}

        uri_dict["Land"] = add_land_triples(g, row, uri_dict)
        uri_dict["Bundesland"] = add_bundesland_triples(g, row, uri_dict)
        uri_dict["Kreis"] = add_kreis_triples(g, row, uri_dict)
        uri_dict["Gemeinde"] = add_gemeinde_triples(g, row, uri_dict)

        uri_dict["Fundstelle"] = add_fundstelle_triples(g, row, uri_dict, log)
        if not uri_dict["Fundstelle"]:
            rows_skipped += 1
            continue

        uri_dict["Fundstellenart"] = add_fundstellenart_triples(g, row, uri_dict, log)
        uri_dict["Entdeckung"] = add_entdeckung_triples(g, row, uri_dict)
        uri_dict["Publikation"] = add_publikation_triples(g, row, uri_dict)
        uri_dict["KulturelleZuordnung"] = add_kulturelle_zuordnung_triples(g, row, uri_dict)
        uri_dict["Datierung"] = add_datierung_triples(g, row, uri_dict, log)
        uri_dict["Scherbe"] = add_scherbe_triples(g, row, uri_dict)
        uri_dict["Activity"] = add_georeferenzierung_triples(g, row, uri_dict)

        rows_processed += 1

    log.info(f"Processed: {rows_processed} rows, skipped: {rows_skipped}")
    log.info(f"Generated graph: {len(g)} triples")

    # ----- Pipeline-level provenance (one activity per run, not per row) ----
    now = datetime.datetime.now(datetime.timezone.utc)
    pipeline_activity = DATA[f"pipeline_run_{now.strftime('%Y%m%dT%H%M%SZ')}"]
    g.add((pipeline_activity, RDF.type, PROV.Activity))
    g.add((pipeline_activity, RDFS.label,
           Literal("bb5kbc CSV-to-RDF pipeline run", lang="en")))
    g.add((pipeline_activity, PROV.wasAssociatedWith, SOPHIE_ORCID))
    g.add((pipeline_activity, PROV.wasAssociatedWith,
           ORCID["0000-0002-3246-3531"]))   # Florian
    g.add((pipeline_activity, PROV.startedAtTime,
           Literal(now.isoformat().replace("+00:00", "Z"),
                   datatype=XSD.dateTime)))
    # Path.as_uri() produces RFC-compliant file:// URIs on every OS,
    # including Windows (file:///C:/...). Plain f"file://{path}" breaks on
    # Windows because backslashes and the drive-letter colon are not valid
    # URI characters.
    g.add((pipeline_activity, PROV.used, URIRef(csv_path.resolve().as_uri())))
    g.add((pipeline_activity, PROV.used, URIRef(ontology_path.resolve().as_uri())))

    # ----- Write data graph --------------------------------------------------
    g.serialize(destination=str(out_data), format="turtle")
    log.info(f"Wrote data graph: {out_data} ({len(g)} triples)")

    # ----- Generate SHACL shapes --------------------------------------------
    log.info("Generating SHACL shapes from ontology ...")
    shapes = generate_shacl_shapes(ontology_path)
    shapes.serialize(destination=str(out_shapes), format="turtle")
    log.info(f"Wrote shapes: {out_shapes} ({len(shapes)} triples)")

    # ----- Validate ----------------------------------------------------------
    if args.no_shacl:
        log.info("Skipping SHACL validation (--no-shacl)")
        return 0

    try:
        from pyshacl import validate as shacl_validate
    except ImportError:
        log.warning("pyshacl not installed — skipping SHACL validation. "
                    "Install with: pip install pyshacl")
        return 0

    log.info("Validating data graph against shapes ...")

    # Load fresh graphs from disk to validate the produced files (not in-memory)
    data_graph = Graph().parse(str(out_data), format="turtle")
    shapes_graph = Graph().parse(str(out_shapes), format="turtle")
    onto_graph = Graph().parse(str(ontology_path), format="turtle")

    conforms, report_graph, report_text = shacl_validate(
        data_graph,
        shacl_graph=shapes_graph,
        ont_graph=onto_graph,
        inference="rdfs",
        meta_shacl=False,
        debug=False,
    )

    report_graph.serialize(destination=str(out_report), format="turtle")
    log.info(f"Wrote SHACL report: {out_report}")

    # Count violations and warnings
    violations = sum(1 for _ in report_graph.subjects(RDF.type, SH.ValidationResult))
    log.info(f"SHACL validation: {'PASS' if conforms else 'CONFORMS=False'} "
             f"({violations} validation results)")

    if not conforms:
        # Print first few failure summaries to the log
        for i, vr in enumerate(report_graph.subjects(RDF.type, SH.ValidationResult)):
            if i >= 10:
                log.info(f"  ... and more (see {out_report})")
                break
            severity = list(report_graph.objects(vr, SH.resultSeverity))
            focus = list(report_graph.objects(vr, SH.focusNode))
            path = list(report_graph.objects(vr, SH.resultPath))
            msg = list(report_graph.objects(vr, SH.resultMessage))
            sev = severity[0].split("#")[-1] if severity else "?"
            log.info(f"  [{sev}] focus={focus[0] if focus else '?'} "
                     f"path={path[0] if path else '?'} "
                     f"msg={msg[0] if msg else ''}")

        if args.strict:
            log.error("Strict mode: SHACL violations are errors. Exiting with code 1.")
            return 1

    log.info("=" * 70)
    log.info("bb5kbc LOD pipeline — done")
    log.info("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
