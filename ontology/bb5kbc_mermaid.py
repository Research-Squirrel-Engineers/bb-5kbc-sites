"""
bb5kbc_mermaid.py — Generate a minimal Mermaid classDiagram from the
bb5kbc application ontology.

USAGE:
    python bb5kbc_mermaid.py [path-to-ontology.ttl] [-o output.mmd]

Defaults (when called without arguments):
    Reads:  ./bb5kbc-ontology.ttl   (script directory)
    Writes: ./bb5kbc-classes.mmd    (script directory)

Designed to live inside the project's ontology/ directory alongside the
ontology file itself, so a plain `python bb5kbc_mermaid.py` from there
regenerates the diagram in place.

The script extracts only bb5kbc:-namespaced classes and properties; for each
class it shows the closest CRM (or CRMsci/CRMgeo) ancestor as a UML stereotype,
plus its datatype properties and a small "metadata" block (rdfs:label and
bb5kbc:hasExternalIdentifier where applicable) — chosen to keep the diagram
useful without bloat.

British English in comments; designed to be run from VS Code on Windows.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from collections import defaultdict

try:
    from rdflib import Graph, RDF, RDFS, OWL, URIRef
except ImportError:
    sys.exit("rdflib is required. Install with: pip install rdflib")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BB5KBC = "http://w3id.org/bb5kbc/ont/"

# Namespaces considered "CRM family" — the closest ancestor in any of these
# is shown as the class stereotype.
CRM_FAMILY = (
    "http://www.cidoc-crm.org/cidoc-crm/",
    "http://www.cidoc-crm.org/extensions/crmsci/",
    "http://www.cidoc-crm.org/extensions/crmgeo/",
)

# Short prefixes for stereotype labels and property qualifiers
PREFIXES = {
    "http://www.cidoc-crm.org/cidoc-crm/":              "crm:",
    "http://www.cidoc-crm.org/extensions/crmsci/":      "crmsci:",
    "http://www.cidoc-crm.org/extensions/crmgeo/":      "crmgeo:",
    "http://archaeology.link/ontology#":                "lado:",
    "http://fuzzy-sl.squirrel.link/ontology/":          "fsl:",
    "http://www.w3.org/2006/time#":                     "time:",
    "http://www.w3.org/ns/prov#":                       "prov:",
    "http://www.opengis.net/ont/geosparql#":            "geo:",
    "http://www.opengis.net/ont/sf#":                   "sf:",
    "http://xmlns.com/foaf/0.1/":                       "foaf:",
    "http://www.w3.org/2004/02/skos/core#":             "skos:",
    "http://www.w3.org/2001/XMLSchema#":                "xsd:",
    "https://pleiades.stoa.org/places/vocab#":          "pleiades:",
    BB5KBC:                                             "",
}

# Classes that are infrastructure (not modelled CSV concepts) and should
# NOT appear as boxes in the diagram. Add to this list if needed.
SKIP_CLASSES = {
    f"{BB5KBC}externalIdentifierType",
}

# Classes that carry a Wikidata QID or other external authority URI via
# bb5kbc:hasExternalIdentifier — used for the synthetic metadata block.
CLASSES_WITH_EXTID = {
    "Land", "Bundesland", "Kreis", "Gemeinde",
    "Kulturgruppe", "Publikation", "Scherbe",
    "FundstellenartType", "EntdeckungsartType", "DatierungsMethodeType",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def short(uri) -> str:
    """Convert a full URI to a prefixed short form."""
    s = str(uri)
    for ns, pfx in PREFIXES.items():
        if s.startswith(ns):
            return pfx + s[len(ns):]
    return s


def local_name(uri) -> str:
    """Strip the bb5kbc namespace and return the local name."""
    return str(uri).replace(BB5KBC, "")


def find_crm_ancestor(g: Graph, node: URIRef, seen: set | None = None) -> URIRef | None:
    """Walk rdfs:subClassOf upwards and return the closest CRM-family class."""
    if seen is None:
        seen = set()
    if node in seen:
        return None
    seen.add(node)
    if any(str(node).startswith(ns) for ns in CRM_FAMILY):
        return node
    for parent in g.objects(node, RDFS.subClassOf):
        result = find_crm_ancestor(g, parent, seen)
        if result is not None:
            return result
    return None


def get_bb5kbc_classes(g: Graph) -> list[URIRef]:
    """Return all owl:Class instances in the bb5kbc namespace, minus SKIP_CLASSES."""
    classes = []
    for c in g.subjects(RDF.type, OWL.Class):
        if str(c).startswith(BB5KBC) and str(c) not in SKIP_CLASSES:
            classes.append(c)
    return sorted(classes, key=str)


def get_datatype_props_for(g: Graph, cls: URIRef) -> list[tuple[str, str]]:
    """Return [(local_name, range_short)] for datatype properties with this class as domain."""
    props = []
    for p in g.subjects(RDF.type, OWL.DatatypeProperty):
        if not str(p).startswith(BB5KBC):
            continue
        domains = list(g.objects(p, RDFS.domain))
        if cls in domains:
            ranges = list(g.objects(p, RDFS.range))
            r = short(ranges[0]) if ranges else "?"
            props.append((local_name(p), r))
    return sorted(props)


def get_object_props(g: Graph) -> list[tuple[str, str, str]]:
    """Return [(domain_local, range_local, prop_local)] for bb5kbc object properties."""
    edges = []
    for p in g.subjects(RDF.type, OWL.ObjectProperty):
        if not str(p).startswith(BB5KBC):
            continue
        domains = list(g.objects(p, RDFS.domain))
        ranges = list(g.objects(p, RDFS.range))
        if not domains or not ranges:
            continue
        d, r = domains[0], ranges[0]
        # Only edges where both endpoints are bb5kbc classes shown in the diagram
        if str(d).startswith(BB5KBC) and str(r).startswith(BB5KBC) \
           and str(d) not in SKIP_CLASSES and str(r) not in SKIP_CLASSES:
            edges.append((local_name(d), local_name(r), local_name(p)))
    return sorted(set(edges))


# ---------------------------------------------------------------------------
# Mermaid generation
# ---------------------------------------------------------------------------

def class_block(name: str, stereotype: str, dt_props: list[tuple[str, str]],
                has_extid: bool) -> str:
    """Render one Mermaid class block with stereotype + properties."""
    lines = [f"class {name} {{"]
    lines.append(f"  <<{stereotype}>>")
    # Synthetic metadata: every box gets at least rdfs:label
    lines.append("  rdfs:label : @de")
    if has_extid:
        lines.append("  bb5kbc:hasExternalIdentifier : URI")
    for pname, prange in dt_props:
        lines.append(f"  {pname} : {prange}")
    lines.append("}")
    return "\n".join(lines)


def mermaid_edge_label(prop_local: str) -> str:
    """Escape a property name so Mermaid does not mis-parse it.

    Mermaid uses ':' as a separator between edge and label; a label that
    itself contains a colon (e.g. 'crm:P2_has_type') gets truncated to the
    part before the colon. Replace ':' with '--' as a visual delimiter.
    """
    return prop_local.replace(":", "--")


def build_mermaid(g: Graph) -> str:
    classes = get_bb5kbc_classes(g)
    edges = get_object_props(g)

    # Class blocks
    blocks = []
    for c in classes:
        name = local_name(c)
        # Stereotype = closest CRM ancestor.
        # With multi-inheritance (e.g. Fundstelle ⊑ lado:Location, fsl:Site,
        # crm:E27_Site simultaneously), the order of g.objects(c, RDFS.subClassOf)
        # is not guaranteed by rdflib. To get a deterministic stereotype:
        #   1. Prefer a direct parent in the CRM family.
        #   2. Otherwise, walk the first non-CRM parent's ancestry until a
        #      CRM-family class is found.
        direct_parents = sorted(g.objects(c, RDFS.subClassOf), key=str)
        crm_direct = next(
            (p for p in direct_parents
             if any(str(p).startswith(ns) for ns in CRM_FAMILY)),
            None,
        )
        if crm_direct is not None:
            stereotype = short(crm_direct)
        else:
            stereotype = None
            for parent in direct_parents:
                anc = find_crm_ancestor(g, parent)
                if anc is not None:
                    stereotype = short(anc)
                    break
            if stereotype is None:
                stereotype = "owl:Class"  # fallback — should not happen
        dt = get_datatype_props_for(g, c)
        blocks.append(class_block(name, stereotype, dt, name in CLASSES_WITH_EXTID))

    # Edges
    edge_lines = [f"{d} --> {r} : {mermaid_edge_label(p)}" for d, r, p in edges]

    out = ["classDiagram", "direction TB", ""]
    out.extend(blocks)
    out.append("")
    out.extend(edge_lines)
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("ontology", nargs="?",
                        default=str(here / "bb5kbc-ontology.ttl"),
                        help="Path to the bb5kbc ontology (.ttl). "
                             "Default: bb5kbc-ontology.ttl in the script directory.")
    parser.add_argument("-o", "--output",
                        default=str(here / "bb5kbc-classes.mmd"),
                        help="Output .mmd file. Default: bb5kbc-classes.mmd in the script directory.")
    args = parser.parse_args()

    onto_path = Path(args.ontology)
    if not onto_path.exists():
        print(f"ERROR: ontology file not found: {onto_path}", file=sys.stderr)
        return 1

    print(f"Reading ontology: {onto_path}")
    g = Graph()
    g.parse(str(onto_path), format="turtle")
    print(f"  {len(g)} triples parsed")

    mermaid = build_mermaid(g)

    out_path = Path(args.output)
    out_path.write_text(mermaid, encoding="utf-8")
    print(f"Wrote Mermaid diagram: {out_path}")
    print(f"  {mermaid.count(chr(10))} lines, {mermaid.count('class ')} classes, "
          f"{mermaid.count(' --> ')} edges")
    return 0


if __name__ == "__main__":
    sys.exit(main())
