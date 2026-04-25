# bb-5kbc-sites

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
│   └── fst_wgs84_comma.csv
├── ontology/                     Anwendungsontologie + Diagramm-Generator
│   ├── bb5kbc-ontology.ttl
│   ├── bb5kbc_mermaid.py
│   └── bb5kbc-classes.mmd        ← auto-generiert
├── rdf/                          Pipeline-Skript + Schema-Artefakte
│   ├── bb5kbc_lod_pipeline.py
│   ├── bb5kbc-shapes.ttl         ← auto-generiert
│   └── bb5kbc-pipeline-readme.md
├── dist/                         Generierter Output
│   ├── bb5kbc-data.ttl
│   ├── shacl-report.ttl
│   └── report.log
├── bb5kbc-modelling-rules.md     Modellierungsregeln + SPARQL-Kochbuch
├── bb5kbc-csv-mapping.md         Spalte-für-Spalte-Mapping zur Ontologie
└── bb5kbc-csv-issues.md          Offene Datenfragen für Sophie
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

Erzeugt `dist/bb5kbc-data.ttl` + `dist/shacl-report.ttl` + `dist/report.log`.

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
| Wie sind die Daten modelliert? | `bb5kbc-modelling-rules.md` |
| Welche CSV-Spalte wird zu welchem Triple? | `bb5kbc-csv-mapping.md` |
| Wie läuft die Pipeline? | `rdf/bb5kbc-pipeline-readme.md` |
| Welche Daten sind noch offen? | `bb5kbc-csv-issues.md` |
| Welche Klassen gibt es? | `ontology/bb5kbc-classes.mmd` (in mermaid.live öffnen) |
| Beispiel-SPARQL-Anfragen | `bb5kbc-modelling-rules.md`, Abschnitt SPARQL-Kochbuch |

---

## Zitieren

> Schmidt, Sophie C. & Thiery, Florian (2026). *bb-5kbc-sites: Linked Open
> Data zu archäologischen Fundstellen (~5000 BC) in Brandenburg, Ostdeutschland
> und Westpolen.* Research Squirrel Engineers. CC BY 4.0.
> https://github.com/Research-Squirrel-Engineers/bb-5kbc-sites

---

*Fragen, Issues, Pull-Requests willkommen.*
