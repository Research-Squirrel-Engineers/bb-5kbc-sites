# bb-5k-bc | Linked Open Data

> Linked Open Data zu archäologischen Fundstellen (~5000 BC) in Brandenburg,
> Ostdeutschland und Westpolen — als RDF-Datensatz, anwendungsspezifischer
> Ontologie und reproduzierbarem CSV-zu-RDF-Pipeline.

**Repository:** https://github.com/Research-Squirrel-Engineers/bb-5kbc-sites
· **Autor:innen:** Sophie C. Schmidt, Florian Thiery
· **Lizenz:** CC BY 4.0

---

## Worum geht's

540 archäologische Fundstellen mit Verwaltungsgebiet, Kulturgruppe,
Datierung, Georeferenzierungs-Provenance und externen Identifikatoren
(Wikidata, Getty TGN, iDAI.gazetteer, OSM, Perio.do).

Modelliert mit CIDOC CRM als Anwendungsontologie, validiert mit SHACL,
publiziert als Turtle.

---

## Verzeichnisstruktur

```
bb-5kbc-sites/
├── data/                         Eingabe-CSV (read-only)
│   ├── fst_wgs84_comma.csv
│   └── bb5kbc-csv-issues.md      Offene Datenfragen für Sophie
├── ontology/                     Anwendungsontologie + Diagramm-Generator
│   ├── bb5kbc-ontology.ttl
│   ├── bb5kbc_mermaid.py
│   ├── bb5kbc-classes.mmd        ← auto-generiert
│   └── bb5kbc-csv-mapping.md     Spalte-für-Spalte-Mapping zur Ontologie
├── rdf/                          Pipeline-Skript + Schema-Artefakte
│   ├── bb5kbc_lod_pipeline.py
│   ├── bb5kbc-shapes.ttl         ← auto-generiert
│   ├── bb5kbc-modelling-rules.md Modellierungsregeln + SPARQL-Kochbuch
│   └── bb5kbc-pipeline-readme.md
└── dist/                         Generierter Output
    ├── bb5kbc-data.ttl           Daten-Graph
    ├── bb5kbc-bundle.ttl         Daten + Ontologie (selbst-genügsam)
    ├── shacl-report.ttl
    ├── shacl-report-bundle.ttl
    └── report.log
```

---

## Voraussetzungen

```bash
pip install rdflib pandas pyshacl
```

Python 3.10 oder neuer.

---

## Quick Start

Aus dem Repository-Root:

```bash
# 1) Diagramm aus der Ontologie regenerieren (optional, falls Ontologie geändert)
cd ontology
python bb5kbc_mermaid.py

# 2) CSV in RDF konvertieren + SHACL-validieren
cd ../rdf
python bb5kbc_lod_pipeline.py
```

Erzeugt `dist/bb5kbc-data.ttl`, `dist/bb5kbc-bundle.ttl`, beide
SHACL-Reports und das `dist/report.log`.

---

## Datensatz-Kennzahlen

| | |
|---|---|
| Fundstellen | 540 |
| Triples (Daten) | 19.261 |
| Klassen (bb5kbc) | 15 |
| Properties (bb5kbc) | 22 |
| SHACL-Validierung | ✓ PASS |
| Externe Vokabulare | CIDOC CRM, FSL, Wikidata, Getty TGN, iDAI, OSM, Perio.do |

---

## Wo finde ich was

| Frage | Datei |
|---|---|
| Wie sind die Daten modelliert? | `rdf/bb5kbc-modelling-rules.md` |
| Welche CSV-Spalte wird zu welchem Triple? | `ontology/bb5kbc-csv-mapping.md` |
| Wie läuft die Pipeline? | `rdf/bb5kbc-pipeline-readme.md` |
| Welche Daten sind noch offen? | `data/bb5kbc-csv-issues.md` |
| Welche Klassen gibt es? | `ontology/bb5kbc-classes.mmd` (in mermaid.live öffnen) |
| Beispiel-SPARQL-Anfragen | `rdf/bb5kbc-modelling-rules.md`, Abschnitt SPARQL-Kochbuch |

---

## Zitieren

> Schmidt, Sophie C. & Thiery, Florian (2026). *bb-5kbc-sites: Linked Open
> Data zu archäologischen Fundstellen (~5000 BC) in Brandenburg, Ostdeutschland
> und Westpolen.* Research Squirrel Engineers. CC BY 4.0.
> https://github.com/Research-Squirrel-Engineers/bb-5kbc-sites

---

*Fragen, Issues, Pull-Requests willkommen.*
