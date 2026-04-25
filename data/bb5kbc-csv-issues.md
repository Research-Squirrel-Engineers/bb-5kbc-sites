# bb5kbc CSV — Auffälligkeiten zur Klärung

Hinweise zur Datei `fst_wgs84_comma.csv` (540 Zeilen, 33 Spalten), die bei der
Vorbereitung des RDF-Mappings aufgefallen sind. Sortiert nach Priorität: erst
Datenfehler, dann Modellierungsfragen, dann formale Inkonsistenzen.

---

## 🔴 Wahrscheinliche Datenfehler

### 1. `dating_end` mit positivem Vorzeichen (vermutlich fehlende Minuszeichen)

Zwei Zeilen haben einen positiven `dating_end`-Wert, während `dating_start` negativ ist —
das passt zeitlich nicht zusammen, da BCE-Datierungen im Datensatz durchgängig negativ kodiert sind.

| FID | fst_name | kultur | dating_start | dating_end | dating_certainty_range |
|---|---|---|---|---|---|
| 31 | Eythra | SBK | `-4800` | `4750` | "medium certainty, good 14C dating, but many mixed features" |
| 257 | Dyrotz 37 | Rössener Kultur | `-4464` | `4344` | "low precision, one 14C date in contradiction to dendrodate" |

**Vermutung:** Tippfehler — gemeint sind wahrscheinlich `-4750` bzw. `-4344`.
Beim Übernehmen ohne Korrektur würde die Datierung im RDF im Jahr +4750 enden,
was offensichtlich falsch ist.

**Aktion:** in der CSV korrigieren oder im Pipeline-Script abfangen?
*(Vorerst nicht angefasst — Sophie klärt.)*

*Sophie: hat korrigiert*

---

## 🟡 Modellierungsfragen

### 2. `fundstellenart = "unbek."` mit QID Q59496158

460 von 540 Zeilen haben `fundstellenart = "unbek."` (= unbekannt) und werden auf
**Q59496158** gemappt. Q59496158 ist auf Wikidata aber `"Findspot of an excavation"`
/ `"Fundstelle einer Grabung"` — das beschreibt eine **bekannte** Fundstellenart und
ist semantisch das Gegenteil von "unbekannt". 

*Sophie: Das ist gelogen: Q59496158 beschreibt 'not yet determined', was genau das ist, was wir sagen wollen.*

**Frage:** Soll `"unbek."` im RDF überhaupt einen QID-Bezug bekommen, oder
besser nur als `rdfs:label "unbek."@de` ohne `bb5kbc:hasExternalIdentifier` modelliert werden?

*Sophie: meinetwegen auch weglassen, geht m.E. beides gut (easy find and replace für Q59496158*

Zudem gibt es eine Zeile mit `fundstellenart = "Ausgrabung"` (1× — was als
Fundstellenart, nicht als Entdeckungsart, ungewöhnlich klingt) ebenfalls auf Q59496158.

*Sophie: ist korrigiert*

### 3. `fundstellenart = "Grab?"` — wie wird die Unsicherheit modelliert?

Eine Zeile hat `fundstellenart = "Grab?"` und wird hart auf `Q173387` (= grave) gemappt.
Das Fragezeichen geht im RDF verloren.

**Optionen:**
- (a) Eigener Knoten `fundstellenart_<hash>` mit Label `"Grab?"@de` und derselben QID — Fragezeichen bleibt im Label sichtbar (aktueller Default).
- (b) Zusätzlich `fsl:certaintyDesc "uncertain"@en` oder ein `fsl:certaintyLevel`-Verweis auf den Knoten.
- (c) `skos:relatedMatch` statt `bb5kbc:hasExternalIdentifier` zur QID, weil die Identität nur vermutet ist.

*Sophie: finde Lösung b gut, ebenso für unten*

Analog: `kultur = "SBK?"` und `kultur = "SRK?"` (jeweils eigene Kulturgruppe-Knoten).

### 4. Mehrwertige `fundstellenart` ("Siedlung und Grab" usw.)

Vier kombinierte Werte landen jeweils auf nur einer QID — die zweite Komponente geht verloren:

| fundstellenart | gemappte QID | verlorene Information |
|---|---|---|
| `"Siedlung und Grab"` | Q486972 (Siedlung) | Grab (Q173387) |
| `"Kreisgrabenanlage und Siedlung"` | Q1787688 (KGA) | Siedlung (Q486972) |
| `"Siedlung, Brunnen"` | Q486972 (Siedlung) | Brunnen (Q43483) |
| `"Siedlung, Kreisgrabenanlage"` | Q1787688 (KGA) | Siedlung (Q486972) |

**Frage:** Sollen mehrwertige Fundstellenarten als **mehrere** `fsl:siteType`-Triples
modelliert werden (eines pro Komponente)? Das wäre RDF-konform und verlustfrei,
würde aber eine Aufsplittung im Pipeline-Script erfordern.

*Sophie: das wäre eine Möglichkeit. Wenn zu aufwändig, als Siedlung lassen, das ist meist die wichtigere Kategorie*

### 5. `entdeckung` ohne QID

Drei Werte haben gar keine `QID_entdeckung`-Zuordnung:

| entdeckung | Anzahl | Beispiel-FID |
|---|---|---|
| `"Altfund"` | 1 | 244 |
| `"Siedlung"` | 1 | 78 |
| `"Sondage, Oberflächenuntersuchung oder zufällige Entdeckung"` | 19 | 93 |

**Anmerkungen:**
- `"Siedlung"` als Entdeckungsart wirkt wie ein Eingabefehler — das ist eine Fundstellenart, keine Entdeckungsart. Bei FID=78 prüfen.
- `"Altfund"` und der dritte Wert sind plausible Entdeckungsarten, denen aber bisher keine QID zugewiesen wurde — eventuell Q3140250 (`Altfund` / `chance find`) bzw. Aufsplittung des Sammelbegriffs.

Im RDF entstehen dadurch `bb5kbc:Entdeckung`-Knoten **ohne** `crm:P2_has_type` —
das ist OK, aber Sophie sollte entscheiden, ob die QIDs nachgetragen werden.

*Sophie: Altfund und "Sondage, ..." = unbek. (geändert) und Siedlung war ein Fehler, ist korrigiert*
---

## 🟠 Formale Inkonsistenzen

### 6. Mischung Deutsch/Englisch in `dating_certainty_*`

Die drei Datierungs-Sicherheitsspalten enthalten heterogene Freitexte mit
sprachlichen und typografischen Varianten:

**`dating_certainty_start` (472 gefüllt):**
| Anzahl | Wert |
|---|---|
| 205 | `"+ / - 100 years"` |
| 190 | `"+ / -100 years"` *(ohne Space vor 100)* |
| 51 | `"+ /- 100 Jahre"` *(deutsch)* |
| 24 | `"+/- 200 years"` *(ohne Spaces, abweichend)* |
| 1 | `"+ / - 10 years"` |
| 1 | `"+ / - 50 Jahre"` |

**`dating_certainty_end` (472 gefüllt):**
| Anzahl | Wert |
|---|---|
| 204 | `"+ / - 100 years"` |
| 190 | `"+ / -100 years"` |
| 51 | `"+ /- 100 Jahre"` |
| 24 | `"+/- 300 years"` |
| 1 | `"+ / - 10 years"` |
| 1 | `"+ / - 50 Jahre"` |
| 1 | `"+ / - 50 years"` |

**Empfehlung:** Aus Modellierungs-Sicht ist das nicht blockierend, weil die
Werte als `xsd:string` erhalten bleiben. Wenn aber eine spätere strukturierte
Auswertung (z.B. numerische Toleranz extrahieren) gewünscht ist, lohnt eine
Normalisierung auf eine Schreibweise, idealerweise englisch (`+/- 100 years`).

*Sophie: vereinheitlicht*

### 7. `dating_perio.do_match` leer trotz vorhandener URI

Eine Zeile hat eine Perio.do-URI, aber kein Match-Level:

| FID | fst_name | dating_perio.do | dating_perio.do_match |
|---|---|---|---|
| 35 | Prettin 6 | `http://n2t.net/ark:/99152/p0wctqtnkjq` | *(leer)* |

**Pipeline-Verhalten (Default):** Bei leerem Match-Level wird `skos:relatedMatch`
verwendet (schwächste Aussage). Falls Sophie dort `closeMatch` oder `exactMatch`
beabsichtigt hatte, sollte das Feld nachgetragen werden.

*Sophie hat das nachgetragen und allgemein die periodo-Links ersetzt, wo nun neue zur Verfügung standen*

### 8. `kultur = "Rössener Kultur"` (Vereinheitlichung gegenüber früherer CSV)

In früheren Versionen der CSV gab es zwei Schreibweisen (`"Rössen"`, `"Rössener"`),
jetzt nur noch `"Rössener Kultur"`. Damit gibt es **9 distinct Kulturgruppen** statt vorher 10:
`SBK`, `SRK`, `BKK`, `FBG`, `Rössener Kultur`, `Guhrau`, `Mesolithikum`, `SBK?`, `SRK?`.

*(Kein Fehler — nur ein Hinweis, dass der Ontologie-Kommentar in v0.3 entsprechend
angepasst wurde.)*

*Sophie: Es sind 7 distinkte Kulturgruppen, die mit Fragezeichen müssen, wie oben gesagt, als unsicher markiert werden -> Lösung b) Zusätzlich `fsl:certaintyDesc "uncertain"@en` oder ein `fsl:certaintyLevel`-Verweis auf den Knoten.*

---

## ⚪ Komplett leere Spalten

Zwei Spalten sind aktuell vollständig leer und werden im Pipeline-Script
übersprungen, sind aber im Schema vorgesehen:

| Spalte | Status | Geplant für |
|---|---|---|
| `perio.do` (Kulturgruppe-Ebene) | 0/540 | Perio.do-URI auf der `bb5kbc:Kulturgruppe` (nicht der Datierung) |
| `QID_publikation` | 0/540 | Wikidata-QID auf der `bb5kbc:Publikation` |

Die Spalten `GEM_TGN`, `GEM_IDAI`, `GEM_OSM_RELATION`, `KREIS_TGN`,
`KREIS_IDAI`, `KREIS_OSM_RELATION`, `BL_TGN`, `BL_IDAI`, `BL_OSM_RELATION`
sind im Mapping-Schema vorgesehen, aktuell aber gar nicht in der CSV vorhanden —
sie werden vom `wikidata_map.py`-Script nachgereicht.

*Sophie: perio.do rausgenommen, gibt die andere Spalte dazu*

---

## ⚙ Hinweis fürs Pipeline-Script

- **Komma als Dezimaltrenner** in `wgs84_x` / `wgs84_y` (z.B. `"12,54"`) muss vor der WKT-Generierung in einen Punkt umgewandelt werden.
- **`publikation_arch` ist in 271/540 Zeilen leer** — keine `bb5kbc:Publikation` in diesen Fällen.
- **`QID_publikation` ist komplett leer** — die Verknüpfung Publikation → Wikidata muss aus dem `enrich_qids.py`-Output (separates Skript) gesetzt werden.
