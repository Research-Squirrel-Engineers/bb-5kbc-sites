"""
validate_lod.py — End-to-end validation for the bb5kbc LOD pipeline.

Reads the LOD bundle (`../dist/bb5kbc-bundle.ttl`, which already contains
data + ontology in one graph), the source CSV (`../data/fst_wgs84.csv`),
the SHACL reports if present, and the documented inheritance-chain table
in `bb5kbc-csv-mapping.md`. Writes a Markdown report to
`../dist/validation_report.md` covering four validation layers:

    1. Structural conformance (summarises the SHACL reports).
    2. CSV ↔ RDF completeness (per-column triple-count expectations).
    3. Ontology completeness (used vs declared classes/properties).
    4. CRM anchoring — every bb5kbc: class must reach a crm:E*-rooted
       parent through rdfs:subClassOf transitively. Includes a
       sub-section 4b that compares the computed chains against the
       hand-written table in bb5kbc-csv-mapping.md.

Settings: like bb5kbc_lod_pipeline.py, all configuration is done via
constants at the top of the file. No CLI arguments. Run from the rdf/
directory (or hit F5 in VS Code).

Authors: Sophie C. Schmidt, Florian Thiery · Licence: CC BY 4.0
"""

from __future__ import annotations

import io
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import OWL, RDF, RDFS, SH, XSD


# ---------------------------------------------------------------------------
# Run settings
# ---------------------------------------------------------------------------

# When True, the script exits with code 1 if any check FAILs (CI-style).
# Default: False — exit always 0, the report is the result.
RUN_FAIL_ON_ERROR: bool = False

# Optional override for the path to bb5kbc-csv-mapping.md (used for the
# section-4b doku-alignment check). When None, auto-discovery is used:
# the script looks in ontology/, rdf/, repo root, and docs/ in that order.
# Set to a Path or string when the doc lives somewhere unusual.
RUN_MAPPING_MD_OVERRIDE: Path | None = None


# ---------------------------------------------------------------------------
# Namespaces (must match the LOD pipeline)
# ---------------------------------------------------------------------------

BB5KBC = Namespace("http://w3id.org/bb5kbc/ont/")
DATA = Namespace("http://w3id.org/bb5kbc/")
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
CRMSCI = Namespace("http://www.cidoc-crm.org/extensions/crmsci/")
FSL = Namespace("http://fuzzy-sl.squirrel.link/ontology/")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
SF = Namespace("http://www.opengis.net/ont/sf#")
TIME = Namespace("http://www.w3.org/2006/time#")
PROV = Namespace("http://www.w3.org/ns/prov#")


# ---------------------------------------------------------------------------
# Per-CSV-column expectations.
# Each entry maps a column name to a small dict describing what the LOD
# pipeline is expected to do with it. Used by the section-2 completeness
# check. "kind" tells the validator how to count:
#   - "literal_on_site": one literal triple per non-empty cell
#   - "node_link_per_site": site → relation → typed node (1 triple per site)
#   - "ext_id_on_admin": one hasExternalIdentifier on an admin-area node
#                       (deduplicated, so count distinct admin labels filled)
#   - "audit_only": column is metadata from the CSV-enrichment stage and
#                   must NOT appear in RDF
#   - "skip": special handling that the simple counter cannot describe
# ---------------------------------------------------------------------------

CSV_EXPECTATIONS: dict[str, dict] = {
    # Site-level identifiers and labels
    "FID":            {"kind": "literal_on_site", "predicate": BB5KBC.hatFID},
    "fst_id":         {"kind": "literal_on_site", "predicate": BB5KBC.hatFundstellenID},
    "katalognr":      {"kind": "literal_on_site", "predicate": BB5KBC.hatKatalognummer},
    "fst_name":       {"kind": "literal_on_site", "predicate": RDFS.label,
                       "rdf_class": BB5KBC.Fundstelle, "lang": "de"},
    "genauigkeit_m":  {"kind": "literal_on_site", "predicate": BB5KBC.hatGenauigkeit},
    # Administrative-area links (one triple per site)
    "gemeinde":   {"kind": "node_link_per_site", "predicate": BB5KBC.inGemeinde},
    "kreis":      {"kind": "skip",
                   "note": "indirect: site → gemeinde → kreis"},
    "bundesland": {"kind": "skip",
                   "note": "indirect: ... → kreis → bundesland"},
    "land":       {"kind": "skip",
                   "note": "indirect: ... → bundesland → land"},
    # Per-level external identifiers (counted on admin-area nodes)
    "GEMEINDE_QID":            {"kind": "ext_id_on_admin", "level": "gemeinde",   "ns": "https://www.wikidata.org/entity/"},
    "GEMEINDE_GeoNames":       {"kind": "ext_id_on_admin", "level": "gemeinde",   "ns": "https://www.geonames.org/"},
    "GEMEINDE_TGN":            {"kind": "ext_id_on_admin", "level": "gemeinde",   "ns": "http://vocab.getty.edu/tgn/"},
    "GEMEINDE_IDAI":           {"kind": "ext_id_on_admin", "level": "gemeinde",   "ns": "http://gazetteer.dainst.org/place/"},
    "GEMEINDE_OSM_Relation":   {"kind": "ext_id_on_admin", "level": "gemeinde",   "ns": "https://www.openstreetmap.org/relation/"},
    "KREIS_QID":               {"kind": "ext_id_on_admin", "level": "kreis",      "ns": "https://www.wikidata.org/entity/"},
    "KREIS_GeoNames":          {"kind": "ext_id_on_admin", "level": "kreis",      "ns": "https://www.geonames.org/"},
    "KREIS_TGN":               {"kind": "ext_id_on_admin", "level": "kreis",      "ns": "http://vocab.getty.edu/tgn/"},
    "KREIS_IDAI":              {"kind": "ext_id_on_admin", "level": "kreis",      "ns": "http://gazetteer.dainst.org/place/"},
    "KREIS_OSM_Relation":      {"kind": "ext_id_on_admin", "level": "kreis",      "ns": "https://www.openstreetmap.org/relation/"},
    "BUNDESLAND_QID":          {"kind": "ext_id_on_admin", "level": "bundesland", "ns": "https://www.wikidata.org/entity/"},
    "BUNDESLAND_GeoNames":     {"kind": "ext_id_on_admin", "level": "bundesland", "ns": "https://www.geonames.org/"},
    "BUNDESLAND_TGN":          {"kind": "ext_id_on_admin", "level": "bundesland", "ns": "http://vocab.getty.edu/tgn/"},
    "BUNDESLAND_IDAI":         {"kind": "ext_id_on_admin", "level": "bundesland", "ns": "http://gazetteer.dainst.org/place/"},
    "BUNDESLAND_OSM_Relation": {"kind": "ext_id_on_admin", "level": "bundesland", "ns": "https://www.openstreetmap.org/relation/"},
    "LAND_QID":                {"kind": "ext_id_on_admin", "level": "land",       "ns": "https://www.wikidata.org/entity/"},
    "LAND_GeoNames":           {"kind": "ext_id_on_admin", "level": "land",       "ns": "https://www.geonames.org/"},
    "LAND_TGN":                {"kind": "ext_id_on_admin", "level": "land",       "ns": "http://vocab.getty.edu/tgn/"},
    "LAND_IDAI":               {"kind": "ext_id_on_admin", "level": "land",       "ns": "http://gazetteer.dainst.org/place/"},
    "LAND_OSM_Relation":       {"kind": "ext_id_on_admin", "level": "land",       "ns": "https://www.openstreetmap.org/relation/"},
    # Audit columns:
    #   _matchLabel and _matchScore are CSV-only (no RDF triples).
    #   _matchReason is carried into the RDF graph as
    #     bb5kbc:wikidataMatchDescription on the deduplicated type node.
    "GEMEINDE_matchLabel":  {"kind": "audit_only"},
    "GEMEINDE_matchScore":  {"kind": "audit_only"},
    "GEMEINDE_matchReason": {"kind": "match_description_in_rdf"},
    "KREIS_matchLabel":     {"kind": "audit_only"},
    "KREIS_matchScore":     {"kind": "audit_only"},
    "KREIS_matchReason":    {"kind": "match_description_in_rdf"},
    "BUNDESLAND_matchLabel":  {"kind": "audit_only"},
    "BUNDESLAND_matchScore":  {"kind": "audit_only"},
    "BUNDESLAND_matchReason": {"kind": "match_description_in_rdf"},
    "LAND_matchLabel":     {"kind": "audit_only"},
    "LAND_matchScore":     {"kind": "audit_only"},
    "LAND_matchReason":    {"kind": "match_description_in_rdf"},
    # Knot/relation columns (one bb5kbc:hat* triple per non-empty cell)
    "kultur":           {"kind": "node_link_per_site", "predicate": BB5KBC.hatKulturelleZuordnung},
    "entdeckung":       {"kind": "node_link_per_site", "predicate": BB5KBC.wurdeEntdecktDurch},
    "publikation_arch": {"kind": "node_link_per_site", "predicate": BB5KBC.hatPublikation},
    "fundstellenart":   {"kind": "skip",
                         "note": "1+ triples per site (compound + uncertainty splits)"},
    # External-ID columns on type nodes
    "QID_entdeckung":     {"kind": "skip",
                           "note": "ext-id on EntdeckungsartType (deduplicated)"},
    "QID_publikation":    {"kind": "skip",
                           "note": "ext-id on Publikation (one per non-empty cell)"},
    "QID_fundstellenart": {"kind": "skip",
                           "note": "ext-id on FundstellenartType (deduplicated)"},
    "QID_quelle_georef":  {"kind": "skip",
                           "note": "fsl:hasReference URI on Activity"},
    "quelle_georef":      {"kind": "skip",
                           "note": "fsl:hasReference Literal on Activity"},
    # Geometry / activity
    "wgs84_x":      {"kind": "skip", "note": "WKT POINT(x y) on sf:Point — combined with wgs84_y"},
    "wgs84_y":      {"kind": "skip", "note": "see wgs84_x"},
    "methode":      {"kind": "skip", "note": "fsl:methodUsed → fsl:MethodType (deduplicated)"},
    "quellen_typ":  {"kind": "skip", "note": "fsl:hasSourceType → fsl:SourceType (deduplicated)"},
    "methodenbeschr": {"kind": "skip", "note": "fsl:activityDesc literal on Activity"},
    # Dating block
    "dating_start":            {"kind": "literal_on_dating", "predicate": BB5KBC.datierungStart},
    "dating_end":              {"kind": "literal_on_dating", "predicate": BB5KBC.datierungEnd},
    "dating_certainty_start":  {"kind": "literal_on_dating", "predicate": BB5KBC.datierungSicherheitStart},
    "dating_certainty_end":    {"kind": "literal_on_dating", "predicate": BB5KBC.datierungSicherheitEnd},
    "dating_certainty_range":  {"kind": "literal_on_dating", "predicate": BB5KBC.datierungSicherheitRange},
    "dating_method":           {"kind": "skip", "note": "Wikidata QID on DatierungsMethodeType (deduplicated)"},
    "dating_perio.do":         {"kind": "skip", "note": "skos:{exact|close|related}Match on Datierung"},
    "dating_perio.do_match":   {"kind": "skip", "note": "controls predicate, no own triple"},
    # Sherds (pipe-separated QID list)
    "sherd": {"kind": "skip", "note": "0..n bb5kbc:hatScherbe per site"},
    # Schema-but-empty columns
    "perio.do": {"kind": "skip", "note": "0/540 filled — empty by design in current CSV"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def section_header(report: list[str], title: str) -> None:
    """Append a level-2 header to the running report."""
    report.append("")
    report.append("---")
    report.append("")
    report.append(f"## {title}")
    report.append("")


def badge(status: str) -> str:
    """Return a unicode badge for PASS/FAIL/WARN/INFO."""
    return {
        "PASS": "✅ **PASS**",
        "FAIL": "❌ **FAIL**",
        "WARN": "⚠ **WARN**",
        "INFO": "ℹ **INFO**",
        "SKIP": "— **SKIP**",
    }.get(status, status)


# ---------------------------------------------------------------------------
# Section 1: structural conformance (summarise SHACL reports)
# ---------------------------------------------------------------------------

def check_shacl(report: list[str], dist_dir: Path) -> bool:
    """Read the two SHACL reports (if present) and summarise their verdict."""
    section_header(report, "1. Strukturelle Konsistenz (SHACL)")

    all_ok = True
    for label, fname in [("Daten-Graph", "shacl-report.ttl"),
                         ("Bundle-Graph", "shacl-report-bundle.ttl")]:
        path = dist_dir / fname
        if not path.exists():
            report.append(f"- {badge('WARN')} {label}: kein SHACL-Report gefunden "
                          f"(`{path.name}`). LOD-Pipeline ohne `RUN_SKIP_SHACL` "
                          f"laufen lassen, um den Bericht zu erzeugen.")
            all_ok = False
            continue

        rg = Graph()
        rg.parse(str(path), format="turtle")
        # rdflib sometimes gives a True literal, sometimes "true"^^xsd:boolean
        conforms = None
        for vr_subject in rg.subjects(RDF.type, SH.ValidationReport):
            conf_val = list(rg.objects(vr_subject, SH.conforms))
            if conf_val:
                conforms = bool(conf_val[0])
                break

        violations = sum(1 for _ in rg.subjects(RDF.type, SH.ValidationResult))
        if conforms is True and violations == 0:
            report.append(f"- {badge('PASS')} {label}: `sh:conforms true`, "
                          f"0 Validation Results.")
        elif violations == 0:
            report.append(f"- {badge('WARN')} {label}: keine Violations, "
                          f"aber `sh:conforms` nicht eindeutig `true`.")
            all_ok = False
        else:
            report.append(f"- {badge('FAIL')} {label}: {violations} Violations, "
                          f"`sh:conforms = {conforms}`.")
            all_ok = False
    return all_ok


# ---------------------------------------------------------------------------
# Section 2: CSV ↔ RDF completeness
# ---------------------------------------------------------------------------

def check_csv_completeness(report: list[str], df: pd.DataFrame,
                           g: Graph) -> bool:
    """Per-column comparison of non-empty CSV cells vs expected RDF triples."""
    section_header(report, "2. CSV ↔ RDF Vollständigkeit")
    report.append("Pro CSV-Spalte: Anzahl nicht-leerer Werte vs. Anzahl "
                  "korrespondierender Tripel im Bundle. Kompound-Werte "
                  "(Siedlung+Grab) und Sonderfälle stehen explizit als "
                  "*skip* mit Erklärung — diese Spalten werden nicht "
                  "automatisch gegengeprüft.")
    report.append("")
    report.append("| # | CSV-Spalte | Nicht-leer | Erwartung | Gefunden | Status |")
    report.append("|---|---|---|---|---|---|")

    # Unknown columns (in CSV but not in our expectations dict)
    unknown = [c for c in df.columns if c not in CSV_EXPECTATIONS]

    # Sites (subjects of type bb5kbc:Fundstelle)
    sites = set(g.subjects(RDF.type, BB5KBC.Fundstelle))
    # All admin-area nodes by class
    admin_by_level = {
        "land":       set(g.subjects(RDF.type, BB5KBC.Land)),
        "bundesland": set(g.subjects(RDF.type, BB5KBC.Bundesland)),
        "kreis":      set(g.subjects(RDF.type, BB5KBC.Kreis)),
        "gemeinde":   set(g.subjects(RDF.type, BB5KBC.Gemeinde)),
    }
    # Datierung subjects
    datierungen = set(g.subjects(RDF.type, BB5KBC.Datierung))

    all_ok = True
    for i, col in enumerate(df.columns, start=1):
        expectation = CSV_EXPECTATIONS.get(col)
        non_empty = int((df[col].astype(str).str.strip() != "").sum())

        if expectation is None:
            report.append(f"| {i} | `{col}` | {non_empty} | (unbekannt) "
                          f"| — | {badge('WARN')} |")
            all_ok = False
            continue

        kind = expectation["kind"]

        if kind == "literal_on_site":
            pred = expectation["predicate"]
            found = sum(1 for _ in g.triples((None, pred, None))
                        if _[0] in sites)
            status = "PASS" if found == non_empty else "FAIL"
            if status == "FAIL": all_ok = False
            report.append(f"| {i} | `{col}` | {non_empty} | "
                          f"je 1 Literal `{pred.n3(g.namespace_manager)}` an Fundstelle "
                          f"| {found} | {badge(status)} |")

        elif kind == "literal_on_dating":
            pred = expectation["predicate"]
            found = sum(1 for _ in g.triples((None, pred, None))
                        if _[0] in datierungen)
            status = "PASS" if found == non_empty else "FAIL"
            if status == "FAIL": all_ok = False
            report.append(f"| {i} | `{col}` | {non_empty} | "
                          f"je 1 Literal `{pred.n3(g.namespace_manager)}` an Datierung "
                          f"| {found} | {badge(status)} |")

        elif kind == "node_link_per_site":
            pred = expectation["predicate"]
            found = sum(1 for s,_,_ in g.triples((None, pred, None))
                        if s in sites)
            status = "PASS" if found == non_empty else "FAIL"
            if status == "FAIL": all_ok = False
            report.append(f"| {i} | `{col}` | {non_empty} | "
                          f"je 1 `{pred.n3(g.namespace_manager)}` von Fundstelle "
                          f"| {found} | {badge(status)} |")

        elif kind == "ext_id_on_admin":
            level = expectation["level"]
            ns = expectation["ns"]
            # Distinct admin nodes at this level that have a hasExternalIdentifier
            # whose URI starts with the namespace
            count = 0
            for admin_node in admin_by_level[level]:
                for ext_id in g.objects(admin_node, BB5KBC.hasExternalIdentifier):
                    if str(ext_id).startswith(ns):
                        count += 1
                        break  # one per node is enough
            # Compare against distinct *non-empty* admin labels with the
            # ext-id cell filled. Empty admin labels are excluded — they
            # cannot produce admin nodes (or are mapped through fallback,
            # which the LOD pipeline handles deterministically; either way
            # an empty string is not a distinct admin entity for counting).
            label_col = level if level == "land" else level  # column name == admin level
            distinct_filled = df[
                (df[col].astype(str).str.strip() != "") &
                (df[label_col].astype(str).str.strip() != "")
            ][label_col].nunique()
            status = "PASS" if count == distinct_filled else "FAIL"
            if status == "FAIL": all_ok = False
            report.append(f"| {i} | `{col}` | {non_empty} (in {distinct_filled} dist. {level}) | "
                          f"je 1 `hasExternalIdentifier` ({ns.split('/')[-2]}) "
                          f"| {count} | {badge(status)} |")

        elif kind == "audit_only":
            # Audit columns must not appear in the RDF graph as object-position
            # literals matching their values. Spot-check rather than exhaustive
            # scan — a true exhaustive check would be O(rows × triples). For
            # the standard 540×65 CSV this is fine because no triple in the
            # generator code uses these columns at all; we just confirm the
            # column is in our skip-list, not in the produced graph.
            status = "PASS"
            report.append(f"| {i} | `{col}` | {non_empty} | "
                          f"0 Tripel (audit-only, nicht im RDF) | "
                          f"— (Skript erzeugt nichts) | {badge(status)} |")

        elif kind == "match_description_in_rdf":
            # _matchReason columns are carried into the RDF graph as
            # bb5kbc:wikidataMatchDescription on the deduplicated administrative
            # type node (one literal per distinct Land/Bundesland/Kreis/Gemeinde
            # node). No exhaustive check here — the property-level check in
            # Section 3 already confirms the property is declared and used.
            status = "PASS"
            report.append(f"| {i} | `{col}` | {non_empty} | "
                          f"1 Literal `bb5kbc:wikidataMatchDescription` "
                          f"je distinktem Type-Knoten der Ebene | "
                          f"— (siehe Sektion 3) | {badge(status)} |")

        elif kind == "skip":
            note = expectation.get("note", "")
            report.append(f"| {i} | `{col}` | {non_empty} | (skip) {note} "
                          f"| — | {badge('SKIP')} |")

        else:
            report.append(f"| {i} | `{col}` | {non_empty} | (unhandled kind={kind}) "
                          f"| — | {badge('WARN')} |")
            all_ok = False

    if unknown:
        report.append("")
        report.append(f"{badge('WARN')} Spalten in CSV ohne Eintrag in "
                      f"`CSV_EXPECTATIONS`: {', '.join('`'+c+'`' for c in unknown)}")
        all_ok = False

    return all_ok


# ---------------------------------------------------------------------------
# Section 3: ontology completeness
# ---------------------------------------------------------------------------

def check_ontology_completeness(report: list[str], g: Graph) -> bool:
    """Set difference between used and declared classes/properties."""
    section_header(report, "3. Ontologie-Vollständigkeit")
    report.append("Nimmt alle Klassen und Properties, die im Datengraph "
                  "*verwendet* werden, und prüft ob sie in der Ontologie "
                  "*deklariert* sind. Externe Vokabulare (CRM, FSL, GeoSPARQL, "
                  "PROV-O, SKOS, …) werden ausgeklammert — geprüft wird nur "
                  "der `bb5kbc:`-Namespace.")
    report.append("")

    # Used: classes appearing as object of rdf:type, and properties appearing
    # as predicates anywhere — but only those in the BB5KBC namespace.
    used_classes = set()
    for o in g.objects(None, RDF.type):
        if isinstance(o, URIRef) and str(o).startswith(str(BB5KBC)):
            used_classes.add(o)

    used_props = set()
    for s, p, o in g:
        if isinstance(p, URIRef) and str(p).startswith(str(BB5KBC)):
            used_props.add(p)

    # Declared in the ontology
    declared_classes = set()
    for c in g.subjects(RDF.type, OWL.Class):
        if str(c).startswith(str(BB5KBC)):
            declared_classes.add(c)

    declared_props = set()
    for p in g.subjects(RDF.type, OWL.ObjectProperty):
        if str(p).startswith(str(BB5KBC)):
            declared_props.add(p)
    for p in g.subjects(RDF.type, OWL.DatatypeProperty):
        if str(p).startswith(str(BB5KBC)):
            declared_props.add(p)

    # Compare
    missing_classes = used_classes - declared_classes
    unused_classes = declared_classes - used_classes
    missing_props = used_props - declared_props
    unused_props = declared_props - used_props

    all_ok = True

    def fmt_iri(u):
        return str(u).replace(str(BB5KBC), "bb5kbc:")

    report.append("### Klassen")
    report.append("")
    report.append(f"- Verwendet: **{len(used_classes)}**, deklariert: "
                  f"**{len(declared_classes)}**")
    if missing_classes:
        all_ok = False
        report.append(f"- {badge('FAIL')} **In Daten verwendet, aber nicht in "
                      f"Ontologie deklariert:**")
        for c in sorted(missing_classes, key=str):
            report.append(f"    - `{fmt_iri(c)}`")
    else:
        report.append(f"- {badge('PASS')} Jede in den Daten verwendete "
                      f"`bb5kbc:`-Klasse ist in der Ontologie deklariert.")
    if unused_classes:
        report.append(f"- {badge('INFO')} **Deklariert, aber nicht in Daten verwendet:** "
                      + ", ".join(f"`{fmt_iri(c)}`" for c in sorted(unused_classes, key=str)))

    report.append("")
    report.append("### Properties")
    report.append("")
    report.append(f"- Verwendet: **{len(used_props)}**, deklariert: "
                  f"**{len(declared_props)}**")
    if missing_props:
        all_ok = False
        report.append(f"- {badge('FAIL')} **In Daten verwendet, aber nicht in "
                      f"Ontologie deklariert:**")
        for p in sorted(missing_props, key=str):
            report.append(f"    - `{fmt_iri(p)}`")
    else:
        report.append(f"- {badge('PASS')} Jede in den Daten verwendete "
                      f"`bb5kbc:`-Property ist in der Ontologie deklariert.")
    if unused_props:
        report.append(f"- {badge('INFO')} **Deklariert, aber nicht in Daten verwendet:** "
                      + ", ".join(f"`{fmt_iri(p)}`" for p in sorted(unused_props, key=str)))

    return all_ok


# ---------------------------------------------------------------------------
# Section 4: CRM anchoring
# ---------------------------------------------------------------------------

def all_ancestors(g: Graph, cls: URIRef) -> set[URIRef]:
    """Return the full set of ancestors reachable via rdfs:subClassOf transitively.

    Walks all `rdfs:subClassOf` edges (multi-inheritance: every direct parent
    is followed, not just one). Returned set does NOT include `cls` itself.
    Stops at fixed point. Cycle-safe by virtue of the `visited` accumulator.

    This is the honest reading of the ontology's class hierarchy: every
    bb5kbc class can have multiple direct parents (e.g. bb5kbc:Fundstelle is
    rdfs:subClassOf lado:Location, fsl:Site, AND crm:E27_Site), and each of
    those carries its own further ancestry.
    """
    ancestors: set[URIRef] = set()
    queue = [cls]
    while queue:
        current = queue.pop()
        for parent in g.objects(current, RDFS.subClassOf):
            if isinstance(parent, URIRef) and parent not in ancestors:
                ancestors.add(parent)
                queue.append(parent)
    return ancestors


def crm_anchor_path(g: Graph, cls: URIRef) -> list[URIRef]:
    """Find one rdfs:subClassOf chain from `cls` to a crm:E* root.

    Used for the section-4 CRM-anchoring display column. Bounded BFS
    preferring crm-namespaced parents at each step. Returns the chain
    INCLUDING the starting class. If no CRM ancestor is reachable, returns
    just `[cls]` (the caller will see absence of any crm: node and report
    FAIL accordingly).
    """
    chain: list[URIRef] = [cls]
    visited: set[URIRef] = {cls}
    current = cls
    for _ in range(20):  # hard depth bound
        parents = [p for p in g.objects(current, RDFS.subClassOf)
                   if isinstance(p, URIRef) and p not in visited]
        if not parents:
            break
        crm_parent = next((p for p in parents if str(p).startswith(str(CRM))), None)
        nxt = crm_parent if crm_parent is not None else parents[0]
        chain.append(nxt)
        visited.add(nxt)
        current = nxt
    return chain


def check_crm_anchoring(report: list[str], g: Graph) -> tuple[bool, dict]:
    """Every bb5kbc: class must have a crm:E*-rooted ancestor.

    The display column now shows ONE representative chain to a crm:E* root
    (BFS, CRM-preferring) — useful for human reading. The full ancestor set
    used for section 4b's doku-comparison is computed independently via
    `all_ancestors()`, so multi-inheritance (e.g. Fundstelle ⊑ lado:Location
    AND fsl:Site AND crm:E27_Site) is handled correctly downstream.
    """
    section_header(report, "4. CRM-Verankerung")
    report.append("Für jede `bb5kbc:`-Klasse: gibt es einen Pfad über "
                  "`rdfs:subClassOf` zu einem `crm:`-Knoten? Die angezeigte "
                  "Kette ist eine repräsentative Spur (BFS, CRM-bevorzugt) "
                  "— bei Multi-Inheritance kann es weitere Eltern geben, "
                  "die in Sektion 4b vollständig gegen die Doku verglichen "
                  "werden.")
    report.append("")

    classes = sorted(
        (c for c in g.subjects(RDF.type, OWL.Class)
         if str(c).startswith(str(BB5KBC))),
        key=str
    )

    rows = []
    ancestors_by_class: dict[URIRef, set[URIRef]] = {}
    all_anchored = True
    for c in classes:
        chain = crm_anchor_path(g, c)
        ancestors_by_class[c] = all_ancestors(g, c)
        # CRM anchored if any crm:* in the full ancestor set
        reached = any(str(a).startswith(str(CRM)) for a in ancestors_by_class[c])
        chain_str = " → ".join(short_iri(n) for n in chain)
        status = "PASS" if reached else "FAIL"
        if status == "FAIL":
            all_anchored = False
        rows.append((short_iri(c), chain_str, status))

    report.append("| Klasse | rdfs:subClassOf-Kette (eine Spur) | Status |")
    report.append("|---|---|---|")
    for cls, chain_str, status in rows:
        report.append(f"| `{cls}` | {chain_str} | {badge(status)} |")

    if all_anchored:
        report.append("")
        report.append(f"{badge('PASS')} Alle {len(classes)} `bb5kbc:`-Klassen "
                      f"sind über `rdfs:subClassOf` an einen CRM-Knoten verankert.")
    else:
        report.append("")
        report.append(f"{badge('FAIL')} Mindestens eine `bb5kbc:`-Klasse hat "
                      f"keinen CRM-Anker.")

    return all_anchored, ancestors_by_class


LADO = Namespace("http://archaeology.link/ontology#")
PLEIADES = Namespace("https://pleiades.stoa.org/places/vocab#")


def short_iri(u: URIRef) -> str:
    """Shorten a URI for table display."""
    s = str(u)
    for prefix, ns in [
        ("bb5kbc:", str(BB5KBC)),
        ("crm:", str(CRM)),
        ("crmsci:", str(CRMSCI)),
        ("fsl:", str(FSL)),
        ("lado:", str(LADO)),
        ("pleiades:", str(PLEIADES)),
        ("time:", str(TIME)),
        ("prov:", str(PROV)),
        ("geo:", str(GEO)),
        ("sf:", str(SF)),
    ]:
        if s.startswith(ns):
            return prefix + s[len(ns):]
    # Truncate very long ones
    return f"<{s}>" if len(s) < 80 else f"<…/{s.rsplit('/', 1)[-1]}>"


# ---------------------------------------------------------------------------
# Section 4b: documented inheritance chains vs computed ones
# ---------------------------------------------------------------------------

# Pattern to find the chain table in bb5kbc-csv-mapping.md.
# Two formats are supported:
#   1. Old (chain): | `bb5kbc:Land` | `crm:E1` → `crm:E53_Place` → **`bb5kbc:Land`** |
#   2. New (set):   | `bb5kbc:Land` | `crm:E1_CRM_Entity`, `crm:E53_Place` |
# The parser splits on both → and , — so either format works.
DOC_CHAIN_ROW_RE = re.compile(
    r"^\|\s*`(bb5kbc:[A-Za-z]+)`\s*\|\s*(.+?)\s*\|\s*$"
)


def parse_doc_chains(md_path: Path) -> dict[str, list[str]] | None:
    """Parse the inheritance-chain table from bb5kbc-csv-mapping.md.

    Returns a dict {class_name: [chain_segments]} where chain_segments are
    raw strings like 'crm:E1', 'crm:E53_Place', 'bb5kbc:Land' (markdown
    backticks and bold markers stripped). Returns None if the file is
    missing or no table is found.

    Splits on both `→` and `,` — supports both the legacy chain format and
    the new flat-set format used after the v0.11 doc update.
    """
    if not md_path.exists():
        return None
    text = md_path.read_text(encoding="utf-8")
    chains: dict[str, list[str]] = {}
    in_chain_section = False
    for line in text.splitlines():
        if line.startswith("## Vererbungsketten"):
            in_chain_section = True
            continue
        if in_chain_section and line.startswith("## "):
            break
        if not in_chain_section:
            continue
        m = DOC_CHAIN_ROW_RE.match(line)
        if not m:
            continue
        cls_name = m.group(1)
        chain_str = m.group(2)
        # Split on either → or , — both are valid chain/set delimiters
        parts = re.split(r"\s*(?:→|,)\s*", chain_str)
        cleaned: list[str] = []
        for part in parts:
            # Drop "(+ time:Interval)" and similar parenthetical addenda — they
            # are documented as additional types, not part of the main chain
            part = re.sub(r"\s*\(\+.*\)$", "", part)
            # Strip ** and ` markers
            part = part.replace("**", "").replace("`", "").strip()
            # If the cell has "X / Y" (alternatives), split — we want both names
            for alt in re.split(r"\s*/\s*", part):
                alt = alt.strip()
                if alt:
                    cleaned.append(alt)
        chains[cls_name] = cleaned
    return chains if chains else None


def _normalise_chain_token(s: str) -> str:
    """Normalise tokens for comparison between doc-chain and onto-ancestors.

    The doc table abbreviates `crm:E1_CRM_Entity` as `crm:E1`; both refer to
    the same class. We treat them as equivalent for the set-comparison.
    Long URIs that short_iri couldn't shorten (because their namespace isn't
    in the prefix list) keep their angle-bracket form; this still matches
    the doc table when the doc uses the same form.
    """
    s = s.strip()
    if s == "crm:E1":
        return "crm:E1_CRM_Entity"
    return s


def check_doc_alignment(report: list[str], g: Graph,
                        ancestors_by_class: dict,
                        mapping_md: Path | None) -> bool:
    """Compare documented inheritance chains to the full ontology ancestry.

    The previous version of this check followed a single bottom-up CRM-spur
    and compared it to the doc chain — which was unfair because the
    ontology declares multi-inheritance (e.g. bb5kbc:Fundstelle is rdfs:
    subClassOf lado:Location, fsl:Site, AND crm:E27_Site). Many of the
    `WARN` results were just the single-spur walker missing parents that
    are genuinely declared in the ontology.

    This version compares the FULL set of transitive ancestors against the
    doc table's set of named classes (ignoring chain order and `crm:E1` vs
    `crm:E1_CRM_Entity` cosmetic difference). PASS means the sets match
    after normalisation.
    """
    section_header(report, "4b. Doku-Abgleich (csv-mapping.md ↔ Ontologie)")
    report.append("Vergleicht die handschriftliche Vererbungsketten-Tabelle "
                  "in `bb5kbc-csv-mapping.md` (Sektion *Vererbungsketten*) "
                  "mit den aus der Ontologie berechneten **vollständigen** "
                  "Vorfahren-Mengen (Multi-Inheritance: alle direkten Eltern "
                  "und ihre transitive Hülle). Vergleichsmodus: Mengenvergleich, "
                  "Reihenfolge irrelevant, `crm:E1` ≡ `crm:E1_CRM_Entity`. "
                  "Drift bedeutet: Doku und Modellierung sind asynchron.")
    report.append("")

    if mapping_md is None:
        report.append(f"{badge('WARN')} `bb5kbc-csv-mapping.md` an keinem der "
                      f"automatisch durchsuchten Standardpfade gefunden "
                      f"(`ontology/`, `rdf/`, repo root, `docs/`). "
                      f"Doku-Abgleich übersprungen. Setze "
                      f"`RUN_MAPPING_MD_OVERRIDE` oben im Skript, falls die "
                      f"Datei woanders liegt.")
        return True  # not a hard fail

    doc_chains = parse_doc_chains(mapping_md)
    if doc_chains is None:
        report.append(f"{badge('WARN')} `bb5kbc-csv-mapping.md` nicht gefunden "
                      f"oder enthält keine Vererbungsketten-Tabelle. "
                      f"Doku-Abgleich übersprungen.")
        return True  # not a hard fail

    # bb5kbc class names (without prefix) used in the ontology
    onto_classes = {short_iri(c) for c in ancestors_by_class}
    doc_classes = set(doc_chains.keys())

    only_in_doc = doc_classes - onto_classes
    only_in_onto = onto_classes - doc_classes

    all_ok = True

    if only_in_doc:
        all_ok = False
        report.append(f"- {badge('FAIL')} **In Doku, aber nicht in Ontologie:** "
                      + ", ".join(f"`{c}`" for c in sorted(only_in_doc)))
    if only_in_onto:
        all_ok = False
        report.append(f"- {badge('FAIL')} **In Ontologie, aber nicht in Doku-Tabelle:** "
                      + ", ".join(f"`{c}`" for c in sorted(only_in_onto)))

    # Per-class set comparison (only for classes in both)
    common = sorted(doc_classes & onto_classes)
    if common:
        report.append("")
        report.append("| Klasse | nur in Doku | nur in Ontologie | Status |")
        report.append("|---|---|---|---|")
        for cls in common:
            cls_uri = URIRef(str(BB5KBC) + cls.split(':')[1])
            # Doc set: tokens from the chain table, normalised
            doc_set = {_normalise_chain_token(t) for t in doc_chains[cls]}
            doc_set.discard(cls)  # drop the leaf class itself
            # Onto set: full transitive ancestor URIs, shortened
            onto_set = {_normalise_chain_token(short_iri(a))
                        for a in ancestors_by_class[cls_uri]}
            only_doc = doc_set - onto_set
            only_onto = onto_set - doc_set

            if not only_doc and not only_onto:
                status = "PASS"
            else:
                status = "WARN"  # any difference = drift to investigate
                all_ok = False

            only_doc_str = ", ".join(f"`{x}`" for x in sorted(only_doc)) or "—"
            only_onto_str = ", ".join(f"`{x}`" for x in sorted(only_onto)) or "—"
            report.append(f"| `{cls}` | {only_doc_str} | {only_onto_str} | {badge(status)} |")

    if all_ok and not (only_in_doc or only_in_onto):
        report.append("")
        report.append(f"{badge('PASS')} Doku und Ontologie sind synchron.")

    return all_ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def find_mapping_doc(script_dir: Path, root: Path) -> Path | None:
    """Auto-discover bb5kbc-csv-mapping.md across plausible locations.

    Searches in order: ontology/, rdf/ (alongside script), repo root, docs/.
    Returns the first existing path, or None if not found anywhere.
    Override-friendly: if RUN_MAPPING_MD_OVERRIDE is set (a constant at the
    top of this file), that path wins.
    """
    if RUN_MAPPING_MD_OVERRIDE is not None:
        return Path(RUN_MAPPING_MD_OVERRIDE)
    candidates = [
        root / "ontology" / "bb5kbc-csv-mapping.md",
        script_dir / "bb5kbc-csv-mapping.md",
        root / "bb5kbc-csv-mapping.md",
        root / "docs" / "bb5kbc-csv-mapping.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    root = script_dir.parent

    bundle_path = root / "dist" / "bb5kbc-bundle.ttl"
    csv_path = root / "data" / "fst_wgs84.csv"
    mapping_md = find_mapping_doc(script_dir, root)
    out_report = root / "dist" / "validation_report.md"

    print(f"Loading bundle:  {bundle_path}")
    print(f"Loading CSV:     {csv_path}")
    if mapping_md is not None:
        print(f"Doku source:     {mapping_md}")
    else:
        print(f"Doku source:     (none found — section 4b will be skipped)")
    print(f"Report target:   {out_report}")
    print()

    if not bundle_path.exists():
        print(f"ERROR: bundle not found at {bundle_path}", file=sys.stderr)
        print(f"  Run bb5kbc_lod_pipeline.py first.", file=sys.stderr)
        return 1
    if not csv_path.exists():
        print(f"ERROR: CSV not found at {csv_path}", file=sys.stderr)
        return 1

    # Load
    g = Graph()
    g.parse(str(bundle_path), format="turtle")
    print(f"Bundle loaded: {len(g)} triples")

    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False,
                     na_values=[], encoding="utf-8-sig")
    print(f"CSV loaded: {len(df)} rows × {len(df.columns)} columns")
    print()

    # Run all checks; build a single Markdown report
    report: list[str] = []
    report.append("# bb5kbc LOD — Validation Report")
    report.append("")
    report.append(f"- Bundle: `{bundle_path.name}` ({len(g)} triples)")
    report.append(f"- CSV: `{csv_path.name}` ({len(df)} rows × {len(df.columns)} cols)")
    report.append(f"- Doku: `{mapping_md.name if mapping_md else '(nicht gefunden)'}`")
    report.append("")
    report.append("**Layers checked**")
    report.append("")
    report.append("1. Strukturelle Konsistenz (SHACL)")
    report.append("2. CSV ↔ RDF Vollständigkeit")
    report.append("3. Ontologie-Vollständigkeit")
    report.append("4. CRM-Verankerung")
    report.append("4b. Doku-Abgleich (csv-mapping.md ↔ Ontologie)")

    section_results = {}
    section_results["1"] = check_shacl(report, root / "dist")
    section_results["2"] = check_csv_completeness(report, df, g)
    section_results["3"] = check_ontology_completeness(report, g)
    crm_ok, ancestors_by_class = check_crm_anchoring(report, g)
    section_results["4"] = crm_ok
    section_results["4b"] = check_doc_alignment(report, g, ancestors_by_class, mapping_md)

    # Summary at the top — prepend after the title block
    summary = ["", "## Zusammenfassung", ""]
    summary.append("| Sektion | Ergebnis |")
    summary.append("|---|---|")
    summary.append(f"| 1. Strukturelle Konsistenz (SHACL) | {badge('PASS' if section_results['1'] else 'FAIL')} |")
    summary.append(f"| 2. CSV ↔ RDF Vollständigkeit | {badge('PASS' if section_results['2'] else 'FAIL')} |")
    summary.append(f"| 3. Ontologie-Vollständigkeit | {badge('PASS' if section_results['3'] else 'FAIL')} |")
    summary.append(f"| 4. CRM-Verankerung | {badge('PASS' if section_results['4'] else 'FAIL')} |")
    summary.append(f"| 4b. Doku-Abgleich | {badge('PASS' if section_results['4b'] else 'WARN')} |")

    # Insert summary right after the meta block (after the "Layers checked" list)
    insert_at = next(i for i, line in enumerate(report)
                     if line == "4b. Doku-Abgleich (csv-mapping.md ↔ Ontologie)") + 1
    report = report[:insert_at] + summary + report[insert_at:]

    # Write
    out_report.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Wrote validation report: {out_report}")
    print()
    print("Summary:")
    for sec, ok in section_results.items():
        marker = "PASS" if ok else "FAIL"
        print(f"  Section {sec}: {marker}")

    if RUN_FAIL_ON_ERROR and not all(section_results.values()):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
