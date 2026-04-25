# bb-5kbc-sites

Dieses Repositorium enthält Fundstelleninformationen aus der Dissertation von Sophie C. Schmidt. 

Die deutschsprachigen CIDOC CRM Begriffe wurden aus dem Referenzwerk der CIDOC CRM SIG 2010 übernommen (https://cidoc-crm.org/sites/default/files/cidoccrm_end.pdf)

Die folgenden Informationen stehen zur Verfügung:

| Spaltenkopf | Beschreibung | CIDOC-CRM / Modellierungshinweis |
|------------ |-------------| ----------|
|quelle_georef | Quelle für die Geoinformation | E32 Referenzdokument |
|QID_quelle_georeff | Wikidata ID für diese Quelle | E42 Objektkennung |
|katalognr | Katalognummer für die Fundstelle in anderen Publikationen | E42 Objektkennung |
|fst_ID | ID pro Fst | E42 Objektkennung |
|fst_name | Name der Fst | E41 Benennung |
|gemeinde | aktuelle Gemeinde, in der die Fst liegt | P89 fällt in (enthält) E53 Ort |
|kreis | aktueller Land- oder Stadtkreis bzw. powiat, in dem die Fst. liegt (teilw. abweichend von älteren arch. Kataloginformationen) |  P89 fällt in (enthält) E53 Ort |
|bundesland | aktuelles Bundesland oder Wojewodschaft, in dem die Fst. liegt  (teilw. abweichend von älteren arch. Kataloginformationen) | P89 fällt in (enthält) E53 Ort |
|land| aktuelles Land, in dem die Fst. liegt | P89 fällt in (enthält) E53 Ort |
|kultur| grobe Einordnung in Kulturgruppe, in die die Fst. datiert | E49 Zeitbenennung |
|entdeckung | Beschreibung der Art der Entdeckung der Fst | E55 Typus von S19 Begegnung (Encounter Event aus der Archaeo-Erweiterung des CIDOC CRM) |
|QID_entdeckung | Kategorisierung der Art der Entdeckung der Fst: Ausgrabung, Lese- oder Einzelfund in Wikidata | E42 Objektkennung von E55 Typus von S19 Begegnung (Encounter Event aus der Archaeo-Erweiterung des CIDOC CRM) |
|publikation_arch | relevante archäologische Publikation mit weiteren Informationen | E32 Referenzdokument |
|QID_publikation | Wikidata ID der relevantesten archäologische Publikation mit weiteren Informationen | E42 Objektkennung von E32 Referenzdokument |
|fundstellenart | Art der Fundstelle: Siedlung, Grab, Kreisgrabenanlage oder unbek. | E55 Typus von E53 Ort |
|QID_fundstellenart | QID der Art der Fundstelle bei Wikidata | E42 Objektkennung |
|genauigkeit_m | Genauigkeit der Georeferenzierung in Meter, Ungenauigkeiten der Quelle unbekannt | E62 Zeichenkette , in Wikibase P23|
|FID | ID pro Kulturgruppe der Fundstelle im Fundstellenkatalog Schmidt 2026 | E92 Raumzeitvolumen (Spacetime Volume) |
|methode | Methode der Gewinnung der Lagekoordinaten | E55 von P32 nutzt allgemeine Technik |
|quellen_typ | Art der Quelle für die Geoinformation |Typus E55 von E32 Referenzdokument |
|methodenbeschr | Beschreibung der Methode für die Georeferenzierung |  E62 Zeichenkette |
|wgs84_x | X-koordinate im WGS84-Dezimalsystem | E47 Raumkoordinaten |
|wgs84_y | Y-koordinate im WGS84-Dezimalsystem | E47 Raumkoordinaten |
|dating_start| Beginn der Datierungsspanne, CIDOC CRM modelliert begin of begin als dating_start - dating_certainty_start | P82a begin of the begin |
|dating_certainty_start| Genauigkeit des Beginns der Datierung in +/- Jahren, meist eine Schätzung| E62 Zeichenkette , in Wikibase P23|
|dating_end| Ende der Datierungsspanne CIDOC CRM modelliert end of the end als dating_end + dating_certainty_end | P82b end of the end |
|dating_certainty_end|  Genauigkeit des Endes der Datierung in +/- Jahren, meist eine Schätzung| E62 Zeichenkette , in Wikibase P23|
|dating_method | Datierungsmethode (Typologie, 14C, etc als QID von Wikidata) | |
|dating_certainty_range | Beschreibung der Präzision der Datierung |  E62 Zeichenkette |
|perio.do| Perio.do ID der Kulturgruppe / Periode, in die die Fst. datiert | E32 Referenzdokument P71 listet E49 Zeitbenennung |
|dating_perio.do_match | Ausdruck der Zugehörigkeit der Fundstelle zu der Perio.do-Zuweisung: relatedMatch, closeMatch und exactMatch | SKOS-Standard |
|sherd | Liste von QIDs von Scherben, die an diesem Fundort gefunden wurden (pipe-seperiert) | S19 (Entdeckung) O19 hat das Objekt gefunden |


Hinweise für Modellierung in Wikidata:

- Entdeckung von Lese- und Einzelfunden wurden als -> Q1144458 "archaeological field survey" kartiert, dies ist nicht in allen Fällen exakt, es kann sich auch um Zufallsfunde handeln

- Fragezeichen in Kulturgruppe oder Fundstellenartzuweiung sollten mit einem Qualifier, der Unsicherheit markiert, belegt werden

- wenn eine Information nicht bekannt, kann Q59496158 "not yet determined" vergeben werden, oder leer gelassen werden

