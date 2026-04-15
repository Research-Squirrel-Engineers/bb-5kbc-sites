# bb5kbc CSV → Ontologie Mapping

## FSL-Metadaten-Struktur

| FSL-Schicht | Bedeutung | Hängt an |
|---|---|---|
| **GLM** — Geolocation Metadata | Fundstelle als Entität: Name, Typ, Lage, Publikation, IDs, Kulturgruppe | `bb5kbc:Fundstelle` |
| **CM** — Coordinate Metadata | Georeferenzierungsakt: Methode, Quelle, Genauigkeit, Koordinaten | `bb5kbc:GeoreferenzierungsAktivitaet` + `sf:Point` |

## Legende

| Symbol | Bedeutung |
|---|---|
| 🟦 | **Instanz** — CSV-Wert → URI eines Named Node (gleiche Werte = selbe URI) |
| 🟨 | **Literal** — CSV-Wert → Datenwert direkt an einem Node |
| 🔗 | **Ext. URI** — CSV-Wert → externe URI + `bb5kbc:hasExternalIdentifier` + `bb5kbc:hasExternalIdentifierType` |

---

## Mapping-Tabelle

| # | CSV-Spalte | Beispielwert | FSL | Art | bb5kbc-Klasse / Property |
|---|---|---|---|---|---|
| 1 | `quelle_georef` | `"LfDA Sachsen-Anhalt"` | CM | 🟦 | `bb5kbc:GeoReferenz` via `fsl:hasReference` |
| 2 | `QID_quelle_georef` | `"Q65631985"` | CM | 🔗 | `bb5kbc:GeoReferenz` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_Wikidata` |
| 3 | `katalognr` | `"55"` | GLM | 🟨 | `bb5kbc:Fundstelle` ← `bb5kbc:hatKatalognummer` : `xsd:string` |
| 4 | `fst_id` | `"444"` | GLM | 🟨 | `bb5kbc:Fundstelle` ← `bb5kbc:hatFundstellenID` : `xsd:string` |
| 5 | `fst_name` | `"Tüngeda"` | GLM | 🟨 | `bb5kbc:Fundstelle` ← `rdfs:label` / `skos:prefLabel` : Literal `@de` |
| 6 | `gemeinde` | `"Behringen"` | GLM | 🟦 | `bb5kbc:Fundstelle` ← `bb5kbc:inGemeinde` → `bb5kbc:Gemeinde` |
| 7 | `kreis` | `"Wartburgkreis"` | GLM | 🟦 | `bb5kbc:Gemeinde` ← `bb5kbc:inKreis` → `bb5kbc:Kreis` |
| 8 | `bundesland` | `"Thüringen"` | GLM | 🟦 | `bb5kbc:Kreis` ← `bb5kbc:inBundesland` → `bb5kbc:Bundesland` |
| 9 | `land` | `"Deutschland"` | GLM | 🟦 | `bb5kbc:Bundesland` ← `bb5kbc:inLand` → `bb5kbc:Land` |
| 10 | `LAND_TGN` | `"7000084"` | GLM | 🔗 | `bb5kbc:Land` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_TGN` |
| 11 | `LAND_IDAI` | `"2044274"` | GLM | 🔗 | `bb5kbc:Land` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_iDAI` |
| 12 | `LAND_OSM_Relation` | `"51477"` | GLM | 🔗 | `bb5kbc:Land` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_OSM` |
| 13 | `perio.do` | `"http://n2t.net/ark:/99152/p0fp7wv"` | GLM | 🔗 | `bb5kbc:Kulturgruppe` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_PerioDo` |
| 14 | `kultur` | `"SBK"` | GLM | 🟦 | `bb5kbc:KulturelleZuordnung` ← `bb5kbc:hatKulturgruppe` → `bb5kbc:Kulturgruppe` |
| 15 | `entdeckung` | `"Ausgrabung"` | GLM | 🟦 | `bb5kbc:Entdeckung` ← `crm:P2_has_type` → `bb5kbc:EntdeckungsartType` |
| 16 | `QID_entdeckung` | `"Q147204"` | GLM | 🔗 | `bb5kbc:EntdeckungsartType` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_Wikidata` |
| 17 | `publikation_arch` | `"Kaufmann 1976"` | GLM | 🟦 | `bb5kbc:Fundstelle` ← `bb5kbc:hatPublikation` → `bb5kbc:Publikation` |
| 18 | `QID_publikation` | `"Q130267885"` | GLM | 🔗 | `bb5kbc:Publikation` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_Wikidata` |
| 19 | `fundstellenart` | `"Siedlung"` | GLM | 🟦 | `bb5kbc:Fundstelle` ← `fsl:siteType` → `bb5kbc:FundstellenartType` |
| 20 | `QID_fundstellenart` | `"Q59496158"` | GLM | 🔗 | `bb5kbc:FundstellenartType` ← `bb5kbc:hasExternalIdentifier` → `bb5kbc:ExternalIdentifier_Wikidata` |
| 21 | `genauigkeit_m` | `"100"` | CM | 🟨 | `bb5kbc:Fundstelle` ← `bb5kbc:hatGenauigkeit` : `xsd:decimal` |
| 22 | `FID` | `"1"` | GLM | 🟨 | `bb5kbc:Fundstelle` ← `bb5kbc:hatFID` : `xsd:integer` — **PID der Fundstelle**, Basis für alle abgeleiteten URIs |

---

## URI-Schema

Alle persistenten Identifier basieren auf dem `FID`-Wert als Primärschlüssel der Fundstelle.

| Entität | URI-Muster | Beispiel (FID=1) |
|---|---|---|
| `bb5kbc:Fundstelle` | `http://w3id.org/bb5kbc/site_{FID}` | `http://w3id.org/bb5kbc/site_1` |
| `bb5kbc:GeoreferenzierungsAktivitaet` | `http://w3id.org/bb5kbc/site_{FID}_activity` | `http://w3id.org/bb5kbc/site_1_activity` |
| `sf:Point` (Geometrie) | `http://w3id.org/bb5kbc/site_{FID}_geom` | `http://w3id.org/bb5kbc/site_1_geom` |
| `bb5kbc:Entdeckung` | `http://w3id.org/bb5kbc/site_{FID}_discovery` | `http://w3id.org/bb5kbc/site_1_discovery` |
| `bb5kbc:KulturelleZuordnung` | `http://w3id.org/bb5kbc/site_{FID}_culture` | `http://w3id.org/bb5kbc/site_1_culture` |

Alle anderen Instanzen (Gemeinde, Kreis, Bundesland, Land, Kulturgruppe, Fundstellenart etc.) werden aus dem **Textwert** der jeweiligen CSV-Spalte als URI-Slug gebaut und **dedupliziert** — gleiche Werte über mehrere Zeilen ergeben dieselbe URI (analog zu `Poseidon2LOD.py`).

| Entität | URI-Muster | Beispiel |
|---|---|---|
| `bb5kbc:Gemeinde` | `http://w3id.org/bb5kbc/gemeinde_{slug}` | `http://w3id.org/bb5kbc/gemeinde_Behringen` |
| `bb5kbc:Kreis` | `http://w3id.org/bb5kbc/kreis_{slug}` | `http://w3id.org/bb5kbc/kreis_Wartburgkreis` |
| `bb5kbc:Bundesland` | `http://w3id.org/bb5kbc/bundesland_{slug}` | `http://w3id.org/bb5kbc/bundesland_Thüringen` |
| `bb5kbc:Land` | `http://w3id.org/bb5kbc/land_{slug}` | `http://w3id.org/bb5kbc/land_Deutschland` |
| `bb5kbc:Kulturgruppe` | `http://w3id.org/bb5kbc/kultur_{slug}` | `http://w3id.org/bb5kbc/kultur_SBK` |
| `bb5kbc:FundstellenartType` | `http://w3id.org/bb5kbc/fundstellenart_{slug}` | `http://w3id.org/bb5kbc/fundstellenart_Siedlung` |
| `bb5kbc:EntdeckungsartType` | `http://w3id.org/bb5kbc/entdeckungsart_{slug}` | `http://w3id.org/bb5kbc/entdeckungsart_Ausgrabung` |
| `bb5kbc:GeoReferenz` | `http://w3id.org/bb5kbc/georef_{slug}` | `http://w3id.org/bb5kbc/georef_LfDA_Sachsen-Anhalt` |
| `bb5kbc:Publikation` | `http://w3id.org/bb5kbc/pub_{slug}` | `http://w3id.org/bb5kbc/pub_Kaufmann_1976` |
| `fsl:MethodType` | `http://w3id.org/bb5kbc/methode_{slug}` | `http://w3id.org/bb5kbc/methode_Übernahme_aus_externer_Datenbank` |
| `fsl:SourceType` | `http://w3id.org/bb5kbc/quellentyp_{slug}` | `http://w3id.org/bb5kbc/quellentyp_Printpublikation` |
| 23 | `methode` | `"Übernahme aus externer Datenbank"` | CM | 🟦 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:method` → `fsl:MethodType` |
| 24 | `quellen_typ` | `"Printpublikation"` | CM | 🟦 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:hasSourceType` → `fsl:SourceType` |
| 25 | `methodenbeschr` | `"Koordinaten wurden vom LdfA..."` | CM | 🟨 | `bb5kbc:GeoreferenzierungsAktivitaet` ← `fsl:activityDesc` : `xsd:string` |
| 26 | `wgs84_x` | `"13.4050"` | CM | 🟨 | zusammen mit `wgs84_y` → `sf:Point` ← `geosparql:asWKT` : `"POINT(13.4050 52.5200)"^^geosparql:wktLiteral` via `fsl:representativeGeometry` |
| 27 | `wgs84_y` | `"52.5200"` | CM | 🟨 | zusammen mit `wgs84_x` → `sf:Point` ← `geosparql:asWKT` : `"POINT(13.4050 52.5200)"^^geosparql:wktLiteral` via `fsl:representativeGeometry` |

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
| `bb5kbc:hatFundstellenID` | `bb5kbc:Fundstelle` | `xsd:string` | `crm:P1_is_identified_by` | `crm:P1_is_identified_by` |
| `bb5kbc:hatKatalognummer` | `bb5kbc:Fundstelle` | `xsd:string` | `crm:P1_is_identified_by` | `crm:P1_is_identified_by` |
| `bb5kbc:hatFID` | `bb5kbc:Fundstelle` | `xsd:integer` | `crm:P1_is_identified_by` | `crm:P1_is_identified_by` |
| `bb5kbc:hatGenauigkeit` | `bb5kbc:Fundstelle` | `xsd:decimal` | `fsl:precision` | `fsl:precision` |
| `bb5kbc:hatBemerkung` | `bb5kbc:Fundstelle` | `xsd:string` | `crm:P3_has_note` | `crm:P3_has_note` |

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
