"""
enrich_fst.py
-------------
Enriches fst_wgs84_comma.csv with authority-ID columns from fst_standortanalysen_ref_mapped.csv.

For each location level (LAND, BUNDESLAND, KREIS, GEMEINDE) the following columns are
inserted *directly after* the matching original column:
  <LEVEL>_QID  <LEVEL>_GeoNames  <LEVEL>_TGN  <LEVEL>_IDAI  <LEVEL>_OSM_Relation
  <LEVEL>_matchLabel  <LEVEL>_matchScore  <LEVEL>_matchReason

Join key: FID (original) == "FID catalogue Schmidt 2026" (mapped)

Output: fst_wgs84_comma_enriched.csv  (same folder)
"""

import csv
import pandas as pd
from pathlib import Path

# ── file paths (script and CSVs live in the same folder) ──────────────────────
BASE = Path(__file__).parent
ORIGINAL = BASE / "fst_wgs84_comma.csv"
MAPPED = BASE / "fst_standortanalysen_ref_mapped.csv"
OUTPUT = BASE / "fst_wgs84_comma_enriched.csv"

# ── load data ─────────────────────────────────────────────────────────────────
orig = pd.read_csv(ORIGINAL, dtype=str)
mapped = pd.read_csv(MAPPED, dtype=str)

# normalise join-key column name in mapped
mapped = mapped.rename(columns={"FID catalogue Schmidt 2026": "FID"})

# ── columns to pull from mapped, grouped by level ────────────────────────────
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

# build the set of enrichment columns we actually need from mapped
enrich_cols = ["FID"]
for level_upper in [l.upper() for l in LEVELS]:
    for suffix in SUFFIX_COLS:
        col = level_upper + suffix
        if col in mapped.columns:
            enrich_cols.append(col)
        else:
            print(f"  [WARN] column '{col}' not found in mapped CSV – skipped")

mapped_slim = mapped[enrich_cols].copy()

# ── join ──────────────────────────────────────────────────────────────────────
# FID in original is an integer-like string; cast both to str to be safe
orig["FID"] = orig["FID"].astype(str).str.strip()
mapped_slim["FID"] = mapped_slim["FID"].astype(str).str.strip()

merged = orig.merge(mapped_slim, on="FID", how="left")

# ── reorder columns: insert enrichment cols right after their base column ─────
final_cols = list(orig.columns)  # start with original order

for orig_col, level_upper in zip(LEVELS.values(), [l.upper() for l in LEVELS]):
    # find position of the base column (case-insensitive match)
    base_col_actual = next(
        (c for c in final_cols if c.lower() == orig_col.lower()), None
    )
    if base_col_actual is None:
        print(
            f"  [WARN] base column '{orig_col}' not found in original – skipping insertion"
        )
        continue

    insert_at = final_cols.index(base_col_actual) + 1

    new_cols = [
        level_upper + s for s in SUFFIX_COLS if level_upper + s in merged.columns
    ]

    # insert after base column
    for i, col in enumerate(new_cols):
        final_cols.insert(insert_at + i, col)

# any enrichment columns not yet placed (shouldn't happen, but safety net)
placed = set(final_cols)
for col in merged.columns:
    if col not in placed:
        final_cols.append(col)

result = merged[final_cols]

# ── write output ──────────────────────────────────────────────────────────────
# write with guaranteed quoting of every field
import io as _io

buf = _io.StringIO()
writer = csv.writer(buf, quoting=csv.QUOTE_ALL)
writer.writerow(result.columns.tolist())
for row in result.itertuples(index=False, name=None):
    writer.writerow(["" if (v != v or v is None) else str(v) for v in row])
with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
    f.write(buf.getvalue())

print(f"\n✓  Enriched CSV written to: {OUTPUT}")
print(f"   Rows: {len(result)}  |  Columns: {len(result.columns)}")
print(f"\nColumn order preview:")
for i, col in enumerate(result.columns):
    print(f"  {i+1:>3}. {col}")
