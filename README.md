# bb-5k-bc | Linked Open Data

> Linked Open Data zu archäologischen Fundstellen (~5000 BC) in Brandenburg,
> Ostdeutschland und Westpolen — als RDF-Datensatz, anwendungsspezifischer
> Ontologie und reproduzierbarem CSV-zu-RDF-Pipeline.

**Repository:** https://github.com/Research-Squirrel-Engineers/bb-5kbc-sites
· **Autor:innen:** Sophie C. Schmidt, Florian Thiery
· **Lizenz:** Code MIT, Daten CC BY 4.0

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
├── data/                                 Eingabe-CSV + CSV-Anreicherungspipeline
│   ├── fst_wgs84_comma.csv               Original-CSV (33 Spalten)
│   ├── fst_wgs84.csv                     ← angereichert (64 Spalten, Output)
│   ├── csv_enrichment.py                 Orchestrator (PIPELINE_MODE konfigurierbar)
│   ├── csv_enrichment_run.ttl            ← PROV-O-Manifest des Enrichment-Laufs
│   ├── bb5kbc-csv-issues.md              Offene Datenfragen für Sophie
│   └── enrichment/                       Anreicherungs-Skripte
│       ├── README.md                     Erklärt enrich_qids/wikidata_map/enrich_fst
│       ├── literature/
│       │   └── enrich_qids.py            Stage 1: Bibliographie-QIDs
│       └── mapping_admin_regions/
│           ├── wikidata_map.py           Stage 2: Geo via SPARQL (Fuzzy-Matching)
│           ├── enrich_fst.py             Stage 3: Geo-Merge ins fst_wgs84.csv
│           └── fst_standortanalysen_ref*.csv
├── ontology/                             Anwendungsontologie + Diagramm-Generator
│   ├── bb5kbc-ontology.ttl
│   ├── bb5kbc_mermaid.py
│   ├── bb5kbc-classes.mmd                ← auto-generiert
│   └── bb5kbc-csv-mapping.md             Spalte-für-Spalte-Mapping zur Ontologie
├── rdf/                                  Pipeline + Validator + Schema
│   ├── bb5kbc_lod_pipeline.py            CSV → RDF + SHACL-Validierung
│   ├── validate_lod.py                   Tieferer Cross-Check (Doku ↔ Ontologie ↔ CSV ↔ RDF)
│   ├── bb5kbc-shapes.ttl                 ← auto-generiert
│   ├── bb5kbc-modelling-rules.md         Modellierungsregeln + SPARQL-Kochbuch
│   └── bb5kbc-pipeline-readme.md
└── dist/                                 Generierter Output
    ├── bb5kbc-data.ttl                   Daten-Graph
    ├── bb5kbc-bundle.ttl                 Daten + Ontologie (selbst-genügsam)
    ├── shacl-report.ttl
    ├── shacl-report-bundle.ttl
    ├── csv_to_lod_run.ttl                PROV-O-Manifest des LOD-Laufs
    ├── validation_report.md              ← validate_lod.py Output (5 Sektionen)
    └── report.log
```

---

## Voraussetzungen

```bash
pip install rdflib pandas pyshacl rapidfuzz requests
```

Python 3.10 oder neuer.

`rapidfuzz` und `requests` werden nur für die CSV-Anreicherungspipeline
(Stage 2, Wikidata-SPARQL) benötigt. Wer die bereits angereicherte
`fst_wgs84.csv` direkt in RDF konvertieren will, kommt mit
`rdflib pandas pyshacl` aus.

---

## Quick Start

Aus dem Repository-Root:

```bash
# 1) (Optional) Diagramm aus der Ontologie regenerieren
cd ontology
python bb5kbc_mermaid.py

# 2) (Optional) CSV-Anreicherung — wenn fst_wgs84.csv schon vorliegt, kann
#    PIPELINE_MODE in csv_enrichment.py auf 'literature' oder 'merge'
#    gesetzt werden, um SPARQL-Calls zu sparen.
cd ../data
python csv_enrichment.py

# 3) CSV in RDF konvertieren + SHACL-validieren
cd ../rdf
python bb5kbc_lod_pipeline.py

# 4) (Optional) Tieferer Cross-Check (Doku ↔ Ontologie ↔ CSV ↔ RDF)
python validate_lod.py
```

**Pipeline-Modi für Schritt 2** (in `data/csv_enrichment.py` oben):

| Mode | Stage 1 (Lit.) | Stage 2 (Geo SPARQL) | Stage 3 (Merge) | Wann |
|---|---|---|---|---|
| `full` | ✅ | ✅ | ✅ | Default, voller Lauf |
| `literature` | ✅ | ⏭ wiederverwendet | ✅ | Nur Bibliographie aktualisiert |
| `geo` | ⏭ | ✅ | ✅ | Nur Wikidata-Updates |
| `merge` | ⏭ | ⏭ | ✅ | Nur Spalten neu zusammenführen |

Übersprungene Stages werden im PROV-O-Manifest mit `ex:stageStatus "skipped"`
und `ex:reusedFromMTime` ehrlich dokumentiert.

Schritt 3 erzeugt `dist/bb5kbc-data.ttl`, `dist/bb5kbc-bundle.ttl`, beide
SHACL-Reports und das `dist/report.log`. Schritt 4 erzeugt zusätzlich den
fünfteiligen `dist/validation_report.md`.

---

## Datensatz-Kennzahlen

| | |
|---|---|
| Fundstellen | 540 |
| Triples (Daten-Graph) | 27.897 |
| Triples (Bundle = Daten + Ontologie) | 28.528 |
| Klassen (bb5kbc) | 16 |
| Properties (bb5kbc) | 26 |
| SHACL-Validierung | ✓ PASS |
| Validator-Sektionen (5/5) | ✓ PASS |
| Externe Vokabulare | CIDOC CRM, FSL, Wikidata, GeoNames, Getty TGN, iDAI, OSM, Perio.do, PROV-O, GeoSPARQL, OWL Time |

---

## Wo finde ich was

| Frage | Datei |
|---|---|
| Wie sind die Daten modelliert? | `rdf/bb5kbc-modelling-rules.md` |
| Welche CSV-Spalte wird zu welchem Triple? | `ontology/bb5kbc-csv-mapping.md` |
| Wie läuft die LOD-Pipeline? | `rdf/bb5kbc-pipeline-readme.md` |
| Wie läuft die CSV-Anreicherung? | `data/enrichment/README.md` |
| Welche Daten sind noch offen? | `data/bb5kbc-csv-issues.md` |
| Welche Klassen gibt es? | `ontology/bb5kbc-classes.mmd` (in [mermaid.live](https://mermaid.live) öffnen) |
| Beispiel-SPARQL-Anfragen | `rdf/bb5kbc-modelling-rules.md`, Abschnitt SPARQL-Kochbuch |
| Validierungs-Ergebnisse (5 Layer) | `dist/validation_report.md` (nach `python validate_lod.py`) |
| PROV-O-Provenance | `data/csv_enrichment_run.ttl` (Enrichment) + `dist/csv_to_lod_run.ttl` (LOD) |

---

## Zitieren

Die Software (Code, Pipeline, Ontologie-Skripte) ist unter **MIT** lizenziert
und kann maschinenlesbar über die mitgelieferte
[`CITATION.cff`](./CITATION.cff) zitiert werden — GitHub bietet darüber
einen "Cite this repository"-Knopf an.

Die generierten Daten und die Anwendungsontologie (`bb5kbc-data.ttl`,
`bb5kbc-bundle.ttl`, `bb5kbc-ontology.ttl`) sind unter **CC BY 4.0**
lizenziert.

Empfohlene Datensatz-Zitation:

> Schmidt, Sophie C. & Thiery, Florian (2026). *bb-5kbc-sites: Linked Open
> Data zu archäologischen Fundstellen (~5000 BC) in Brandenburg, Ostdeutschland
> und Westpolen.* Research Squirrel Engineers. CC BY 4.0.
> https://github.com/Research-Squirrel-Engineers/bb-5kbc-sites

---

*Fragen, Issues, Pull-Requests willkommen.*
