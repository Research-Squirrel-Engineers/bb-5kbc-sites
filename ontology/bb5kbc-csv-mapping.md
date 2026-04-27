# bb5kbc CSV → Ontologie Mapping

## FSL-Metadaten-Struktur

| FSL-Schicht | Bedeutung | Hängt an |
|---|---|---|
| **GLM** — Geolocation Metadata | Fundstelle als Entität: Name, Typ, Lage, Publikation, IDs, Kulturgruppe | `bb5kbc:Fundstelle` |
| **CM** — Coordinate Metadata | Georeferenzierungsakt: Methode, Quelle, Genauigkeit, Koordinaten | `bb5kbc:GeoreferenzierungsAktivitaet` + `sf:Point` |

## Legende

| Symbol | Bedeutung |
|---|---|
| 🟦 | **Knoten (einfach)** — CSV-Wert → Named Node mit `rdfs:label`, URI = `{typ}_{hash}` |
| 🟦🔗 | **Knoten + ext. Link** — Named Node mit `rdfs:label` + mind. einem `bb5kbc:hasExternalIdentifier` |
| 🟨 | **Literal** — CSV-Wert → Datenwert direkt an einem Node, kein eigener Node |
| 🔗 | **Ext. URI** — CSV-Wert ist selbst eine externe ID → wird zu URI + `bb5kbc:hasExternalIdentifierType` |
| ⚙ | **Audit-only** — Spalte aus dem CSV-Enrichment, wird vom LOD-Skript **nicht** in RDF übersetzt |
| ⏳ | **Noch leer** — Spalte im Schema vorgesehen, Daten werden später ergänzt |

> Die CSV `fst_wgs84.csv` (540 Zeilen, 65 Spalten) ist der angereicherte Output
> der vorgelagerten `csv_enrichment.py`-Pipeline: ursprünglich 33 Spalten, plus
> 32 neue Spalten mit Authority-IDs für die vier Verwaltungsebenen (LAND,
> BUNDESLAND, KREIS, GEMEINDE) — pro Ebene jeweils 5 Authority-Spalten
> (Wikidata QID, GeoNames, TGN, iDAI.gazetteer, OSM Relation) und 3 Audit-
> Metadatenspalten (`matchLabel`, `matchScore`, `matchReason`). Davon wandert
> nur `matchReason` als `bb5kbc:wikidataMatchDescription` in den RDF-Graph
> (eine Klartext-Beschreibung pro distinktem Type-Knoten); `matchLabel` und
> `matchScore` bleiben CSV-only und dienen der Triage über
> `fst_standortanalysen_ref_report.csv`.

---

## URI-Schema

### FID-basiert (einmalig pro Fundstelle, direkte Site-Attribute)

| Entität | URI-Muster | Beispiel (FID=1) |
|---|---|---|
| `bb5kbc:Fundstelle` | `http://w3id.org/bb5kbc/site_{FID}` | `http://w3id.org/bb5kbc/site_1` |
| `bb5kbc:GeoreferenzierungsAktivitaet` | `http://w3id.org/bb5kbc/site_{FID}_activity` | `http://w3id.org/bb5kbc/site_1_activity` |
| `sf:Point` | `http://w3id.org/bb5kbc/site_{FID}_geom` | `http://w3id.org/bb5kbc/site_1_geom` |

### Hash-basiert (dedupliziert, URI = MD5 des Originalwerts, 8 Zeichen)

| Entität | URI-Muster | Beispiel |
|---|---|---|
| `bb5kbc:Gemeinde` | `http://w3id.org/bb5kbc/gemeinde_{hash}` | `gemeinde_c672785b` ← `"Behringen"` |
| `bb5kbc:Kreis` | `http://w3id.org/bb5kbc/kreis_{hash}` | `kreis_09060b5f` ← `"Wartburgkreis"` |
| `bb5kbc:Bundesland` | `http://w3id.org/bb5kbc/bundesland_{hash}` | `bundesland_eec0c902` ← `"Thüringen"` |
| `bb5kbc:Land` | `http://w3id.org/bb5kbc/land_{hash}` | `land_3c2f8b8c` ← `"Deutschland"` |
| `bb5kbc:Kulturgruppe` | `http://w3id.org/bb5kbc/kultur_{hash}` | `kultur_cc414e20` ← `"SBK"`, `kultur_7a001224` ← `"SBK?"` |
| `bb5kbc:KulturelleZuordnung` | `http://w3id.org/bb5kbc/site_{FID}_culture` | `site_33_culture` ← Fundstelle FID=33 |
| `bb5kbc:Datierung` | `http://w3id.org/bb5kbc/site_{FID}_dating` | `site_33_dating` ← Fundstelle FID=33 |
| `bb5kbc:DatierungsMethodeType` | `http://w3id.org/bb5kbc/datmethode_{hash}` | `datmethode_{hash}` ← hash aus Wikidata-QID |
| `bb5kbc:Scherbe` | `http://w3id.org/bb5kbc/sherd_{hash}` | `sherd_ddd27e7f` ← `"Q173387"` |
| `bb5kbc:Entdeckung` | `http://w3id.org/bb5kbc/entdeckung_{hash}` | `entdeckung_{hash}` ← hash aus entdeckung-Text |
| `bb5kbc:EntdeckungsartType` | `http://w3id.org/bb5kbc/entdeckungsart_{hash}` | `entdeckungsart_1f56a08c` ← `"Ausgrabung"` |
| `bb5kbc:FundstellenartType` | `http://w3id.org/bb5kbc/fundstellenart_{hash}` | `fundstellenart_1972902b` ← `"Siedlung"` |
| `bb5kbc:Publikation` | `http://w3id.org/bb5kbc/pub_{hash}` | `pub_c5110572` ← `"Kaufmann 1976"` |
| `fsl:MethodType` | `http://w3id.org/bb5kbc/methode_{hash}` | `methode_b57e2231` ← `"Übernahme aus externer Datenbank"` |
| `fsl:SourceType` | `http://w3id.org/bb5kbc/quellentyp_{hash}` | `quellentyp_e6dc730e` ← `"Printpublikation"` |

> **Hash-Funktion:** `MD5(originalwert_utf8)[:8]` — kollisionssicher auch bei Unicode-Varianten.
> **`_activity` und `_geom`** sind die einzigen site-spezifischen Suffixe. Alle anderen Entitäten werden global dedupliziert.

---

## Mapping-Tabelle — GLM

> Die Spaltennummern entsprechen der tatsächlichen Position in `fst_wgs84.csv`
> (1-indiziert, 65 Spalten). Die Spalten `*_matchLabel` und `*_matchScore`
> stammen aus dem CSV-Enrichment-Lauf und werden vom LOD-Skript nicht ins RDF
> übernommen (CSV-only). Die Spalte `*_matchReason` wird hingegen als
> `bb5kbc:wikidataMatchDescription` an den jeweiligen Verwaltungs-Type-Knoten
> in den RDF-Graph übernommen (siehe Datatype-Properties-Tabelle weiter unten).
> Aus Übersichtlichkeitsgründen sind alle Audit-Spalten (`*_matchLabel`,
> `*_matchScore`, `*_matchReason`) trotzdem nicht in der folgenden Mapping-
> Tabelle aufgeführt.

| # | CSV-Spalte | Beispielwert | Art | bb5kbc-Klasse / Property | Hinweis |
|---|---|---|---|---|---|
| 51 | `FID` | `"1"` | 🟨 | `bb5kbc:Fundstelle` ← `bb5kbc:hatFID` : `xsd:integer` (subPropertyOf `dc:identifier` + `crm:P1_is_identified_by`) | PID, Basis aller FID-URIs |
| 4 | `fst_id` | `"444"` | 🟨 | `bb5kbc:Fundstelle` ← `bb5kbc:hatFundstellenID` : `xsd:string` | Interne ID, nicht immer eindeutig |
| 3 | `katalognr` | `"55"` | 🟨 | `bb5kbc:Fundstelle` ← `bb5kbc:hatKatalognummer` : `xsd:string` | 52 leer |
| 5 | `fst_name` | `"Tüngeda"` | 🟨 | `bb5kbc:Fundstelle` ← `rdfs:label` + `skos:prefLabel` : Literal `@de` | |
| 6 | `gemeinde` | `"Friesack"` | 🟦🔗 | `bb5kbc:Fundstelle` ← `bb5kbc:inGemeinde` → `bb5kbc:Gemeinde` | + bis zu 5 Authority-IDs (Spalten 7–11) |
| 7 | `GEMEINDE_QID` | `"Q585632"` | 🔗 | `bb5kbc:Gemeinde` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_Wikidata` | |
| 8 | `GEMEINDE_GeoNames` | `"6550607"` | 🔗 | `bb5kbc:Gemeinde` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_GeoNames` | |
| 9 | `GEMEINDE_TGN` | *(meist leer)* | 🔗 | `bb5kbc:Gemeinde` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_TGN` | |
| 10 | `GEMEINDE_IDAI` | *(meist leer)* | 🔗 | `bb5kbc:Gemeinde` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_iDAI` | |
| 11 | `GEMEINDE_OSM_Relation` | `"1342247"` | 🔗 | `bb5kbc:Gemeinde` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_OSM` | |
| 12–14 | `GEMEINDE_match*` | — | ⚙ | — | Audit-only, nicht im RDF |
| 15 | `kreis` | `"Havelland"` | 🟦🔗 | `bb5kbc:Gemeinde` ← `bb5kbc:inKreis` → `bb5kbc:Kreis` | + bis zu 5 Authority-IDs (Spalten 16–20) |
| 16 | `KREIS_QID` | `"Q6139"` | 🔗 | `bb5kbc:Kreis` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_Wikidata` | |
| 17 | `KREIS_GeoNames` | *(häufig leer)* | 🔗 | `bb5kbc:Kreis` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_GeoNames` | |
| 18 | `KREIS_TGN` | *(häufig leer)* | 🔗 | `bb5kbc:Kreis` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_TGN` | |
| 19 | `KREIS_IDAI` | *(häufig leer)* | 🔗 | `bb5kbc:Kreis` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_iDAI` | |
| 20 | `KREIS_OSM_Relation` | *(häufig leer)* | 🔗 | `bb5kbc:Kreis` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_OSM` | |
| 21–23 | `KREIS_match*` | — | ⚙ | — | Audit-only, nicht im RDF |
| 24 | `bundesland` | `"Brandenburg"` | 🟦🔗 | `bb5kbc:Kreis` ← `bb5kbc:inBundesland` → `bb5kbc:Bundesland` | + bis zu 5 Authority-IDs (Spalten 25–29); inkl. Wojewodschaften |
| 25 | `BUNDESLAND_QID` | `"Q1208"` | 🔗 | `bb5kbc:Bundesland` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_Wikidata` | |
| 26 | `BUNDESLAND_GeoNames` | `"2945356"` | 🔗 | `bb5kbc:Bundesland` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_GeoNames` | |
| 27 | `BUNDESLAND_TGN` | `"7000096"` | 🔗 | `bb5kbc:Bundesland` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_TGN` | |
| 28 | `BUNDESLAND_IDAI` | `"2048409"` | 🔗 | `bb5kbc:Bundesland` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_iDAI` | |
| 29 | `BUNDESLAND_OSM_Relation` | `"62504"` | 🔗 | `bb5kbc:Bundesland` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_OSM` | |
| 30–32 | `BUNDESLAND_match*` | — | ⚙ | — | Audit-only, nicht im RDF |
| 33 | `land` | `"Deutschland"` | 🟦🔗 | `bb5kbc:Bundesland` ← `bb5kbc:inLand` → `bb5kbc:Land` | + 5 Authority-IDs (Spalten 34–38) |
| 34 | `LAND_QID` | `"Q183"` | 🔗 | `bb5kbc:Land` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_Wikidata` | |
| 35 | `LAND_GeoNames` | `"2921044"` | 🔗 | `bb5kbc:Land` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_GeoNames` | |
| 36 | `LAND_TGN` | `"7000084"` | 🔗 | `bb5kbc:Land` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_TGN` | |
| 37 | `LAND_IDAI` | `"2044274"` | 🔗 | `bb5kbc:Land` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_iDAI` | |
| 38 | `LAND_OSM_Relation` | `"51477"` | 🔗 | `bb5kbc:Land` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_OSM` | |
| 39–41 | `LAND_match*` | — | ⚙ | — | Audit-only, nicht im RDF |
| 42 | `perio.do` | *(leer)* | 🔗 ⏳ | `bb5kbc:Kulturgruppe` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_PerioDo` | 0/540 gefüllt; Spalte verbleibt im Schema |
| 43 | `kultur` | `"SBK"` / `"SBK?"` | 🟦🔗 | `bb5kbc:KulturelleZuordnung` ← `bb5kbc:hatKulturgruppe` → `bb5kbc:Kulturgruppe` | `?`-Werte: `fsl:certaintyDesc "uncertain"@en` an der `KulturelleZuordnung` |
| 44 | `entdeckung` | `"Ausgrabung Bersu"` | 🟦🔗 | `bb5kbc:Fundstelle` ← `bb5kbc:wurdeEntdecktDurch` → `bb5kbc:Entdeckung` | `rdfs:label` aus Text + `bb5kbc:hatEntdeckungsart` → `bb5kbc:EntdeckungsartType` |
| 45 | `QID_entdeckung` | `"Q959782"` | 🔗 | `bb5kbc:EntdeckungsartType` ← `bb5kbc:hasExternalIdentifier` → Wikidata | nur 2 QIDs |
| 46 | `publikation_arch` | `"Kaufmann 1976"` | 🟦🔗 | `bb5kbc:Fundstelle` ← `bb5kbc:hatPublikation` → `bb5kbc:Publikation` | + `QID_publikation` (via `enrich_qids.py`); 273 leer |
| 47 | `QID_publikation` | `"Q139304616"` | 🔗 | `bb5kbc:Publikation` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_Wikidata` | gefüllt durch `enrich_qids.py`; Pyzel 2019 / Umbreit 1940 noch offen |
| 48 | `fundstellenart` | `"Siedlung und Grab"` / `"Grab?"` | 🟦🔗 | `bb5kbc:Fundstelle` ← `bb5kbc:hatFundstellenart` → `bb5kbc:FundstellenartType` | subPropertyOf `crm:P2_has_type` + `fsl:siteType`; Kombi-Werte als mehrere Type-Knoten; `?`-Werte: eigener Knoten pro Site mit `fsl:certaintyDesc "uncertain"@en` |
| 49 | `QID_fundstellenart` | `"Q173387"` | 🔗 | `bb5kbc:FundstellenartType` ← `bb5kbc:hasExternalIdentifier` → Wikidata | 4 QIDs |

### Dating-Spalten

| # | CSV-Spalte | Beispielwert | Art | bb5kbc-Klasse / Property | Hinweis |
|---|---|---|---|---|---|
| — | *(URI)* | `site_{FID}_dating` | 🟦 | `bb5kbc:KulturelleZuordnung` ← `bb5kbc:hatDatierung` → `bb5kbc:Datierung` | 1 Node pro Fundstelle; URI FID-basiert (entkoppelt von Kulturgruppe) |
| 57 | `dating_start` | `"-4550"` | 🟨 | `bb5kbc:Datierung` ← `bb5kbc:datierungStart` : `xsd:integer` | subPropertyOf `crm:P82a_begin_of_the_begin`; negativ = BCE |
| 59 | `dating_end` | `"-3900"` | 🟨 | `bb5kbc:Datierung` ← `bb5kbc:datierungEnd` : `xsd:integer` | subPropertyOf `crm:P82b_end_of_the_end` |
| 61 | `dating_method` | `"Q173412"` | 🟦🔗 | `bb5kbc:Datierung` ← `bb5kbc:datierungMethode` → `bb5kbc:DatierungsMethodeType` | hash-URI `datmethode_{MD5(QID)[:8]}`; nur 2 distinct (Q173412 14C, Q816829 stilistisch) |
| 58 | `dating_certainty_start` | `"+/- 100 years"` | 🟨 | `bb5kbc:Datierung` ← `bb5kbc:datierungSicherheitStart` : `xsd:string` | Freitext, vereinheitlicht auf Englisch |
| 60 | `dating_certainty_end` | `"+/- 100 years"` | 🟨 | `bb5kbc:Datierung` ← `bb5kbc:datierungSicherheitEnd` : `xsd:string` | Freitext, vereinheitlicht auf Englisch |
| 62 | `dating_certainty_range` | `"medium certainty, some 14C dates available"` | 🟨 | `bb5kbc:Datierung` ← `bb5kbc:datierungSicherheitRange` : `xsd:string` | qualitative Bewertung der Gesamtdatierung; 14 distinct |
| 63 | `dating_perio.do` | `"http://n2t.net/ark:/99152/p0wctqtnkjq"` | 🔗 | `bb5kbc:Datierung` ← `skos:{matchType}` → Perio.do-URI | nur wenige distinct URIs |
| 64 | `dating_perio.do_match` | `"closeMatch"` | — | bestimmt Property: `skos:exactMatch` / `skos:closeMatch` / `skos:relatedMatch` | kein eigenes Triple — steuert welche SKOS-Property genutzt wird; leer → Default `relatedMatch` |

### Scherben-Spalte

| # | CSV-Spalte | Beispielwert | Art | bb5kbc-Klasse / Property | Hinweis |
|---|---|---|---|---|---|
| 65 | `sherd` | `"Q139477253\|Q139477652"` | 🟦🔗 | `bb5kbc:Fundstelle` ← `bb5kbc:hatScherbe` → `bb5kbc:Scherbe` | 1-n Wikidata-QIDs, Delimiter `\|`; hash-URI `sherd_{MD5(QID)[:8]}`; Wikidata-URI via `bb5kbc:hasExternalIdentifier`; nur 4/540 gefüllt (FID 37, 41, 48, 80) |

---

## Mapping-Tabelle — CM

| # | CSV-Spalte | Beispielwert | Art | bb5kbc-Klasse / Property | FSL OWL | Wikibase | Hinweis |
|---|---|---|---|---|---|---|---|
| — | *(abgeleitet)* | `Q23 / Q15 / Q24 / Q113` | 🟦 | `bb5kbc:Fundstelle` ← `fsl:certaintyLevel` → `fsl:CertaintyType` | `fsl:certaintyLevel` | P5 | Aus `genauigkeit_m`: `<Q23>` high = 0m · `<Q15>` medium = 50–500m · `<Q24>` low = 800–5000m · `<Q113>` dubious = wgs84 0,0 (Koordinatenfehler) |
| 53 | `quellen_typ` | `"Printpublikation"` | 🟦 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:hasSourceType` → `fsl:SourceType` | `fsl:hasSourceType` | P6 | Named Node `quellentyp_{hash}`; 4 distinct |
| 52 | `methode` | `"Übernahme aus externer Datenbank"` | 🟦 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:methodUsed` → `fsl:MethodType` | `fsl:methodUsed` | P7 | Named Node `methode_{hash}`; 3 distinct |
| 55+56 | `wgs84_x` + `wgs84_y` | `"10.58"` + `"51.03"` | 🟨 | `sf:Point` ← `geosparql:asWKT` : `"POINT(10.58 51.03)"^^geosparql:wktLiteral` via `fsl:representativeGeometry` + `geosparql:hasGeometry` | `geosparql:hasGeometry` | P4 | Komma als Dezimaltrenner in CSV (`"10,58"`) → Punkt im WKT; bei `0,0` kein `sf:Point`, `fsl:certaintyLevel` → `<Q113>` dubious |
| 54 | `methodenbeschr` | `"Koordinaten wurden vom LdfA..."` | 🟨 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:certaintyDesc` : `xsd:string` | `fsl:certaintyDesc` | P13 | Freitext; 22 distinct |
| — | *(fest)* | `https://orcid.org/0000-0003-4696-2101` | 🟦 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:georeferencingBy` → `foaf:Person` | `fsl:georeferencingBy` | P14 | Sophie C. Schmidt; auch `prov:wasAssociatedWith` |
| 54 | `methodenbeschr` | `"Koordinaten wurden vom LdfA..."` | 🟨 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:activityDesc` : `xsd:string` | `fsl:activityDesc` | P15 | Freitext; 22 distinct |
| 53 | `quellen_typ` | `"Printpublikation"` | 🟦 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:hasSourceTypeDetail` → `fsl:SourceType` | `fsl:hasSourceTypeDetail` | P16 | Gleiche Spalte wie P6, detail-Ebene |
| 50 | `genauigkeit_m` | `"100"` | 🟨 | `bb5kbc:Fundstelle` ← `bb5kbc:hatGenauigkeit` : `xsd:decimal` | `fsl:precision` | P23 | subPropertyOf `fsl:precision` |
| — | *(fest)* | `https://fuzzy-sl.wikibase.cloud/entity/Q80` | 🟦 | `bb5kbc:Fundstelle` ← `fsl:hasLocationType` → `fsl:LocationType` | `fsl:hasLocationType` | P24 | Immer `<Q80>` Findspot |
| 1 | `quelle_georef` | `"LfDA Sachsen-Anhalt"` | 🟨 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:hasReference` : `xsd:string` | `fsl:hasReference` | P25 | Literal |
| 2 | `QID_quelle_georef` | `"Q1802049"` | 🔗 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:hasReference` → Wikidata-URI | `fsl:hasReference` | P31 | Gefüllt durch `enrich_qids.py`; einige institutionelle Quellen weiterhin offen |
| — | *(fest)* | `https://fuzzy-sl.wikibase.cloud/entity/Q126` | 🟦 | `sf:Point` ← `fsl:hasPointType` → `fsl:PointType` | `fsl:hasPointType` | P33 | Immer `<Q126>` Representative Point |

---

## Properties

### bb5kbc Object Properties

| Property | Domäne | Range | subPropertyOf | CRM-Top-Edge |
|---|---|---|---|---|
| `bb5kbc:inGemeinde` | `bb5kbc:Fundstelle` | `bb5kbc:Gemeinde` | `crm:P89_falls_within`, `fsl:locatedInAdministrativeEntity` | `crm:P89_falls_within` |
| `bb5kbc:inKreis` | `bb5kbc:Gemeinde` | `bb5kbc:Kreis` | `crm:P89_falls_within`, `fsl:locatedInAdministrativeEntity` | `crm:P89_falls_within` |
| `bb5kbc:inBundesland` | `bb5kbc:Kreis` | `bb5kbc:Bundesland` | `crm:P89_falls_within`, `fsl:locatedInAdministrativeEntity` | `crm:P89_falls_within` |
| `bb5kbc:inLand` | `bb5kbc:Bundesland` | `bb5kbc:Land` | `crm:P89_falls_within`, `fsl:locatedInAdministrativeEntity` | `crm:P89_falls_within` |
| `bb5kbc:wurdeEntdecktDurch` | `bb5kbc:Fundstelle` | `bb5kbc:Entdeckung` | `crm:P12i_was_present_at` | `crm:P12i_was_present_at` |
| `bb5kbc:wurdeGeoreferenziertDurch` | `bb5kbc:Fundstelle` | `bb5kbc:GeoreferenzierungsAktivitaet` | `prov:wasGeneratedBy` | `prov:wasGeneratedBy` |
| `bb5kbc:hatEntdeckungsart` | `bb5kbc:Entdeckung` | `bb5kbc:EntdeckungsartType` | `crm:P2_has_type` | `crm:P2_has_type` |
| `bb5kbc:hatFundstellenart` | `bb5kbc:Fundstelle` | `bb5kbc:FundstellenartType` | `crm:P2_has_type`, `fsl:siteType` | `crm:P2_has_type` |
| `bb5kbc:hatKulturelleZuordnung` | `bb5kbc:Fundstelle` | `bb5kbc:KulturelleZuordnung` | `crm:P10i_contains` | `crm:P10i_contains` |
| `bb5kbc:hatKulturgruppe` | `bb5kbc:KulturelleZuordnung` | `bb5kbc:Kulturgruppe` | `crm:P9i_forms_part_of` | `crm:P9i_forms_part_of` |
| `bb5kbc:hatPublikation` | `bb5kbc:Fundstelle` | `bb5kbc:Publikation` | `crm:P70i_is_documented_in` | `crm:P70i_is_documented_in` |
| `bb5kbc:hatDatierung` | `bb5kbc:KulturelleZuordnung` | `bb5kbc:Datierung` | `crm:P4_has_time-span` | `crm:P4_has_time-span` |
| `bb5kbc:datierungMethode` | `bb5kbc:Datierung` | `bb5kbc:DatierungsMethodeType` | `crm:P2_has_type` | `crm:P2_has_type` |
| `bb5kbc:hatScherbe` | `bb5kbc:Fundstelle` | `bb5kbc:Scherbe` | `crm:P46i_forms_part_of` | `crm:P46i_forms_part_of` |
| `bb5kbc:hasExternalIdentifier` | `owl:Thing` | `rdfs:Resource` | `skos:closeMatch` | `skos:closeMatch` |
| `bb5kbc:hasExternalIdentifierType` | `rdfs:Resource` | `bb5kbc:externalIdentifierType` | — | — |

### bb5kbc Datatype Properties

| Property | Domäne | Range | subPropertyOf | CRM-Top-Edge |
|---|---|---|---|---|
| `bb5kbc:hatFID` | `bb5kbc:Fundstelle` | `xsd:integer` | `crm:P1_is_identified_by`, `dc:identifier` | `crm:P1_is_identified_by` |
| `bb5kbc:hatFundstellenID` | `bb5kbc:Fundstelle` | `xsd:string` | `crm:P1_is_identified_by` | `crm:P1_is_identified_by` |
| `bb5kbc:hatKatalognummer` | `bb5kbc:Fundstelle` | `xsd:string` | `crm:P1_is_identified_by` | `crm:P1_is_identified_by` |
| `bb5kbc:hatGenauigkeit` | `bb5kbc:Fundstelle` | `xsd:decimal` | `fsl:precision` | `fsl:precision` |
| `bb5kbc:datierungStart` | `bb5kbc:Datierung` | `xsd:integer` | `crm:P82a_begin_of_the_begin` | `crm:P82a_begin_of_the_begin` |
| `bb5kbc:datierungEnd` | `bb5kbc:Datierung` | `xsd:integer` | `crm:P82b_end_of_the_end` | `crm:P82b_end_of_the_end` |
| `bb5kbc:datierungSicherheitStart` | `bb5kbc:Datierung` | `xsd:string` | `fsl:certaintyDesc` | `fsl:certaintyDesc` |
| `bb5kbc:datierungSicherheitEnd` | `bb5kbc:Datierung` | `xsd:string` | `fsl:certaintyDesc` | `fsl:certaintyDesc` |
| `bb5kbc:datierungSicherheitRange` | `bb5kbc:Datierung` | `xsd:string` | `fsl:certaintyDesc` | `fsl:certaintyDesc` |
| `bb5kbc:wikidataMatchDescription` | `bb5kbc:Land`, `bb5kbc:Bundesland`, `bb5kbc:Kreis`, `bb5kbc:Gemeinde` | `xsd:string` | — | — (Audit-Property) |

### Nachgenutzte Properties (kein bb5kbc-Wrapper)

| Property | Ontologie | Domäne | Range |
|---|---|---|---|
| `fsl:hasReference` | FSL | `bb5kbc:GeoreferenzierungsAktivitaet` | `bb5kbc:GeoReferenz` |
| `fsl:method` | FSL | `bb5kbc:GeoreferenzierungsAktivitaet` | `fsl:MethodType` |
| `fsl:hasSourceType` | FSL | `bb5kbc:GeoreferenzierungsAktivitaet` | `fsl:SourceType` |
| `fsl:activityDesc` | FSL | `bb5kbc:GeoreferenzierungsAktivitaet` | `xsd:string` |
| `fsl:precision` | FSL | `bb5kbc:Fundstelle` | `xsd:decimal` |
| `fsl:representativeGeometry` | FSL | `bb5kbc:Fundstelle` | `sf:Point` |
| `prov:wasAssociatedWith` | PROV-O | `bb5kbc:GeoreferenzierungsAktivitaet` | `foaf:Person` |
| `rdfs:label` / `skos:prefLabel` | RDFS / SKOS | alle Klassen | Literal `@de` |
| `geosparql:hasGeometry` | GeoSPARQL | `bb5kbc:Fundstelle` | `sf:Point` |
| `geosparql:asWKT` | GeoSPARQL | `sf:Point` | `geosparql:wktLiteral` |

---

## Vererbungsketten (Kurzreferenz)

> **Warum `crm:E53_Place` direkt für Verwaltungsgebiete:**
> `pleiades:Place` ist semantisch für antike Toponyme ohne sichere Geometrie gedacht
> (Pleiades-Datenmodell, Samian-Ware-Use-Case in LADO/ArNO). Moderne Verwaltungsgebiete
> haben klar definierte Grenzen — sie sind direkt `crm:E53_Place`.
> `bb5kbc:Fundstelle` geht zusätzlich über `crm:E27_Site` (= "Constellation of matter
> on the surface", CRM E27), parallel zu den FSL- und LADO-Spuren.

Die Tabelle listet pro `bb5kbc:`-Klasse die **vollständige Vorfahren-Menge** als
flache Liste (alle direkten Eltern + transitive Hülle). Darunter zeigt jeder
Code-Block die Mehrfach-Vererbung als Baum, was die parallelen Spuren sichtbar
macht. Die Liste in der Tabelle ist die Quelle für den automatischen Doku-Abgleich
(`validate_lod.py`, Sektion 4b) — sie muss exakt der Ontologie entsprechen.

### Übersicht (vollständige Vorfahren-Mengen)

| bb5kbc-Klasse | Alle Vorfahren (transitiv) |
|---|---|
| `bb5kbc:Land` | `crm:E1_CRM_Entity`, `crm:E53_Place` |
| `bb5kbc:Bundesland` | `crm:E1_CRM_Entity`, `crm:E53_Place` |
| `bb5kbc:Kreis` | `crm:E1_CRM_Entity`, `crm:E53_Place` |
| `bb5kbc:Gemeinde` | `crm:E1_CRM_Entity`, `crm:E53_Place` |
| `bb5kbc:Fundstelle` | `crm:E18_Physical_Thing`, `crm:E1_CRM_Entity`, `crm:E26_Physical_Feature`, `crm:E27_Site`, `crm:E53_Place`, `crm:E70_Thing`, `crm:E72_Legal_Object`, `fsl:Location`, `fsl:Site`, `geo:SpatialObject`, `lado:Location`, `pleiades:Location`, `prov:Location` |
| `bb5kbc:GeoreferenzierungsAktivitaet` | `crm:E13_Attribute_Assignment`, `crm:E1_CRM_Entity`, `crm:E2_Temporal_Entity`, `crm:E4_Period`, `crm:E5_Event`, `crm:E7_Activity`, `prov:Activity` |
| `bb5kbc:Entdeckung` | `crm:E13_Attribute_Assignment`, `crm:E1_CRM_Entity`, `crm:E2_Temporal_Entity`, `crm:E4_Period`, `crm:E5_Event`, `crm:E7_Activity`, `crmsci:S19_Encounter_Event`, `crmsci:S4_Observation` |
| `bb5kbc:EntdeckungsartType` | `crm:E1_CRM_Entity`, `crm:E55_Type` |
| `bb5kbc:FundstellenartType` | `crm:E1_CRM_Entity`, `crm:E55_Type`, `fsl:SiteType`, `fsl:Type`, `lado:PlaceType` |
| `bb5kbc:KulturelleZuordnung` | `crm:E1_CRM_Entity`, `crm:E92_Spacetime_Volume`, `lado:SpaceTimeItem` |
| `bb5kbc:Kulturgruppe` | `crm:E1_CRM_Entity`, `crm:E2_Temporal_Entity`, `crm:E4_Period` |
| `bb5kbc:Datierung` | `crm:E1_CRM_Entity`, `crm:E52_Time-Span`, `time:Interval`, `time:TemporalEntity` |
| `bb5kbc:DatierungsMethodeType` | `crm:E1_CRM_Entity`, `crm:E55_Type` |
| `bb5kbc:Scherbe` | `crm:E18_Physical_Thing`, `crm:E1_CRM_Entity`, `crm:E22_Human-Made_Object`, `crm:E70_Thing`, `crm:E72_Legal_Object` |
| `bb5kbc:Publikation` | `crm:E1_CRM_Entity`, `crm:E32_Authority_Document`, `crm:E70_Thing`, `crm:E73_Information_Object` |
| `bb5kbc:externalIdentifierType` | `crm:E1_CRM_Entity`, `crm:E55_Type` |

### Mehrfach-Vererbung als Baum

Verwaltungsgebiete (Land/Bundesland/Kreis/Gemeinde) haben alle dieselbe einfache
Spur über `crm:E53_Place`:

```
bb5kbc:Land           ┐
bb5kbc:Bundesland     ├── alle: └── crm:E53_Place
bb5kbc:Kreis          │             └── crm:E1_CRM_Entity
bb5kbc:Gemeinde       ┘
```

`bb5kbc:Fundstelle` ist die komplexeste Klasse — drei parallele Eltern, einer mit
weiterer Mehrfach-Vererbung:

```
bb5kbc:Fundstelle
├── lado:Location
│   └── pleiades:Location
│       └── geo:SpatialObject
├── fsl:Site
│   └── fsl:Location
│       └── prov:Location
└── crm:E27_Site
    ├── crm:E26_Physical_Feature
    │   └── crm:E18_Physical_Thing
    │       └── crm:E72_Legal_Object
    │           └── crm:E70_Thing
    │               └── crm:E1_CRM_Entity
    └── crm:E53_Place
        └── crm:E1_CRM_Entity
```

`bb5kbc:GeoreferenzierungsAktivitaet` ist parallel CRM-Activity und PROV-Activity:

```
bb5kbc:GeoreferenzierungsAktivitaet
├── crm:E13_Attribute_Assignment
│   └── crm:E7_Activity
│       └── crm:E5_Event
│           └── crm:E4_Period
│               └── crm:E2_Temporal_Entity
│                   └── crm:E1_CRM_Entity
└── prov:Activity
```

`bb5kbc:Entdeckung` als CRMsci-Observation, mit voller CRM-Hierarchie:

```
bb5kbc:Entdeckung
└── crmsci:S19_Encounter_Event
    └── crmsci:S4_Observation
        └── crm:E13_Attribute_Assignment
            └── crm:E7_Activity
                └── crm:E5_Event
                    └── crm:E4_Period
                        └── crm:E2_Temporal_Entity
                            └── crm:E1_CRM_Entity
```

`bb5kbc:FundstellenartType` ist parallel LADO-Place-Type und FSL-SiteType:

```
bb5kbc:FundstellenartType
├── lado:PlaceType
│   └── crm:E55_Type
│       └── crm:E1_CRM_Entity
└── fsl:SiteType
    └── fsl:Type
```

`bb5kbc:KulturelleZuordnung` als Spacetime-Volume:

```
bb5kbc:KulturelleZuordnung
└── lado:SpaceTimeItem
    └── crm:E92_Spacetime_Volume
        └── crm:E1_CRM_Entity
```

`bb5kbc:Kulturgruppe` als Period:

```
bb5kbc:Kulturgruppe
└── crm:E4_Period
    └── crm:E2_Temporal_Entity
        └── crm:E1_CRM_Entity
```

`bb5kbc:Datierung` ist parallel CRM-Time-Span und OWL-Time-Interval:

```
bb5kbc:Datierung
├── crm:E52_Time-Span
│   └── crm:E1_CRM_Entity
└── time:Interval
    └── time:TemporalEntity
```

Die übrigen Type-Klassen sind alle einfach `crm:E55_Type`-Subklassen:

```
bb5kbc:EntdeckungsartType         ┐
bb5kbc:DatierungsMethodeType      ├── alle: └── crm:E55_Type
bb5kbc:externalIdentifierType     ┘             └── crm:E1_CRM_Entity
```

`bb5kbc:Scherbe` als Human-Made-Object:

```
bb5kbc:Scherbe
└── crm:E22_Human-Made_Object
    └── crm:E18_Physical_Thing
        └── crm:E72_Legal_Object
            └── crm:E70_Thing
                └── crm:E1_CRM_Entity
```

`bb5kbc:Publikation` als Authority-Document:

```
bb5kbc:Publikation
└── crm:E32_Authority_Document
    └── crm:E73_Information_Object
        └── crm:E70_Thing
            └── crm:E1_CRM_Entity
```

### Geometrie-Klassen (extern, nicht im `bb5kbc:`-Namespace)

`sf:Point` aus dem Simple-Features-Vokabular wird vom LOD-Skript für die
WGS84-Punkt-Geometrie verwendet. Die volle Vererbungskette ist hier zur Information
dokumentiert, fließt aber **nicht** in den automatischen Doku-Abgleich ein
(weil keine `bb5kbc:`-Klasse):

```
sf:Point
└── geosparql:Geometry
    └── crmgeo:SP5_Geometric_Place_Expression
        └── crm:E73_Information_Object
            └── crm:E90_Symbolic_Object
                └── crm:E1_CRM_Entity
```

---

## Ortsklassen im Vergleich

```
crm:E1_CRM_Entity
  └── crm:E53_Place
        │
        ├── bb5kbc:Land          ← modernes Staatsgebiet (ISO 3166)
        ├── bb5kbc:Bundesland    ← modernes Verwaltungsgebiet (NUTS-1)
        ├── bb5kbc:Kreis         ← modernes Verwaltungsgebiet (NUTS-3)
        ├── bb5kbc:Gemeinde      ← modernes Verwaltungsgebiet (LAU-2)
        │
        └── crm:E27_Site         ← physisches Stück Land
              └── pleiades:Location
                    ├── lado:Location
                    └── fsl:Site
                          └── bb5kbc:Fundstelle  ← archäolog. Fundstelle mit Koordinaten
```

---

## P5 Certainty Level — Ableitungslogik

| Bedingung | Wikibase-Item | Label | Begründung |
|---|---|---|---|
| `genauigkeit_m = 0` | `fslwb:Q23` | **high** | Exakte Koordinate direkt aus Datenbank übernommen |
| `genauigkeit_m = 50–500` | `fslwb:Q15` | **medium** | Grobe Lokalisierung, eindeutig einer Flur/Gemeinde zuzuordnen |
| `genauigkeit_m = 800–5000` | `fslwb:Q24` | **low** | Nur auf Gemeindeebene verortet |
| `wgs84_x = 0 AND wgs84_y = 0` | `fslwb:Q113` | **dubious** | Koordinatenfehler — kein `sf:Point` wird erzeugt |

---

## Datierung — Modellierungslogik

Die neun CSV-Spalten zur Datierung (`dating_start`, `dating_end`, `dating_method`,
`dating_certainty_start`, `dating_certainty_end`, `dating_certainty_range`,
`dating_perio.do`, `dating_perio.do_match`) werden gebündelt an einem
**`bb5kbc:Datierung`**-Knoten modelliert. Pro Fundstelle gibt es genau einen
Datierungs-Knoten, der über `bb5kbc:hatDatierung` an die `bb5kbc:KulturelleZuordnung`
hängt. URI-Schema: `site_{FID}_dating` — FID-basiert pro Fundstelle, damit
site-spezifische Start/End/Sicherheits-Werte unmissverständlich an dem
Knoten der jeweiligen Site landen.

### Doppel-Verankerung: CRM E52 + OWL Time Interval

`bb5kbc:Datierung` ist Subklasse **beider** Oberklassen:

```turtle
bb5kbc:Datierung
    rdfs:subClassOf time:Interval ,           # OWL Time
                    crm:E52_Time-Span .       # CIDOC CRM
```

Das ist absichtlich redundant. Der Grund:

- **`crm:E52_Time-Span`** verbindet die Datierung mit dem CIDOC-Universum
  (über `bb5kbc:hatDatierung ⊂ crm:P4_has_time-span`). Damit ist sichergestellt,
  dass jeder CRM-konforme Reasoner und jede Edition Topic Maps die Datierung
  als Zeit-Span einer Periode/Activity erkennt.
- **`time:Interval ⊂ time:TemporalEntity`** ist die OWL-Time-Sicht auf denselben
  Knoten. OWL Time bringt ein reicheres Vokabular für Intervall-Topologie mit
  (Allen-Relationen wie `time:before`, `time:after`, `time:intervalMeets`),
  das CRM nicht hat. Wenn später z.B. relative Datierungen modelliert werden
  sollen ("Phase B beginnt nachdem Phase A endet"), ist OWL Time dafür das
  passendere Werkzeug.

**Kein Konflikt:** Beide Oberklassen verlangen nichts, was die andere ausschließt.
Der Knoten ist ein Zeit-Span *und* ein Intervall — zwei orthogonale Sichten
auf dieselbe temporale Entität.

### Start- und Endpunkte als Integer

```turtle
data:site_<FID>_dating
    bb5kbc:datierungStart "-4550"^^xsd:integer ;   # ⊂ crm:P82a_begin_of_the_begin
    bb5kbc:datierungEnd   "-3900"^^xsd:integer .   # ⊂ crm:P82b_end_of_the_end
```

Die CSV liefert ganzzahlige Jahresangaben (negativ = BCE). Das mappt direkt
auf `xsd:integer`, nicht auf `xsd:gYear`. Begründung:

- `xsd:gYear` kennt zwar negative Jahre, in der Praxis ist die Tooling-Unterstützung
  in Triple-Stores aber inkonsistent (z.B. ist `-4550` als gYear nicht überall
  als reine Jahreszahl interpretierbar).
- Die CRM-Properties `P82a/P82b` haben keinen festen `rdfs:range` — Integer ist
  also kompatibel.
- Wer OWL-Time-konforme `time:hasBeginning` / `time:inXSDgYear`-Triples ableiten
  möchte, kann das im Pipeline-Script in einem zweiten Schritt erzeugen.

### Drei Unsicherheits-Felder — drei verschiedene Bedeutungen

Die CSV trennt drei Arten von Unsicherheit, die wir 1:1 als drei Datatype
Properties auf den Datierungs-Knoten legen:

| CSV-Spalte | bb5kbc-Property | Bedeutung |
|---|---|---|
| `dating_certainty_start` | `bb5kbc:datierungSicherheitStart` | numerische Toleranz auf den Anfangspunkt (z.B. `"+ / - 100 years"`) |
| `dating_certainty_end` | `bb5kbc:datierungSicherheitEnd` | numerische Toleranz auf den Endpunkt |
| `dating_certainty_range` | `bb5kbc:datierungSicherheitRange` | qualitative Bewertung der gesamten Datierung (z.B. `"medium certainty, some 14C dates available"`) |

Alle drei sind als **`xsd:string`** modelliert, bewusst nicht als strukturierte
Werte. Begründung:

- Die Werte sind heterogene Freitexte, teils deutsch (`"+ / - 50 Jahre"`), teils
  englisch (`"+ / - 100 years"`), mit Tippvarianten (`"+ / -100 years"`,
  `"+ /- 100 Jahre"`). Eine strukturierte Modellierung (z.B. als
  `time:Duration` mit `time:numericDuration`) würde Normalisierung erfordern,
  die nicht ohne Datenverlust geht.
- Die `_range`-Spalte ist explizit qualitativ — eine Mischung aus Vertrauensgrad
  und methodischer Begründung. Diese gehört strukturell *nicht* in dieselbe
  Schublade wie eine numerische Toleranz.

Für eine spätere FSL-Wikibase-Integration (Property `P5` certaintyLevel) wäre
ein separater Knoten denkbar, der `dating_certainty_range` interpretiert und
auf eine `fsl:CertaintyType` (Q23/Q15/Q24) mappt. Das ist im aktuellen Mapping
**nicht** vorgesehen — die Strings bleiben als nachvollziehbarer Audit-Trail.

### Datierungsmethode als eigene Klasse

`dating_method` enthält Wikidata-QIDs (`Q173412` Radiokarbondatierung,
`Q816829` stilistische Datierung). Diese werden zu **`bb5kbc:DatierungsMethodeType`**-
Knoten dedupliziert (URI: `datmethode_{MD5(QID)[:8]}`):

```turtle
data:site_<FID>_dating
    bb5kbc:datierungMethode data:datmethode_98fc5e34 .   # ⊂ crm:P2_has_type

data:datmethode_98fc5e34
    a bb5kbc:DatierungsMethodeType ;
    rdfs:label "Radiokarbondatierung"@de ;
    bb5kbc:hasExternalIdentifier wd:Q173412 .
```

`bb5kbc:DatierungsMethodeType` ist Subklasse von `crm:E55_Type`, parallel zu
`bb5kbc:EntdeckungsartType` und `bb5kbc:FundstellenartType`. Der Hash basiert
auf der QID, nicht auf dem Label, weil die QID die stabilere Identität ist.

### Perio.do-Verknüpfung als SKOS-Match

Die Spalten `dating_perio.do` (URI) und `dating_perio.do_match`
(`exactMatch` / `closeMatch` / `relatedMatch`) zusammen bestimmen, **welche**
SKOS-Property zwischen Datierung und Perio.do-URI gesetzt wird:

```turtle
# dating_perio.do_match = "closeMatch"
data:site_<FID>_dating
    skos:closeMatch <http://n2t.net/ark:/99152/p0wctqtnkjq> .
```

Wenn `dating_perio.do_match` leer ist (1 Zeile in der CSV), wird per Default
`skos:relatedMatch` verwendet — die schwächste der drei Match-Levels.

## Beispiel-TTL (FID=33 — Friesack 4, mit echten CSV-Werten)

Das folgende Beispiel zeigt, wie eine vollständig ausgefüllte CSV-Zeile in RDF aussieht.
Alle Werte stammen direkt aus der aktuellen CSV; FID=33 hat keinen Sherd, daher ist
der Sherd-Block beispielhaft für eine andere Fundstelle (FID=80, Seelow 20) gezeigt.

```turtle
@prefix bb5kbc:  <http://w3id.org/bb5kbc/ont/> .
@prefix data:    <http://w3id.org/bb5kbc/> .
@prefix crm:     <http://www.cidoc-crm.org/cidoc-crm/> .
@prefix crmsci:  <http://www.cidoc-crm.org/extensions/crmsci/> .
@prefix fsl:     <http://fuzzy-sl.squirrel.link/ontology/> .
@prefix fslwb:   <https://fuzzy-sl.wikibase.cloud/entity/> .
@prefix time:    <http://www.w3.org/2006/time#> .
@prefix geo:     <http://www.opengis.net/ont/geosparql#> .
@prefix sf:      <http://www.opengis.net/ont/sf#> .
@prefix prov:    <http://www.w3.org/ns/prov#> .
@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix dc:      <http://purl.org/dc/elements/1.1/> .
@prefix wd:      <https://www.wikidata.org/entity/> .
@prefix gn:      <https://www.geonames.org/> .
@prefix orcid:   <https://orcid.org/> .

# =============================================================================
# FUNDSTELLE
# =============================================================================

data:site_33
    a bb5kbc:Fundstelle ;
    dc:identifier "33"^^xsd:integer ;          # FID — auch URI-Basis
    bb5kbc:hatFID "33"^^xsd:integer ;
    bb5kbc:hatFundstellenID "129" ;
    bb5kbc:hatKatalognummer "12485" ;
    rdfs:label "Friesack 4"@de ;
    skos:prefLabel "Friesack 4"@de ;
    # Verwaltungsgebiete
    bb5kbc:inGemeinde   data:gemeinde_ef3c98d9 ;
    # Fundstellenart
    bb5kbc:hatFundstellenart data:fundstellenart_1972902b ; # ⊂ crm:P2_has_type, ⊂ fsl:siteType
    # Entdeckung
    bb5kbc:wurdeEntdecktDurch data:entdeckung_1f56a08c ;
    # Publikation
    bb5kbc:hatPublikation     data:pub_c54b495e ;
    # Kulturelle Zuordnung
    bb5kbc:hatKulturelleZuordnung data:site_33_culture ;
    # Georeferenzierung
    bb5kbc:wurdeGeoreferenziertDurch data:site_33_activity ;   # ⊂ prov:wasGeneratedBy
    # Geometrie
    geo:hasGeometry     data:site_33_geom ;
    # FSL CM properties (auf Site, nicht auf Activity)
    bb5kbc:hatGenauigkeit "0"^^xsd:decimal ;    # P23 genauigkeit_m (= fsl:precision)
    fsl:certaintyLevel  fslwb:Q23 ;             # P5 high (genauigkeit_m = 0)
    fsl:hasLocationType fslwb:Q80 .             # P24 Findspot (fest)

# =============================================================================
# GEOMETRIE  (sf:Point)
# =============================================================================

data:site_33_geom
    a sf:Point ;
    geo:asWKT "POINT(12.54 52.75)"^^geo:wktLiteral ;
    fsl:hasPointType fslwb:Q126 .               # P33 Representative Point (fest)

# =============================================================================
# GEOREFERENZIERUNGS-AKTIVITÄT
# =============================================================================

data:site_33_activity
    a bb5kbc:GeoreferenzierungsAktivitaet ;
    fsl:hasReference    "Denkmaldaten / BLDAM 2021" ;   # P25 quelle_georef
    fsl:hasReference    wd:Q897952 ;                    # P31 QID_quelle_georef
    fsl:methodUsed      data:methode_b57e2231 ;         # P7  methode
    fsl:hasSourceType   data:quellentyp_5ae20fe0 ;      # P6  quellen_typ
    fsl:hasSourceTypeDetail data:quellentyp_5ae20fe0 ;  # P16 quellen_typ (detail)
    fsl:activityDesc    "die Koordinaten wurden beim BLDAM angefragt und übernommen" ; # P13+P15
    fsl:georeferencingBy orcid:0000-0003-4696-2101 ;    # P14 acting person (fest)
    prov:wasAssociatedWith orcid:0000-0003-4696-2101 .

# =============================================================================
# VERWALTUNGSGEBIETE  (mit Authority-IDs aus dem CSV-Enrichment-Lauf)
# =============================================================================

data:gemeinde_ef3c98d9
    a bb5kbc:Gemeinde ;
    rdfs:label "Friesack"@de ;
    bb5kbc:hasExternalIdentifier wd:Q585632 ,                              # GEMEINDE_QID
                                  gn:6550607 ,                              # GEMEINDE_GeoNames
                                  <https://www.openstreetmap.org/relation/1342247> ;  # GEMEINDE_OSM_Relation
    bb5kbc:inKreis data:kreis_d4d0a03b .
    # GEMEINDE_TGN / GEMEINDE_IDAI für Friesack nicht in der CSV gefüllt

data:kreis_d4d0a03b
    a bb5kbc:Kreis ;
    rdfs:label "Havelland"@de ;
    bb5kbc:hasExternalIdentifier wd:Q6139 ;                                # KREIS_QID
    bb5kbc:inBundesland data:bundesland_2ddb2d82 .
    # KREIS_GeoNames / TGN / IDAI / OSM_Relation für Havelland nicht in der CSV gefüllt

data:bundesland_2ddb2d82
    a bb5kbc:Bundesland ;
    rdfs:label "Brandenburg"@de ;
    bb5kbc:hasExternalIdentifier wd:Q1208 ,                                # BUNDESLAND_QID
                                  gn:2945356 ,                              # BUNDESLAND_GeoNames
                                  <http://vocab.getty.edu/tgn/7000096> ,    # BUNDESLAND_TGN
                                  <http://gazetteer.dainst.org/place/2048409> ,  # BUNDESLAND_IDAI
                                  <https://www.openstreetmap.org/relation/62504> ;  # BUNDESLAND_OSM_Relation
    bb5kbc:inLand data:land_3c2f8b8c .

data:land_3c2f8b8c
    a bb5kbc:Land ;
    rdfs:label "Deutschland"@de ;
    bb5kbc:hasExternalIdentifier wd:Q183 ,                                 # LAND_QID
                                  gn:2921044 ,                              # LAND_GeoNames
                                  <http://vocab.getty.edu/tgn/7000084> ,    # LAND_TGN
                                  <http://gazetteer.dainst.org/place/2044274> ,  # LAND_IDAI
                                  <https://www.openstreetmap.org/relation/51477> .  # LAND_OSM_Relation

# =============================================================================
# KULTURELLE ZUORDNUNG + KULTURGRUPPE
# =============================================================================

data:site_33_culture
    a bb5kbc:KulturelleZuordnung ;
    bb5kbc:hatKulturgruppe data:kultur_a36e9d6d ;        # geteilt mit allen FBG-Sites
    bb5kbc:hatDatierung    data:site_33_dating .         # FID-spezifisch

data:kultur_a36e9d6d
    a bb5kbc:Kulturgruppe ;
    rdfs:label "FBG"@de .
    # perio.do (Kulturgruppe-Ebene) → noch leer ⏳

# =============================================================================
# DATIERUNG  (echte Werte aus CSV: -4550 bis -3900, 14C-Datierung)
# =============================================================================

data:site_33_dating
    a bb5kbc:Datierung , time:Interval , crm:E52_Time-Span ;
    # Start / Ende als Integer (BCE = negativ)
    bb5kbc:datierungStart "-4550"^^xsd:integer ;
    bb5kbc:datierungEnd   "-3900"^^xsd:integer ;
    # Datierungsmethode → 14C (Q173412)
    bb5kbc:datierungMethode data:datmethode_98fc5e34 ;
    # Unsicherheits-Beschreibungen (Freitext)
    bb5kbc:datierungSicherheitStart "+ / - 100 years" ;
    bb5kbc:datierungSicherheitEnd   "+ / - 100 years" ;
    bb5kbc:datierungSicherheitRange "medium certainty, some 14C dates available" .
    # dating_perio.do für FID=33 leer; bei FID=1 z.B.:
    #   skos:relatedMatch <http://n2t.net/ark:/99152/p0wctqtnkjq>

data:datmethode_98fc5e34
    a bb5kbc:DatierungsMethodeType ;
    rdfs:label "Radiokarbondatierung"@de ;
    bb5kbc:hasExternalIdentifier wd:Q173412 .

# =============================================================================
# ENTDECKUNG + ENTDECKUNGSART
# =============================================================================

data:entdeckung_1f56a08c
    a bb5kbc:Entdeckung ;
    rdfs:label "Ausgrabung"@de ;
    bb5kbc:hatEntdeckungsart data:entdeckungsart_2b73226f .   # ⊂ crm:P2_has_type

data:entdeckungsart_2b73226f
    a bb5kbc:EntdeckungsartType ;
    rdfs:label "Ausgrabung"@de ;
    bb5kbc:hasExternalIdentifier wd:Q959782 .

# =============================================================================
# FUNDSTELLENART
# =============================================================================

data:fundstellenart_1972902b
    a bb5kbc:FundstellenartType ;
    rdfs:label "Siedlung"@de ;
    bb5kbc:hasExternalIdentifier wd:Q486972 .

# =============================================================================
# PUBLIKATION
# =============================================================================

data:pub_c54b495e
    a bb5kbc:Publikation ;
    rdfs:label "Wetzel/Beran 2023"@de ;
    bb5kbc:hasExternalIdentifier wd:Q139304633 .   # gefüllt durch enrich_qids.py

# =============================================================================
# GEOREFERENZIERUNGS-TYPEN (dedupliziert, geteilt mit anderen Fundstellen)
# =============================================================================

data:methode_b57e2231
    a fsl:MethodType ;
    rdfs:label "Übernahme aus externer Datenbank"@de .

data:quellentyp_5ae20fe0
    a fsl:SourceType ;
    rdfs:label "Strukturen des Landesdenkmalamts"@de .

# =============================================================================
# SCHERBE  (FID=33 hat keine; Beispiel aus FID=80 Seelow 20)
# =============================================================================

# data:site_80
#     bb5kbc:hatScherbe data:sherd_<hash> , data:sherd_<hash> .
#
# data:sherd_<hash>
#     a bb5kbc:Scherbe ;
#     bb5kbc:hasExternalIdentifier wd:Q139477253 .
```

---

## Beispiel-TTL — Unsicherheits-Modellierung (`?`-Werte)

Werte mit Fragezeichen — `kultur = "SBK?"`, `fundstellenart = "Grab?"` — werden
mit `fsl:certaintyDesc "uncertain"@en` modelliert. Die Ankerstelle unterscheidet
sich je nach Domäne:

- **Kulturgruppe**: `certaintyDesc` an der **`KulturelleZuordnung`** (Verknüpfungs-
  knoten zwischen Site und Kulturgruppe), nicht an der Kulturgruppe selbst.
  Begründung: Die Kulturgruppe (`SBK?` als Konzept) ist ein eigener Knoten und
  wird über alle Sites hinweg dedupliziert. Die Unsicherheit betrifft *diese
  Zuweisung*, nicht das Konzept.
- **Fundstellenart**: Eigener, **nicht-deduplizierter** Type-Knoten pro Site
  (URI-Salt mit FID), `certaintyDesc` direkt am Type-Knoten. Begründung: Hier
  gibt es keinen Verknüpfungs-Zwischenknoten, also wird die Unsicherheit nur
  per FID-Salt-Trennung von der "sicheren" Variante getrennt.

```turtle
# --- SBK? (Kultur unsicher) — FID=81 ---
data:site_81
    a bb5kbc:Fundstelle ;
    bb5kbc:hatKulturelleZuordnung data:site_81_culture .

data:site_81_culture
    a bb5kbc:KulturelleZuordnung ;
    fsl:certaintyDesc "uncertain"@en ;          # ← an der Verknüpfung
    bb5kbc:hatKulturgruppe data:kultur_7a001224 .

data:kultur_7a001224
    a bb5kbc:Kulturgruppe ;
    rdfs:label "SBK?"@de .                      # Label behält das `?`

# --- Grab? (Fundstellenart unsicher) — FID=54 ---
data:site_54
    a bb5kbc:Fundstelle ;
    bb5kbc:hatFundstellenart data:fundstellenart_e5b4c377 .   # FID-gesalzener Hash

data:fundstellenart_e5b4c377
    a bb5kbc:FundstellenartType ;
    rdfs:label "Grab?"@de ;
    fsl:certaintyDesc "uncertain"@en ;          # ← am Type-Knoten selbst
    bb5kbc:hasExternalIdentifier wd:Q173387 .   # Q173387 = grave (gleiche QID wie für sicheres "Grab")
```

Der "sichere" `Grab`-Knoten (`data:fundstellenart_b635ceb0`) bleibt deduplizierter
Sammelknoten für alle Sites mit `fundstellenart = "Grab"` — ohne `certaintyDesc`.
