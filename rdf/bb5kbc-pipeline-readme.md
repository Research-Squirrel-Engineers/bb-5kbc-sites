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
6. [CLI-Optionen](#cli-optionen)
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
│   └── fst_wgs84.csv                 ← Eingabe (Output von csv_enrichment.py, read-only)
└── dist/
    ├── bb5kbc-data.ttl               ← konvertierte Daten
    ├── bb5kbc-bundle.ttl             ← Daten + Ontologie (selbst-genügsam)
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

Aus dem `rdf/`-Verzeichnis:

```bash
python bb5kbc_lod_pipeline.py
```

Erwartete Ausgabe (gekürzt):

```
[INFO] bb5kbc LOD pipeline — start
[INFO] Loaded CSV: 540 rows, 65 columns
[INFO] Processing rows ...
[INFO] Row 30: split fundstellenart 'Kreisgrabenanlage und Siedlung' into 2 components
[INFO] Row FID=54: fundstellenart 'Grab?' marked as uncertain (fsl:certaintyDesc).
[INFO] Row FID=35: dating_perio.do present but no match level specified — defaulting to skos:relatedMatch.
[INFO] Processed: 540 rows, skipped: 0
[INFO] Generated graph: 21657 triples
[INFO] Wrote data graph: ../dist/bb5kbc-data.ttl (21664 triples)
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

### 3. Pipeline-Provenance hinzufügen

Eine **einzelne** `prov:Activity` für den ganzen Lauf wird angelegt
(nicht eine pro Zeile, wie z.B. in Poseidon2LOD), mit:

- `prov:wasAssociatedWith` Sophie und Florian (ORCID-URIs)
- `prov:startedAtTime` UTC-Zeitstempel
- `prov:used` Eingabe-CSV und Ontologie-URI

### 4. Daten-Graph schreiben

Serialisiert nach `dist/bb5kbc-data.ttl` (Turtle-Format). Im Ergebnis
**nur die Daten**, keine Ontologie-Triples — dadurch bleibt die Datei
schlank und ist klar trennbar.

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
Exit-Code 0, auch wenn es Validierungsfehler gibt. Mit `--strict` kann
dieses Verhalten umgekehrt werden.

---

## Output-Dateien

### `dist/bb5kbc-data.ttl`

Die konvertierten Daten als Turtle. Enthält **keine Ontologie-Triples** —
zum Lesen oder Abfragen sollte sie zusammen mit `bb5kbc-ontology.ttl`
geladen werden.

Typische Größe für 540 Zeilen: ca. 21 650 Triples in 1.8 MB.

### `dist/bb5kbc-bundle.ttl`

**Daten + Ontologie in einer Datei** — selbst-genügsam, ideal zum Hochladen
in Triplestores oder zum Teilen mit Dritten. Enthält dieselben Daten-Triples
wie `bb5kbc-data.ttl` plus die kompletten Ontologie-Definitionen.

Typische Größe: ca. 22 280 Triples (~620 mehr als `bb5kbc-data.ttl`).

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

### `rdf/bb5kbc-shapes.ttl`

Die SHACL-Shapes selbst. Beim nächsten Lauf werden sie überschrieben
(immer in Sync mit der Ontologie). Keine manuelle Bearbeitung — falls
ein Shape nicht passt, ändert sich entweder die Ontologie oder die
Generator-Logik in Section 5 des Skripts.

---

## CLI-Optionen

```bash
python bb5kbc_lod_pipeline.py [OPTIONS]
```

| Option | Default | Wirkung |
|---|---|---|
| `--csv PATH` | `../data/fst_wgs84.csv` | andere CSV-Datei verwenden |
| `--ontology PATH` | `../ontology/bb5kbc-ontology.ttl` | andere Ontologie verwenden |
| `--out-dir PATH` | `../dist` | anderes Output-Verzeichnis |
| `--limit N` | unbegrenzt | nur die ersten N Zeilen verarbeiten (Tests) |
| `--strict` | aus | Exit-Code 1 bei SHACL-Verletzungen |
| `--no-shacl` | aus | SHACL-Validierung überspringen |

Beispiele:

```bash
# Schnelle Smoke-Tests mit 5 Zeilen
python bb5kbc_lod_pipeline.py --limit 5

# Strenge Validierung für CI/CD
python bb5kbc_lod_pipeline.py --strict

# Nur Daten generieren ohne Validierung (z.B. wenn pyshacl fehlt)
python bb5kbc_lod_pipeline.py --no-shacl
```

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

Pfade prüfen — das Skript erwartet die Datei standardmäßig unter
`../data/fst_wgs84.csv` relativ zu seiner eigenen Position. Mit
`--csv PATH` lässt sich ein anderer Pfad angeben.

### SHACL meldet hunderte Verstöße

Wahrscheinlich hat sich die Ontologie geändert, ohne dass die Datenstruktur
mitgezogen ist. Tipp: zuerst `--no-shacl` laufen lassen, dann den Daten-
Graph manuell inspizieren, um zu sehen ob die Triples sinnvoll aussehen.

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
