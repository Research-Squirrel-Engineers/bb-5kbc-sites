# bb5kbc LOD Pipeline — README

> Konvertiert die Brandenburg-5000-BC-Fundstellen-CSV in ein einziges
> Turtle-Dokument (`bb5kbc-data.ttl`) gemäß den Modellierungsregeln aus
> `bb5kbc-modelling-rules.md` und validiert das Ergebnis automatisch gegen
> SHACL-Shapes, die aus der Ontologie generiert werden.
>
> **Skript:** `bb5kbc_lod_pipeline.py` · **Stand:** Ontologie v0.10
> · **Lizenz:** CC BY 4.0

---

## Inhalt

1. [Verzeichnisstruktur](#verzeichnisstruktur)
2. [Voraussetzungen](#voraussetzungen)
3. [Erster Lauf](#erster-lauf)
4. [Was die Pipeline tut](#was-die-pipeline-tut)
5. [Output-Dateien](#output-dateien)
6. [Run-Settings](#run-settings)
7. [Logging und Warnungen](#logging-und-warnungen)
8. [SHACL-Validierung](#shacl-validierung)
9. [Bekannte Verhaltensweisen](#bekannte-verhaltensweisen)
10. [Wenn etwas nicht stimmt](#wenn-etwas-nicht-stimmt)

---

## Verzeichnisstruktur

Die Pipeline erwartet das Projekt in dieser Form (relative Pfade ab Skript):

```
root/
├── rdf/
│   ├── bb5kbc_lod_pipeline.py        ← dieses Skript
│   ├── bb5kbc-shapes.ttl             ← auto-generiert beim Lauf
│   └── bb5kbc-pipeline-readme.md     ← dieses Dokument
├── ontology/
│   └── bb5kbc-ontology.ttl           ← Anwendungsontologie
├── data/
│   ├── fst_wgs84.csv                 ← Eingabe (Output von csv_enrichment.py, read-only)
│   └── csv_enrichment_run.ttl        ← Upstream-PROV-Manifest (wird auto-discovered)
└── dist/
    ├── bb5kbc-data.ttl               ← konvertierte Daten (mit eingebetteter PROV-Kette)
    ├── bb5kbc-bundle.ttl             ← Daten + Ontologie (selbst-genügsam, mit PROV)
    ├── csv_to_lod_run.ttl            ← Standalone-PROV-Manifest dieses Laufs
    ├── shacl-report.ttl              ← Validierungsbericht (Daten-Graph)
    ├── shacl-report-bundle.ttl       ← Validierungsbericht (Bundle-Graph)
    └── report.log                    ← vollständiger Terminal-Output
```

Das Skript wird aus `rdf/` heraus aufgerufen. Eingabe-CSV und Ontologie
werden nie verändert. Alle generierten Artefakte landen in `dist/`, mit der
einen Ausnahme: `bb5kbc-shapes.ttl` liegt bei `rdf/`, weil sie konzeptionell
zum Schema gehören (versionsverwaltet, durchsuchbar, wiederverwendbar).

Die Eingabe-CSV `fst_wgs84.csv` ist der angereicherte Output der vorgelagerten
`csv_enrichment.py`-Pipeline (540 Zeilen, 65 Spalten — die ursprünglichen 33
Spalten plus je 8 Authority-ID-Spalten für LAND, BUNDESLAND, KREIS, GEMEINDE:
Wikidata QID, GeoNames, TGN, iDAI.gazetteer, OSM Relation und drei Match-
Metadatenspalten).

---

## Voraussetzungen

Python 3.10+ und drei Pakete:

```bash
pip install rdflib pandas pyshacl
```

`pyshacl` ist optional — ohne sie überspringt die Pipeline die Validierung
mit einer Warnung statt mit einem Fehler.

---

## Erster Lauf

Das Skript hat keine Kommandozeilen-Argumente — alle Einstellungen sind
Konstanten am Anfang des Skripts (Sektion 2, Block "Run settings"). Einfach
das Skript in VS Code öffnen und mit *F5* (oder *Run Python File*) starten;
oder aus dem `rdf/`-Verzeichnis heraus:

```bash
python bb5kbc_lod_pipeline.py
```

Erwartete Ausgabe (gekürzt):

```
[INFO] bb5kbc LOD pipeline — start
[INFO] Loaded CSV: 540 rows, 65 columns
[INFO] Upstream PROV:    ../data/csv_enrichment_run.ttl
[INFO] Processing rows ...
[INFO] Row 30: split fundstellenart 'Kreisgrabenanlage und Siedlung' into 2 components
[INFO] Row FID=54: fundstellenart 'Grab?' marked as uncertain (fsl:certaintyDesc).
[INFO] Row FID=35: dating_perio.do present but no match level specified — defaulting to skos:relatedMatch.
[INFO] Processed: 540 rows, skipped: 0
[INFO] Generated graph: 27347 triples
[INFO] Loaded upstream PROV: 93 triples, top-level activity: https://example.org/bb-5kbc-sites/run/2026-04-27T08-21-21Z
[INFO] Identified upstream entity for fst_wgs84.csv: https://example.org/bb-5kbc-sites/fst_wgs84_csv
[INFO] Embedded upstream PROV into data graph (+93 triples)
[INFO] PROV activity: http://w3id.org/bb5kbc/pipeline_run_2026-04-27T...Z
[INFO] Wrote data graph: ../dist/bb5kbc-data.ttl (27467 triples)
[INFO] Wrote bundle graph: ../dist/bb5kbc-bundle.ttl (28089 triples)
[INFO] Wrote LOD PROV manifest: ../dist/csv_to_lod_run.ttl (30 triples)
[INFO] Wrote shapes: ./bb5kbc-shapes.ttl (152 triples)
[INFO] SHACL validation: PASS (0 validation results)
[INFO] bb5kbc LOD pipeline — done
```

Laufzeit: ca. 20 Sekunden auf einem normalen Laptop, davon ~16 Sekunden SHACL-
Validierung (zwei Durchläufe: Daten-Graph + Bundle-Graph).

---

## Was die Pipeline tut

Sechs Schritte, in dieser Reihenfolge:

### 1. CSV einlesen

Mit `pandas.read_csv(..., dtype=str, keep_default_na=False)` — alle Werte
bleiben als String erhalten, leere Felder als leerer String. Damit gibt es
keine versteckte `NaN`-zu-Float-Konversion, die später zu `'nan'`-Triples
führen könnte.

### 2. Pro Zeile Triples bauen

Für jede Zeile durchläuft das Skript zehn Builder-Funktionen, in dieser
Reihenfolge (Reihenfolge ist relevant, weil spätere Builder Verweise auf
URIs früherer Builder brauchen):

```
add_land_triples           ┐
add_bundesland_triples     │ Verwaltungs-Containment
add_kreis_triples          │ (von außen nach innen)
add_gemeinde_triples       ┘
add_fundstelle_triples       ← FID-basierte URI; ohne FID wird Zeile übersprungen
add_fundstellenart_triples   ← Compound-Splitting falls "und"/","
add_entdeckung_triples       ← Ohne QID kein hatEntdeckungsart
add_publikation_triples
add_kulturelle_zuordnung_triples
add_datierung_triples        ← Mit dating_end-Korrekturen für FID 31/257
add_scherbe_triples          ← Pipe-Splitting für mehrere QIDs
add_georeferenzierung_triples ← Activity + sf:Point + alle FSL-Properties
```

Jede Builder-Funktion gibt die erzeugten URIs als Liste zurück, die im
`uri_dict` gesammelt werden — damit kann z.B. `add_kulturelle_zuordnung_triples`
auf die `Fundstelle`-URI zugreifen, die gerade erzeugt wurde.

### 3. Pipeline-Provenance + Verkettung zum CSV-Enrichment

Eine **einzelne** `prov:Activity` für den ganzen Lauf wird angelegt
(nicht eine pro Zeile, wie z.B. in Poseidon2LOD), mit:

- URI: `data:pipeline_run_<ISO-Timestamp>` (Doppelpunkte zu Bindestrichen,
  z.B. `pipeline_run_2026-04-27T09-22-28Z`)
- `prov:wasAssociatedWith` Sophie und Florian (ORCID-URIs) sowie der
  Software-Agent `data:bb5kbc_lod_pipeline_py`
- `prov:startedAtTime` und `prov:endedAtTime` UTC-Zeitstempel
- `prov:used` Eingabe-CSV und Ontologie-URI

Zwei explizite **Output-Entities** werden ebenfalls angelegt:

- `data:bb5kbc_data_ttl` (Daten-Graph) und `data:bb5kbc_bundle_ttl` (Bundle).
  Beide haben `prov:wasGeneratedBy` (diese Activity) und
  `prov:wasDerivedFrom` (die upstream-Entity für `fst_wgs84.csv`).

**Verkettung zum CSV-Enrichment-Lauf:** Wenn das Skript ein
`csv_enrichment_run.ttl` findet — entweder per Auto-Discovery in
`../data/csv_enrichment_run.ttl` oder per Override über die Konstante
`RUN_PROV_CSV_ENRICHMENT_OVERRIDE` im Skript-Header — passieren drei
Dinge:

1. Das Skript parst das Manifest und sucht die Top-Level-Activity (die
   keinen `prov:wasInformedBy`-Outlink hat).
2. Die LOD-Activity bekommt `prov:wasInformedBy <upstream-top-level>` —
   eine Cross-Namespace-Verknüpfung, weil das Upstream-Manifest in
   `https://example.org/bb-5kbc-sites/` lebt und die LOD-Pipeline in
   `http://w3id.org/bb5kbc/`.
3. Alle Tripel des Upstream-Manifests werden physisch in den Datengraphen
   eingebettet (≈ 90 Tripel) und damit auch ins Bundle. Jeder, der eines
   der LOD-Files lädt, sieht direkt die ganze Provenanz-Kette von der
   Original-CSV bis zum aktuellen Lauf.

Wenn kein Manifest gefunden wird, läuft das Skript **standalone** weiter
(ohne Verkettung), schreibt aber trotzdem seine eigene PROV-Activity in
das Output.

### 4. Daten-Graph schreiben

Serialisiert nach `dist/bb5kbc-data.ttl` (Turtle-Format). Enthält die Daten,
die LOD-PROV-Activity und (falls vorhanden) die eingebetteten upstream-PROV-
Tripel — **keine** Ontologie-Tripel, dadurch bleibt die Datei schlank und
klar trennbar.

Zusätzlich wird `dist/csv_to_lod_run.ttl` geschrieben — ein schlankes
Standalone-Manifest mit *nur* den LOD-seitigen PROV-Tripeln (ca. 30 Tripel),
analog zum `csv_enrichment_run.ttl` der vorgelagerten Pipeline. Das ist
nützlich, wenn man die Provenanz-Kette ohne die Daten betrachten möchte.

### 5. SHACL-Shapes generieren

Das Skript liest die Ontologie ein und erzeugt automatisch SHACL-Shapes:

- Eine `sh:NodeShape` pro `bb5kbc:`-Klasse (Target via `sh:targetClass`)
- Pro Object Property mit Domain-Constraint: `sh:property` mit `sh:path` und `sh:class` (= Range)
- Pro Datatype Property analog mit `sh:datatype`
- **Eine harte Regel:** `bb5kbc:Fundstelle` muss exakt einen `bb5kbc:hatFID` haben (`sh:Violation`)
- Alle übrigen Constraints sind `sh:Warning` (Domain/Range-Hinweise, nicht blockierend)

Das Ergebnis landet in `rdf/bb5kbc-shapes.ttl` und ist versionierbar.

### 6. Validieren und Bericht schreiben

`pyshacl.validate()` lädt die **frisch geschriebene** TTL-Datei (nicht den
In-Memory-Graph), die Shapes und die Ontologie als Inferenz-Graph. Der
Bericht wird nach `dist/shacl-report.ttl` geschrieben. Die ersten 10
Validierungsergebnisse erscheinen zusätzlich im Log.

Standard-Verhalten ist **Warning-only**: das Skript beendet sich mit
Exit-Code 0, auch wenn es Validierungsfehler gibt. Mit `RUN_STRICT = True`
im Skript-Header kann dieses Verhalten umgekehrt werden.

---

## Output-Dateien

### `dist/bb5kbc-data.ttl`

Die konvertierten Daten als Turtle. Enthält die Daten-Tripel, die LOD-PROV-
Activity und (bei Verkettung mit dem CSV-Enrichment-Lauf) auch die
eingebetteten upstream-PROV-Tripel — **keine** Ontologie-Tripel. Zum Lesen
oder Abfragen sollte sie zusammen mit `bb5kbc-ontology.ttl` geladen werden.

Typische Größe für 540 Zeilen: ca. 21 780 Triples in 1.8 MB (mit
eingebetteter Verkettung) bzw. ca. 21 685 Triples ohne (Standalone-Lauf).

### `dist/bb5kbc-bundle.ttl`

**Daten + Ontologie + PROV in einer Datei** — selbst-genügsam, ideal zum
Hochladen in Triplestores oder zum Teilen mit Dritten. Enthält dieselben
Daten- und PROV-Tripel wie `bb5kbc-data.ttl` plus die kompletten Ontologie-
Definitionen.

Typische Größe: ca. 22 400 Triples (~620 mehr als `bb5kbc-data.ttl`).

### `dist/shacl-report.ttl` und `dist/shacl-report-bundle.ttl`

Der Validierungsbericht im SHACL-Standardformat. Bei einem sauberen Lauf
enthält die Datei nur einen `sh:ValidationReport` mit `sh:conforms true`.
Bei Fehlern listet sie pro Verstoß einen `sh:ValidationResult` mit
`sh:focusNode` (welcher Knoten?), `sh:resultPath` (welche Property?) und
`sh:resultMessage` (was war falsch?).

Es gibt **zwei separate Berichte**: einen für `bb5kbc-data.ttl` (Daten-Graph
allein) und einen für `bb5kbc-bundle.ttl` (Daten + Ontologie). Beide werden
gegen dieselben SHACL-Shapes validiert, mit der Ontologie als Inferenz-Graph.
Im Idealfall sind beide Reports identisch (`sh:conforms true`).

Der Bericht ist selbst RDF und kann mit SPARQL abgefragt werden — siehe
`bb5kbc-modelling-rules.md` für ein Beispiel.

### `dist/report.log`

Vollständiger Terminal-Output dieses Laufs, mit Zeitstempel pro Zeile.
Hilfreich, um beim nächsten CSV-Update zu sehen, welche Daten-
korrekturen die Pipeline angewendet hat.

### `dist/csv_to_lod_run.ttl`

Schlankes Standalone-Manifest mit den PROV-O-Tripeln dieses LOD-Laufs:
die Activity, die Software-Agent-Erklärung, die zwei Output-Entities und —
falls upstream vorhanden — die Verkettungsangaben (`prov:wasInformedBy`,
`prov:wasDerivedFrom`). Analog zum `csv_enrichment_run.ttl` der vorgelagerten
Pipeline. Die *gleichen* Tripel sind auch in `bb5kbc-data.ttl` eingebettet —
diese Datei ist nur die separate Sicht zum Auditieren.

### `rdf/bb5kbc-shapes.ttl`

Die SHACL-Shapes selbst. Beim nächsten Lauf werden sie überschrieben
(immer in Sync mit der Ontologie). Keine manuelle Bearbeitung — falls
ein Shape nicht passt, ändert sich entweder die Ontologie oder die
Generator-Logik in Section 5 des Skripts.

---

## Run-Settings

Alle Einstellungen sind Konstanten am Anfang des Skripts (Sektion 2, Block
"Run settings"). Ändere die Werte direkt im Code; es gibt keine
Kommandozeilen-Argumente.

```python
# In bb5kbc_lod_pipeline.py, Section 2:

RUN_LIMIT: int | None = None
# Process only the first N rows (None = process the entire CSV).
# Useful for smoke-testing changes without waiting for the full 540-row run.

RUN_STRICT: bool = False
# Treat SHACL violations as errors (return code 1 on violations).
# When False, the pipeline always exits cleanly; violations are only logged.

RUN_SKIP_SHACL: bool = False
# Skip SHACL validation entirely (saves ~16 seconds).
# When True, no shacl-report*.ttl files are produced.

RUN_PROV_CSV_ENRICHMENT_OVERRIDE: Path | None = None
# Optional override for the upstream PROV manifest. When None, the pipeline
# auto-discovers ../data/csv_enrichment_run.ttl. Set to a Path object (or a
# string path) to point at a different manifest, e.g. an archived copy.
```

Pfade für CSV, Ontologie und Output-Ordner sind ebenfalls fix verdrahtet
(in `main()`):

| Was | Pfad |
|---|---|
| CSV-Eingabe | `../data/fst_wgs84.csv` |
| Ontologie | `../ontology/bb5kbc-ontology.ttl` |
| Output-Verzeichnis | `../dist` |
| Upstream PROV (auto-discovered) | `../data/csv_enrichment_run.ttl` |

Wenn du eine andere CSV oder Ontologie verwenden willst, änderst du das
direkt in `main()` (oder kopierst das Skript). Für eine schnelle
Smoke-Test-Iteration: `RUN_LIMIT = 5` und `RUN_SKIP_SHACL = True` setzen.

---

## Logging und Warnungen

Drei Log-Levels werden verwendet:

- **`INFO`** für normale Schritt-Meldungen und absichtliche Anpassungen
  (z.B. Compound-Splits, Default-Match-Level)
- **`WARNING`** für Daten, die korrigiert wurden (z.B. dating_end-Tippfehler)
- **`ERROR`** wird im Standardbetrieb nicht ausgelöst, nur bei
  fehlender CSV oder kaputter Ontologie

Alle Meldungen erscheinen im Terminal **und** in `dist/report.log`. Damit
ist der Lauf reproduzierbar nachvollziehbar.

---

## SHACL-Validierung

Die generierten Shapes folgen einem konservativen Ansatz:

- **Strikte Regel** (`sh:Violation`): jede `bb5kbc:Fundstelle` muss genau
  einen `bb5kbc:hatFID` haben. Wenn das fehlt, ist der Datensatz kaputt.
- **Hinweise** (`sh:Warning`): Domain/Range-Constraints aus der Ontologie.
  Ein typischer Hinweis wäre "Property X erwartet Range Y, gefunden Z".
  Diese sind oft False-Positives bei externen Identifiern (Wikidata-URIs
  haben keinen RDF-Typ in unseren Daten), deshalb sind sie warnend.

Wenn der Bericht **`sh:conforms true`** sagt, ist die Daten-Modellierung
mindestens strukturell konsistent. Inhaltliche Fragen (sind die Daten
*richtig*?) beantwortet SHACL nicht — dazu gibt es `bb5kbc-csv-issues.md`
und Sophies Review.

### Bericht selbst per SPARQL abfragen

```sparql
PREFIX sh: <http://www.w3.org/ns/shacl#>
SELECT ?focus ?path ?msg WHERE {
    ?result a sh:ValidationResult ;
            sh:focusNode ?focus ;
            sh:resultPath ?path ;
            sh:resultMessage ?msg .
}
```

---

## Bekannte Verhaltensweisen

Das Skript wendet diese **bewussten Anpassungen** an:

| Eintrag | Was passiert | Wo dokumentiert |
|---|---|---|
| `fundstellenart` mit "und" / "," | aufgesplittet in mehrere Type-Knoten | `COMPOUND_FUNDSTELLENART`-Dict im Skript |
| `fundstellenart` endet auf `?` (z.B. `Grab?`) | eigener, nicht-deduplizierter Type-Knoten pro Site mit `fsl:certaintyDesc "uncertain"@en` | `add_fundstellenart_triples`, Sophies Issue 3 |
| `kultur` endet auf `?` (z.B. `SBK?`) | `fsl:certaintyDesc "uncertain"@en` an der `KulturelleZuordnung` (nicht an der Kulturgruppe selbst) | `add_kulturelle_zuordnung_triples`, Sophies Issue 8 |
| `entdeckung` ohne QID | Knoten erstellt, aber kein `hatEntdeckungsart` | Modellierungsentscheidung |
| `dating_perio.do` ohne Match-Level | Default `skos:relatedMatch` | Info im Log |
| `wgs84 = (0,0)` | kein `sf:Point`, certainty `Q113 dubious` | Modellierungsregel |
| Leere CSV-Felder | kein Triple erzeugt (kein `""`-Literal) | Modellierungsregel |

**Authority-Identifier** werden für alle vier Verwaltungsebenen (LAND,
BUNDESLAND, KREIS, GEMEINDE) gelesen und als `bb5kbc:hasExternalIdentifier`
modelliert. Unterstützte Authorities: Wikidata (Spalte `<EBENE>_QID`),
GeoNames (`<EBENE>_GeoNames`), Getty TGN (`<EBENE>_TGN`), iDAI.gazetteer
(`<EBENE>_IDAI`), OSM Relation (`<EBENE>_OSM_Relation`). Zusätzlich zu
diesen fünf Authority-Spalten enthält die Eingabe-CSV pro Ebene drei Match-
Metadatenspalten (`matchLabel`, `matchScore`, `matchReason`), die das Skript
**nicht** in den RDF-Graph übernimmt — sie sind Audit-Information aus dem
vorgelagerten `csv_enrichment.py`-Lauf.

Falls Sophie eine der Korrekturen rückgängig machen möchte: die Tabelle
oben verweist auf die genauen Stellen im Skript.

---

## Wenn etwas nicht stimmt

### "ImportError: No module named rdflib"

```bash
pip install rdflib pandas pyshacl
```

### "CSV not found"

Pfade prüfen — das Skript erwartet die Datei unter `../data/fst_wgs84.csv`
relativ zu seiner eigenen Position. Wenn die CSV woanders liegt, im Skript
direkt in `main()` den `csv_path` anpassen.

### SHACL meldet hunderte Verstöße

Wahrscheinlich hat sich die Ontologie geändert, ohne dass die Datenstruktur
mitgezogen ist. Tipp: zuerst `RUN_SKIP_SHACL = True` setzen und laufen
lassen, dann den Daten-Graph manuell inspizieren, um zu sehen ob die
Triples sinnvoll aussehen.

### Pipeline läuft, aber `bb5kbc-data.ttl` ist leer / sehr klein

CSV-Headerzeile prüfen — wenn die Spaltennamen nicht den erwarteten
entsprechen (siehe `bb5kbc-csv-mapping.md`), generiert das Skript keine
Triples, weil alle Felder als leer eingestuft werden.

### Output sieht "vernünftig" aus, aber ich vermute Modellierungsfehler

Das Beispiel-TTL für FID=33 in `bb5kbc-csv-mapping.md` ist der **Goldstandard**.
Der entsprechende Block in `dist/bb5kbc-data.ttl` (suche nach `data:site_33`)
sollte dieselben 75 Triples enthalten. Abweichungen sind ein Bug.

---

*Fragen, Korrekturen, Erweiterungen: Issues im Repository oder direkt an
Sophie und Florian.*
