# =============================================================================
# enrich_qids.py
#
# Reichert eine Eingabe-CSV mit Wikidata-QIDs an für:
#   - Spalte "QID_quelle_georef"  (Lookup-Key: "quelle_georef")
#   - Spalte "QID_publikation"    (Lookup-Key: "publikation_arch")
#
# QID-Mappings stammen aus zwei Quellen:
#   1. Den QuickStatements-HTML-Seiten (Initial-Import)
#   2. Manuellen Korrekturen / Sophies Reviews (laufend gepflegt im Code)
#
# Authoritäts-Modell (Stand: April 2026):
#   Die Code-Dictionaries QID_PUBLIKATION und QID_QUELLE_GEOREF gelten als
#   "Single Source of Truth". Wenn das Mapping einen QID liefert, überschreibt
#   das Skript den Wert in der CSV-Zelle — auch dann, wenn dort schon ein
#   anderer QID stand. Konflikte (alter ≠ neuer QID) werden im Log
#   protokolliert, sodass nachträgliche Audits möglich sind.
#
# Fehlende Matches und Konflikte werden in eine Log-Datei geschrieben.
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
    "Raddatz 1956":              "Q139304631",
    "Raddatz 1958":              "Q139570571",
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
    # --- Nachgereicht: Sophies Review (April 2026) ------------------------
    "Pyzel 2019":                "Q139460445",
    "Umbreit 1940":              "Q139459720",
    "Schier et al. 2023":        "Q139555255",
    "Wetzel/Babiel 2016":        "Q139555259",
    # ---------------------------------------------------------------------
    # Zur Historie der oben genannten Einträge (Stand: April 2026):
    #
    # - Pyzel 2019 (FID 548, 549): Sophie hat bestätigt, dass dasselbe Werk
    #   wie in QID_QUELLE_GEOREF gemeint ist (Q139460445).
    # - Umbreit 1940 (FID 244):    Sophie hat bestätigt, Q139459720.
    # - Schier et al. 2023 (FID 8): Sophie hat geklärt, dass es sich nicht
    #   um die Ippesheim-Endmonografie handelt — eigene QID Q139555255.
    # - Wetzel/Babiel 2016 (FID 257): CSV-Tippfehler "Babieel" wurde in der
    #   CSV korrigiert zu "Babiel". QID Q139555259 von Sophie nachgereicht.
    # - Raddatz 1956 / Raddatz 1958: Der frühere Code-Eintrag "Raddatz 1959"
    #   war eine Falsch-Zuordnung — laut Sophie war "1959" ein Tippfehler,
    #   gemeint war "Raddatz 1958" (Q139570571). "Raddatz 1956" ist eine
    #   eigenständige Publikation (Q139304631). Beide stehen jetzt mit
    #   ihrer korrekten QID im Mapping; der alte "1959"-Eintrag wurde
    #   entfernt.
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
    "Raddatz 1958":                          "Q139570571",
    "Ciesielski/Goczyca 2013":               "Q139304640",
    "Dziewanowski 2023":                     "Q139460420",
    "Swieder 2009, Kulczycka-Leciejewiczowa 1993, Karte 1 Nr. 23": "Q139304628",
    # Sonstige Quellen-Entitäten (Sophies Review).
    # Anmerkung: Diese QIDs sind nicht in jedem Fall publizierte Werke — sie
    # umfassen auch Institutionen (z. B. BLDAM, LfDA Sachsen-Anhalt) und
    # Personen (Wolfram Schier für persönl. Kommunikation; Lech Czerniak als
    # Sammelreferenz). Werden in Spalte `quelle_georef` semantisch wie Werke
    # behandelt; eine eventuelle Type-Differenzierung (Werk vs. Agent) erfolgt
    # ggf. nachgelagert in der LOD-Pipeline.
    "LfDA Sachsen-Anhalt":                   "Q1802049",
    "BLDAM 2021":                            "Q897952",
    "BLDAM 2024":                            "Q897952",
    "BLDAM / M. Ismail-Weber 2018":          "Q897952",
    "Denkmaldaten / BLDAM 2021":             "Q897952",
    "Denkmaldaten / BLDAM 2024":             "Q897952",
    "Museum Angermünde":                     "Q76632599",
    "Museum Szczecin":                       "Q2802195",
    "Zabytek.pl":                            "Q43301933",
    "W. Schier persönl. Kommunikation":      "Q15445052",
    "Berlekamp 1966, Liste 9":               "Q139304613",
    "Czerniak":                              "Q11753457",
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
        ``filled_georef``, ``filled_pub``, ``confirmed_georef``,
        ``confirmed_pub``, ``overwritten_georef``, ``overwritten_pub``,
        ``n_missing``, ``n_rows``.
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

    # Counter (Modus A: Mapping ist Single Source of Truth)
    filled_georef = 0     # leere Zelle gefuellt
    filled_pub = 0
    confirmed_georef = 0  # Zelle hatte bereits korrekten QID
    confirmed_pub = 0
    overwritten_georef = 0  # Zelle hatte anderen QID, ueberschrieben
    overwritten_pub = 0

    def _apply(col_qid, col_label, mapping, row, i):
        """Apply Modus-A logic for one cell. Returns ('filled'|'confirmed'|'overwritten'|'noop')."""
        new_qid = _lookup_qid(row.get(col_label), mapping, col_label, i, log)
        if not new_qid:
            return "noop"  # miss oder None — Lookup-Helper hat bereits geloggt

        current = str(row.get(col_qid, "")).strip()
        if current in ("", "nan"):
            df.at[i, col_qid] = new_qid
            return "filled"
        if current == new_qid:
            return "confirmed"
        # Konflikt: alter QID != neuer QID
        log.warning(
            "Konflikt: CSV-Zelle ueberschrieben | Zeile %d | Spalte: %s | "
            "Label %r | alter QID: %s -> neuer QID: %s",
            i + 2, col_qid, str(row.get(col_label, "")).strip(), current, new_qid,
        )
        df.at[i, col_qid] = new_qid
        return "overwritten"

    for i, row in df.iterrows():
        # -- QID_quelle_georef --
        result = _apply("QID_quelle_georef", "quelle_georef", QID_QUELLE_GEOREF, row, i)
        if result == "filled":
            filled_georef += 1
        elif result == "confirmed":
            confirmed_georef += 1
        elif result == "overwritten":
            overwritten_georef += 1

        # -- QID_publikation --
        result = _apply("QID_publikation", "publikation_arch", QID_PUBLIKATION, row, i)
        if result == "filled":
            filled_pub += 1
        elif result == "confirmed":
            confirmed_pub += 1
        elif result == "overwritten":
            overwritten_pub += 1

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
        "confirmed_georef": confirmed_georef,
        "confirmed_pub": confirmed_pub,
        "overwritten_georef": overwritten_georef,
        "overwritten_pub": overwritten_pub,
        "n_missing": n_missing,
        "log_path": str(log_path),
    }

    print(
        f"  [enrich_qids] QID_quelle_georef: {filled_georef} filled, "
        f"{confirmed_georef} confirmed, {overwritten_georef} overwritten"
    )
    print(
        f"  [enrich_qids] QID_publikation:   {filled_pub} filled, "
        f"{confirmed_pub} confirmed, {overwritten_pub} overwritten"
    )
    if n_missing == 0:
        print("  [enrich_qids] No missing matches, no conflicts.")
    else:
        print(f"  [enrich_qids] {n_missing} log entries (misses + conflicts) -> {log_path}")

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
