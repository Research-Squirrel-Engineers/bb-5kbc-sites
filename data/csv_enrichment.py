"""
csv_enrichment.py
=================
End-to-end enrichment pipeline for the fst dataset.

Flow
----
    fst_wgs84_comma.csv                           (original, read-only)
            │
            ▼  [1/4] Literature enrichment
            │       enrich_qids.run(...)
            │
    fst_wgs84_lit_enriched.csv                    (intermediate, kept)
            │
            │  ┌─────────────────────────────────────────────────┐
            │  │ [2/4] Geo reference mapping (SPARQL, ~minutes) │
            │  │       wikidata_map.run(...)                     │
            │  │   in:  fst_standortanalysen_ref.csv             │
            │  │   out: fst_standortanalysen_ref_mapped.csv      │
            │  └─────────────────────────────────────────────────┘
            ▼
    + fst_standortanalysen_ref_mapped.csv         (intermediate, kept)
            │
            ▼  [3/4] Geo merge
            │       enrich_fst.run(...)
            │
    fst_wgs84.csv                                 (FINAL, LOD-ready)
            │
            ▼  [4/4] Provenance manifest
            │       PROV-O turtle of the run
            │
    csv_enrichment_run.ttl                        (provenance record)

Layout assumed (paths are configured in PATHS below):
    data/
    ├── csv_enrichment.py                  (this file)
    ├── fst_wgs84_comma.csv                (input)
    ├── fst_wgs84_lit_enriched.csv         (tmp 1, generated)
    ├── fst_wgs84.csv                      (final, generated)
    ├── csv_enrichment_run.ttl             (provenance, generated)
    └── enrichment/
        ├── literature/
        │   └── enrich_qids.py
        └── mapping_admin_regions/
            ├── wikidata_map.py
            ├── enrich_fst.py
            ├── fst_standortanalysen_ref.csv         (input)
            └── fst_standortanalysen_ref_mapped.csv  (tmp 2, generated)

Usage
-----
    python csv_enrichment.py
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------
# All paths are relative to this file's directory (data/).

DATA_DIR = Path(__file__).parent
ENRICH_DIR = DATA_DIR / "enrichment"
LITERATURE_DIR = ENRICH_DIR / "literature"
GEO_DIR = ENRICH_DIR / "mapping_admin_regions"

# --- Inputs (read-only) ---
ORIGINAL_CSV = DATA_DIR / "fst_wgs84_comma.csv"
GEO_REF_CSV = GEO_DIR / "fst_standortanalysen_ref.csv"

# --- Intermediate (kept on disk as audit trail) ---
LIT_ENRICHED_CSV = DATA_DIR / "fst_wgs84_lit_enriched.csv"
GEO_MAPPED_CSV = GEO_DIR / "fst_standortanalysen_ref_mapped.csv"
GEO_REPORT_CSV = GEO_DIR / "fst_standortanalysen_ref_report.csv"

# --- Final output ---
FINAL_CSV = DATA_DIR / "fst_wgs84.csv"

# --- Logs and manifest ---
LIT_LOG = DATA_DIR / "csv_enrichment_literature.log"
GEO_LOG = DATA_DIR / "csv_enrichment_geo.log"
RUN_LOG = DATA_DIR / "csv_enrichment_run.log"
RUN_MANIFEST = DATA_DIR / "csv_enrichment_run.ttl"

# --- PROV-O configuration ---
# The base IRI used for all entities/activities/agents in the manifest.
# Adjust to the canonical project IRI when known. Trailing slash is required.
PROV_BASE = "https://example.org/bb-5kbc-sites/"


# ---------------------------------------------------------------------------
# Module loader
# ---------------------------------------------------------------------------

def _load_module(name: str, path: Path) -> ModuleType:
    """Load a Python module from a file path."""
    if not path.exists():
        raise FileNotFoundError(f"Cannot load module {name!r}: {path} does not exist")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for {name!r} at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Run-level tee logger
# ---------------------------------------------------------------------------

class _RunLogger:
    """Mirror everything written to sys.stdout into a run-level log file.

    Usage:
        with _RunLogger(RUN_LOG) as tee:
            sys.stdout = tee
            ...                # all print() output is teed to file
            # __exit__ restores stdout and closes the log file

    Stage-level tee loggers (e.g. wikidata_map.py's _TeeLogger) compose
    correctly with this one: when they capture the "terminal" reference at
    construction time they pick up *this* tee, so their output goes to both
    their own log file AND through to the run log.
    """

    def __init__(self, path: Path) -> None:
        self.terminal = sys.stdout
        self.log = open(path, "w", encoding="utf-8")

    def write(self, message: str) -> None:
        self.terminal.write(message)
        self.log.write(message)

    def flush(self) -> None:
        self.terminal.flush()
        self.log.flush()

    def __enter__(self) -> "_RunLogger":
        return self

    def __exit__(self, *args) -> None:
        sys.stdout = self.terminal
        self.log.close()


# ---------------------------------------------------------------------------
# Git info helpers (for PROV-O agent provenance)
# ---------------------------------------------------------------------------

def _git(*args: str, cwd: Path) -> str | None:
    """Run a git command; return stripped stdout or None on failure."""
    try:
        r = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return r.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _git_info(repo_dir: Path) -> dict:
    """Return git commit, branch, and dirty-flag for the given directory.

    Any field may be None if git is not available or the directory is not a
    git working tree.
    """
    commit = _git("rev-parse", "HEAD", cwd=repo_dir)
    branch = _git("rev-parse", "--abbrev-ref", "HEAD", cwd=repo_dir)
    status = _git("status", "--porcelain", cwd=repo_dir)
    dirty = (status is not None and status != "") if commit is not None else None
    return {"commit": commit, "branch": branch, "dirty": dirty}


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

def stage_literature() -> dict:
    """Stage 1: enrich literature QID columns.

    Reads ORIGINAL_CSV, writes LIT_ENRICHED_CSV.
    """
    print("\n" + "=" * 78)
    print("[1/4]  LITERATURE ENRICHMENT")
    print("=" * 78)

    enrich_qids = _load_module(
        "enrich_qids", LITERATURE_DIR / "enrich_qids.py"
    )

    t0 = time.perf_counter()
    summary = enrich_qids.run(
        input_csv=ORIGINAL_CSV,
        output_csv=LIT_ENRICHED_CSV,
        log_path=LIT_LOG,
    )
    dt = time.perf_counter() - t0
    print(f"  [stage 1/4] done in {dt:.2f}s")
    summary["duration_s"] = dt
    return summary


def stage_geo_mapping() -> dict:
    """Stage 2: SPARQL-based geo reference mapping.

    Reads GEO_REF_CSV, writes GEO_MAPPED_CSV and GEO_REPORT_CSV.

    Note: this stage makes many SPARQL calls to Wikidata and typically takes
    several minutes.
    """
    print("\n" + "=" * 78)
    print("[2/4]  GEO REFERENCE MAPPING (SPARQL — this takes a few minutes)")
    print("=" * 78)

    wikidata_map = _load_module(
        "wikidata_map", GEO_DIR / "wikidata_map.py"
    )

    t0 = time.perf_counter()
    wikidata_map.run(
        input_csv=GEO_REF_CSV,
        output_csv=GEO_MAPPED_CSV,
        report_csv=GEO_REPORT_CSV,
        log_path=GEO_LOG,
    )
    dt = time.perf_counter() - t0
    print(f"  [stage 2/4] done in {dt:.2f}s")
    return {"duration_s": dt}


def stage_geo_merge() -> dict:
    """Stage 3: merge geo enrichment columns into the literature-enriched CSV.

    Reads LIT_ENRICHED_CSV and GEO_MAPPED_CSV, writes FINAL_CSV.
    """
    print("\n" + "=" * 78)
    print("[3/4]  GEO MERGE")
    print("=" * 78)

    enrich_fst = _load_module(
        "enrich_fst", GEO_DIR / "enrich_fst.py"
    )

    t0 = time.perf_counter()
    summary = enrich_fst.run(
        original_csv=LIT_ENRICHED_CSV,
        mapped_csv=GEO_MAPPED_CSV,
        output_csv=FINAL_CSV,
    )
    dt = time.perf_counter() - t0
    print(f"  [stage 3/4] done in {dt:.2f}s")
    summary["duration_s"] = dt
    return summary


# ---------------------------------------------------------------------------
# PROV-O manifest writer
# ---------------------------------------------------------------------------
# Hand-rolled Turtle output to avoid an rdflib dependency. The triple set is
# small enough that templating is comfortable; switch to rdflib if it grows.

PROV_PREFIXES = """\
@prefix prov:    <http://www.w3.org/ns/prov#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix ex:      <{base}> .
"""


def _ttl_str(s: str) -> str:
    """Escape a Python string for use as a Turtle string literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _file_uri(path: Path) -> str:
    """Convert a Path to a file:// URI (Windows-safe)."""
    p = path.resolve().as_posix()
    if not p.startswith("/"):
        # Windows: as_posix() returns 'C:/git/...' (no leading slash).
        # file:// URIs need three slashes for absolute paths on Windows.
        return f"file:///{p}"
    return f"file://{p}"


def _iso(ts: float) -> str:
    """Convert an epoch float to ISO-8601 with timezone (xsd:dateTime)."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")


def _stanza(subject: str, predicates: list[tuple[str, str]]) -> str:
    """Format a subject and a list of (predicate, object) pairs as a Turtle stanza.

    The list-of-pairs API allows the same predicate to be repeated when needed
    (for example, multiple ``prov:used`` edges).  ``object`` strings are taken
    verbatim — the caller is responsible for quoting/escaping them.
    """
    lines = [f"{subject}"]
    for i, (pred, obj) in enumerate(predicates):
        suffix = " ;" if i < len(predicates) - 1 else " ."
        lines.append(f"    {pred} {obj}{suffix}")
    return "\n".join(lines) + "\n"


def write_prov_manifest(
    manifest_path: Path,
    *,
    run_id: str,
    started_at: float,
    ended_at: float,
    git: dict,
    lit_summary: dict,
    geo_summary: dict,
    merge_summary: dict,
) -> None:
    """Write a PROV-O turtle file describing this pipeline run.

    All run IRIs use absolute URIs (e.g. ``<…/run/2026-04-27T…Z>``) rather
    than CURIEs because the run_id contains characters (colons, slashes) that
    aren't safe in a Turtle PNAME local name.
    """
    base = PROV_BASE
    parts: list[str] = [PROV_PREFIXES.format(base=base), ""]

    # The top-level run and its sub-activities are addressed via absolute IRIs:
    run_iri = f"<{base}run/{run_id}>"
    stage1_iri = f"<{base}run/{run_id}/stage1_literature>"
    stage2_iri = f"<{base}run/{run_id}/stage2_geo>"
    stage3_iri = f"<{base}run/{run_id}/stage3_merge>"

    # ---- Agents (the four scripts) -----------------------------------------
    plans = {
        "csv_enrichment_py": DATA_DIR / "csv_enrichment.py",
        "enrich_qids_py": LITERATURE_DIR / "enrich_qids.py",
        "wikidata_map_py": GEO_DIR / "wikidata_map.py",
        "enrich_fst_py": GEO_DIR / "enrich_fst.py",
    }

    parts.append("# === Software agents (scripts) ===")
    for local, p in plans.items():
        parts.append(_stanza(
            f"ex:{local}",
            [
                ("a", "prov:SoftwareAgent, prov:Plan"),
                ("rdfs:label", f'"{_ttl_str(p.name)}"'),
                ("prov:atLocation", f"<{_file_uri(p)}>"),
            ],
        ))

    # ---- Repository version (one node referenced from the top-level run) ---
    if git.get("commit"):
        repo_preds: list[tuple[str, str]] = [
            ("a", "prov:Entity"),
            ("rdfs:label", '"Repository state at run time"'),
            ("ex:gitCommit", f'"{_ttl_str(git["commit"])}"'),
        ]
        if git.get("branch"):
            repo_preds.append(("ex:gitBranch", f'"{_ttl_str(git["branch"])}"'))
        if git.get("dirty") is not None:
            repo_preds.append(
                ("ex:gitDirty",
                 f'"{"true" if git["dirty"] else "false"}"^^xsd:boolean')
            )
        parts.append("# === Source code version (git) ===")
        parts.append(_stanza("ex:repo_version", repo_preds))

    # ---- Entities (the CSVs and logs) --------------------------------------
    entities = {
        "fst_wgs84_comma_csv": (ORIGINAL_CSV, "Original location dataset (input)"),
        "fst_standortanalysen_ref_csv": (
            GEO_REF_CSV,
            "Geo reference table (input)",
        ),
        "fst_wgs84_lit_enriched_csv": (
            LIT_ENRICHED_CSV,
            "Literature-enriched intermediate dataset",
        ),
        "fst_standortanalysen_ref_mapped_csv": (
            GEO_MAPPED_CSV,
            "Geo reference table with Wikidata authority IDs",
        ),
        "fst_standortanalysen_ref_report_csv": (
            GEO_REPORT_CSV,
            "Per-row QA report for geo mapping",
        ),
        "fst_wgs84_csv": (FINAL_CSV, "Final enriched dataset (LOD-ready)"),
        "lit_log": (LIT_LOG, "Literature stage warning log"),
        "geo_log": (GEO_LOG, "Geo stage full stdout log"),
        "run_log": (RUN_LOG, "Full pipeline run log (all stages, teed from stdout)"),
    }

    parts.append("# === Entities (data files and logs) ===")
    for local, (p, label) in entities.items():
        parts.append(_stanza(
            f"ex:{local}",
            [
                ("a", "prov:Entity"),
                ("rdfs:label", f'"{_ttl_str(label)}"'),
                ("prov:atLocation", f"<{_file_uri(p)}>"),
            ],
        ))

    # ---- Top-level activity ------------------------------------------------
    started_iso = _iso(started_at)
    ended_iso = _iso(ended_at)

    top_preds: list[tuple[str, str]] = [
        ("a", "prov:Activity"),
        ("rdfs:label", f'"CSV enrichment pipeline run {_ttl_str(run_id)}"'),
        ("prov:startedAtTime", f'"{started_iso}"^^xsd:dateTime'),
        ("prov:endedAtTime", f'"{ended_iso}"^^xsd:dateTime'),
        ("prov:used", "ex:fst_wgs84_comma_csv"),
        ("prov:used", "ex:fst_standortanalysen_ref_csv"),
    ]
    if git.get("commit"):
        top_preds.append(("prov:used", "ex:repo_version"))
    top_preds.append(("prov:wasAssociatedWith", "ex:csv_enrichment_py"))

    parts.append("# === Top-level activity ===")
    parts.append(_stanza(run_iri, top_preds))

    # Final-output derivation, attributed to the top-level run
    parts.append(_stanza(
        "ex:fst_wgs84_csv",
        [
            ("prov:wasGeneratedBy", run_iri),
            ("prov:wasDerivedFrom", "ex:fst_wgs84_comma_csv"),
            ("prov:wasDerivedFrom", "ex:fst_standortanalysen_ref_mapped_csv"),
        ],
    ))

    # The run log is generated by the top-level run (it captures *everything*,
    # including the orchestrator output that no sub-stage produces).
    parts.append(_stanza(
        "ex:run_log",
        [("prov:wasGeneratedBy", run_iri)],
    ))

    # ---- Stage 1: literature ----------------------------------------------
    stage1_preds: list[tuple[str, str]] = [
        ("a", "prov:Activity"),
        ("rdfs:label", '"Stage 1 — literature QID enrichment"'),
        ("prov:wasInformedBy", run_iri),
        ("prov:used", "ex:fst_wgs84_comma_csv"),
        ("prov:wasAssociatedWith", "ex:enrich_qids_py"),
    ]
    if "duration_s" in lit_summary:
        stage1_preds.append(
            ("ex:durationSeconds",
             f'"{lit_summary["duration_s"]:.2f}"^^xsd:decimal')
        )
    if "filled_georef" in lit_summary:
        stage1_preds.append(
            ("ex:qidsFilledGeoref",
             f'"{lit_summary["filled_georef"]}"^^xsd:integer')
        )
    if "filled_pub" in lit_summary:
        stage1_preds.append(
            ("ex:qidsFilledPublication",
             f'"{lit_summary["filled_pub"]}"^^xsd:integer')
        )
    if "n_missing" in lit_summary:
        stage1_preds.append(
            ("ex:warningsLogged",
             f'"{lit_summary["n_missing"]}"^^xsd:integer')
        )

    parts.append("# === Stage 1: literature ===")
    parts.append(_stanza(stage1_iri, stage1_preds))
    parts.append(_stanza(
        "ex:fst_wgs84_lit_enriched_csv",
        [
            ("prov:wasGeneratedBy", stage1_iri),
            ("prov:wasDerivedFrom", "ex:fst_wgs84_comma_csv"),
        ],
    ))
    parts.append(_stanza(
        "ex:lit_log",
        [("prov:wasGeneratedBy", stage1_iri)],
    ))

    # ---- Stage 2: geo SPARQL ----------------------------------------------
    stage2_preds: list[tuple[str, str]] = [
        ("a", "prov:Activity"),
        ("rdfs:label", '"Stage 2 — geo SPARQL mapping (Wikidata)"'),
        ("prov:wasInformedBy", run_iri),
        ("prov:used", "ex:fst_standortanalysen_ref_csv"),
        ("prov:wasAssociatedWith", "ex:wikidata_map_py"),
    ]
    if "duration_s" in geo_summary:
        stage2_preds.append(
            ("ex:durationSeconds",
             f'"{geo_summary["duration_s"]:.2f}"^^xsd:decimal')
        )

    parts.append("# === Stage 2: geo SPARQL mapping ===")
    parts.append(_stanza(stage2_iri, stage2_preds))
    parts.append(_stanza(
        "ex:fst_standortanalysen_ref_mapped_csv",
        [
            ("prov:wasGeneratedBy", stage2_iri),
            ("prov:wasDerivedFrom", "ex:fst_standortanalysen_ref_csv"),
        ],
    ))
    parts.append(_stanza(
        "ex:fst_standortanalysen_ref_report_csv",
        [
            ("prov:wasGeneratedBy", stage2_iri),
            ("prov:wasDerivedFrom", "ex:fst_standortanalysen_ref_csv"),
        ],
    ))
    parts.append(_stanza(
        "ex:geo_log",
        [("prov:wasGeneratedBy", stage2_iri)],
    ))

    # ---- Stage 3: merge ---------------------------------------------------
    stage3_preds: list[tuple[str, str]] = [
        ("a", "prov:Activity"),
        ("rdfs:label",
         '"Stage 3 — merge geo IDs into literature-enriched CSV"'),
        ("prov:wasInformedBy", run_iri),
        ("prov:used", "ex:fst_wgs84_lit_enriched_csv"),
        ("prov:used", "ex:fst_standortanalysen_ref_mapped_csv"),
        ("prov:wasAssociatedWith", "ex:enrich_fst_py"),
    ]
    if "duration_s" in merge_summary:
        stage3_preds.append(
            ("ex:durationSeconds",
             f'"{merge_summary["duration_s"]:.2f}"^^xsd:decimal')
        )
    if "n_rows" in merge_summary:
        stage3_preds.append(
            ("ex:rowCount", f'"{merge_summary["n_rows"]}"^^xsd:integer')
        )
    if "n_cols" in merge_summary:
        stage3_preds.append(
            ("ex:columnCount", f'"{merge_summary["n_cols"]}"^^xsd:integer')
        )

    parts.append("# === Stage 3: merge ===")
    parts.append(_stanza(stage3_iri, stage3_preds))
    # The final CSV is generated by stage 3, but we ALSO assert it on the
    # top-level run above (prov:wasGeneratedBy is allowed to have multiple
    # values). This dual link makes both views queryable.
    parts.append(_stanza(
        "ex:fst_wgs84_csv",
        [("prov:wasGeneratedBy", stage3_iri)],
    ))

    # ---- Write file --------------------------------------------------------
    manifest_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"  [stage 4/4] manifest written to {manifest_path}")


# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

def _preflight() -> None:
    """Verify that all required inputs exist before any work starts."""
    required_inputs = {
        "Original CSV": ORIGINAL_CSV,
        "Geo reference CSV": GEO_REF_CSV,
    }
    required_modules = {
        "Literature script": LITERATURE_DIR / "enrich_qids.py",
        "Geo mapping script": GEO_DIR / "wikidata_map.py",
        "Geo merge script": GEO_DIR / "enrich_fst.py",
    }

    missing = []
    for label, path in {**required_inputs, **required_modules}.items():
        if not path.exists():
            missing.append(f"  - {label}: {path}")

    if missing:
        print("ERROR: required files not found:")
        for m in missing:
            print(m)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point.  Wraps the actual pipeline in a tee logger so that all
    stdout output is mirrored into RUN_LOG."""
    # Pre-flight has to run before we open the log so that error messages
    # about missing inputs go to the terminal (an empty/half-written log
    # would be confusing).
    _preflight()

    with _RunLogger(RUN_LOG) as tee:
        sys.stdout = tee
        try:
            _main_impl()
        except BaseException as exc:
            # Mirror the exception into the run log so the file documents
            # *why* the run failed, not just the last successful step.
            # We re-raise afterwards so the normal traceback still shows up
            # on the terminal (stderr) for the user.
            print()
            print("=" * 78)
            print(f"PIPELINE ABORTED: {type(exc).__name__}: {exc}")
            print("=" * 78)
            import traceback
            traceback.print_exc(file=tee)
            raise
        finally:
            sys.stdout = tee.terminal


def _main_impl() -> None:
    """Run the full pipeline. All stdout here is teed by the surrounding
    _RunLogger context in main()."""
    print("=" * 78)
    print("CSV ENRICHMENT PIPELINE")
    print("=" * 78)
    print(f"  Data dir: {DATA_DIR}")
    print(f"  Original: {ORIGINAL_CSV.name}")
    print(f"  Final:    {FINAL_CSV.name}")

    # Capture run identity up front
    started_at = time.time()
    run_id = datetime.fromtimestamp(started_at, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H-%M-%SZ"
    )
    git = _git_info(DATA_DIR)
    if git.get("commit"):
        msg = f"  Git:      {git['commit'][:8]} on {git.get('branch') or '?'}"
        if git.get("dirty"):
            msg += " (dirty)"
        print(msg)
    else:
        print("  Git:      (no git info available)")
    print(f"  Run ID:   {run_id}")
    print(f"  Run log:  {RUN_LOG}")

    t_total = time.perf_counter()

    lit_summary = stage_literature()
    geo_summary = stage_geo_mapping()
    merge_summary = stage_geo_merge()

    dt_total = time.perf_counter() - t_total
    ended_at = time.time()

    # Stage 4: provenance manifest
    print("\n" + "=" * 78)
    print("[4/4]  PROVENANCE MANIFEST")
    print("=" * 78)
    write_prov_manifest(
        RUN_MANIFEST,
        run_id=run_id,
        started_at=started_at,
        ended_at=ended_at,
        git=git,
        lit_summary=lit_summary,
        geo_summary=geo_summary,
        merge_summary=merge_summary,
    )

    print("\n" + "=" * 78)
    print("PIPELINE COMPLETE")
    print("=" * 78)
    print(f"  Total time:       {dt_total:.2f}s")
    print(f"  Literature QIDs:  {lit_summary['filled_georef']} georef + "
          f"{lit_summary['filled_pub']} pub  "
          f"({lit_summary['n_missing']} missing in {LIT_LOG.name})")
    print(f"  Final CSV:        {FINAL_CSV}")
    print(f"                    {merge_summary['n_rows']} rows x "
          f"{merge_summary['n_cols']} columns")
    print(f"  Provenance:       {RUN_MANIFEST.name}")
    print(f"  Run log:          {RUN_LOG.name}")
    if merge_summary['missing_enrich_cols']:
        print(f"  WARN: missing enrichment columns: "
              f"{merge_summary['missing_enrich_cols']}")
    print()


if __name__ == "__main__":
    main()
