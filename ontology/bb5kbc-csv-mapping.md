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
| ⏳ | **Noch leer** — Spalte im Schema vorgesehen, Daten werden später ergänzt |

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
| `bb5kbc:KulturelleZuordnung` | `http://w3id.org/bb5kbc/culture_{hash}` | `culture_{hash}` ← hash aus kultur-Wert |
| `bb5kbc:Datierung` | `http://w3id.org/bb5kbc/culture_{hash}_dating` | `culture_cc414e20_dating` ← KulturelleZuordnung von `"SBK"` |
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

| # | CSV-Spalte | Beispielwert | Art | bb5kbc-Klasse / Property | Hinweis |
|---|---|---|---|---|---|
| 22 | `FID` | `"1"` | 🟨 | `bb5kbc:Fundstelle` ← `bb5kbc:hatFID` : `xsd:integer` (subPropertyOf `dc:identifier` + `crm:P1_is_identified_by`) | PID, Basis aller FID-URIs |
| 4 | `fst_id` | `"444"` | 🟨 | `bb5kbc:Fundstelle` ← `bb5kbc:hatFundstellenID` : `xsd:string` | Interne ID, nicht immer eindeutig |
| 3 | `katalognr` | `"55"` | 🟨 | `bb5kbc:Fundstelle` ← `bb5kbc:hatKatalognummer` : `xsd:string` | 52 leer |
| 5 | `fst_name` | `"Tüngeda"` | 🟨 | `bb5kbc:Fundstelle` ← `rdfs:label` + `skos:prefLabel` : Literal `@de` | |
| 6 | `gemeinde` | `"Behringen"` | 🟦🔗 | `bb5kbc:Fundstelle` ← `bb5kbc:inGemeinde` → `bb5kbc:Gemeinde` | + TGN + iDAI + OSM |
| 7 | `GEM_TGN` | *(leer)* | 🔗 ⏳ | `bb5kbc:Gemeinde` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_TGN` | neue Spalte |
| 8 | `GEM_IDAI` | *(leer)* | 🔗 ⏳ | `bb5kbc:Gemeinde` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_iDAI` | neue Spalte |
| 9 | `GEM_OSM_RELATION` | *(leer)* | 🔗 ⏳ | `bb5kbc:Gemeinde` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_OSM` | neue Spalte |
| 10 | `kreis` | `"Wartburgkreis"` | 🟦🔗 | `bb5kbc:Gemeinde` ← `bb5kbc:inKreis` → `bb5kbc:Kreis` | + TGN + iDAI + OSM |
| 11 | `KREIS_TGN` | *(leer)* | 🔗 ⏳ | `bb5kbc:Kreis` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_TGN` | neue Spalte |
| 12 | `KREIS_IDAI` | *(leer)* | 🔗 ⏳ | `bb5kbc:Kreis` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_iDAI` | neue Spalte |
| 13 | `KREIS_OSM_RELATION` | *(leer)* | 🔗 ⏳ | `bb5kbc:Kreis` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_OSM` | neue Spalte |
| 14 | `bundesland` | `"Thüringen"` | 🟦🔗 | `bb5kbc:Kreis` ← `bb5kbc:inBundesland` → `bb5kbc:Bundesland` | + TGN + iDAI + OSM; inkl. Wojewodschaften |
| 15 | `BL_TGN` | *(leer)* | 🔗 ⏳ | `bb5kbc:Bundesland` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_TGN` | neue Spalte |
| 16 | `BL_IDAI` | *(leer)* | 🔗 ⏳ | `bb5kbc:Bundesland` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_iDAI` | neue Spalte |
| 17 | `BL_OSM_RELATION` | *(leer)* | 🔗 ⏳ | `bb5kbc:Bundesland` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_OSM` | neue Spalte |
| 18 | `land` | `"Deutschland"` | 🟦🔗 | `bb5kbc:Bundesland` ← `bb5kbc:inLand` → `bb5kbc:Land` | + TGN + iDAI + OSM |
| 19 | `LAND_TGN` | `"7000084"` | 🔗 | `bb5kbc:Land` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_TGN` | |
| 20 | `LAND_IDAI` | `"2044274"` | 🔗 | `bb5kbc:Land` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_iDAI` | |
| 21 | `LAND_OSM_Relation` | `"51477"` | 🔗 | `bb5kbc:Land` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_OSM` | |
| 13 | `perio.do` | *(leer)* | 🔗 ⏳ | `bb5kbc:Kulturgruppe` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_PerioDo` | 0/540 gefüllt |
| 14 | `kultur` | `"SBK"` | 🟦🔗 | `bb5kbc:KulturelleZuordnung` ← `bb5kbc:hatKulturgruppe` → `bb5kbc:Kulturgruppe` | + Perio.do (⏳); `SBK?`/`SRK?` eigene Nodes |
| 15 | `entdeckung` | `"Ausgrabung Bersu"` | 🟦🔗 | `bb5kbc:Fundstelle` ← `bb5kbc:wurdeEntdecktDurch` → `bb5kbc:Entdeckung` | `rdfs:label` aus Text + `bb5kbc:hatEntdeckungsart` → `bb5kbc:EntdeckungsartType` |
| 16 | `QID_entdeckung` | `"Q959782"` | 🔗 | `bb5kbc:EntdeckungsartType` ← `bb5kbc:hasExternalIdentifier` → Wikidata | nur 2 QIDs |
| 17 | `publikation_arch` | `"Kaufmann 1976"` | 🟦🔗 | `bb5kbc:Fundstelle` ← `bb5kbc:hatPublikation` → `bb5kbc:Publikation` | + QID_publikation (⏳); 273 leer |
| 18 | `QID_publikation` | *(leer)* | 🔗 ⏳ | `bb5kbc:Publikation` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_Wikidata` | 0/540 gefüllt |
| 19 | `fundstellenart` | `"Siedlung und Grab"` | 🟦🔗 | `bb5kbc:Fundstelle` ← `bb5kbc:hatFundstellenart` → `bb5kbc:FundstellenartType` | subPropertyOf `crm:P2_has_type` + `fsl:siteType`; Kombi-Werte als ein Node |
| 20 | `QID_fundstellenart` | `"Q173387"` | 🔗 | `bb5kbc:FundstellenartType` ← `bb5kbc:hasExternalIdentifier` → Wikidata | 4 QIDs |

### Dating-Spalten

| # | CSV-Spalte | Beispielwert | Art | bb5kbc-Klasse / Property | Hinweis |
|---|---|---|---|---|---|
| — | *(URI)* | `culture_{hash}_dating` | 🟦 | `bb5kbc:KulturelleZuordnung` ← `bb5kbc:hatDatierung` → `bb5kbc:Datierung` | 1 Node pro Fundstelle; URI abgeleitet aus KulturelleZuordnung-Hash |
| 25 | `dating_start` | `"-4550"` | 🟨 | `bb5kbc:Datierung` ← `bb5kbc:datierungStart` : `xsd:integer` | subPropertyOf `crm:P82a_begin_of_the_begin`; negativ = BCE |
| 27 | `dating_end` | `"-3900"` | 🟨 | `bb5kbc:Datierung` ← `bb5kbc:datierungEnd` : `xsd:integer` | subPropertyOf `crm:P82b_end_of_the_end`; ⚠ FID=31 und FID=257 mit positivem Wert |
| 29 | `dating_method` | `"Q173412"` | 🟦🔗 | `bb5kbc:Datierung` ← `bb5kbc:datierungMethode` → `bb5kbc:DatierungsMethodeType` | hash-URI `datmethode_{MD5(QID)[:8]}`; nur 2 distinct (Q173412 14C, Q816829 stilistisch) |
| 26 | `dating_certainty_start` | `"+ / - 100 years"` | 🟨 | `bb5kbc:Datierung` ← `bb5kbc:datierungSicherheitStart` : `xsd:string` | Freitext, Mischsprache (de/en) |
| 28 | `dating_certainty_end` | `"+ / - 100 years"` | 🟨 | `bb5kbc:Datierung` ← `bb5kbc:datierungSicherheitEnd` : `xsd:string` | Freitext, Mischsprache (de/en) |
| 30 | `dating_certainty_range` | `"medium certainty, some 14C dates available"` | 🟨 | `bb5kbc:Datierung` ← `bb5kbc:datierungSicherheitRange` : `xsd:string` | qualitative Bewertung der Gesamtdatierung; 14 distinct |
| 31 | `dating_perio.do` | `"http://n2t.net/ark:/99152/p0wctqtnkjq"` | 🔗 | `bb5kbc:Datierung` ← `skos:{matchType}` → Perio.do-URI | nur 2 distinct URIs |
| 32 | `dating_perio.do_match` | `"closeMatch"` | — | bestimmt Property: `skos:exactMatch` / `skos:closeMatch` / `skos:relatedMatch` | kein eigenes Triple — steuert welche SKOS-Property genutzt wird; leer → Default `relatedMatch` |

### Scherben-Spalte

| # | CSV-Spalte | Beispielwert | Art | bb5kbc-Klasse / Property | Hinweis |
|---|---|---|---|---|---|
| 33 | `sherd` | `"Q139477253\|Q139477652"` | 🟦🔗 | `bb5kbc:Fundstelle` ← `bb5kbc:hatScherbe` → `bb5kbc:Scherbe` | 1-n Wikidata-QIDs, Delimiter `\|`; hash-URI `sherd_{MD5(QID)[:8]}`; Wikidata-URI via `bb5kbc:hasExternalIdentifier`; nur 4/540 gefüllt (FID 37, 41, 48, 80) |

---

## Mapping-Tabelle — CM

| # | CSV-Spalte | Beispielwert | Art | bb5kbc-Klasse / Property | FSL OWL | Wikibase | Hinweis |
|---|---|---|---|---|---|---|---|
| — | *(abgeleitet)* | `Q23 / Q15 / Q24 / Q113` | 🟦 | `bb5kbc:Fundstelle` ← `fsl:certaintyLevel` → `fsl:CertaintyType` | `fsl:certaintyLevel` | P5 | Aus `genauigkeit_m`: `<Q23>` high = 0m · `<Q15>` medium = 50–500m · `<Q24>` low = 800–5000m · `<Q113>` dubious = wgs84 0,0 (Koordinatenfehler) |
| 24 | `quellen_typ` | `"Printpublikation"` | 🟦 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:hasSourceType` → `fsl:SourceType` | `fsl:hasSourceType` | P6 | Named Node `quellentyp_{hash}`; 4 distinct |
| 23 | `methode` | `"Übernahme aus externer Datenbank"` | 🟦 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:methodUsed` → `fsl:MethodType` | `fsl:methodUsed` | P7 | Named Node `methode_{hash}`; 3 distinct |
| 26+27 | `wgs84_x` + `wgs84_y` | `"10.58"` + `"51.03"` | 🟨 | `sf:Point` ← `geosparql:asWKT` : `"POINT(10.58 51.03)"^^geosparql:wktLiteral` via `fsl:representativeGeometry` + `geosparql:hasGeometry` | `geosparql:hasGeometry` | P4 | Komma als Dezimaltrenner in CSV (`"10,58"`) → Punkt im WKT; bei `0,0` kein `sf:Point`, `fsl:certaintyLevel` → `<Q113>` dubious |
| 25 | `methodenbeschr` | `"Koordinaten wurden vom LdfA..."` | 🟨 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:certaintyDesc` : `xsd:string` | `fsl:certaintyDesc` | P13 | Freitext; 22 distinct |
| — | *(fest)* | `https://orcid.org/0000-0003-4696-2101` | 🟦 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:georeferencingBy` → `foaf:Person` | `fsl:georeferencingBy` | P14 | Sophie C. Schmidt; auch `prov:wasAssociatedWith` |
| 25 | `methodenbeschr` | `"Koordinaten wurden vom LdfA..."` | 🟨 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:activityDesc` : `xsd:string` | `fsl:activityDesc` | P15 | Freitext; 22 distinct |
| 24 | `quellen_typ` | `"Printpublikation"` | 🟦 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:hasSourceTypeDetail` → `fsl:SourceType` | `fsl:hasSourceTypeDetail` | P16 | Gleiche Spalte wie P6, detail-Ebene |
| 21 | `genauigkeit_m` | `"100"` | 🟨 | `bb5kbc:Fundstelle` ← `bb5kbc:hatGenauigkeit` : `xsd:decimal` | `fsl:precision` | P23 | subPropertyOf `fsl:precision` |
| — | *(fest)* | `https://fuzzy-sl.wikibase.cloud/entity/Q80` | 🟦 | `bb5kbc:Fundstelle` ← `fsl:hasLocationType` → `fsl:LocationType` | `fsl:hasLocationType` | P24 | Immer `<Q80>` Findspot |
| 1 | `quelle_georef` | `"LfDA Sachsen-Anhalt"` | 🟨 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:hasReference` : `xsd:string` | `fsl:hasReference` | P25 | Literal |
| 2 | `QID_quelle_georef` | `"Q65631985"` | 🔗 ⏳ | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:hasReference` → Wikidata-URI | `fsl:hasReference` | P31 | 206 leer |
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

### Nachgenutzte Properties (kein bb5kbc-Wrapper)

| Property | Ontologie | Domäne | Range |
|---|---|---|---|
| `fsl:hasReference` | FSL | `bb5kbc:GeoreferenzierungsAktivitaet` | `bb5kbc:GeoReferenz` |
| `fsl:method` | FSL | `bb5kbc:GeoreferenzierungsAktivitaet` | `fsl:MethodType` |
| `fsl:hasSourceType` | FSL | `bb5kbc:GeoreferenzierungsAktivitaet` | `fsl:SourceType` |
| `fsl:activityDesc` | FSL | `bb5kbc:GeoreferenzierungsAktivitaet` | `xsd:string` |
| `fsl:precision` | FSL | `bb5kbc:Fundstelle` | `xsd:decimal` |
| `fsl:representativeGeometry` | FSL | `bb5kbc:Fundstelle` | `sf:Point` |
| `prov:wasGeneratedBy` | PROV-O | `bb5kbc:Fundstelle` | `bb5kbc:GeoreferenzierungsAktivitaet` |
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
> `bb5kbc:Fundstelle` geht über `crm:E27_Site`, weil eine archäologische Fundstelle
> ein physisches Stück Land ist (*„Constellation of matter on the surface"*, CRM E27).

| bb5kbc-Klasse | Vollständige Kette |
|---|---|
| `bb5kbc:Land` | `crm:E1` → `crm:E53_Place` → **`bb5kbc:Land`** |
| `bb5kbc:Bundesland` | `crm:E1` → `crm:E53_Place` → **`bb5kbc:Bundesland`** |
| `bb5kbc:Kreis` | `crm:E1` → `crm:E53_Place` → **`bb5kbc:Kreis`** |
| `bb5kbc:Gemeinde` | `crm:E1` → `crm:E53_Place` → **`bb5kbc:Gemeinde`** |
| `bb5kbc:Fundstelle` | `crm:E1` → `crm:E53_Place` → `crm:E27_Site` → `pleiades:Location` → `lado:Location` / `fsl:Site` → **`bb5kbc:Fundstelle`** |
| `bb5kbc:GeoreferenzierungsAktivitaet` | `crm:E1` → `crm:E2_Temporal_Entity` → `crm:E4_Period` → `crm:E5_Event` → `crm:E7_Activity` → `prov:Activity` → **`bb5kbc:GeoreferenzierungsAktivitaet`** |
| `bb5kbc:Entdeckung` | `crm:E1` → `crm:E13_Attribute_Assignment` → `crmsci:S4_Observation` → `crmsci:S19_Encounter_Event` → **`bb5kbc:Entdeckung`** |
| `bb5kbc:EntdeckungsartType` | `crm:E1` → `crm:E55_Type` → **`bb5kbc:EntdeckungsartType`** |
| `bb5kbc:FundstellenartType` | `crm:E1` → `crm:E55_Type` → `lado:PlaceType` → `fsl:SiteType` → **`bb5kbc:FundstellenartType`** |
| `bb5kbc:KulturelleZuordnung` | `crm:E1` → `crm:E92_Spacetime_Volume` → `lado:SpaceTimeItem` → **`bb5kbc:KulturelleZuordnung`** |
| `bb5kbc:Datierung` | `crm:E1` → `crm:E2_Temporal_Entity` → `crm:E52_Time-Span` → **`bb5kbc:Datierung`** (+ `time:Interval`) |
| `bb5kbc:DatierungsMethodeType` | `crm:E1` → `crm:E55_Type` → **`bb5kbc:DatierungsMethodeType`** |
| `bb5kbc:Scherbe` | `crm:E1` → `crm:E18_Physical_Thing` → `crm:E22_Human-Made_Object` → **`bb5kbc:Scherbe`** |
| `bb5kbc:Kulturgruppe` | `crm:E1` → `crm:E2_Temporal_Entity` → `crm:E4_Period` → **`bb5kbc:Kulturgruppe`** |
| `bb5kbc:GeoReferenz` | `crm:E1` → `crm:E90_Symbolic_Object` → `crm:E73_Information_Object` → `crm:E32_Authority_Document` → **`bb5kbc:GeoReferenz`** |
| `bb5kbc:Publikation` | `crm:E1` → `crm:E90_Symbolic_Object` → `crm:E73_Information_Object` → `crm:E32_Authority_Document` → **`bb5kbc:Publikation`** |
| `bb5kbc:externalIdentifierType` | `crm:E1` → `crm:E55_Type` → **`bb5kbc:externalIdentifierType`** |
| `sf:Point` (Geometrie) | `crm:E1` → `crm:E90_Symbolic_Object` → `crm:E73_Information_Object` → `crmgeo:SP5_Geometric_Place_Expression` → `geosparql:Geometry` → **`sf:Point`** |

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
hängt. URI-Schema: `culture_{hash}_dating` — abgeleitet aus dem Hash der
KulturelleZuordnung.

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
data:culture_<hash>_dating
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
data:culture_<hash>_dating
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
data:culture_<hash>_dating
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
    bb5kbc:hatKulturelleZuordnung data:culture_a36e9d6d ;
    # Georeferenzierung
    prov:wasGeneratedBy data:site_33_activity ;
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
# VERWALTUNGSGEBIETE
# =============================================================================

data:gemeinde_ef3c98d9
    a bb5kbc:Gemeinde ;
    rdfs:label "Friesack"@de ;
    bb5kbc:inKreis data:kreis_d4d0a03b .
    # GEM_TGN / GEM_IDAI / GEM_OSM_RELATION → noch leer ⏳

data:kreis_d4d0a03b
    a bb5kbc:Kreis ;
    rdfs:label "Havelland"@de ;
    bb5kbc:inBundesland data:bundesland_2ddb2d82 .
    # KREIS_TGN / KREIS_IDAI / KREIS_OSM_RELATION → noch leer ⏳

data:bundesland_2ddb2d82
    a bb5kbc:Bundesland ;
    rdfs:label "Brandenburg"@de ;
    bb5kbc:inLand data:land_3c2f8b8c .
    # BL_TGN / BL_IDAI / BL_OSM_RELATION → noch leer ⏳

data:land_3c2f8b8c
    a bb5kbc:Land ;
    rdfs:label "Deutschland"@de ;
    bb5kbc:hasExternalIdentifier <http://vocab.getty.edu/tgn/7000084> ,
                                  <http://gazetteer.dainst.org/place/2044274> ,
                                  <https://www.openstreetmap.org/relation/51477> .

# =============================================================================
# KULTURELLE ZUORDNUNG + KULTURGRUPPE
# =============================================================================

data:culture_a36e9d6d
    a bb5kbc:KulturelleZuordnung ;
    bb5kbc:hatKulturgruppe data:kultur_a36e9d6d ;
    bb5kbc:hatDatierung    data:culture_a36e9d6d_dating .

data:kultur_a36e9d6d
    a bb5kbc:Kulturgruppe ;
    rdfs:label "FBG"@de .
    # perio.do (Kulturgruppe-Ebene) → noch leer ⏳

# =============================================================================
# DATIERUNG  (echte Werte aus CSV: -4550 bis -3900, 14C-Datierung)
# =============================================================================

data:culture_a36e9d6d_dating
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
    rdfs:label "Wetzel/Beran 2023"@de .
    # QID_publikation → noch leer ⏳

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
