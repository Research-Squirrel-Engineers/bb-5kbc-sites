# bb5kbc CSV → Ontologie Mapping

## FSL-Metadaten-Struktur

| FSL-Schicht | Bedeutung | Hängt an |
|---|---|---|
| **GLM** — Geolocation Metadata | Fundstelle als Entität: Name, Typ, Lage, Publikation, IDs, Kulturgruppe | `bb5kbc:Fundstelle` |
| **CM** — Coordinate Metadata | Georeferenzierungsakt: Methode, Quelle, Genauigkeit, Koordinaten | `bb5kbc:GeoreferenzierungsAktivitaet` + `sf:Point` |

## Legende

| Symbol | Bedeutung |
|---|---|
| 🟦 | **Instanz** — CSV-Wert → Named Node, URI = `{typ}_{md5hash8}` |
| 🟨 | **Literal** — CSV-Wert → Datenwert direkt an einem Node |
| 🔗 | **Ext. URI** — CSV-Wert → externe URI + `bb5kbc:hasExternalIdentifier` + `bb5kbc:hasExternalIdentifierType` |
| ⏳ | **Noch leer** — Spalte im Schema vorgesehen, Daten werden später ergänzt |

---

## URI-Schema

### FID-basiert (einmalig pro Fundstelle)

| Entität | URI-Muster | Beispiel (FID=1) |
|---|---|---|
| `bb5kbc:Fundstelle` | `http://w3id.org/bb5kbc/site_{FID}` | `http://w3id.org/bb5kbc/site_1` |
| `bb5kbc:GeoreferenzierungsAktivitaet` | `http://w3id.org/bb5kbc/site_{FID}_activity` | `http://w3id.org/bb5kbc/site_1_activity` |
| `sf:Point` | `http://w3id.org/bb5kbc/site_{FID}_geom` | `http://w3id.org/bb5kbc/site_1_geom` |
| `bb5kbc:Entdeckung` | `http://w3id.org/bb5kbc/site_{FID}_discovery` | `http://w3id.org/bb5kbc/site_1_discovery` |
| `bb5kbc:KulturelleZuordnung` | `http://w3id.org/bb5kbc/site_{FID}_culture` | `http://w3id.org/bb5kbc/site_1_culture` |

> `bb5kbc:Entdeckung` und `bb5kbc:KulturelleZuordnung` sind FID-basiert weil sie immer an genau einer Fundstelle hängen — auch wenn der Entdeckungstext oder die Kulturgruppe bei mehreren Fundstellen gleich ist, ist die *Zuordnung* jeweils eine eigene Instanz.

### Hash-basiert (dedupliziert, URI = MD5 des Originalwerts, 8 Zeichen)

| Entität | URI-Muster | Beispiel |
|---|---|---|
| `bb5kbc:Gemeinde` | `http://w3id.org/bb5kbc/gemeinde_{hash}` | `gemeinde_c672785b` ← `"Behringen"` |
| `bb5kbc:Kreis` | `http://w3id.org/bb5kbc/kreis_{hash}` | `kreis_09060b5f` ← `"Wartburgkreis"` |
| `bb5kbc:Bundesland` | `http://w3id.org/bb5kbc/bundesland_{hash}` | `bundesland_eec0c902` ← `"Thüringen"` |
| `bb5kbc:Land` | `http://w3id.org/bb5kbc/land_{hash}` | `land_3c2f8b8c` ← `"Deutschland"` |
| `bb5kbc:Kulturgruppe` | `http://w3id.org/bb5kbc/kultur_{hash}` | `kultur_cc414e20` ← `"SBK"`, `kultur_7a001224` ← `"SBK?"` |
| `bb5kbc:EntdeckungsartType` | `http://w3id.org/bb5kbc/entdeckungsart_{hash}` | `entdeckungsart_1f56a08c` ← `"Ausgrabung"` |
| `bb5kbc:FundstellenartType` | `http://w3id.org/bb5kbc/fundstellenart_{hash}` | `fundstellenart_1972902b` ← `"Siedlung"` |
| `bb5kbc:Publikation` | `http://w3id.org/bb5kbc/pub_{hash}` | `pub_c5110572` ← `"Kaufmann 1976"` |
| `bb5kbc:GeoReferenz` | `http://w3id.org/bb5kbc/georef_{hash}` | `georef_bede18a7` ← `"LfDA Sachsen-Anhalt"` |
| `fsl:MethodType` | `http://w3id.org/bb5kbc/methode_{hash}` | `methode_b57e2231` ← `"Übernahme aus externer Datenbank"` |
| `fsl:SourceType` | `http://w3id.org/bb5kbc/quellentyp_{hash}` | `quellentyp_e6dc730e` ← `"Printpublikation"` |

> **Hash-Funktion:** `MD5(originalwert_utf8)[:8]` — kollisionssicher auch bei Unicode-Varianten (z.B. `"Thüringen"` ≠ `"Thuringen"`).

---

## Mapping-Tabelle — GLM

| # | CSV-Spalte | Beispielwert | Art | bb5kbc-Klasse / Property | Hinweis |
|---|---|---|---|---|---|
| 22 | `FID` | `"1"` | 🟨 | `bb5kbc:Fundstelle` ← `bb5kbc:hatFID` : `xsd:integer` | PID, Basis aller FID-URIs |
| 4 | `fst_id` | `"444"` | 🟨 | `bb5kbc:Fundstelle` ← `bb5kbc:hatFundstellenID` : `xsd:string` | Interne ID, nicht immer eindeutig |
| 3 | `katalognr` | `"55"` | 🟨 | `bb5kbc:Fundstelle` ← `bb5kbc:hatKatalognummer` : `xsd:string` | Katalognr. aus Publikationen, 52 leer |
| 5 | `fst_name` | `"Tüngeda"` | 🟨 | `bb5kbc:Fundstelle` ← `rdfs:label` + `skos:prefLabel` : Literal `@de` | |
| 6 | `gemeinde` | `"Behringen"` | 🟦 | `bb5kbc:Fundstelle` ← `bb5kbc:inGemeinde` → `bb5kbc:Gemeinde` | hash-URI + `rdfs:label` + TGN + iDAI + OSM |
| 7 | `kreis` | `"Wartburgkreis"` | 🟦 | `bb5kbc:Gemeinde` ← `bb5kbc:inKreis` → `bb5kbc:Kreis` | hash-URI + `rdfs:label` + TGN + iDAI + OSM |
| 8 | `bundesland` | `"Thüringen"` | 🟦 | `bb5kbc:Kreis` ← `bb5kbc:inBundesland` → `bb5kbc:Bundesland` | hash-URI + `rdfs:label` + TGN + iDAI + OSM; inkl. Wojewodschaften |
| 9 | `land` | `"Deutschland"` | 🟦 | `bb5kbc:Bundesland` ← `bb5kbc:inLand` → `bb5kbc:Land` | hash-URI + `rdfs:label` + TGN + iDAI + OSM; nur 2 Werte |
| 10 | `LAND_TGN` | `"7000084"` | 🔗 | `bb5kbc:Land` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_TGN` | Wird auch für Bundesland/Kreis/Gemeinde als neue CSV-Spalten ergänzt |
| 11 | `LAND_IDAI` | `"2044274"` | 🔗 | `bb5kbc:Land` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_iDAI` | dto. |
| 12 | `LAND_OSM_Relation` | `"51477"` | 🔗 | `bb5kbc:Land` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_OSM` | dto. |
| 13 | `perio.do` | *(leer)* | 🔗 ⏳ | `bb5kbc:Kulturgruppe` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_PerioDo` | 0/540 gefüllt, Spalte bleibt im Schema |
| 14 | `kultur` | `"SBK"` | 🟦 | `bb5kbc:KulturelleZuordnung` ← `bb5kbc:hatKulturgruppe` → `bb5kbc:Kulturgruppe` | hash-URI + `rdfs:label`; `SBK?`/`SRK?` als eigene Nodes |
| 15 | `entdeckung` | `"Ausgrabung Bersu"` | 🟨 | `bb5kbc:Entdeckung` ← `rdfs:label` : Literal `@de` | Freitext, 15 heterogene Werte inkl. Eigennamen; 155 leer |
| 16 | `QID_entdeckung` | `"Q1144458"` | 🟦 🔗 | `bb5kbc:Entdeckung` ← `crm:P2_has_type` → `bb5kbc:EntdeckungsartType` | hash-URI + `rdfs:label` + `bb5kbc:hasExternalIdentifier` → Wikidata; nur 2 distinct QIDs |
| 17 | `publikation_arch` | `"Kaufmann 1976"` | 🟦 | `bb5kbc:Fundstelle` ← `bb5kbc:hatPublikation` → `bb5kbc:Publikation` | hash-URI + `rdfs:label`; 273 leer |
| 18 | `QID_publikation` | *(leer)* | 🔗 ⏳ | `bb5kbc:Publikation` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_Wikidata` | 0/540 gefüllt, Spalte bleibt im Schema |
| 19 | `fundstellenart` | `"Siedlung und Grab"` | 🟦 | `bb5kbc:Fundstelle` ← `fsl:siteType` → `bb5kbc:FundstellenartType` | hash-URI + `rdfs:label`; Kombi-Werte als ein Node |
| 20 | `QID_fundstellenart` | `"Q173387"` | 🔗 | `bb5kbc:FundstellenartType` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_Wikidata` | 4 distinct QIDs |

---

## Mapping-Tabelle — CM

| # | CSV-Spalte | Beispielwert | Art | bb5kbc-Klasse / Property | Hinweis |
|---|---|---|---|---|---|
| 1 | `quelle_georef` | `"LfDA Sachsen-Anhalt"` | 🟦 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:hasReference` → `bb5kbc:GeoReferenz` | hash-URI + `rdfs:label` |
| 2 | `QID_quelle_georef` | `"Q65631985"` | 🔗 | `bb5kbc:GeoReferenz` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_Wikidata` | |
| 21 | `genauigkeit_m` | `"100"` | 🟨 | `bb5kbc:Fundstelle` ← `bb5kbc:hatGenauigkeit` : `xsd:decimal` | subPropertyOf `fsl:precision` |
| 23 | `methode` | `"Übernahme aus externer Datenbank"` | 🟦 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:method` → `fsl:MethodType` | hash-URI + `rdfs:label` |
| 24 | `quellen_typ` | `"Printpublikation"` | 🟦 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:hasSourceType` → `fsl:SourceType` | hash-URI + `rdfs:label` |
| 25 | `methodenbeschr` | `"Koordinaten wurden vom LdfA..."` | 🟨 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:activityDesc` : `xsd:string` | |
| 26 | `wgs84_x` | `"13.4050"` | 🟨 | zusammen mit `wgs84_y` → `sf:Point` ← `geosparql:asWKT` : `"POINT(13.4050 52.5200)"^^geosparql:wktLiteral` via `fsl:representativeGeometry` | |
| 27 | `wgs84_y` | `"52.5200"` | 🟨 | zusammen mit `wgs84_x` → `sf:Point` ← `geosparql:asWKT` : `"POINT(13.4050 52.5200)"^^geosparql:wktLiteral` via `fsl:representativeGeometry` | |

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
| `bb5kbc:hatKulturelleZuordnung` | `bb5kbc:Fundstelle` | `bb5kbc:KulturelleZuordnung` | `crm:P10i_contains` | `crm:P10i_contains` |
| `bb5kbc:hatKulturgruppe` | `bb5kbc:KulturelleZuordnung` | `bb5kbc:Kulturgruppe` | `crm:P9i_forms_part_of` | `crm:P9i_forms_part_of` |
| `bb5kbc:hatPublikation` | `bb5kbc:Fundstelle` | `bb5kbc:Publikation` | `crm:P70i_is_documented_in` | `crm:P70i_is_documented_in` |
| `bb5kbc:hasExternalIdentifier` | `owl:Thing` | `rdfs:Resource` | `skos:closeMatch` | `skos:closeMatch` |
| `bb5kbc:hasExternalIdentifierType` | `rdfs:Resource` | `bb5kbc:externalIdentifierType` | — | — |

### bb5kbc Datatype Properties

| Property | Domäne | Range | subPropertyOf | CRM-Top-Edge |
|---|---|---|---|---|
| `bb5kbc:hatFID` | `bb5kbc:Fundstelle` | `xsd:integer` | `crm:P1_is_identified_by` | `crm:P1_is_identified_by` |
| `bb5kbc:hatFundstellenID` | `bb5kbc:Fundstelle` | `xsd:string` | `crm:P1_is_identified_by` | `crm:P1_is_identified_by` |
| `bb5kbc:hatKatalognummer` | `bb5kbc:Fundstelle` | `xsd:string` | `crm:P1_is_identified_by` | `crm:P1_is_identified_by` |
| `bb5kbc:hatGenauigkeit` | `bb5kbc:Fundstelle` | `xsd:decimal` | `fsl:precision` | `fsl:precision` |

### Nachgenutzte Properties (kein bb5kbc-Wrapper)

| Property | Ontologie | Domäne | Range |
|---|---|---|---|
| `fsl:hasReference` | FSL | `bb5kbc:GeoreferenzierungsAktivitaet` | `bb5kbc:GeoReferenz` |
| `fsl:method` | FSL | `bb5kbc:GeoreferenzierungsAktivitaet` | `fsl:MethodType` |
| `fsl:hasSourceType` | FSL | `bb5kbc:GeoreferenzierungsAktivitaet` | `fsl:SourceType` |
| `fsl:activityDesc` | FSL | `bb5kbc:GeoreferenzierungsAktivitaet` | `xsd:string` |
| `fsl:precision` | FSL | `bb5kbc:Fundstelle` | `xsd:decimal` |
| `fsl:siteType` | FSL | `bb5kbc:Fundstelle` | `bb5kbc:FundstellenartType` |
| `fsl:representativeGeometry` | FSL | `bb5kbc:Fundstelle` | `sf:Point` |
| `crm:P2_has_type` | CRM | `bb5kbc:Entdeckung` | `bb5kbc:EntdeckungsartType` |
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
