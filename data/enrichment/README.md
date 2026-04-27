# `data/enrichment` — Anreicherungs-Skripte

Dieses Verzeichnis enthält die drei Skripte, die das `fst_wgs84_comma.csv`
mit Wikidata-Identifikatoren anreichern. Sie werden vom Orchestrator
`data/csv_enrichment.py` aufgerufen, können aber auch einzeln laufen.

```
data/enrichment/
├── README.md                            (dieses Dokument)
├── literature/
│   └── enrich_qids.py                   ← Stage 1: Bibliographie
└── mapping_admin_regions/
    ├── wikidata_map.py                  ← Stage 2: Geo via SPARQL
    ├── enrich_fst.py                    ← Stage 3: Geo-Merge
    ├── fst_standortanalysen_ref.csv         (Input für Stage 2)
    └── fst_standortanalysen_ref_mapped.csv  (Output Stage 2 / Input Stage 3)
```

Der Orchestrator (`csv_enrichment.py`) kombiniert die drei Stufen, schreibt
die finale `fst_wgs84.csv` und ein PROV-O-Manifest. Die Stages 1 und 2 sind
unabhängig voneinander; Stage 3 erwartet die Outputs beider Vorstufen.
Über die Konstante `PIPELINE_MODE` im Orchestrator können einzelne Stages
übersprungen werden (siehe `csv_enrichment.py`).

---

## Stage 1 — `literature/enrich_qids.py`

### Was es macht

Reichert zwei Spalten der CSV mit Wikidata-QIDs an, die zu publizierten
Werken oder zu Quellen-Entitäten (Institutionen, Personen) führen:

| CSV-Spalte (Lookup-Key) | Ergebnis-Spalte | Mapping-Dictionary |
|---|---|---|
| `publikation_arch` | `QID_publikation` | `QID_PUBLIKATION` |
| `quelle_georef` | `QID_quelle_georef` | `QID_QUELLE_GEOREF` |

Die Mappings sind statisch im Code hinterlegt. Sie wurden ursprünglich aus
zwei QuickStatements-HTML-Seiten extrahiert und werden seitdem manuell
gepflegt — neue Treffer kommen typischerweise aus Reviews durch das
Fachpersonal (im Projekt durchgeführt von Sophie).

### Authoritäts-Modell („Modus A")

Das Code-Dictionary gilt als **Single Source of Truth**. Beim Lauf werden
drei Fälle pro Zelle unterschieden:

| Fall | Zelle in CSV | Mapping liefert | Aktion |
|---|---|---|---|
| `filled` | leer | QID | Zelle füllen |
| `confirmed` | gleicher QID | QID | unverändert (no-op) |
| `overwritten` | anderer QID | QID | überschreiben + Konflikt loggen |
| `noop` | egal | kein Mapping | unverändert (Miss-Log-Eintrag) |

Das ermöglicht es, Korrekturen am Code durchzureichen, ohne die CSV manuell
nachzuziehen — und umgekehrt fängt der Konflikt-Fall versehentliche
Falscheinträge ab. Jeder Konflikt landet mit Label, CSV-Zeile, alter und
neuer QID im Log (`csv_enrichment_literature.log`).

### Aufruf

Als Modul (so ruft der Orchestrator):

```python
from enrich_qids import run
summary = run(input_csv=..., output_csv=..., log_path=...)
```

Standalone (Default-Pfade relativ zum Skript, schreibt in-place):

```bash
python enrich_qids.py
```

### Output-Konventionen

* CSV mit `csv.QUOTE_ALL` (alle Felder gequotet)
* UTF-8 mit BOM (`utf-8-sig`)
* Leere Zellen als leere Strings, nicht als `nan`

---

## Stage 2 — `mapping_admin_regions/wikidata_map.py`

### Was es macht

Nimmt die Pipe-getrennte `fst_standortanalysen_ref.csv` mit deutschen und
polnischen Verwaltungs-Bezeichnungen und löst sie gegen Wikidata auf.
Pro Verwaltungsebene werden bis zu fünf externe Identifier-Spalten und
drei Audit-Spalten angefügt:

| Suffix | Quelle | Wikidata-Property |
|---|---|---|
| `_QID` | Wikidata | (Subjekt) |
| `_GeoNames` | GeoNames | P1566 |
| `_TGN` | Getty Thesaurus of Geographic Names | P1667 |
| `_IDAI` | iDAI.gazetteer (DAI) | P8217 |
| `_OSM_Relation` | OpenStreetMap | P402 |
| `_matchLabel` | Wikidata-Label des Treffers | (Audit, CSV-only) |
| `_matchScore` | Fuzzy-Score 0.0–1.0 | (Audit, CSV-only) |
| `_matchReason` | Diagnose-Text | (Audit, → RDF als `bb5kbc:wikidataMatchDescription`) |

Von den drei Audit-Spalten wird `_matchReason` in den späteren RDF-Graph als
`bb5kbc:wikidataMatchDescription` an den jeweiligen Type-Knoten übernommen —
ein einzelnes Klartext-Literal pro distinkter Verwaltungs-Entität, das Methode
(exact / fuzzy / override / transitive P131+), Normalisierungsschritte,
gesuchtes und gefundenes Label sowie den Score in einer Zeile zusammenfasst.
Damit lassen sich später per SPARQL z. B. alle Gemeinden mit nicht-exakter
Zuordnung zur Sophie-Review filtern. Die zwei verbleibenden Spalten
`_matchLabel` und `_matchScore` bleiben CSV-only und dienen der Triage über
`fst_standortanalysen_ref_report.csv`. Wikidata wird zusätzlich als Hub
benutzt: Alle externen Identifikatoren werden in derselben SPARQL-Antwort
mitgelesen.

### Wie das Fuzzy-Matching arbeitet

Für jede Verwaltungsebene wird in vier Schritten gearbeitet:

**1. SPARQL-Abruf eines Index.** Eine Liste aller plausiblen Wikidata-Items
für die Ebene wird einmal geholt. Pro Treffer werden Label (und alternative
Labels via `skos:altLabel`) sowie alle externen IDs in einem Dict
abgelegt, gekeyed auf das Lowercase-Label.

**2. Normalisierung der Eingabe.** Bevor gematcht wird, durchläuft jeder
CSV-Wert eine Pipeline:

* **Strip-Präfixe** (regex, case-insensitiv): z. B. `Landkreis X` → `X`,
  `Stadt X` → `X`, `Lutherstadt X` → `X`.
* **Aliases**: manuell gepflegtes Dict für Abkürzungen und übliche Varianten,
  z. B. `MVP` → `Mecklenburg-Vorpommern`, `Gmin X` → `Gmina X`.
* **Overrides**: hartkodierte Treffer für Edge Cases, die das Fuzzy-Matching
  nicht zuverlässig löst — z. B. aufgelöste Landkreise (`Hoyerswerda` →
  Q571947), ungewöhnliche polnische Schreibweisen, oder Fälle, in denen
  Wikidata mehrere ähnlich benannte Items hat. Ein Override-Treffer
  überspringt das Fuzzy-Matching komplett.

**3. Fuzzy-Matching mit `rapidfuzz`.** Wenn weder Alias noch Override
greifen, wird `process.extractOne` mit `fuzz.token_sort_ratio` gegen den
Index aufgerufen. `token_sort_ratio` ist wortreihenfolge-unabhängig und
toleriert dadurch Varianten wie `Bundesrepublik Deutschland` ↔ `Deutschland`.
Der Score wird auf 0.0–1.0 normalisiert.

Schwellwerte sind nach Ebene gestaffelt:

| Ebene | Schwellwert | Begründung |
|---|---|---|
| LAND | 0.85 | Sehr wenige Items, Labels stabil |
| BUNDESLAND | 0.85 | Stabile Labels, Aliases decken Abkürzungen ab |
| KREIS | 0.75 | Wikidata-Labels enthalten oft `Landkreis`-Präfixe, die in der CSV fehlen |
| GEMEINDE | 0.82 | Kleinere Orte mit knappen Labels, aber dafür P131-gescoped |

**4. Scoping pro Ebene.** Die SPARQL-Strategie unterscheidet sich, weil
ein einziger globaler Index für KREIS und GEMEINDE Wikidata sprengen würde:

* **LAND** und **BUNDESLAND**: Ein einziger globaler Index (Filter via
  `wdt:P31` auf passende Klassen wie `Q6256` Land, `Q1221156` deutsches
  Bundesland, `Q150093` polnische Woiwodschaft).
* **KREIS**: Ein Index *pro Bundesland*, gescoped per `wdt:P131` direkt
  (keine Transitivität, hält die Antwort klein). Aufgelöste Items werden
  via `MINUS { ?item wdt:P582 [] }` ausgeschlossen, KFZ-Kürzel via
  `FILTER(STRLEN > 3)`.
* **GEMEINDE**: Zweistufige Strategie.
  * *Stufe 1* — Index pro Kreis via `wdt:P131` direkt. Trifft polnische
    Gminas (zeigen direkt auf den Powiat) und deutsche Gemeinden, die direkt
    am Kreis hängen.
  * *Stufe 2* — Fallback nur für Stufe-1-Misses: pro unmatchtes Label ein
    eigener SPARQL-Call mit transitivem `wdt:P131+`. Sicher in der Laufzeit,
    weil sowohl Label als auch Kreis-QID die Suche eng begrenzen. Trifft
    deutsche Ortsteile, die unter einer Gemeinde hängen
    (Beispiel: Babekuhl → Putlitz → Prignitz).

### Index-Aufbau (`build_index`)

Wikidata gibt pro Item oft mehrere Zeilen zurück (eine pro Label-Variante,
eine pro alternativer Sprache). `build_index` *merged* diese Zeilen auf
denselben Lowercase-Schlüssel und akkumuliert die externen IDs. So gehen
keine GeoNames- oder TGN-IDs verloren, nur weil sie auf einer anderen Zeile
als die `rdfs:label`-Zeile stehen. Das `rdfs:label` setzt sich gegenüber
`skos:altLabel` als kanonisches Display-Label durch.

### Robustheit

* **Höflichkeitspause**: 1 s zwischen aufeinanderfolgenden SPARQL-Calls
  (`REQUEST_DELAY`).
* **Tee-Logger**: Wenn ein `log_path` angegeben ist, wird stdout parallel
  in die Log-Datei geschrieben — der Orchestrator bekommt also weiterhin
  die volle Konsolen-Ausgabe.
* **Stage-2-Timeout im Fallback**: Transitive Queries können auf großen
  Kreis-Hierarchien lange laufen; bei Timeout wird der Eintrag als
  No-Match behandelt, statt den ganzen Lauf abzubrechen.

### Aufruf

```python
from wikidata_map import run
run(
    input_csv=...,
    output_csv=...,
    report_csv=...,
    log_path=...,   # optional
)
```

Standalone-Lauf schreibt nach Default-Pfaden im Skript-Ordner. Achtung:
Ein voller Lauf dauert mehrere Minuten, da viele SPARQL-Calls anfallen.

### Output

* `fst_standortanalysen_ref_mapped.csv` — Eingabe + alle `<LEVEL>_*`-Spalten.
* `fst_standortanalysen_ref_report.csv` — Pro Zeile/Ebene ein Eintrag mit
  Score und `matchReason`, sortiert nach Score (zur Review-Triage).

---

## Stage 3 — `mapping_admin_regions/enrich_fst.py`

### Was es macht

Nimmt die literarisch angereicherte CSV (Stage-1-Output) und die
geo-angereicherte Referenz-CSV (Stage-2-Output) und führt sie zur finalen
`fst_wgs84.csv` zusammen. Pro Verwaltungsebene werden die Anreicherungs-
spalten **direkt nach** der jeweiligen Basis-Spalte eingefügt — die
Spaltenreihenfolge bleibt also lesbar und gruppiert.

Beispiel-Reihenfolge nach dem Merge:

```
... gemeinde, GEMEINDE_QID, GEMEINDE_GeoNames, GEMEINDE_TGN, GEMEINDE_IDAI,
GEMEINDE_OSM_Relation, GEMEINDE_matchLabel, GEMEINDE_matchScore,
GEMEINDE_matchReason, kreis, KREIS_QID, ...
```

### Join-Logik

Der Join ist ein einfacher `merge(... how="left")` über den FID:

| Quelle | Spalte |
|---|---|
| Original-CSV | `FID` |
| Mapped-CSV | `FID catalogue Schmidt 2026` (intern umbenannt zu `FID`) |

Beide Spalten werden vor dem Join auf String getrimmt. Ein Left-Join
garantiert, dass die Original-CSV als „treibende Seite" alle Zeilen
behält, auch wenn (sehr unwahrscheinlich) eine FID nicht in der Mapped-CSV
vorkommt — die Anreicherungsspalten bleiben dann leer.

### Robustheit

* Fehlende Anreicherungsspalten in der Mapped-CSV werden mit `[WARN]`
  geloggt, nicht als Fehler — das Skript bleibt funktional, wenn z. B.
  IDAI-Spalten fehlen.
* Fehlende Basis-Spalten in der Original-CSV werden ebenfalls gewarnt;
  die zugehörigen Anreicherungsspalten landen dann am Ende, statt in der
  Mitte.
* Spalten, die das Re-Order-Schema nicht zuordnen kann, werden auf jeden
  Fall ans Ende angehängt — Datenverlust ist konstruktionsbedingt
  ausgeschlossen.

### Aufruf

```python
from enrich_fst import run
summary = run(
    original_csv=...,   # Stage-1-Output (lit-enriched)
    mapped_csv=...,     # Stage-2-Output
    output_csv=...,     # finale fst_wgs84.csv
)
```

Das Summary-Dict enthält Zeilen- und Spaltenzahl, plus zwei Listen:
`missing_enrich_cols` und `missing_base_cols` (üblicherweise leer).

### Output-Konventionen

Wie bei Stage 1: alle Felder gequotet, UTF-8 mit BOM, leere Strings für
leere Zellen.

---

## Zusammenspiel der Stages

```
fst_wgs84_comma.csv
        │
        ▼  Stage 1 (enrich_qids.py)
fst_wgs84_lit_enriched.csv

fst_standortanalysen_ref.csv
        │
        ▼  Stage 2 (wikidata_map.py)
fst_standortanalysen_ref_mapped.csv

fst_wgs84_lit_enriched.csv  +  fst_standortanalysen_ref_mapped.csv
        │
        ▼  Stage 3 (enrich_fst.py)
fst_wgs84.csv  ← finale, LOD-fertige Datei
```

Stages 1 und 2 sind voneinander unabhängig und können in beliebiger
Reihenfolge oder parallel laufen. Stage 3 setzt beide Vor-Outputs voraus.
Der Orchestrator stellt das durch sein `PIPELINE_MODE`-System sicher und
führt zusätzlich PROV-O-Provenance über alle drei Stufen — auch über
übersprungene Stufen, die wiederverwendete Outputs nutzen.

---

## Konventionen über alle Stages

| Aspekt | Wert |
|---|---|
| CSV-Trennzeichen (Output) | Komma |
| CSV-Quoting | `csv.QUOTE_ALL` |
| Encoding | UTF-8 mit BOM (`utf-8-sig`) |
| Leere Zellen | leerer String, nicht `nan` |
| QID-Politik | nie raten — nur bestätigte Lookups oder manuelle Overrides |
| Code-Sprache | Englische Bezeichner und Docstrings, deutsche Inline-Kommentare wo fachlich nötig |
