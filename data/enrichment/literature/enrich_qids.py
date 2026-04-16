# =============================================================================
# enrich_qids.py
#
# Reichert das CSV fst_wgs84_comma.csv mit Wikidata-QIDs für:
#   - Spalte "QID_quelle_georef"  (Lookup-Key: "quelle_georef")
#   - Spalte "QID_publikation"    (Lookup-Key: "publikation_arch")
#
# QID-Mappings wurden aus den QuickStatements-HTML-Seiten extrahiert.
# Fehlende Matches werden in eine Log-Datei geschrieben.
#
# Verwendung (VSCode Terminal / cmd):
#   python enrich_qids.py
#   Das CSV muss im gleichen Ordner wie das Script liegen.
# =============================================================================

import pandas as pd
import logging
import os
from datetime import datetime

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

CSV_FILENAME = "fst_wgs84_comma.csv"
LOG_FILENAME = "enrich_qids_missing.log"

# Trennzeichen und Encoding des CSV anpassen falls nötig
CSV_SEP = ","
CSV_ENCODING = "utf-8"

# ---------------------------------------------------------------------------
# QID-Mapping: publikation_arch -> QID
# Quelle: QuickStatements_1.htm und QuickStatements_2.htm
#
# Schema: "Autor Jahr" (wie im CSV) -> "Q-ID" (wie in Wikidata angelegt)
#
# Autoren/Jahr wurden aus P2093 (Autor) und P577 (Jahr) der HTML-Einträge
# abgeleitet und mit den CSV-Kurzreferenzen abgeglichen.
# ---------------------------------------------------------------------------

QID_PUBLIKATION = {
    # --- Aus QuickStatements_1.htm ---
    "Sprockhoff 1926":           "Q139304606",  # Die Kulturen der jüngeren Steinzeit in der Mark Brandenburg
    "Czerniak/Pyzel 2016":       "Q139304607",  # The Brześć Kujawski culture (Czerniak + Pyzel, 2019 pub.)
    "Beran 2012 b":              "Q139304609",  # Spitzhauen, Schöningen und Swifterband (Jonas Beran, 2012)
    "Lehmphul 2015":             "Q139304610",  # Durch Getreidekörner datiert (Ralf Lehmphul, 2015)
    "Wetzel 2013":               "Q139304611",  # Die Brześć Kujawski-Gruppe in Brandenburg (Günter Wetzel, 2013)
    "Eberhardt 2007":            "Q139304612",  # Jungsteinzeitliche Funde vom Nuthe-Oberlauf (Gisela Eberhardt, 2007)
    "Berlekamp 1966,":           "Q139304613",  # Die Einflüsse des donauländischen Kulturkreises (Hansdieter Berlekamp, 1966)
    "Meyer 2011":                "Q139304614",  # Die Nordperipherie - mittelneolithische Kreisgrabenanlagen (Michael Meyer, 2011)
    "Marschallek 1944":          "Q139304615",  # Die Urgeschichte des Kreises Luckau (Karl Heinz Marschalleck, 1944)
    "Kaufmann 1976":             "Q139304616",  # Wirtschaft und Kultur der Stichbandkeramiker (Dieter Kaufmann, 1976)
    "Wetzel 1973":               "Q139304617",  # Ein Becher der Stichreihenkeramik von Prettin (Günter Wetzel, 1973)
    "Kirsch 1993":               "Q139304618",  # Funde des Mittelneolithikums im Land Brandenburg (Eberhard Kirsch, 1993)
    "Gramsch 1960":              "Q139304619",  # Ein neuer Fund von Rössener Keramik in der Uckermark (Bernhard Gramsch, 1960)
    "Wetzel 1988":               "Q139304620",  # Neue frühneolithische Funde aus dem Bezirk Cottbus (Günter Wetzel, 1988)
    "Beran 2011 a":              "Q139304621",  # Kulturkreise und Regionalgruppen in Mittel- und Ostdeutschland (Jonas Beran, 2011)
    "Stark 2020":                "Q139304622",  # Vom Steinkreis des 5. Jahrtausends v. Chr. (Joachim Stark, 2020)
    "Czerniak 1980":             "Q139304624",  # Rozwój społeczeństw kultury późnej ceramiki wstȩgowej (Lech Czerniak, 1980)
    "Czerniak et al. 2016":      "Q139304625",  # House time: Neolithic settlement development at Racot (Czerniak et al., 2016)
    "Völker 2002":               "Q139304626",  # Abschlussbericht Seelow 2 (Eberhard Völker, 2002)
    "Kulczycka-Leciejewiczowa 1993": "Q139304628",  # Osadnictwo neolityczne w Polsce południowo-zachodniej (1993)
    "Czerniak 2007":             "Q139304629",  # The North-East Frontier of the Post-LBK Cultures (Lech Czerniak, 2007)
    "Smoczyńska 1952":           "Q139304630",  # Kultura ceramiki wstęgowej w Wielkopolsce (1952)
    "Raddatz 1959":              "Q139304631",  # Ein Gefäß der Rössener Kultur aus der Uckermark (Klaus Raddatz) -- Hinweis: HTML hat 1956, CSV hat 1959
    "Umbreit 1937":              "Q139304632",  # Neue Forschungen zur ostdeutschen Steinzeit (Carl Umbreit, 1937)
    "Wetzel/Beran 2023":         "Q139304633",  # Friesack 4 (Wetzel + Beran, 2023)
    "von Richthofen 1930":       "Q139304635",  # Zur bandkeramischen Besiedlung im Bereich der unteren Weichsel und Oder (1930)
    "Jentsch 1885":              "Q139304636",  # Ein verziertes Beigefäss... Sitzung 18. April 1885 (H. Jentsch, 1885)
    "Dziewanowski 2015":         "Q139304639",  # Obiekty kultur postlinearnych (Marcin Dziewanowski, 2015)
    "Ciesielski/Goczyca 2013":   "Q139304640",  # Osada ludności późnej fazy... (Ciesielski + Gorzyca, 2013)
    "Dorka 1939":                "Q139304641",  # Urgeschichte des Weizacker-Kreises Pyritz (Gertrud Dorka, 1939)
    "Grygiel 2008":              "Q139304642",  # Neolit i początki epoki brązu w rejonie Brześcia Kujawskiego (Ryszard Grygiel, 2008)
    "Schmiederer 1997":          "Q139304643",  # Ein Pferdchen in Ton geritzt (Wolfgang Schmiederer, 1997)
    "Kunkel 1939":               "Q139304644",  # Urgeschichte, zugleich Bericht des Vertrauensmannes (Otto Kunkel, 1939)
    "Rybicka/Wysocki 2004":      "Q139304645",  # Materiały kultury późnej ceramiki wstęgowej z Równiny Dolnej (2004)
    "Stäuble/Veit 2016":         "Q139304647",  # Der bandkeramische Siedlungsplatz Eythra in Sachsen (Stäuble + Veit, 2016)
    "Czerniak et al 2020":       "Q139304648",  # The Neolithic roundel and its social context (Czerniak et al., 2020)
    "Czerniak et al. 2020":      "Q139304648",  # identisch, nur Schreibvariante mit Punkt
    "Czerniak et al 2020":       "Q139304648",  # Schreibvariante ohne Punkt
    "Ratajczyk 2007":            "Q139304649",  # Being at Home in the Early Chalcolithic – Hinweis: Ratajczyk nicht direkt in HTML; zugewiesen nach Kontext
    "Schoknecht 1986":           "Q139304650",  # Kurze Fundberichte 1984 Bezirk Neubrandenburg (Ulrich Schoknecht, 1986)
    # --- Aus QuickStatements_2.htm ---
    "Dziewanowski 2019":         "Q139304679",  # Niesformalizowany projekt badań mikroregionalnych (Marcin Dziewanowski, 2019)
    "Umbreit 1939":              "Q139304632",  # manuell ergänzt (gleiche Publikation wie Umbreit 1937? -> von Sophie bestätigt)
    # --- Noch nicht aufgelöst (Sophie prüft) ---
    # "Pyzel 2019"               -> kein direktes Match in HTML
    # "Umbreit 1940"             -> kein Eintrag in HTML
}

# ---------------------------------------------------------------------------
# QID-Mapping: quelle_georef -> QID
# Gleiche Quellen wie oben, aber als Georeferenz-Quelle zitiert.
# Felder wie "Czerniak 1980L", "Czerniak 2007, Karte 1" etc. werden auf
# denselben Basisartikel gemappt (Karte/Varianten-Suffixe werden ignoriert).
# ---------------------------------------------------------------------------

QID_QUELLE_GEOREF = {
    "Kaufmann 1976":                         "Q139304616",
    "Czerniak 1980":                         "Q139304624",
    "Czerniak 1980L":                        "Q139304624",  # Variante mit Suffix
    "Czerniak 2007":                         "Q139304629",
    "Czerniak 2007, Karte 1":               "Q139304629",
    "Dorka 1939":                            "Q139304641",
    "Grygiel 2008, Karte 1":                "Q139304642",
    "Stäuble/Veit 2016":                     "Q139304647",
    "Wetzel 1988":                           "Q139304620",
    "von Richthofen 1930, Karte 2":         "Q139304635",
    "Pyzel 2019":                            None,   # kein eindeutiger QID aus HTML
    "Umbreit 1937":                          "Q139304632",
    "Umbreit 1940":                          None,   # kein Eintrag in HTML
    "Kulczycka-Leciejewiczowa 1993, Karte 1":             "Q139304628",
    "Kulczycka-Leciejewiczowa 1993, Karte 1 Nr 5":        "Q139304628",
    "Kulczycka-Leciejewiczowa 1993, Karte 1, Berlekamp 1966":                            "Q139304628",
    "Kulczycka-Leciejewiczowa 1993, Karte 1, von Richthofen 1930, Karte 2 Nr 35":        "Q139304628",
    "Raddatz 1956":                          "Q139304631",
    "Ciesielski/Goczyca 2013":               "Q139304640",
    "Dziewanowski 2023":                     None,   # Dziewanowski 2023 nicht in HTML (dort 2015/2019)
    "Swieder 2009, Kulczycka-Leciejewiczowa 1993, Karte 1 Nr. 23": "Q139304628",
    # Nicht in HTML (institutionelle / sonstige Quellen):
    "LfDA Sachsen-Anhalt":                   None,
    "BLDAM 2021":                            None,
    "BLDAM 2024":                            None,
    "BLDAM / M. Ismail-Weber 2018":          None,
    "Denkmaldaten / BLDAM 2021":             None,
    "Denkmaldaten / BLDAM 2024":             None,
    "Museum Angermünde":                     None,
    "Museum Szczecin":                       None,
    "Zabytek.pl":                            None,
    "W. Schier persönl. Kommunikation":      None,
    "Berlekamp 1966, Liste 9":               "Q139304613",
    "Czerniak":                              None,   # zu unspezifisch für eindeutiges Mapping
}


# ---------------------------------------------------------------------------
# Logging einrichten
# ---------------------------------------------------------------------------

script_dir = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(script_dir, LOG_FILENAME)

logging.basicConfig(
    filename=log_path,
    filemode="w",
    level=logging.WARNING,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CSV laden
# ---------------------------------------------------------------------------

csv_path = os.path.join(script_dir, CSV_FILENAME)
print(f"Lade CSV: {csv_path}")

df = pd.read_csv(csv_path, sep=CSV_SEP, encoding=CSV_ENCODING, dtype=str)

total_rows = len(df)
print(f"  {total_rows} Zeilen geladen, {len(df.columns)} Spalten")


# ---------------------------------------------------------------------------
# Hilfsfunktion: Wert aus Mapping holen und fehlende Treffer loggen
# ---------------------------------------------------------------------------

def lookup_qid(value, mapping: dict, col_name: str, row_idx: int) -> str | None:
    """Gibt QID zurück oder None; loggt fehlende/nicht gemappte Werte."""
    if pd.isna(value) or str(value).strip() == "":
        return None  # kein Wert -> kein Log-Eintrag, einfach leer lassen

    key = str(value).strip()

    if key not in mapping:
        log.warning(
            "Kein Mapping gefunden | Zeile %d | Spalte: %s | Wert: %r",
            row_idx + 2,  # +2: 1-basiert + Headerzeile
            col_name,
            key,
        )
        return None

    qid = mapping[key]
    if qid is None:
        log.warning(
            "Mapping vorhanden, aber QID bewusst leer (kein Wikidata-Item aus HTML) "
            "| Zeile %d | Spalte: %s | Wert: %r",
            row_idx + 2,
            col_name,
            key,
        )
    return qid


# ---------------------------------------------------------------------------
# QIDs befüllen
# ---------------------------------------------------------------------------

filled_georef = 0
filled_pub = 0
skipped_georef = 0
skipped_pub = 0

for i, row in df.iterrows():

    # -- QID_quelle_georef --
    current_georef_qid = str(row.get("QID_quelle_georef", "")).strip()
    if current_georef_qid in ("", "nan"):
        new_qid = lookup_qid(row.get("quelle_georef"), QID_QUELLE_GEOREF, "quelle_georef", i)
        if new_qid:
            df.at[i, "QID_quelle_georef"] = new_qid
            filled_georef += 1
    else:
        skipped_georef += 1  # bereits befüllt, nicht überschreiben

    # -- QID_publikation --
    current_pub_qid = str(row.get("QID_publikation", "")).strip()
    if current_pub_qid in ("", "nan"):
        new_qid = lookup_qid(row.get("publikation_arch"), QID_PUBLIKATION, "publikation_arch", i)
        if new_qid:
            df.at[i, "QID_publikation"] = new_qid
            filled_pub += 1
    else:
        skipped_pub += 1  # bereits befüllt, nicht überschreiben


# ---------------------------------------------------------------------------
# CSV zurückschreiben (direktes Überschreiben)
# ---------------------------------------------------------------------------

df.to_csv(csv_path, sep=CSV_SEP, index=False, encoding=CSV_ENCODING)
print(f"\nCSV gespeichert: {csv_path}")


# ---------------------------------------------------------------------------
# Zusammenfassung
# ---------------------------------------------------------------------------

print("\n--- Ergebnis ---")
print(f"  QID_quelle_georef:  {filled_georef} neu befüllt, {skipped_georef} bereits vorhanden")
print(f"  QID_publikation:    {filled_pub} neu befüllt, {skipped_pub} bereits vorhanden")
print(f"\n  Log-Datei (fehlende Matches): {log_path}")

# Zähle Log-Einträge
with open(log_path, encoding="utf-8") as f:
    log_lines = [l for l in f if "WARNING" in l]
n_missing = len(log_lines)
if n_missing == 0:
    print("  Keine fehlenden Matches - alles aufgelöst!")
else:
    print(f"  {n_missing} fehlende oder bewusst leere Einträge im Log")

print("\nFertig.")
