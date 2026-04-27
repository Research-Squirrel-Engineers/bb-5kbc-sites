"""
bb5kbc_lod_pipeline.py — Brandenburg 5000 BC Sites: CSV to Linked Open Data.

Reads `fst_wgs84.csv` (the Schmidt 2026 site catalogue, enriched with authority
identifiers — Wikidata QIDs, GeoNames, TGN, iDAI.gazetteer, OSM relations — for
all four administrative levels via the upstream csv_enrichment.py pipeline),
applies the modelling rules defined in `bb5kbc-modelling-rules.md`, and writes
a single Turtle file `bb5kbc-data.ttl` with all triples generated from the data.
The output is then validated against auto-generated SHACL shapes derived from
`bb5kbc-ontology.ttl`; the validation report is written separately, and the
pipeline does NOT abort on shape violations (warning-only mode by default).

Project layout (relative to repository root):
    rdf/        ← this script + bb5kbc-shapes.ttl + readme
    ontology/   ← bb5kbc-ontology.ttl
    data/       ← fst_wgs84.csv  (read-only, output of csv_enrichment.py)
                 csv_enrichment_run.ttl  (upstream PROV manifest, auto-discovered)
    dist/       ← generated output (bb5kbc-data.ttl, csv_to_lod_run.ttl,
                 shacl-report.ttl, report.log)

Usage:
    Just run the script directly (e.g. F5 in VS Code, or python from the
    rdf/ directory). All settings are constants at the top of the file —
    look for the "Run settings" block in Section 2 and edit values there
    when you want non-default behaviour. No command-line arguments needed.

Inspired by the structure of `Poseidon2LOD.py` (Mattis Schmidt, ArNO project),
adapted to bb5kbc's modelling rules: MD5-based hash URIs, FID-based site URIs,
British English comments, deterministic output, no per-row PROV activities
(one global pipeline activity instead, chained to the upstream CSV-enrichment
activity via prov:wasInformedBy).

Authors: Sophie C. Schmidt, Florian Thiery · Licence: CC BY 4.0
"""

from __future__ import annotations

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
GN = Namespace("https://www.geonames.org/")


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
    "geonames":  BB5KBC["ExternalIdentifier_GeoNames"],
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

# CSV columns that are present in the schema but currently fully unpopulated.
# We don't read them for triple generation; documented for transparency.
# - perio.do (Kulturgruppe-level Perio.do URI): Sophie removed it in the
#   reviewed CSV (see bb5kbc-csv-issues.md, issue 8/empty-columns); the column
#   header is still present but every row is empty.
# - QID_publikation: filled by enrich_qids.py downstream (Pyzel 2019 and
#   Umbreit 1940 still pending Sophie's review).
EMPTY_COLUMNS = {"perio.do", "QID_publikation"}


# ---------------------------------------------------------------------------
# Run settings (formerly CLI flags — now plain constants).
# Edit these directly when you want a non-default behaviour. Each setting is
# applied unconditionally on every run; no command-line invocation needed.
# ---------------------------------------------------------------------------

# Process only the first N rows (None = process the entire CSV).
# Useful for smoke-testing changes without waiting for the full 540-row run.
RUN_LIMIT: int | None = None

# Treat SHACL violations as errors (return code 1 on violations).
# When False, the pipeline always exits cleanly; violations are only logged.
RUN_STRICT: bool = False

# Skip SHACL validation entirely (saves ~16 seconds).
# When True, no shacl-report*.ttl files are produced.
RUN_SKIP_SHACL: bool = False

# Optional override for the upstream PROV manifest. When None, the pipeline
# auto-discovers ../data/csv_enrichment_run.ttl. Set to a Path object (or a
# string path) to point at a different manifest, e.g. an archived copy.
RUN_PROV_CSV_ENRICHMENT_OVERRIDE: Path | None = None


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
    g.bind("gn", GN)


# ---------------------------------------------------------------------------
# SECTION 4: Triple builders
# ---------------------------------------------------------------------------
# Each builder adds triples for one bb5kbc class to the graph and returns the
# URI(s) it created (or an empty list if the value was missing). The orchestrator
# in main() chains them together using a `uri_dict` to share state across calls.

def _admin_node(g: Graph, label: str, klass: URIRef, prefix: str,
                tgn_id: str = "", idai_id: str = "", osm_id: str = "",
                geonames_id: str = "", wikidata_qid: str = "") -> URIRef:
    """Create or reuse an administrative-area node with optional external IDs.

    Used for Land, Bundesland, Kreis, Gemeinde — they all share the same
    pattern: hash-URI deduplicated by label, with up to five external
    identifiers attached (Wikidata, GeoNames, TGN, iDAI, OSM).
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

    if geonames_id and not _empty(geonames_id):
        ext = GN[str(geonames_id).strip()]
        g.add((uri, BB5KBC.hasExternalIdentifier, ext))
        g.add((ext, BB5KBC.hasExternalIdentifierType, EXT_ID_TYPES["geonames"]))

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
        geonames_id=row.get("LAND_GeoNames", ""),
        wikidata_qid=row.get("LAND_QID", ""),
    )
    return [uri]


def add_bundesland_triples(g, row, uri_dict):
    """Bundesland / Województwo. Linked upward to Land."""
    label = _norm_str(row.get("bundesland"))
    if not label:
        return []
    uri = _admin_node(
        g, label, BB5KBC.Bundesland, "bundesland",
        tgn_id=row.get("BUNDESLAND_TGN", ""),
        idai_id=row.get("BUNDESLAND_IDAI", ""),
        osm_id=row.get("BUNDESLAND_OSM_Relation", ""),
        geonames_id=row.get("BUNDESLAND_GeoNames", ""),
        wikidata_qid=row.get("BUNDESLAND_QID", ""),
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
        osm_id=row.get("KREIS_OSM_Relation", ""),
        geonames_id=row.get("KREIS_GeoNames", ""),
        wikidata_qid=row.get("KREIS_QID", ""),
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
        tgn_id=row.get("GEMEINDE_TGN", ""),
        idai_id=row.get("GEMEINDE_IDAI", ""),
        osm_id=row.get("GEMEINDE_OSM_Relation", ""),
        geonames_id=row.get("GEMEINDE_GeoNames", ""),
        wikidata_qid=row.get("GEMEINDE_QID", ""),
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
    """Site type. Multi-valued strings (e.g. 'Siedlung und Grab') are split.

    For values containing '?' (e.g. 'Grab?'), a dedicated, non-deduplicated
    type node is created per site, with fsl:certaintyDesc "uncertain"@en
    attached. The uncertainty is a statement about *this* assignment, not
    about the type itself, so attaching it to the deduplicated type node
    would propagate to all sites with the same type — which is wrong.
    Per Sophie's review (bb5kbc-csv-issues.md, issue 3), this is the agreed
    modelling for question-mark values.
    """
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

    # Uncertainty case ('Grab?', etc.) — dedicated node per site, with certaintyDesc.
    # URI is salted with the FID so it does not collide with the deduplicated
    # certain version of the same type (if any).
    if "?" in label:
        fid = _norm_str(row.get("FID"))
        salt = f"{label}_uncertain_{fid}"
        t_uri = DATA[f"fundstellenart_{_hash8(salt)}"]
        g.add((t_uri, RDF.type, BB5KBC.FundstellenartType))
        g.add((t_uri, RDFS.label, Literal(label, lang="de")))
        g.add((t_uri, SKOS.prefLabel, Literal(label, lang="de")))
        g.add((t_uri, FSL.certaintyDesc, Literal("uncertain", lang="en")))
        if qid:
            ext = WD[qid]
            g.add((t_uri, BB5KBC.hasExternalIdentifier, ext))
            g.add((ext, BB5KBC.hasExternalIdentifierType, EXT_ID_TYPES["wikidata"]))
        for site in sites:
            g.add((site, BB5KBC.hatFundstellenart, t_uri))
        log.info(f"Row FID={fid}: fundstellenart '{label}' marked as uncertain "
                 f"(fsl:certaintyDesc).")
        return [t_uri]

    # Single-valued, certain: one deduplicated type node
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

    For uncertain assignments (kultur ending in '?', e.g. 'SBK?'), the
    fsl:certaintyDesc "uncertain"@en is attached to the KulturelleZuordnung
    (not to the Kulturgruppe itself) — the uncertainty concerns *the
    assignment*, not the cultural group as a concept. Per Sophie's review
    (bb5kbc-csv-issues.md, issue 8).
    """
    kultur = _norm_str(row.get("kultur"))
    sites = uri_dict.get("Fundstelle", [])
    if not kultur or not sites:
        return []

    kultur_uri = DATA[f"kultur_{_hash8(kultur)}"]
    g.add((kultur_uri, RDF.type, BB5KBC.Kulturgruppe))
    g.add((kultur_uri, RDFS.label, Literal(kultur, lang="de")))

    # Kulturgruppe-level perio.do is empty in current CSV (column = "perio.do");
    # left in for forward compatibility — emits no triples while empty.
    if "perio.do" in row.index and not _empty(row.get("perio.do")):
        ext = URIRef(_norm_str(row["perio.do"]))
        g.add((kultur_uri, BB5KBC.hasExternalIdentifier, ext))
        g.add((ext, BB5KBC.hasExternalIdentifierType, EXT_ID_TYPES["periodo"]))

    zuordnung_uri = DATA[f"culture_{_hash8(kultur)}"]
    g.add((zuordnung_uri, RDF.type, BB5KBC.KulturelleZuordnung))
    g.add((zuordnung_uri, BB5KBC.hatKulturgruppe, kultur_uri))

    if "?" in kultur:
        g.add((zuordnung_uri, FSL.certaintyDesc, Literal("uncertain", lang="en")))

    for site in sites:
        g.add((site, BB5KBC.hatKulturelleZuordnung, zuordnung_uri))

    return [zuordnung_uri]


def add_datierung_triples(g, row, uri_dict, log):
    """Per-site dating node, attached to the kulturelle Zuordnung.

    Note: previous versions of this script applied hard-coded fixes for
    dating_end typos at FID 31 and 257 (positive value where negative was
    intended). These were corrected by Sophie in the reviewed CSV
    (bb5kbc-csv-issues.md, issue 1) and the runtime fix has been removed.
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

    start_lex = _lex_integer(row.get("dating_start"))
    end_lex = _lex_integer(row.get("dating_end"))
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
# SECTION 4b: PROV-O chaining
# ---------------------------------------------------------------------------
# These helpers connect the LOD pipeline's provenance to the upstream CSV
# enrichment pipeline. The upstream produces a manifest file (typically
# csv_enrichment_run.ttl) describing the multi-stage CSV-enrichment activity
# that built fst_wgs84.csv. We embed that manifest's triples into our output
# graphs, identify its top-level activity, and chain to it via wasInformedBy.

def find_top_level_prov_activity(g: Graph) -> URIRef | None:
    """Identify the top-level prov:Activity in a manifest graph.

    The "top-level" activity is the one that no other activity in the same
    graph wasInformedBy. In the csv_enrichment manifest, stage activities
    declare wasInformedBy ?top, so the top-level run is the activity that
    appears as a wasInformedBy *target* but never as a *source*.

    Falls back to: any activity that has prov:startedAtTime but no
    wasInformedBy. Returns None if the graph contains no activities.
    """
    activities = set(g.subjects(RDF.type, PROV.Activity))
    if not activities:
        return None

    # Activities that are themselves informedBy something else are sub-stages
    informed = {s for s in activities if list(g.objects(s, PROV.wasInformedBy))}
    candidates = activities - informed

    if len(candidates) == 1:
        return next(iter(candidates))
    if len(candidates) > 1:
        # Prefer the one with the earliest startedAtTime (the run that started
        # the chain). If still ambiguous, return any deterministic pick.
        with_start = [(s, list(g.objects(s, PROV.startedAtTime)))
                      for s in candidates]
        with_start = [(s, t[0]) for s, t in with_start if t]
        if with_start:
            with_start.sort(key=lambda x: str(x[1]))
            return with_start[0][0]
        return sorted(candidates, key=str)[0]
    # No candidate without wasInformedBy: graph is malformed, return None
    return None


def add_lod_pipeline_provenance(g: Graph, *,
                                 csv_path: Path,
                                 ontology_path: Path,
                                 script_path: Path,
                                 out_data: Path,
                                 out_bundle: Path,
                                 csv_enrichment_top: URIRef | None,
                                 csv_enrichment_output: URIRef | None,
                                 started_at: datetime.datetime,
                                 ended_at: datetime.datetime,
                                 row_count: int,
                                 triple_count: int) -> URIRef:
    """Add the LOD pipeline's PROV-O activity to graph `g` and return its URI.

    The activity URI uses the same scheme as the rest of the bb5kbc LOD data
    namespace (`data:pipeline_run_<timestamp>`), with the timestamp formatted
    so colons become dashes — that yields a URI-safe form analogous to the
    csv_enrichment convention (e.g. `2026-04-27T08-21-21Z`) while keeping the
    LOD's own w3id-based namespace.

    Cross-namespace chaining (csv_enrichment lives in example.org) is done
    via `prov:wasInformedBy`. Output entities (`bb5kbc_data_ttl`,
    `bb5kbc_bundle_ttl`) are declared with `prov:wasGeneratedBy` (this
    activity) and `prov:wasDerivedFrom` (the upstream output entity).
    """
    # URI-safe timestamp: 2026-04-27T08:30:15Z → 2026-04-27T08-30-15Z
    ts = started_at.strftime("%Y-%m-%dT%H-%M-%SZ")
    activity = DATA[f"pipeline_run_{ts}"]

    # --- Software agent (the script itself) -------------------------------
    script_agent = DATA["bb5kbc_lod_pipeline_py"]
    g.add((script_agent, RDF.type, PROV.SoftwareAgent))
    g.add((script_agent, RDF.type, PROV.Plan))
    g.add((script_agent, RDFS.label, Literal("bb5kbc_lod_pipeline.py")))
    g.add((script_agent, PROV.atLocation,
           URIRef(script_path.resolve().as_uri())))

    # --- Activity ----------------------------------------------------------
    g.add((activity, RDF.type, PROV.Activity))
    g.add((activity, RDFS.label,
           Literal(f"bb5kbc CSV-to-RDF pipeline run {ts}", lang="en")))
    g.add((activity, PROV.startedAtTime,
           Literal(started_at.isoformat().replace("+00:00", "Z"),
                   datatype=XSD.dateTime)))
    g.add((activity, PROV.endedAtTime,
           Literal(ended_at.isoformat().replace("+00:00", "Z"),
                   datatype=XSD.dateTime)))
    g.add((activity, PROV.wasAssociatedWith, SOPHIE_ORCID))
    g.add((activity, PROV.wasAssociatedWith, ORCID["0000-0002-3246-3531"]))
    g.add((activity, PROV.wasAssociatedWith, script_agent))

    # --- Inputs (used) -----------------------------------------------------
    # Path.as_uri() produces RFC-compliant file:// URIs on every OS,
    # including Windows (file:///C:/...). Plain f"file://{path}" breaks on
    # Windows because backslashes and the drive-letter colon are not valid
    # URI characters.
    csv_uri = URIRef(csv_path.resolve().as_uri())
    g.add((activity, PROV.used, csv_uri))
    g.add((activity, PROV.used, URIRef(ontology_path.resolve().as_uri())))

    # If we know the upstream's output-entity URI for fst_wgs84.csv, prefer
    # it (cross-namespace identity) — this lets a triplestore see that the
    # file we used IS the one csv_enrichment generated.
    if csv_enrichment_output is not None:
        g.add((activity, PROV.used, csv_enrichment_output))

    # --- Cross-pipeline chaining ------------------------------------------
    if csv_enrichment_top is not None:
        g.add((activity, PROV.wasInformedBy, csv_enrichment_top))

    # --- Output entities --------------------------------------------------
    # Two outputs: the slim data graph and the self-contained bundle. Both
    # are derived from the (upstream) fst_wgs84.csv — we declare the chain
    # explicitly so a SPARQL query can walk from any LOD triple back to the
    # source CSV, and from there into the csv_enrichment provenance.
    data_entity = DATA["bb5kbc_data_ttl"]
    g.add((data_entity, RDF.type, PROV.Entity))
    g.add((data_entity, RDFS.label,
           Literal("bb5kbc-data.ttl (LOD-converted site data)", lang="en")))
    g.add((data_entity, PROV.atLocation,
           URIRef(out_data.resolve().as_uri())))
    g.add((data_entity, PROV.wasGeneratedBy, activity))
    if csv_enrichment_output is not None:
        g.add((data_entity, PROV.wasDerivedFrom, csv_enrichment_output))
    else:
        g.add((data_entity, PROV.wasDerivedFrom, csv_uri))

    bundle_entity = DATA["bb5kbc_bundle_ttl"]
    g.add((bundle_entity, RDF.type, PROV.Entity))
    g.add((bundle_entity, RDFS.label,
           Literal("bb5kbc-bundle.ttl (data + ontology, self-contained)",
                   lang="en")))
    g.add((bundle_entity, PROV.atLocation,
           URIRef(out_bundle.resolve().as_uri())))
    g.add((bundle_entity, PROV.wasGeneratedBy, activity))
    if csv_enrichment_output is not None:
        g.add((bundle_entity, PROV.wasDerivedFrom, csv_enrichment_output))
    else:
        g.add((bundle_entity, PROV.wasDerivedFrom, csv_uri))

    # --- Run statistics (custom predicates, kept under DATA namespace) ----
    # rowCount: CSV rows successfully processed (one row per Fundstelle).
    # dataTripleCount: triples in g at the moment this activity is recorded —
    # i.e. data triples + embedded upstream PROV, but NOT yet this activity's
    # own triples. The final on-disk file is slightly larger because of the
    # ~20 PROV triples added below.
    g.add((activity, DATA.rowCount, Literal(row_count, datatype=XSD.integer)))
    g.add((activity, DATA.dataTripleCount,
           Literal(triple_count, datatype=XSD.integer)))

    return activity


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

def main():
    # ----- Path setup --------------------------------------------------------
    script_dir = Path(__file__).resolve().parent
    root = script_dir.parent

    csv_path = root / "data" / "fst_wgs84.csv"
    ontology_path = root / "ontology" / "bb5kbc-ontology.ttl"
    out_dir = root / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_data = out_dir / "bb5kbc-data.ttl"
    out_bundle = out_dir / "bb5kbc-bundle.ttl"          # data + ontology merged
    out_shapes = script_dir / "bb5kbc-shapes.ttl"   # shapes live alongside the script
    out_report = out_dir / "shacl-report.ttl"
    out_report_bundle = out_dir / "shacl-report-bundle.ttl"
    out_log = out_dir / "report.log"
    out_prov = out_dir / "csv_to_lod_run.ttl"        # this run's PROV manifest

    # Resolve csv_enrichment_run.ttl: explicit override (set in run settings
    # at the top of this file) wins over auto-discovery. Auto-discovery looks
    # at ../data/csv_enrichment_run.ttl — the natural sibling file produced
    # by the upstream pipeline. If neither is present, the LOD run still
    # works, but writes its own provenance without the upstream chain.
    if RUN_PROV_CSV_ENRICHMENT_OVERRIDE is not None:
        prov_csv_enrichment_path = Path(RUN_PROV_CSV_ENRICHMENT_OVERRIDE)
    else:
        candidate = root / "data" / "csv_enrichment_run.ttl"
        prov_csv_enrichment_path = candidate if candidate.exists() else None

    # ----- Logger ------------------------------------------------------------
    log = setup_logger(out_log)
    log.info("=" * 70)
    log.info("bb5kbc LOD pipeline — start")
    log.info("=" * 70)
    log.info(f"CSV input:        {csv_path}")
    log.info(f"Ontology input:   {ontology_path}")
    log.info(f"Data output:      {out_data}")
    log.info(f"Bundle output:    {out_bundle}")
    log.info(f"SHACL shapes:     {out_shapes}")
    log.info(f"SHACL report:     {out_report}")
    log.info(f"Bundle report:    {out_report_bundle}")
    log.info(f"PROV manifest:    {out_prov}")
    if prov_csv_enrichment_path is not None:
        log.info(f"Upstream PROV:    {prov_csv_enrichment_path}")
    else:
        log.info("Upstream PROV:    (none found — running standalone)")
    log.info(f"Log file:         {out_log}")
    log.info("")

    # ----- Read CSV ----------------------------------------------------------
    if not csv_path.exists():
        log.error(f"CSV not found: {csv_path}")
        return 1
    # The enriched CSV (output of csv_enrichment.py) is written with a UTF-8
    # BOM by project convention. utf-8-sig strips the BOM transparently and is
    # backwards-compatible with plain UTF-8 files.
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False,
                     na_values=[], encoding="utf-8-sig")
    log.info(f"Loaded CSV: {len(df)} rows, {len(df.columns)} columns")

    if RUN_LIMIT is not None:
        df = df.head(RUN_LIMIT)
        log.info(f"Limited to first {len(df)} rows (RUN_LIMIT)")

    # ----- Build data graph --------------------------------------------------
    g = Graph()
    _bind_namespaces(g)

    add_fixed_individuals(g)

    # Capture start time before row processing — the activity spans the full
    # row-processing loop, not just the provenance-writing step.
    pipeline_started_at = datetime.datetime.now(datetime.timezone.utc)

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

    # ----- Capture run timing for PROV ---------------------------------------
    pipeline_ended_at = datetime.datetime.now(datetime.timezone.utc)

    # ----- Load + embed upstream PROV (csv_enrichment_run.ttl) --------------
    # If the upstream manifest is available, parse it to a dedicated graph,
    # find its top-level activity, locate the entity that represents the CSV
    # we just consumed, and merge the manifest's triples into our data graph.
    # The same triples are also added to the bundle below — this gives a
    # cross-pipeline chain that lives inside both LOD outputs.
    csv_enrichment_top: URIRef | None = None
    csv_enrichment_output: URIRef | None = None
    upstream_graph = Graph()
    if prov_csv_enrichment_path is not None and prov_csv_enrichment_path.exists():
        try:
            upstream_graph.parse(str(prov_csv_enrichment_path), format="turtle")
            csv_enrichment_top = find_top_level_prov_activity(upstream_graph)
            log.info(f"Loaded upstream PROV: "
                     f"{len(upstream_graph)} triples, "
                     f"top-level activity: {csv_enrichment_top}")

            # Find the upstream entity for fst_wgs84.csv: any prov:Entity whose
            # prov:atLocation matches the file we read. Falls back to None if
            # nothing matches — the chain still works via wasInformedBy alone.
            csv_uri_local = URIRef(csv_path.resolve().as_uri())
            for ent in upstream_graph.subjects(RDF.type, PROV.Entity):
                locs = list(upstream_graph.objects(ent, PROV.atLocation))
                # Match on filename (the upstream paths are typically Windows
                # absolute paths that won't equal our local resolved path).
                for loc in locs:
                    if str(loc).endswith("/" + csv_path.name):
                        csv_enrichment_output = ent
                        break
                if csv_enrichment_output is not None:
                    break
            if csv_enrichment_output is not None:
                log.info(f"Identified upstream entity for {csv_path.name}: "
                         f"{csv_enrichment_output}")
            else:
                log.info(f"No upstream entity matched filename {csv_path.name} — "
                         f"chaining via wasInformedBy only.")
        except Exception as exc:
            log.warning(f"Could not parse upstream PROV manifest "
                        f"{prov_csv_enrichment_path}: {exc}")
            upstream_graph = Graph()

    # Embed upstream triples directly into the data graph. Using `+=` is
    # idempotent — duplicate triples (e.g. namespace bindings) are simply
    # not stored twice.
    if len(upstream_graph) > 0:
        g += upstream_graph
        log.info(f"Embedded upstream PROV into data graph "
                 f"(+{len(upstream_graph)} triples)")

    # ----- LOD pipeline provenance (one activity per run, not per row) -----
    pipeline_activity = add_lod_pipeline_provenance(
        g,
        csv_path=csv_path,
        ontology_path=ontology_path,
        script_path=Path(__file__),
        out_data=out_data,
        out_bundle=out_bundle,
        csv_enrichment_top=csv_enrichment_top,
        csv_enrichment_output=csv_enrichment_output,
        started_at=pipeline_started_at,
        ended_at=pipeline_ended_at,
        row_count=rows_processed,
        triple_count=len(g),
    )
    log.info(f"PROV activity: {pipeline_activity}")

    # ----- Write data graph --------------------------------------------------
    g.serialize(destination=str(out_data), format="turtle")
    log.info(f"Wrote data graph: {out_data} ({len(g)} triples)")

    # ----- Write bundle graph (data + ontology merged) ----------------------
    # The bundle is self-contained: a single TTL that loads cleanly into any
    # triplestore without needing a separate ontology import. Useful for
    # publishing, sharing, and SHACL validation that needs full class hierarchy.
    log.info("Building bundle graph (data + ontology) ...")
    bundle = Graph()
    _bind_namespaces(bundle)
    bundle += g                                         # data triples + PROV
    bundle += Graph().parse(str(ontology_path), format="turtle")  # ontology triples
    bundle.serialize(destination=str(out_bundle), format="turtle")
    log.info(f"Wrote bundle graph: {out_bundle} ({len(bundle)} triples)")

    # ----- Write standalone PROV manifest for this LOD run ------------------
    # Only the LOD-side activity triples (no upstream embedding here — the
    # upstream manifest already exists as its own file). The bundle above
    # has both, the data graph has both, and this file has just our own.
    prov_only = Graph()
    _bind_namespaces(prov_only)
    # Subject filter: anything related to our pipeline_activity, the script
    # agent, or the two output entities. We pull every triple that mentions
    # them as subject.
    prov_subjects = {pipeline_activity,
                     DATA["bb5kbc_lod_pipeline_py"],
                     DATA["bb5kbc_data_ttl"],
                     DATA["bb5kbc_bundle_ttl"]}
    for s in prov_subjects:
        for p, o in g.predicate_objects(s):
            prov_only.add((s, p, o))
    # Plus the Sophie/Florian ORCID labels (one-line ones from add_fixed_individuals)
    for p, o in g.predicate_objects(SOPHIE_ORCID):
        prov_only.add((SOPHIE_ORCID, p, o))
    prov_only.serialize(destination=str(out_prov), format="turtle")
    log.info(f"Wrote LOD PROV manifest: {out_prov} ({len(prov_only)} triples)")

    # ----- Generate SHACL shapes --------------------------------------------
    log.info("Generating SHACL shapes from ontology ...")
    shapes = generate_shacl_shapes(ontology_path)
    shapes.serialize(destination=str(out_shapes), format="turtle")
    log.info(f"Wrote shapes: {out_shapes} ({len(shapes)} triples)")

    # ----- Validate ----------------------------------------------------------
    if RUN_SKIP_SHACL:
        log.info("Skipping SHACL validation (RUN_SKIP_SHACL=True)")
        return 0

    try:
        from pyshacl import validate as shacl_validate
    except ImportError:
        log.warning("pyshacl not installed — skipping SHACL validation. "
                    "Install with: pip install pyshacl")
        return 0

    log.info("Loading shapes for validation ...")
    shapes_graph = Graph().parse(str(out_shapes), format="turtle")
    onto_graph = Graph().parse(str(ontology_path), format="turtle")

    # Validate two TTLs in turn: the slim data file, and the self-contained
    # bundle. Both go through the same shapes; results are written separately
    # so reviewers can see whether the ontology import affects validation.
    targets = [
        ("data graph",   out_data,   out_report),
        ("bundle graph", out_bundle, out_report_bundle),
    ]

    any_violations = False

    for label, target_path, report_path in targets:
        log.info(f"Validating {label} against shapes ...")
        target_graph = Graph().parse(str(target_path), format="turtle")

        conforms, report_graph, _ = shacl_validate(
            target_graph,
            shacl_graph=shapes_graph,
            ont_graph=onto_graph,
            inference="rdfs",
            meta_shacl=False,
            debug=False,
        )

        report_graph.serialize(destination=str(report_path), format="turtle")
        log.info(f"Wrote SHACL report ({label}): {report_path}")

        violations = sum(1 for _ in report_graph.subjects(RDF.type, SH.ValidationResult))
        log.info(f"SHACL validation [{label}]: "
                 f"{'PASS' if conforms else 'CONFORMS=False'} "
                 f"({violations} validation results)")

        if not conforms:
            any_violations = True
            # Print first few failure summaries to the log
            for i, vr in enumerate(report_graph.subjects(RDF.type, SH.ValidationResult)):
                if i >= 10:
                    log.info(f"  ... and more (see {report_path})")
                    break
                severity = list(report_graph.objects(vr, SH.resultSeverity))
                focus = list(report_graph.objects(vr, SH.focusNode))
                path = list(report_graph.objects(vr, SH.resultPath))
                msg = list(report_graph.objects(vr, SH.resultMessage))
                sev = severity[0].split("#")[-1] if severity else "?"
                log.info(f"  [{sev}] focus={focus[0] if focus else '?'} "
                         f"path={path[0] if path else '?'} "
                         f"msg={msg[0] if msg else ''}")

    if any_violations and RUN_STRICT:
        log.error("Strict mode (RUN_STRICT=True): SHACL violations are errors. "
                  "Exiting with code 1.")
        return 1

    log.info("=" * 70)
    log.info("bb5kbc LOD pipeline — done")
    log.info("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
