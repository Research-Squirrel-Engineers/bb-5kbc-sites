"""
enrich_fst.py
-------------
Merges authority-ID columns from a "ref_mapped" CSV (produced by
wikidata_map.py) into the main fst CSV.

For each location level (LAND, BUNDESLAND, KREIS, GEMEINDE) the following
columns are inserted *directly after* the matching original column:
  <LEVEL>_QID  <LEVEL>_GeoNames  <LEVEL>_TGN  <LEVEL>_IDAI  <LEVEL>_OSM_Relation
  <LEVEL>_matchLabel  <LEVEL>_matchScore  <LEVEL>_matchReason

Join key: FID (original)  ==  "FID catalogue Schmidt 2026" (mapped)

Usage
-----
- As a module (from the orchestrator):
    from enrich_fst import run
    run(original_csv=Path(...), mapped_csv=Path(...), output_csv=Path(...))

- Standalone (legacy behaviour, all paths relative to script):
    python enrich_fst.py
"""

import csv
import io
from pathlib import Path

import pandas as pd

# ── columns to pull from mapped, grouped by level ─────────────────────────────
LEVELS = {
    "land": "land",  # original col name (lowercase)
    "bundesland": "bundesland",
    "kreis": "kreis",
    "gemeinde": "gemeinde",
}

SUFFIX_COLS = [
    "_QID",
    "_GeoNames",
    "_TGN",
    "_IDAI",
    "_OSM_Relation",
    "_matchLabel",
    "_matchScore",
    "_matchReason",
]

JOIN_KEY_ORIGINAL = "FID"
JOIN_KEY_MAPPED = "FID catalogue Schmidt 2026"


def _write_csv_quoted(df: pd.DataFrame, path: Path) -> None:
    """Write CSV with all fields quoted, empty strings for NaN, UTF-8 BOM."""
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_ALL)
    writer.writerow(df.columns.tolist())
    for row in df.itertuples(index=False, name=None):
        writer.writerow(["" if (v != v or v is None) else str(v) for v in row])
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        f.write(buf.getvalue())


def run(original_csv: Path, mapped_csv: Path, output_csv: Path) -> dict:
    """Merge authority IDs from ``mapped_csv`` into ``original_csv``.

    Parameters
    ----------
    original_csv : Path
        Main fst CSV (comma-separated).  Must contain a ``FID`` column and
        the level columns (land, bundesland, kreis, gemeinde).
    mapped_csv : Path
        Output of wikidata_map.run() with enrichment columns and the
        ``FID catalogue Schmidt 2026`` join key.
    output_csv : Path
        Destination for the enriched CSV. Written with QUOTE_ALL and
        UTF-8 BOM, following project convention.

    Returns
    -------
    dict
        Summary with keys ``n_rows``, ``n_cols``, ``output_path``,
        ``missing_enrich_cols`` (list of expected mapped columns that were
        not found), ``missing_base_cols`` (list of original level columns
        not found).
    """
    original_csv = Path(original_csv)
    mapped_csv = Path(mapped_csv)
    output_csv = Path(output_csv)

    if not original_csv.exists():
        raise FileNotFoundError(f"Original CSV not found: {original_csv}")
    if not mapped_csv.exists():
        raise FileNotFoundError(f"Mapped CSV not found: {mapped_csv}")

    print(f"  [enrich_fst] Reading original: {original_csv}")
    orig = pd.read_csv(original_csv, dtype=str)
    print(f"  [enrich_fst]   {len(orig)} rows, {len(orig.columns)} columns")

    print(f"  [enrich_fst] Reading mapped:   {mapped_csv}")
    mapped = pd.read_csv(mapped_csv, dtype=str)
    print(f"  [enrich_fst]   {len(mapped)} rows, {len(mapped.columns)} columns")

    # normalise join-key column name in mapped
    mapped = mapped.rename(columns={JOIN_KEY_MAPPED: JOIN_KEY_ORIGINAL})

    # build the set of enrichment columns we actually need from mapped
    enrich_cols = [JOIN_KEY_ORIGINAL]
    missing_enrich = []
    for level_upper in [l.upper() for l in LEVELS]:
        for suffix in SUFFIX_COLS:
            col = level_upper + suffix
            if col in mapped.columns:
                enrich_cols.append(col)
            else:
                missing_enrich.append(col)
                print(
                    f"  [enrich_fst] [WARN] column '{col}' not found in mapped CSV – skipped"
                )

    mapped_slim = mapped[enrich_cols].copy()

    # ── join ──────────────────────────────────────────────────────────────────
    orig[JOIN_KEY_ORIGINAL] = orig[JOIN_KEY_ORIGINAL].astype(str).str.strip()
    mapped_slim[JOIN_KEY_ORIGINAL] = mapped_slim[JOIN_KEY_ORIGINAL].astype(str).str.strip()

    merged = orig.merge(mapped_slim, on=JOIN_KEY_ORIGINAL, how="left")

    # ── reorder columns: insert enrichment cols right after their base column
    final_cols = list(orig.columns)  # start with original order
    missing_base = []

    for orig_col, level_upper in zip(LEVELS.values(), [l.upper() for l in LEVELS]):
        # find position of the base column (case-insensitive match)
        base_col_actual = next(
            (c for c in final_cols if c.lower() == orig_col.lower()), None
        )
        if base_col_actual is None:
            missing_base.append(orig_col)
            print(
                f"  [enrich_fst] [WARN] base column '{orig_col}' not found in original – skipping insertion"
            )
            continue

        insert_at = final_cols.index(base_col_actual) + 1
        new_cols = [
            level_upper + s for s in SUFFIX_COLS if level_upper + s in merged.columns
        ]
        for i, col in enumerate(new_cols):
            final_cols.insert(insert_at + i, col)

    # any enrichment columns not yet placed (shouldn't happen, but safety net)
    placed = set(final_cols)
    for col in merged.columns:
        if col not in placed:
            final_cols.append(col)

    result = merged[final_cols]

    # ── write output ──────────────────────────────────────────────────────────
    _write_csv_quoted(result, output_csv)
    print(f"  [enrich_fst] Wrote: {output_csv}")
    print(f"  [enrich_fst]   Rows: {len(result)}  |  Columns: {len(result.columns)}")

    return {
        "n_rows": len(result),
        "n_cols": len(result.columns),
        "output_path": str(output_csv),
        "missing_enrich_cols": missing_enrich,
        "missing_base_cols": missing_base,
    }


# ---------------------------------------------------------------------------
# Standalone-Modus (legacy behaviour, all paths relative to script)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    here = Path(__file__).parent
    summary = run(
        original_csv=here / "fst_wgs84_comma.csv",
        mapped_csv=here / "fst_standortanalysen_ref_mapped.csv",
        output_csv=here / "fst_wgs84_comma_enriched.csv",
    )
    # Original-style column-order preview for human eyeballing
    import pandas as pd
    print("\nColumn order preview:")
    df_preview = pd.read_csv(summary["output_path"], dtype=str, nrows=0)
    for i, col in enumerate(df_preview.columns):
        print(f"  {i+1:>3}. {col}")
