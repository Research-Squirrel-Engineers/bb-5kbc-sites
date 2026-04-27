# bb5kbc LOD — Validation Report

- Bundle: `bb5kbc-bundle.ttl` (28099 triples)
- CSV: `fst_wgs84.csv` (540 rows × 64 cols)
- Doku: `bb5kbc-csv-mapping.md`

**Layers checked**

1. Strukturelle Konsistenz (SHACL)
2. CSV ↔ RDF Vollständigkeit
3. Ontologie-Vollständigkeit
4. CRM-Verankerung
4b. Doku-Abgleich (csv-mapping.md ↔ Ontologie)

## Zusammenfassung

| Sektion | Ergebnis |
|---|---|
| 1. Strukturelle Konsistenz (SHACL) | ✅ **PASS** |
| 2. CSV ↔ RDF Vollständigkeit | ✅ **PASS** |
| 3. Ontologie-Vollständigkeit | ✅ **PASS** |
| 4. CRM-Verankerung | ✅ **PASS** |
| 4b. Doku-Abgleich | ✅ **PASS** |

---

## 1. Strukturelle Konsistenz (SHACL)

- ✅ **PASS** Daten-Graph: `sh:conforms true`, 0 Validation Results.
- ✅ **PASS** Bundle-Graph: `sh:conforms true`, 0 Validation Results.

---

## 2. CSV ↔ RDF Vollständigkeit

Pro CSV-Spalte: Anzahl nicht-leerer Werte vs. Anzahl korrespondierender Tripel im Bundle. Kompound-Werte (Siedlung+Grab) und Sonderfälle stehen explizit als *skip* mit Erklärung — diese Spalten werden nicht automatisch gegengeprüft.

| # | CSV-Spalte | Nicht-leer | Erwartung | Gefunden | Status |
|---|---|---|---|---|---|
| 1 | `quelle_georef` | 540 | (skip) fsl:hasReference Literal on Activity | — | — **SKIP** |
| 2 | `QID_quelle_georef` | 540 | (skip) fsl:hasReference URI on Activity | — | — **SKIP** |
| 3 | `katalognr` | 488 | je 1 Literal `bb5kbc:hatKatalognummer` an Fundstelle | 488 | ✅ **PASS** |
| 4 | `fst_id` | 540 | je 1 Literal `bb5kbc:hatFundstellenID` an Fundstelle | 540 | ✅ **PASS** |
| 5 | `fst_name` | 540 | je 1 Literal `rdfs:label` an Fundstelle | 540 | ✅ **PASS** |
| 6 | `gemeinde` | 540 | je 1 `bb5kbc:inGemeinde` von Fundstelle | 540 | ✅ **PASS** |
| 7 | `GEMEINDE_QID` | 540 (in 318 dist. gemeinde) | je 1 `hasExternalIdentifier` (entity) | 318 | ✅ **PASS** |
| 8 | `GEMEINDE_GeoNames` | 327 (in 169 dist. gemeinde) | je 1 `hasExternalIdentifier` (www.geonames.org) | 169 | ✅ **PASS** |
| 9 | `GEMEINDE_TGN` | 63 (in 42 dist. gemeinde) | je 1 `hasExternalIdentifier` (tgn) | 42 | ✅ **PASS** |
| 10 | `GEMEINDE_IDAI` | 2 (in 2 dist. gemeinde) | je 1 `hasExternalIdentifier` (place) | 2 | ✅ **PASS** |
| 11 | `GEMEINDE_OSM_Relation` | 330 (in 172 dist. gemeinde) | je 1 `hasExternalIdentifier` (relation) | 172 | ✅ **PASS** |
| 12 | `GEMEINDE_matchLabel` | 540 | 0 Tripel (audit-only, nicht im RDF) | — (Skript erzeugt nichts) | ✅ **PASS** |
| 13 | `GEMEINDE_matchScore` | 540 | 0 Tripel (audit-only, nicht im RDF) | — (Skript erzeugt nichts) | ✅ **PASS** |
| 14 | `GEMEINDE_matchReason` | 540 | 0 Tripel (audit-only, nicht im RDF) | — (Skript erzeugt nichts) | ✅ **PASS** |
| 15 | `kreis` | 540 | (skip) indirect: site → gemeinde → kreis | — | — **SKIP** |
| 16 | `KREIS_QID` | 540 (in 82 dist. kreis) | je 1 `hasExternalIdentifier` (entity) | 82 | ✅ **PASS** |
| 17 | `KREIS_GeoNames` | 327 (in 55 dist. kreis) | je 1 `hasExternalIdentifier` (www.geonames.org) | 55 | ✅ **PASS** |
| 18 | `KREIS_TGN` | 153 (in 13 dist. kreis) | je 1 `hasExternalIdentifier` (tgn) | 13 | ✅ **PASS** |
| 19 | `KREIS_IDAI` | 4 (in 1 dist. kreis) | je 1 `hasExternalIdentifier` (place) | 1 | ✅ **PASS** |
| 20 | `KREIS_OSM_Relation` | 327 (in 55 dist. kreis) | je 1 `hasExternalIdentifier` (relation) | 55 | ✅ **PASS** |
| 21 | `KREIS_matchLabel` | 540 | 0 Tripel (audit-only, nicht im RDF) | — (Skript erzeugt nichts) | ✅ **PASS** |
| 22 | `KREIS_matchScore` | 540 | 0 Tripel (audit-only, nicht im RDF) | — (Skript erzeugt nichts) | ✅ **PASS** |
| 23 | `KREIS_matchReason` | 540 | 0 Tripel (audit-only, nicht im RDF) | — (Skript erzeugt nichts) | ✅ **PASS** |
| 24 | `bundesland` | 540 | (skip) indirect: ... → kreis → bundesland | — | — **SKIP** |
| 25 | `BUNDESLAND_QID` | 540 (in 15 dist. bundesland) | je 1 `hasExternalIdentifier` (entity) | 15 | ✅ **PASS** |
| 26 | `BUNDESLAND_GeoNames` | 540 (in 15 dist. bundesland) | je 1 `hasExternalIdentifier` (www.geonames.org) | 15 | ✅ **PASS** |
| 27 | `BUNDESLAND_TGN` | 374 (in 8 dist. bundesland) | je 1 `hasExternalIdentifier` (tgn) | 8 | ✅ **PASS** |
| 28 | `BUNDESLAND_IDAI` | 362 (in 5 dist. bundesland) | je 1 `hasExternalIdentifier` (place) | 5 | ✅ **PASS** |
| 29 | `BUNDESLAND_OSM_Relation` | 540 (in 15 dist. bundesland) | je 1 `hasExternalIdentifier` (relation) | 15 | ✅ **PASS** |
| 30 | `BUNDESLAND_matchLabel` | 540 | 0 Tripel (audit-only, nicht im RDF) | — (Skript erzeugt nichts) | ✅ **PASS** |
| 31 | `BUNDESLAND_matchScore` | 540 | 0 Tripel (audit-only, nicht im RDF) | — (Skript erzeugt nichts) | ✅ **PASS** |
| 32 | `BUNDESLAND_matchReason` | 540 | 0 Tripel (audit-only, nicht im RDF) | — (Skript erzeugt nichts) | ✅ **PASS** |
| 33 | `land` | 528 | (skip) indirect: ... → bundesland → land | — | — **SKIP** |
| 34 | `LAND_QID` | 540 (in 2 dist. land) | je 1 `hasExternalIdentifier` (entity) | 2 | ✅ **PASS** |
| 35 | `LAND_GeoNames` | 540 (in 2 dist. land) | je 1 `hasExternalIdentifier` (www.geonames.org) | 2 | ✅ **PASS** |
| 36 | `LAND_TGN` | 540 (in 2 dist. land) | je 1 `hasExternalIdentifier` (tgn) | 2 | ✅ **PASS** |
| 37 | `LAND_IDAI` | 540 (in 2 dist. land) | je 1 `hasExternalIdentifier` (place) | 2 | ✅ **PASS** |
| 38 | `LAND_OSM_Relation` | 540 (in 2 dist. land) | je 1 `hasExternalIdentifier` (relation) | 2 | ✅ **PASS** |
| 39 | `LAND_matchLabel` | 540 | 0 Tripel (audit-only, nicht im RDF) | — (Skript erzeugt nichts) | ✅ **PASS** |
| 40 | `LAND_matchScore` | 540 | 0 Tripel (audit-only, nicht im RDF) | — (Skript erzeugt nichts) | ✅ **PASS** |
| 41 | `LAND_matchReason` | 540 | 0 Tripel (audit-only, nicht im RDF) | — (Skript erzeugt nichts) | ✅ **PASS** |
| 42 | `kultur` | 540 | je 1 `bb5kbc:hatKulturelleZuordnung` von Fundstelle | 540 | ✅ **PASS** |
| 43 | `entdeckung` | 432 | je 1 `bb5kbc:wurdeEntdecktDurch` von Fundstelle | 432 | ✅ **PASS** |
| 44 | `QID_entdeckung` | 382 | (skip) ext-id on EntdeckungsartType (deduplicated) | — | — **SKIP** |
| 45 | `publikation_arch` | 271 | je 1 `bb5kbc:hatPublikation` von Fundstelle | 271 | ✅ **PASS** |
| 46 | `QID_publikation` | 271 | (skip) ext-id on Publikation (one per non-empty cell) | — | — **SKIP** |
| 47 | `fundstellenart` | 540 | (skip) 1+ triples per site (compound + uncertainty splits) | — | — **SKIP** |
| 48 | `QID_fundstellenart` | 540 | (skip) ext-id on FundstellenartType (deduplicated) | — | — **SKIP** |
| 49 | `genauigkeit_m` | 540 | je 1 Literal `bb5kbc:hatGenauigkeit` an Fundstelle | 540 | ✅ **PASS** |
| 50 | `FID` | 540 | je 1 Literal `bb5kbc:hatFID` an Fundstelle | 540 | ✅ **PASS** |
| 51 | `methode` | 540 | (skip) fsl:methodUsed → fsl:MethodType (deduplicated) | — | — **SKIP** |
| 52 | `quellen_typ` | 540 | (skip) fsl:hasSourceType → fsl:SourceType (deduplicated) | — | — **SKIP** |
| 53 | `methodenbeschr` | 540 | (skip) fsl:activityDesc literal on Activity | — | — **SKIP** |
| 54 | `wgs84_x` | 540 | (skip) WKT POINT(x y) on sf:Point — combined with wgs84_y | — | — **SKIP** |
| 55 | `wgs84_y` | 540 | (skip) see wgs84_x | — | — **SKIP** |
| 56 | `dating_start` | 540 | je 1 Literal `bb5kbc:datierungStart` an Datierung | 540 | ✅ **PASS** |
| 57 | `dating_certainty_start` | 540 | je 1 Literal `bb5kbc:datierungSicherheitStart` an Datierung | 540 | ✅ **PASS** |
| 58 | `dating_end` | 540 | je 1 Literal `bb5kbc:datierungEnd` an Datierung | 540 | ✅ **PASS** |
| 59 | `dating_certainty_end` | 540 | je 1 Literal `bb5kbc:datierungSicherheitEnd` an Datierung | 540 | ✅ **PASS** |
| 60 | `dating_method` | 472 | (skip) Wikidata QID on DatierungsMethodeType (deduplicated) | — | — **SKIP** |
| 61 | `dating_certainty_range` | 540 | je 1 Literal `bb5kbc:datierungSicherheitRange` an Datierung | 540 | ✅ **PASS** |
| 62 | `dating_perio.do` | 501 | (skip) skos:{exact|close|related}Match on Datierung | — | — **SKIP** |
| 63 | `dating_perio.do_match` | 501 | (skip) controls predicate, no own triple | — | — **SKIP** |
| 64 | `sherd` | 4 | (skip) 0..n bb5kbc:hatScherbe per site | — | — **SKIP** |

---

## 3. Ontologie-Vollständigkeit

Nimmt alle Klassen und Properties, die im Datengraph *verwendet* werden, und prüft ob sie in der Ontologie *deklariert* sind. Externe Vokabulare (CRM, FSL, GeoSPARQL, PROV-O, SKOS, …) werden ausgeklammert — geprüft wird nur der `bb5kbc:`-Namespace.

### Klassen

- Verwendet: **16**, deklariert: **16**
- ✅ **PASS** Jede in den Daten verwendete `bb5kbc:`-Klasse ist in der Ontologie deklariert.

### Properties

- Verwendet: **25**, deklariert: **25**
- ✅ **PASS** Jede in den Daten verwendete `bb5kbc:`-Property ist in der Ontologie deklariert.

---

## 4. CRM-Verankerung

Für jede `bb5kbc:`-Klasse: gibt es einen Pfad über `rdfs:subClassOf` zu einem `crm:`-Knoten? Die angezeigte Kette ist eine repräsentative Spur (BFS, CRM-bevorzugt) — bei Multi-Inheritance kann es weitere Eltern geben, die in Sektion 4b vollständig gegen die Doku verglichen werden.

| Klasse | rdfs:subClassOf-Kette (eine Spur) | Status |
|---|---|---|
| `bb5kbc:Bundesland` | bb5kbc:Bundesland → crm:E53_Place → crm:E1_CRM_Entity | ✅ **PASS** |
| `bb5kbc:Datierung` | bb5kbc:Datierung → crm:E52_Time-Span → crm:E1_CRM_Entity | ✅ **PASS** |
| `bb5kbc:DatierungsMethodeType` | bb5kbc:DatierungsMethodeType → crm:E55_Type → crm:E1_CRM_Entity | ✅ **PASS** |
| `bb5kbc:Entdeckung` | bb5kbc:Entdeckung → crmsci:S19_Encounter_Event → crmsci:S4_Observation → crm:E13_Attribute_Assignment → crm:E7_Activity → crm:E5_Event → crm:E4_Period → crm:E2_Temporal_Entity → crm:E1_CRM_Entity | ✅ **PASS** |
| `bb5kbc:EntdeckungsartType` | bb5kbc:EntdeckungsartType → crm:E55_Type → crm:E1_CRM_Entity | ✅ **PASS** |
| `bb5kbc:Fundstelle` | bb5kbc:Fundstelle → crm:E27_Site → crm:E26_Physical_Feature → crm:E18_Physical_Thing → crm:E72_Legal_Object → crm:E70_Thing → crm:E1_CRM_Entity | ✅ **PASS** |
| `bb5kbc:FundstellenartType` | bb5kbc:FundstellenartType → lado:PlaceType → crm:E55_Type → crm:E1_CRM_Entity | ✅ **PASS** |
| `bb5kbc:Gemeinde` | bb5kbc:Gemeinde → crm:E53_Place → crm:E1_CRM_Entity | ✅ **PASS** |
| `bb5kbc:GeoreferenzierungsAktivitaet` | bb5kbc:GeoreferenzierungsAktivitaet → crm:E13_Attribute_Assignment → crm:E7_Activity → crm:E5_Event → crm:E4_Period → crm:E2_Temporal_Entity → crm:E1_CRM_Entity | ✅ **PASS** |
| `bb5kbc:Kreis` | bb5kbc:Kreis → crm:E53_Place → crm:E1_CRM_Entity | ✅ **PASS** |
| `bb5kbc:KulturelleZuordnung` | bb5kbc:KulturelleZuordnung → lado:SpaceTimeItem → crm:E92_Spacetime_Volume → crm:E1_CRM_Entity | ✅ **PASS** |
| `bb5kbc:Kulturgruppe` | bb5kbc:Kulturgruppe → crm:E4_Period → crm:E2_Temporal_Entity → crm:E1_CRM_Entity | ✅ **PASS** |
| `bb5kbc:Land` | bb5kbc:Land → crm:E53_Place → crm:E1_CRM_Entity | ✅ **PASS** |
| `bb5kbc:Publikation` | bb5kbc:Publikation → crm:E32_Authority_Document → crm:E73_Information_Object → crm:E70_Thing → crm:E1_CRM_Entity | ✅ **PASS** |
| `bb5kbc:Scherbe` | bb5kbc:Scherbe → crm:E22_Human-Made_Object → crm:E18_Physical_Thing → crm:E72_Legal_Object → crm:E70_Thing → crm:E1_CRM_Entity | ✅ **PASS** |
| `bb5kbc:externalIdentifierType` | bb5kbc:externalIdentifierType → crm:E55_Type → crm:E1_CRM_Entity | ✅ **PASS** |

✅ **PASS** Alle 16 `bb5kbc:`-Klassen sind über `rdfs:subClassOf` an einen CRM-Knoten verankert.

---

## 4b. Doku-Abgleich (csv-mapping.md ↔ Ontologie)

Vergleicht die handschriftliche Vererbungsketten-Tabelle in `bb5kbc-csv-mapping.md` (Sektion *Vererbungsketten*) mit den aus der Ontologie berechneten **vollständigen** Vorfahren-Mengen (Multi-Inheritance: alle direkten Eltern und ihre transitive Hülle). Vergleichsmodus: Mengenvergleich, Reihenfolge irrelevant, `crm:E1` ≡ `crm:E1_CRM_Entity`. Drift bedeutet: Doku und Modellierung sind asynchron.


| Klasse | nur in Doku | nur in Ontologie | Status |
|---|---|---|---|
| `bb5kbc:Bundesland` | — | — | ✅ **PASS** |
| `bb5kbc:Datierung` | — | — | ✅ **PASS** |
| `bb5kbc:DatierungsMethodeType` | — | — | ✅ **PASS** |
| `bb5kbc:Entdeckung` | — | — | ✅ **PASS** |
| `bb5kbc:EntdeckungsartType` | — | — | ✅ **PASS** |
| `bb5kbc:Fundstelle` | — | — | ✅ **PASS** |
| `bb5kbc:FundstellenartType` | — | — | ✅ **PASS** |
| `bb5kbc:Gemeinde` | — | — | ✅ **PASS** |
| `bb5kbc:GeoreferenzierungsAktivitaet` | — | — | ✅ **PASS** |
| `bb5kbc:Kreis` | — | — | ✅ **PASS** |
| `bb5kbc:KulturelleZuordnung` | — | — | ✅ **PASS** |
| `bb5kbc:Kulturgruppe` | — | — | ✅ **PASS** |
| `bb5kbc:Land` | — | — | ✅ **PASS** |
| `bb5kbc:Publikation` | — | — | ✅ **PASS** |
| `bb5kbc:Scherbe` | — | — | ✅ **PASS** |
| `bb5kbc:externalIdentifierType` | — | — | ✅ **PASS** |

✅ **PASS** Doku und Ontologie sind synchron.
