# bb5kbc Modellierungs-Regeln

> Wie die Daten von `fst_wgs84_comma.csv` als Linked Open Data abgebildet werden,
> in einer Sprache, die ohne CIDOC-CRM-Vorwissen lesbar ist. Das Dokument
> beschreibt die *Spielregeln* der Modellierung — nicht die technische Umsetzung
> (das macht das Pipeline-Skript `bb5kbc_lod_pipeline.py`).
>
> **Autoren:** Sophie C. Schmidt, Florian Thiery · **Stand:** Ontologie v0.9
> · **Lizenz:** CC BY 4.0

---

## Inhalt

1. [Worum geht's](#worum-gehts)
2. [Das Mentalmodell auf einer Seite](#das-mentalmodell-auf-einer-seite)
3. [Sechs Modellierungsregeln](#sechs-modellierungsregeln)
4. [URI-Konventionen](#uri-konventionen)
5. [SPARQL-Kochbuch](#sparql-kochbuch)
6. [Was die Modellierung *nicht* kann](#was-die-modellierung-nicht-kann)
7. [Mini-Glossar](#mini-glossar)

---

## Worum geht's

Die CSV `fst_wgs84_comma.csv` hat 540 Zeilen — jede Zeile eine archäologische
Fundstelle aus Brandenburg und Umgebung, ca. 5000 BC. Pro Zeile gibt es 33
Spalten: Fundstellenname, Verwaltungsgebiete, Kulturgruppe, Datierung, Quelle
der Georeferenzierung, Koordinaten, Wikidata-IDs für Publikation und
Fundstellenart, etc.

Das Ziel der Modellierung ist es, **diese tabellarischen Daten so in RDF
(Linked Open Data) zu übersetzen**, dass:

- jede archäologisch bedeutsame Aussage einen eigenen, abfragbaren Knoten bekommt
- die Daten an internationale Vokabulare anschließen (CIDOC CRM, Wikidata,
  Getty TGN, Perio.do, iDAI.gazetteer, OpenStreetMap)
- die Wiederverwendung effizient ist: "Brandenburg" ist genau **ein** Knoten,
  egal wie viele Fundstellen drinliegen
- man mit SPARQL Fragen stellen kann wie "Welche SBK-Fundstellen liegen in
  Sachsen-Anhalt und sind 14C-datiert?" (siehe Kochbuch unten)

Was hier *nicht* dokumentiert ist:
- die genaue Implementierung des Pipeline-Skripts (separates Dokument)
- der Vollständige CIDOC-CRM-Mapping (dafür siehe `bb5kbc-csv-mapping.md`
  und die Ontologie selbst)

---

## Das Mentalmodell auf einer Seite

Eine Fundstelle steht im Zentrum. An ihr hängen sieben Arten von Beziehungen:

```
                     ┌─────────────────────┐
                     │   Verwaltungsgebiet │
                     │  (Land, Bundesland, │
                     │   Kreis, Gemeinde)  │
                     └──────────┬──────────┘
                                │  liegt in
                                │
                                ▼
       Datierung   ◀────  ┌──────────┐  ────▶  Fundstellenart
       Kulturgruppe       │          │         (Siedlung, Grab, …)
            ▲             │          │
            │   gehört zu │ Fundstelle│  wurde entdeckt durch ▶ Entdeckung
       Kulturelle ◀───────│          │                       (mit Entdeckungsart)
       Zuordnung          │          │
                          │          │  ────▶  Publikation
                          │          │
                          │          │  ────▶  Scherbe (1-n)
                          │          │
                          └────┬─────┘
                               │  hat Geometrie / wurde georeferenziert von
                               ▼
                       ┌────────────────┐
                       │  Punkt (WGS84) │
                       │  + Aktivität   │
                       │   die ihn      │
                       │   erzeugt hat  │
                       └────────────────┘
```

Für ein klickbares, vollständiges Klassendiagramm: siehe `bb5kbc-classes.mmd`
(rendert in mermaid.live, GitHub, VS Code, Obsidian).

---

## Sechs Modellierungsregeln

Diese sechs Regeln entscheiden, **welche Werte einen eigenen Knoten bekommen
und welche als einfache Texte/Zahlen direkt an einem Knoten hängen**.

### Regel 1: Eine Fundstelle ist ein eigener Knoten mit einer ID (FID)

Jede Zeile der CSV wird zu **einem** Fundstellen-Knoten. Der Identifier ist
die FID (`fst_id` in der CSV). Die FID landet in der URI:

```
http://w3id.org/bb5kbc/site_33     ← Fundstelle mit FID=33 (Friesack 4)
http://w3id.org/bb5kbc/site_1      ← Fundstelle mit FID=1
```

Direkt an der Fundstelle hängen nur die **Eigenschaften, die nur diese eine
Fundstelle betreffen**: ihr Name, ihre Katalognummer, ihre interne ID, ihre
räumliche Genauigkeit. Alles andere geht über Beziehungen (Regeln 2–6).

**Warum?** Eine FID ist garantiert eindeutig pro Fundstelle, sie ist stabil
(ändert sich nicht), und sie ist im Quelldatensatz so vorgesehen.

### Regel 2: Verwaltungsebenen werden geteilt — ein Hash-Knoten pro Wert

"Friesack" als Gemeinde ist **genau ein** Knoten, egal ob 1 Fundstelle oder
50 Fundstellen darin liegen. Der Knoten hat eine URI, die aus dem Namen
abgeleitet wird (MD5-Hash der ersten 8 Zeichen):

```
http://w3id.org/bb5kbc/gemeinde_ef3c98d9     ← "Friesack"
http://w3id.org/bb5kbc/kreis_d4d0a03b        ← "Havelland"
http://w3id.org/bb5kbc/bundesland_2ddb2d82   ← "Brandenburg"
http://w3id.org/bb5kbc/land_3c2f8b8c         ← "Deutschland"
```

Die vier Verwaltungsebenen bilden eine Kette: Fundstelle liegt in Gemeinde,
Gemeinde liegt in Kreis, Kreis liegt in Bundesland, Bundesland liegt in Land.
**Jede dieser Ebenen kann zusätzlich eine Wikidata-QID, eine Getty-TGN-ID,
eine iDAI-gazetteer-ID und eine OSM-Relation tragen** — das sind externe
Identifikatoren, die als zusätzliche Triples an den Verwaltungsknoten hängen
(siehe Regel 5).

**Warum?** Wenn man später fragt "Welche Fundstellen liegen in Brandenburg?",
soll der Brandenburg-Knoten *einer* sein, nicht 100 Duplikate.

### Regel 3: Typen werden geteilt — auch ein Hash-Knoten pro Wert

Genauso wie Verwaltungsebenen werden auch **Typ-Werte dedupliziert**:

| CSV-Spalte | Typ-Klasse | Beispiel-URI |
|---|---|---|
| `fundstellenart` | Fundstellenart-Typ | `fundstellenart_1972902b` (Siedlung) |
| `entdeckung` (QID) | Entdeckungs-Typ | `entdeckungsart_2b73226f` (Ausgrabung) |
| `kultur` | Kulturgruppe | `kultur_a36e9d6d` (FBG) |
| `dating_method` (QID) | Datierungsmethode | `datmethode_98fc5e34` (Radiokarbon) |

"Siedlung" wird zu *einem* Knoten, der von allen Fundstellen-Knoten geteilt
wird, die als Siedlung klassifiziert sind. Auf diesem Typ-Knoten hängt dann
**einmal** das `rdfs:label "Siedlung"@de` und **einmal** die Wikidata-QID
`Q486972`.

**Warum?** Damit Anfragen wie "Wie viele Siedlungen gibt es?" einfach
funktionieren — man fragt einen Knoten, nicht 137 Strings.

**Sonderfall Unsicherheit:** Werte wie `"SBK?"` und `"Grab?"` bekommen
**eigene Knoten**, getrennt von `"SBK"` und `"Grab"`. Der Wert mit Fragezeichen
ist *nicht* dasselbe wie der Wert ohne — die Unsicherheit ist Teil der
Aussage. Beide tragen aber dieselbe Wikidata-QID.

**Sonderfall Mehrwertige Fundstellenart:** Werte wie `"Siedlung und Grab"`
oder `"Kreisgrabenanlage und Siedlung"` werden in **zwei separate Knoten**
aufgesplittet. An der Fundstelle hängen dann zwei `bb5kbc:hatFundstellenart`-
Triples — eines pro Komponente. Beispiel:

```
data:site_X
    bb5kbc:hatFundstellenart data:fundstellenart_<hash_siedlung> ;
    bb5kbc:hatFundstellenart data:fundstellenart_<hash_grab> .
```

Damit geht keine Information verloren, und Anfragen wie "Welche Fundstellen
sind sowohl Siedlung als auch Grab?" funktionieren ohne String-Matching.

### Regel 4: Kulturelle Zuordnung trägt eigene Datierung — 1:1 zur Fundstelle

Eine Fundstelle hat genau **eine** kulturelle Zuordnung — das ist die
Verbindung zwischen *dieser* Fundstelle, *einer* Kulturgruppe (z.B. FBG) und
*einer* zeitlichen Datierung (z.B. -4550 bis -3900 BCE). Diese drei Dinge
hängen zusammen; deshalb gibt es einen eigenen Knoten dafür:

```
Fundstelle ─→ KulturelleZuordnung ─→ Kulturgruppe (geteilt!)
                       │
                       └──────────→ Datierung (eigen pro Fundstelle)
```

- **Kulturgruppe** ist geteilt (alle SBK-Fundstellen zeigen auf den gleichen
  SBK-Knoten — Regel 3).
- **Datierung** ist *nicht* geteilt: jede Fundstelle hat ihre eigene
  Datierung mit ihren eigenen Start/End-Werten und Sicherheits-Beschreibungen.

Die Datierung ist sowohl ein **CRM-Time-Span** als auch ein **OWL-Time-Intervall** —
das gibt späteren Anfragen sowohl eine CRM-konforme als auch eine
intervall-topologische Sicht (z.B. "Phase A endet bevor Phase B beginnt").

**Warum 1:1?** Weil die CSV genau eine Datierung pro Zeile hat. Wenn später
mehrere Phasen pro Fundstelle modelliert werden sollen (z.B. SBK-Phase
gefolgt von Rössen-Phase an derselben Fundstelle), braucht es ein Update der
Modellierungsregel — siehe [Limits](#was-die-modellierung-nicht-kann).

### Regel 5: Externe IDs hängen direkt am Knoten — eine Property für alle

Wikidata-QIDs, Getty-TGN-IDs, iDAI-gazetteer-IDs, OSM-Relationen und
Perio.do-URIs werden alle über **eine einzige Property** angehängt:
`bb5kbc:hasExternalIdentifier`. Welcher Identifier-Typ es ist, sieht man am
URI-Präfix:

```turtle
data:land_3c2f8b8c
    a bb5kbc:Land ;
    rdfs:label "Deutschland"@de ;
    bb5kbc:hasExternalIdentifier <http://vocab.getty.edu/tgn/7000084> ,
                                 <http://gazetteer.dainst.org/place/2044274> ,
                                 <https://www.openstreetmap.org/relation/51477> ,
                                 <https://www.wikidata.org/entity/Q183> .
```

**Warum eine Property statt vier?** Weil aus archäologischer Sicht alle vier
das Gleiche tun ("dieser Knoten ist auch dort zu finden"), und weil eine
einzige Property SPARQL-Anfragen stark vereinfacht — man muss nicht für jeden
Identifier-Typ eine eigene Query schreiben.

### Regel 6: Georeferenzierung ist ein eigener Akt

Eine Fundstelle ist *nicht* ihre Koordinate. Sie ist ein archäologischer Ort,
der irgendwann von jemandem mit irgendeiner Methode irgendwo verortet wurde.
Diese Verortung wird als **eigene Aktivität** modelliert:

```
Fundstelle ─wurdeGeoreferenziertDurch→ GeoreferenzierungsAktivitaet
    │                                  │
    │                                  ├─→ Methode (z.B. "Übernahme aus DB")
    │                                  ├─→ Quelle ("BLDAM 2021")
    │                                  ├─→ Genauigkeit (Beschreibung)
    │                                  └─→ Person (ORCID)
    │
    └──hatGeometrie──→ Punkt (WGS84)
```

Damit sind drei Sichten möglich, die in der CSV vermischt sind:
1. **Was die Fundstelle ist** — räumlich, archäologisch, identifizierbar
2. **Wie die Koordinate zustande kam** — Provenienz-Information
3. **Wo die Fundstelle ist** — der eigentliche Punkt im WGS84-System

**Warum so aufwendig?** Weil wir wissen wollen, *wie verlässlich* eine
Verortung ist. Eine Übernahme aus dem Landesdenkmalamt ist anders zu
bewerten als eine Mittelpunkt-der-Gemeinde-Schätzung. Diese Information geht
verloren, wenn man Koordinaten direkt an die Fundstelle hängt.

---

## URI-Konventionen

Alle URIs liegen unter dem Datennamespace `http://w3id.org/bb5kbc/`. Die
**Ontologie selbst** liegt unter `http://w3id.org/bb5kbc/ont/` (z.B.
`http://w3id.org/bb5kbc/ont/Fundstelle` für die Klasse).

| URI-Muster | Bedeutung | Beispiel |
|---|---|---|
| `site_{FID}` | Eine Fundstelle | `site_33` |
| `site_{FID}_activity` | Die Georeferenzierung *dieser* Fundstelle | `site_33_activity` |
| `site_{FID}_geom` | Der WGS84-Punkt *dieser* Fundstelle | `site_33_geom` |
| `gemeinde_{hash}` | Eine Gemeinde (geteilt) | `gemeinde_ef3c98d9` (Friesack) |
| `kreis_{hash}` | Ein Kreis (geteilt) | `kreis_d4d0a03b` (Havelland) |
| `bundesland_{hash}` | Ein Bundesland (geteilt) | `bundesland_2ddb2d82` (Brandenburg) |
| `land_{hash}` | Ein Land (geteilt) | `land_3c2f8b8c` (Deutschland) |
| `kultur_{hash}` | Eine Kulturgruppe (geteilt) | `kultur_a36e9d6d` (FBG) |
| `culture_{hash}` | Eine Kulturelle Zuordnung (geteilt pro Kulturgruppe) | `culture_a36e9d6d` |
| `culture_{hash}_dating` | Die Datierung dieser Zuordnung | `culture_a36e9d6d_dating` |
| `entdeckung_{hash}` | Eine Entdeckung (geteilt) | `entdeckung_1f56a08c` |
| `entdeckungsart_{hash}` | Eine Entdeckungsart (geteilt) | `entdeckungsart_2b73226f` |
| `fundstellenart_{hash}` | Eine Fundstellenart (geteilt) | `fundstellenart_1972902b` |
| `pub_{hash}` | Eine Publikation (geteilt) | `pub_c54b495e` |
| `datmethode_{hash}` | Eine Datierungsmethode (geteilt) | `datmethode_98fc5e34` (14C) |
| `sherd_{hash}` | Eine Scherbe (geteilt pro Wikidata-QID) | `sherd_02807cc2` |

`{hash}` ist immer die ersten 8 Zeichen eines MD5-Hashes über den ursprünglichen
Wert (UTF-8). Das macht die URIs kollisionssicher (auch für Umlaute) und
deterministisch — derselbe Wert ergibt immer dieselbe URI.

---

## SPARQL-Kochbuch

Die Beispiele gehen davon aus, dass die Daten in einem SPARQL-Endpunkt liegen,
mit folgenden Prefixen:

```sparql
PREFIX bb5kbc: <http://w3id.org/bb5kbc/ont/>
PREFIX data:   <http://w3id.org/bb5kbc/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX wd:     <https://www.wikidata.org/entity/>
PREFIX geo:    <http://www.opengis.net/ont/geosparql#>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
```

### 1. Alle Fundstellen mit Namen und FID

```sparql
SELECT ?fid ?name WHERE {
    ?site a bb5kbc:Fundstelle ;
          bb5kbc:hatFID ?fid ;
          rdfs:label ?name .
}
ORDER BY ?fid
```

> Liefert alle 540 Fundstellen mit ihrer FID und ihrem Namen — der "Hello World"
> der Anfragen.

### 2. Alle SBK-Fundstellen

```sparql
SELECT ?name WHERE {
    ?kultur rdfs:label "SBK"@de .
    ?zuordnung bb5kbc:hatKulturgruppe ?kultur .
    ?site bb5kbc:hatKulturelleZuordnung ?zuordnung ;
          rdfs:label ?name .
}
```

> Findet alle Fundstellen einer bestimmten Kulturgruppe. Beachte: `"SBK?"` mit
> Fragezeichen findet diese Query *nicht* — das ist ein eigener Knoten (Regel 3).

### 3. Alle Fundstellen in Brandenburg (egal in welchem Kreis/welcher Gemeinde)

```sparql
SELECT ?name ?gemeinde_name WHERE {
    ?bundesland rdfs:label "Brandenburg"@de .
    ?kreis bb5kbc:inBundesland ?bundesland .
    ?gemeinde bb5kbc:inKreis ?kreis ;
              rdfs:label ?gemeinde_name .
    ?site bb5kbc:inGemeinde ?gemeinde ;
          rdfs:label ?name .
}
ORDER BY ?gemeinde_name ?name
```

> Folgt der Verwaltungs-Kette nach oben (Regel 2). Wer eine kürzere Anfrage
> möchte: die Property `bb5kbc:inGemeinde`, `inKreis`, `inBundesland`, `inLand`
> sind alle Subproperties von `crm:P89_falls_within` — ein Reasoner kann
> daraus inferieren, dass eine Fundstelle direkt in einem Bundesland liegt.

### 4. Alle Siedlungen mit Wikidata-Verknüpfung der Fundstellenart

```sparql
SELECT ?name ?wikidata_qid WHERE {
    ?fundstellenart rdfs:label "Siedlung"@de ;
                    bb5kbc:hasExternalIdentifier ?wikidata_qid .
    FILTER(STRSTARTS(STR(?wikidata_qid), "https://www.wikidata.org/"))

    ?site bb5kbc:hatFundstellenart ?fundstellenart ;
          rdfs:label ?name .
}
```

> Zeigt, wie externe Identifier abgefragt werden (Regel 5): die `FILTER`-Zeile
> schränkt auf Wikidata-URIs ein. Für andere Authority Files (TGN, iDAI, OSM)
> nimmt man entsprechend andere Präfixe.

### 5. Alle Fundstellen, die jünger als 4000 BCE datiert sind

```sparql
SELECT ?name ?dating_start ?dating_end WHERE {
    ?site a bb5kbc:Fundstelle ;
          rdfs:label ?name ;
          bb5kbc:hatKulturelleZuordnung ?zuordnung .
    ?zuordnung bb5kbc:hatDatierung ?dating .
    ?dating bb5kbc:datierungStart ?dating_start ;
            bb5kbc:datierungEnd ?dating_end .

    FILTER(?dating_end > -4000)
}
ORDER BY ?dating_end
```

> BCE-Jahre sind negative Integer (Regel 4). `-4000` (4000 BCE) ist *früher*
> als `-3500` (3500 BCE). Die Query liefert Fundstellen, deren Ende nach
> 4000 BCE liegt — also Fundstellen, die teilweise in die jüngere Phase
> hineinreichen.

### 6. Alle 14C-datierten Fundstellen

```sparql
SELECT ?name WHERE {
    ?dating bb5kbc:datierungMethode ?methode .
    ?methode bb5kbc:hasExternalIdentifier wd:Q173412 .   # Q173412 = Radiokarbondatierung

    ?zuordnung bb5kbc:hatDatierung ?dating .
    ?site bb5kbc:hatKulturelleZuordnung ?zuordnung ;
          rdfs:label ?name .
}
```

> Findet Fundstellen über die Wikidata-QID der Datierungsmethode. Q173412 ist
> die Wikidata-Entität für Radiokarbondatierung — egal wie die Methode in
> der CSV beschriftet war.

### 7. Fundstellen, deren Perio.do-Periode bekannt ist

```sparql
SELECT ?name ?periodo_uri ?match_strength WHERE {
    ?site a bb5kbc:Fundstelle ;
          rdfs:label ?name ;
          bb5kbc:hatKulturelleZuordnung ?zuordnung .
    ?zuordnung bb5kbc:hatDatierung ?dating .

    {
        ?dating skos:exactMatch ?periodo_uri .
        BIND("exact" AS ?match_strength)
    } UNION {
        ?dating skos:closeMatch ?periodo_uri .
        BIND("close" AS ?match_strength)
    } UNION {
        ?dating skos:relatedMatch ?periodo_uri .
        BIND("related" AS ?match_strength)
    }

    FILTER(STRSTARTS(STR(?periodo_uri), "http://n2t.net/ark:/99152/"))
}
```

> Zeigt das SKOS-Match-Pattern (Regel 4): `exactMatch`, `closeMatch`,
> `relatedMatch` werden hier in eine einheitliche Variable gemerged, die
> Stärke des Matches kommt mit.

### 8. Kreuztabelle: Fundstellenart × Kulturgruppe

```sparql
SELECT ?fundstellenart_label ?kultur_label (COUNT(?site) AS ?anzahl) WHERE {
    ?site a bb5kbc:Fundstelle ;
          bb5kbc:hatFundstellenart ?fundstellenart ;
          bb5kbc:hatKulturelleZuordnung ?zuordnung .

    ?fundstellenart rdfs:label ?fundstellenart_label .
    ?zuordnung bb5kbc:hatKulturgruppe ?kultur .
    ?kultur rdfs:label ?kultur_label .
}
GROUP BY ?fundstellenart_label ?kultur_label
ORDER BY DESC(?anzahl)
```

> Eine analytische Anfrage: wie viele Fundstellen gibt es pro Kombination
> Fundstellenart × Kulturgruppe? Zeigt den Wert der Knoten-Deduplizierung —
> ohne Regel 3 wäre `GROUP BY` über String-Werte unzuverlässig.

### 9. Fundstellen, deren Koordinaten vom BLDAM stammen

```sparql
SELECT ?name ?genauigkeit WHERE {
    ?site a bb5kbc:Fundstelle ;
          rdfs:label ?name ;
          bb5kbc:hatGenauigkeit ?genauigkeit ;
          bb5kbc:wurdeGeoreferenziertDurch ?activity .

    ?activity ?p ?ref .
    FILTER(CONTAINS(LCASE(STR(?ref)), "bldam"))
}
ORDER BY ?genauigkeit
```

> Folgt der Provenance-Kette (Regel 6): von der Fundstelle über die
> Georeferenzierungs-Aktivität zur Quelle. Hier ist die Quelle als String
> hinterlegt — bei strikt typisierten Anfragen würde man stattdessen die
> Wikidata-QID `Q897952` (BLDAM) über `bb5kbc:hasExternalIdentifier` matchen.

---

## Was die Modellierung *nicht* kann

Damit Sophie und andere fair einschätzen können, ob die Modellierung passt,
hier die bewussten Entscheidungen, **etwas wegzulassen**:

### Mehrere Datierungen pro Fundstelle

Aktuell hat jede Fundstelle **genau eine** `bb5kbc:KulturelleZuordnung` mit
**genau einer** `bb5kbc:Datierung`. Wenn an einer Fundstelle mehrere
zeitliche Phasen sichtbar sind (z.B. SBK gefolgt von Rössen), lässt sich das
mit der aktuellen Modellierung *nicht* abbilden — die CSV unterstützt es auch
nicht.

**Was zu tun wäre:** Die CSV müsste pro Fundstelle mehrere Zeilen erlauben
(eine pro Phase), und die Modellierungsregel 4 würde von 1:1 auf 1:n
geöffnet. Das ist ein moderater Eingriff.

### Mehrwertige Fundstellenarten

Werte wie `"Siedlung und Grab"` werden aktuell auf **einen einzigen**
Fundstellenart-Typ gemappt (in dem Fall den Siedlungs-Knoten, mit dem Label
`"Siedlung und Grab"@de`). Die zweite Komponente (Grab) geht verloren —
sie wäre als zweites `bb5kbc:hatFundstellenart`-Triple modellierbar, aber das
würde die Pipeline komplexer machen.

Siehe `bb5kbc-csv-issues.md` für Sophies Entscheidung.

### Numerische Unsicherheits-Toleranz

Die Werte `dating_certainty_start` (`"+ / - 100 years"` etc.) sind als
**Freitext-Strings** modelliert, nicht als strukturierte Toleranzen. Wer
Anfragen wie "Datierung mit Toleranz < 50 Jahre" stellen will, müsste die
Strings vorher parsen. Hintergrund: die CSV-Werte sind heterogen
(deutsch/englisch, mit Tippvarianten — siehe `bb5kbc-csv-issues.md`).

### Fundstellen-zu-Fundstellen-Beziehungen

Es gibt keine Modellierung für räumliche oder kulturelle Beziehungen
*zwischen* Fundstellen ("Fundstelle A liegt in Sichtweite von Fundstelle B",
"Fundstelle C ist Vorgänger von Fundstelle D"). Das ist Forschungsoutput,
nicht Quelldaten.

### Personen / Institutionen außer Sophie

Die einzige Person in der aktuellen Modellierung ist Sophie C. Schmidt als
Akteurin der Georeferenzierung (über ORCID). Andere Forscher:innen
(z.B. Bersu, Wysocki) tauchen *nur* als Teil von Entdeckungs-Labels auf
(`"Ausgrabung Bersu"`) und werden nicht als eigene Entitäten modelliert.

---

## Mini-Glossar

Drei Begriffe, die unvermeidbar sind, wenn man mit RDF arbeitet:

**Triple** — Eine Aussage in der Form *Subjekt → Prädikat → Objekt*, wie ein
Satz mit drei Worten. Beispiel: *Fundstelle 33 → hat Fundstellenart →
Siedlung*. Alle Daten in RDF bestehen aus Triples; ein SPARQL-Endpunkt ist
eine Datenbank dafür.

**URI** (Uniform Resource Identifier) — Ein global eindeutiger Bezeichner,
der wie eine Web-Adresse aussieht. `http://w3id.org/bb5kbc/site_33` ist die
URI der Fundstelle Friesack 4. Zwei URIs, die gleich aussehen, sind dieselbe
Sache; zwei URIs, die anders aussehen, sind verschiedene Sachen — auch wenn
sie das gleiche meinen sollen. Deshalb teilen wir Knoten (Regel 2 + 3): damit
"Friesack" für alle Fundstellen *dieselbe* URI hat.

**Prefix** — Eine Abkürzung für einen URI-Anfang. Statt
`<http://w3id.org/bb5kbc/ont/Fundstelle>` schreibt man `bb5kbc:Fundstelle`,
wenn vorher `PREFIX bb5kbc: <http://w3id.org/bb5kbc/ont/>` deklariert ist.
Macht Anfragen lesbar.

---

*Fragen, Korrekturen, Erweiterungen: Issues im Repository oder direkt an
Sophie und Florian.*
