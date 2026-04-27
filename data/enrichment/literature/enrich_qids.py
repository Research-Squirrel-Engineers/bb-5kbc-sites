# =============================================================================
# enrich_qids.py
#
# Reichert eine Eingabe-CSV mit Wikidata-QIDs an für:
#   - Spalte "QID_quelle_georef"  (Lookup-Key: "quelle_georef")
#   - Spalte "QID_publikation"    (Lookup-Key: "publikation_arch")
#
# QID-Mappings wurden aus den QuickStatements-HTML-Seiten extrahiert.
# Fehlende Matches werden in eine Log-Datei geschrieben.
#
# Verwendung:
#   - Als Modul (vom Orchestrator):
#       from enrich_qids import run
#       run(input_csv=Path(...), output_csv=Path(...), log_path=Path(...))
#
#   - Standalone (Default-Pfade relativ zum Skript):
#       python enrich_qids.py
# =============================================================================

import csv
import io
import logging
import os
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Konfiguration (CSV-Format-Konstanten)
# ---------------------------------------------------------------------------

CSV_SEP = ","
CSV_ENCODING_IN = "utf-8"
CSV_ENCODING_OUT = "utf-8-sig"  # BOM, gemäss Projekt-Konvention

# ---------------------------------------------------------------------------
# QID-Mapping: publikation_arch -> QID
# Quelle: QuickStatements_1.htm und QuickStatements_2.htm
# ---------------------------------------------------------------------------

QID_PUBLIKATION = {
    # --- Aus QuickStatements_1.htm ---
    "Sprockhoff 1926":           "Q139304606",
    "Czerniak/Pyzel 2016":       "Q139304607",
    "Beran 2012 b":              "Q139304609",
    "Lehmphul 2015":             "Q139304610",
    "Wetzel 2013":               "Q139304611",
    "Eberhardt 2007":            "Q139304612",
    "Berlekamp 1966,":           "Q139304613",
    "Meyer 2011":                "Q139304614",
    "Marschallek 1944":          "Q139304615",
    "Kaufmann 1976":             "Q139304616",
    "Wetzel 1973":               "Q139304617",
    "Kirsch 1993":               "Q139304618",
    "Gramsch 1960":              "Q139304619",
    "Wetzel 1988":               "Q139304620",
    "Beran 2011 a":              "Q139304621",
    "Stark 2020":                "Q139304622",
    "Czerniak 1980":             "Q139304624",
    "Czerniak et al. 2016":      "Q139304625",
    "Völker 2002":               "Q139304626",
    "Kulczycka-Leciejewiczowa 1993": "Q139304628",
    "Czerniak 2007":             "Q139304629",
    "Smoczyńska 1952":           "Q139304630",
    "Raddatz 1959":              "Q139304631",
    "Umbreit 1937":              "Q139304632",
    "Wetzel/Beran 2023":         "Q139304633",
    "von Richthofen 1930":       "Q139304635",
    "Jentsch 1885":              "Q139304636",
    "Dziewanowski 2015":         "Q139304639",
    "Ciesielski/Goczyca 2013":   "Q139304640",
    "Dorka 1939":                "Q139304641",
    "Grygiel 2008":              "Q139304642",
    "Schmiederer 1997":          "Q139304643",
    "Kunkel 1939":               "Q139304644",
    "Rybicka/Wysocki 2004":      "Q139304645",
    "Stäuble/Veit 2016":         "Q139304647",
    "Czerniak et al 2020":       "Q139304648",
    "Czerniak et al. 2020":      "Q139304648",
    "Ratajczyk 2007":            "Q139304649",
    "Schoknecht 1986":           "Q139304650",
    # --- Aus QuickStatements_2.htm ---
    "Dziewanowski 2019":         "Q139304679",
    "Umbreit 1939":              "Q139304632",
    # --- Pending: warten auf Sophies Review (Stand: April 2026) -----------
    # Hinweis: Die folgenden Publikationen tauchen in der CSV in Spalte
    # `publikation_arch` auf, sind aber (noch) nicht eindeutig auf ein
    # Wikidata-Item gemappt. Per Projektregel werden hier keine QIDs
    # geraten — entweder Sophie liefert die QID nach, oder die Zelle
    # bleibt leer.
    #
    # "Pyzel 2019"        FID 548, 549 (Ludwinowo 7, SBK, Polen)
    #                     In QID_QUELLE_GEOREF als Q139460445 hinterlegt;
    #                     Sophie muss bestätigen, ob dasselbe Werk gemeint ist.
    # "Umbreit 1940"      FID 244 (Lietzow-Buddelin/Saiser 1)
    #                     In QID_QUELLE_GEOREF als Q139459720 hinterlegt;
    #                     Sophie muss bestätigen, ob dasselbe Werk gemeint ist.
    # "Schier et al. 2023" FID 8 (Quedlinburg KGA 1)
    #                     Mehrdeutig: Schiers 2023-Hauptpublikation ist die
    #                     Ippesheim-Endmonografie (BAF 22, Rahden/Westf. 2023);
    #                     Quedlinburg ist eine andere Anlage. Sophie klärt
    #                     welches Werk gemeint ist.
    # "Raddatz 1956"      FID 94 (Kaaso/Kozów, SBK, Polen, Woj. Lubuskie)
    #                     Achtung: in QID_QUELLE_GEOREF unten als Q139304631
    #                     hinterlegt — das ist aber das QID für "Raddatz 1959"
    #                     (siehe oben). Sophie muss klären: ist das ein Tippfehler
    #                     in der CSV (1956 → 1959), oder existiert eine separate
    #                     Raddatz-1956-Publikation, die noch ein eigenes
    #                     Wikidata-Item braucht?
    # "Wetzel/Babieel 2016" FID 257 (Dyrotz 37, Rössener Kultur, Havelland)
    #                     Eindeutig identifiziert als:
    #                       Wetzel, G. / Babiel, K.: Der Rössener Brunnen von
    #                       Dyrotz 37, Lkr. Havelland, und sein Umfeld. In:
    #                       Veröff. brandenb. Landesarchäologie 47 (2016),
    #                       79–108.
    #                     CSV-Tippfehler: Co-Autor heißt Babiel, nicht Babieel.
    #                     Wikidata-Item existiert (Stand April 2026) noch nicht.
    # ---------------------------------------------------------------------
}

# ---------------------------------------------------------------------------
# QID-Mapping: quelle_georef -> QID
# ---------------------------------------------------------------------------

QID_QUELLE_GEOREF = {
    "Kaufmann 1976":                         "Q139304616",
    "Czerniak 1980":                         "Q139304624",
    "Czerniak 1980L":                        "Q139304624",
    "Czerniak 2007":                         "Q139304629",
    "Czerniak 2007, Karte 1":                "Q139304629",
    "Dorka 1939":                            "Q139304641",
    "Grygiel 2008, Karte 1":                 "Q139304642",
    "Stäuble/Veit 2016":                     "Q139304647",
    "Wetzel 1988":                           "Q139304620",
    "von Richthofen 1930, Karte 2":          "Q139304635",
    "Pyzel 2019":                            "Q139460445",
    "Umbreit 1937":                          "Q139304632",
    "Umbreit 1940":                          "Q139459720",
    "Kulczycka-Leciejewiczowa 1993, Karte 1":             "Q139304628",
    "Kulczycka-Leciejewiczowa 1993, Karte 1 Nr 5":        "Q139304628",
    "Kulczycka-Leciejewiczowa 1993, Karte 1, Berlekamp 1966":                            "Q139304628",
    "Kulczycka-Leciejewiczowa 1993, Karte 1, von Richthofen 1930, Karte 2 Nr 35":        "Q139304628",
    "Raddatz 1956":                          "Q139304631",
    "Ciesielski/Goczyca 2013":               "Q139304640",
    "Dziewanowski 2023":                     "Q139460420",
    "Swieder 2009, Kulczycka-Leciejewiczowa 1993, Karte 1 Nr. 23": "Q139304628",
    # Institutionelle Quellen (von Sophie nachgereicht):
    "LfDA Sachsen-Anhalt":                   "Q1802049",
    "BLDAM 2021":                            "Q897952",
    "BLDAM 2024":                            "Q897952",
    "BLDAM / M. Ismail-Weber 2018":          "Q897952",
    "Denkmaldaten / BLDAM 2021":             "Q897952",
    "Denkmaldaten / BLDAM 2024":             "Q897952",
    "Museum Angermünde":                     "Q76632599",
    "Museum Szczecin":                       "Q2802195",
    "Zabytek.pl":                            "Q43301933",
    "W. Schier persönl. Kommunikation":      None,
    "Berlekamp 1966, Liste 9":               "Q139304613",
    "Czerniak":                              None,
}


# ---------------------------------------------------------------------------
# Hilfsfunktion: Lookup mit Logging
# ---------------------------------------------------------------------------

def _lookup_qid(
    value, mapping: dict, col_name: str, row_idx: int, log: logging.Logger
) -> str | None:
    """Returns the QID for a value or None; logs misses and intentional empties."""
    if pd.isna(value) or str(value).strip() == "":
        return None

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
            "Mapping vorhanden, aber QID bewusst leer | Zeile %d | Spalte: %s | Wert: %r",
            row_idx + 2,
            col_name,
            key,
        )
    return qid


# ---------------------------------------------------------------------------
# Logger-Setup (modul-eigener Logger, jeder run()-Aufruf bekommt frischen Handler)
# ---------------------------------------------------------------------------

def _setup_logger(log_path: Path) -> logging.Logger:
    """Configure a dedicated logger for this run; replaces any prior handlers."""
    log = logging.getLogger("enrich_qids")
    log.setLevel(logging.WARNING)
    # Remove handlers from previous runs (important when imported as a module)
    for h in list(log.handlers):
        log.removeHandler(h)
        h.close()
    handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s  %(levelname)s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    log.addHandler(handler)
    log.propagate = False  # don't bubble up to root logger
    return log


# ---------------------------------------------------------------------------
# CSV-Writer (folgt Projekt-Konvention: QUOTE_ALL, na_rep="", UTF-8 BOM)
# ---------------------------------------------------------------------------

def _write_csv_quoted(df: pd.DataFrame, path: Path) -> None:
    """Write CSV with all fields quoted, empty strings for NaN, UTF-8 BOM."""
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_ALL)
    writer.writerow(df.columns.tolist())
    for row in df.itertuples(index=False, name=None):
        writer.writerow(["" if (v != v or v is None) else str(v) for v in row])
    with open(path, "w", newline="", encoding=CSV_ENCODING_OUT) as f:
        f.write(buf.getvalue())


# ---------------------------------------------------------------------------
# Hauptfunktion (vom Orchestrator aufgerufen)
# ---------------------------------------------------------------------------

def run(input_csv: Path, output_csv: Path, log_path: Path) -> dict:
    """Enrich a CSV with QID columns from the embedded mappings.

    Parameters
    ----------
    input_csv : Path
        Source CSV (read-only). Must be comma-separated, UTF-8.
    output_csv : Path
        Destination CSV. Will be written with QUOTE_ALL and UTF-8 BOM.
    log_path : Path
        Where to write the per-row warning log (overwritten each run).

    Returns
    -------
    dict
        Summary with keys:
        ``filled_georef``, ``filled_pub``, ``skipped_georef``,
        ``skipped_pub``, ``n_missing``, ``n_rows``.
    """
    input_csv = Path(input_csv)
    output_csv = Path(output_csv)
    log_path = Path(log_path)

    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    log = _setup_logger(log_path)

    print(f"  [enrich_qids] Reading: {input_csv}")
    df = pd.read_csv(input_csv, sep=CSV_SEP, encoding=CSV_ENCODING_IN, dtype=str)
    n_rows = len(df)
    print(f"  [enrich_qids]   {n_rows} rows, {len(df.columns)} columns")

    # Counter
    filled_georef = 0
    filled_pub = 0
    skipped_georef = 0
    skipped_pub = 0

    for i, row in df.iterrows():
        # -- QID_quelle_georef --
        current_georef_qid = str(row.get("QID_quelle_georef", "")).strip()
        if current_georef_qid in ("", "nan"):
            new_qid = _lookup_qid(
                row.get("quelle_georef"), QID_QUELLE_GEOREF, "quelle_georef", i, log
            )
            if new_qid:
                df.at[i, "QID_quelle_georef"] = new_qid
                filled_georef += 1
        else:
            skipped_georef += 1

        # -- QID_publikation --
        current_pub_qid = str(row.get("QID_publikation", "")).strip()
        if current_pub_qid in ("", "nan"):
            new_qid = _lookup_qid(
                row.get("publikation_arch"), QID_PUBLIKATION, "publikation_arch", i, log
            )
            if new_qid:
                df.at[i, "QID_publikation"] = new_qid
                filled_pub += 1
        else:
            skipped_pub += 1

    # Flush log handler so the file is fully written before we count lines
    for h in log.handlers:
        h.flush()

    # Output schreiben
    _write_csv_quoted(df, output_csv)
    print(f"  [enrich_qids] Wrote:   {output_csv}")

    # Log-Einträge zählen
    n_missing = 0
    if log_path.exists():
        with open(log_path, encoding="utf-8") as f:
            n_missing = sum(1 for line in f if "WARNING" in line)

    summary = {
        "n_rows": n_rows,
        "filled_georef": filled_georef,
        "filled_pub": filled_pub,
        "skipped_georef": skipped_georef,
        "skipped_pub": skipped_pub,
        "n_missing": n_missing,
        "log_path": str(log_path),
    }

    print(
        f"  [enrich_qids] QID_quelle_georef: {filled_georef} new, {skipped_georef} pre-existing"
    )
    print(
        f"  [enrich_qids] QID_publikation:   {filled_pub} new, {skipped_pub} pre-existing"
    )
    if n_missing == 0:
        print("  [enrich_qids] No missing matches.")
    else:
        print(f"  [enrich_qids] {n_missing} missing/empty entries -> {log_path}")

    return summary


# ---------------------------------------------------------------------------
# Standalone-Modus (Verhalten wie ursprünglich, mit Default-Pfaden)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Default-Pfade: alle relativ zum Skript-Ordner.
    # Wenn du das Skript standalone laufen lässt, schreibt es output IN-PLACE,
    # also unter dem gleichen Dateinamen wie früher.
    here = Path(__file__).parent
    default_input = here / "fst_wgs84_comma.csv"
    default_output = here / "fst_wgs84_comma.csv"  # in-place wie vorher
    default_log = here / "enrich_qids_missing.log"

    run(input_csv=default_input, output_csv=default_output, log_path=default_log)
    print("\nFertig.")
