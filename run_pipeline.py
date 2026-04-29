"""
bb5kbc — Pipeline runner.

Runs the three stages of the CSV → LOD workflow in one go:

    1. data/csv_enrichment.py        (CSV enrichment: literature + geo + merge)
    2. rdf/bb5kbc_lod_pipeline.py    (LOD generation + SHACL validation)
    3. rdf/validate_lod.py           (post-hoc validation report)

Designed to be launched directly from VS Code's "Run" button — no command-line
arguments. Configure the run by editing the constants below.

The three child scripts are executed via ``runpy.run_path``, which means:
- they are run in fresh module namespaces (no import side-effects bleed across)
- their ``__file__`` is set correctly, so their internal ``Path(__file__).parent``
  logic resolves to ``data/`` and ``rdf/`` exactly as if launched standalone
- this runner does not modify any of the three child scripts

For ``csv_enrichment.py``, the ``PIPELINE_MODE`` constant is overridden via
``init_globals`` — i.e. it is set in the module's namespace *before* the module
body runs, so the assignment in the script picks it up without a code change.
"""

from __future__ import annotations

import runpy
import sys
import time
import traceback
from pathlib import Path


# ---------------------------------------------------------------------------
# Run settings — edit these, then hit "Run" in VS Code.
# ---------------------------------------------------------------------------

# Stage 1 — CSV enrichment.
#
# Set RUN_ENRICHMENT to False to skip Stage 1 entirely. The LOD pipeline will
# then read the existing data/fst_wgs84.csv produced by a previous run.
#
# When RUN_ENRICHMENT is True, ENRICHMENT_MODE controls which sub-stages of
# the enrichment script run fresh vs. reuse their previous outputs:
#
#   "full"        — literature + geo SPARQL + merge (longest run)
#   "literature"  — only literature fresh; geo reused from disk; re-merge
#   "geo"         — only geo SPARQL fresh; literature reused; re-merge
#   "merge"       — both upstream stages reused; only re-merge
#
RUN_ENRICHMENT: bool = False
ENRICHMENT_MODE: str = "full"

# Stage 2 — LOD generation.
RUN_LOD: bool = True

# Stage 3 — Validation report.
RUN_VALIDATE: bool = True


# ---------------------------------------------------------------------------
# Path setup — assumes this runner lives in the project root.
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent

STAGE_ENRICHMENT = ROOT / "data" / "csv_enrichment.py"
STAGE_LOD = ROOT / "rdf" / "bb5kbc_lod_pipeline.py"
STAGE_VALIDATE = ROOT / "rdf" / "validate_lod.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_MODES = ("full", "literature", "geo", "merge")


def _format_duration(seconds: float) -> str:
    """Human-readable duration: '1m 23.4s' or '12.3s'."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, sec = divmod(seconds, 60)
    return f"{int(minutes)}m {sec:.1f}s"


def _print_header(stage_num: int, stage_name: str, script_path: Path) -> None:
    """Banner printed before each stage runs."""
    print()
    print("=" * 72)
    print(f"  STAGE {stage_num}: {stage_name}")
    print(f"  Script: {script_path.relative_to(ROOT)}")
    print("=" * 72)
    print()


def _print_skip(stage_num: int, stage_name: str, reason: str) -> None:
    """Banner printed when a stage is skipped."""
    print()
    print("-" * 72)
    print(f"  STAGE {stage_num}: {stage_name} — SKIPPED ({reason})")
    print("-" * 72)


def _run_stage(
    stage_num: int,
    stage_name: str,
    script_path: Path,
    init_globals: dict | None = None,
) -> tuple[bool, float]:
    """
    Execute one stage via runpy.run_path.

    Returns (ok, elapsed_seconds). ``ok`` is True iff the stage finished
    without raising and (if it returns an int) returned 0.
    """
    if not script_path.exists():
        print(f"ERROR: stage script not found: {script_path}", file=sys.stderr)
        return False, 0.0

    _print_header(stage_num, stage_name, script_path)

    t_start = time.perf_counter()
    try:
        # run_path executes the script as __main__ in a fresh namespace.
        # init_globals is injected *before* the script body runs, so module
        # constants assigned in the script body will overwrite them — but for
        # csv_enrichment.py that is exactly what we want: the script's
        # ``PIPELINE_MODE = "full"`` assignment is replaced because we pass
        # a non-default mode via run_pipeline (see how we use this below).
        #
        # Wait — actually run_path's init_globals are set BEFORE the script
        # runs, and assignments in the script will overwrite them. To force
        # an override we use a small trick: we set the override under a
        # sentinel name and the child script doesn't know about it. So
        # instead, we use a different approach for csv_enrichment.py: we
        # patch the constant *after* the module is loaded. See main() below.
        runpy.run_path(
            str(script_path),
            init_globals=init_globals or {},
            run_name="__main__",
        )
        ok = True
    except SystemExit as exc:
        # Scripts may call sys.exit(). 0 / None = success.
        code = exc.code
        ok = code is None or code == 0
        if not ok:
            print(f"\nStage exited with code {code}", file=sys.stderr)
    except Exception:
        print(f"\nStage raised an exception:", file=sys.stderr)
        traceback.print_exc()
        ok = False

    elapsed = time.perf_counter() - t_start
    print()
    print(
        f"  → Stage {stage_num} finished in {_format_duration(elapsed)} "
        f"({'OK' if ok else 'FAILED'})"
    )
    return ok, elapsed


def _run_enrichment_stage(mode: str) -> tuple[bool, float]:
    """
    Stage 1 needs ``PIPELINE_MODE`` overridden in csv_enrichment.py.

    Strategy: read the script source, replace the ``PIPELINE_MODE = "..."``
    line with the requested mode, then exec the patched source in a fresh
    namespace whose ``__file__`` points at the original script path so
    ``Path(__file__).parent`` still resolves to data/.

    This is the only place we touch the child script's behaviour, and we do
    it without writing back to disk.
    """
    if mode not in _VALID_MODES:
        print(
            f"ERROR: ENRICHMENT_MODE must be one of {_VALID_MODES}, " f"got {mode!r}",
            file=sys.stderr,
        )
        return False, 0.0

    if not STAGE_ENRICHMENT.exists():
        print(f"ERROR: stage script not found: {STAGE_ENRICHMENT}", file=sys.stderr)
        return False, 0.0

    _print_header(1, f"CSV enrichment (mode={mode!r})", STAGE_ENRICHMENT)

    # Patch the source: rewrite the PIPELINE_MODE assignment line.
    source = STAGE_ENRICHMENT.read_text(encoding="utf-8")
    patched_lines = []
    patched = False
    for line in source.splitlines(keepends=True):
        # Match the exact assignment used in csv_enrichment.py (line 114).
        # We're conservative: only rewrite lines that begin with
        # ``PIPELINE_MODE = `` so we don't accidentally mangle comments.
        if not patched and line.lstrip().startswith("PIPELINE_MODE = "):
            indent = line[: len(line) - len(line.lstrip())]
            patched_lines.append(f'{indent}PIPELINE_MODE = "{mode}"\n')
            patched = True
        else:
            patched_lines.append(line)

    if not patched:
        print(
            "ERROR: could not find 'PIPELINE_MODE = ...' assignment in "
            f"{STAGE_ENRICHMENT}",
            file=sys.stderr,
        )
        return False, 0.0

    patched_source = "".join(patched_lines)

    # Execute the patched source as if it were the original script.
    # Setting __file__ to the real path means Path(__file__).parent inside
    # the script still resolves to data/ — directories, sibling files, and
    # PROV manifest paths are all correct.
    t_start = time.perf_counter()
    namespace = {
        "__name__": "__main__",
        "__file__": str(STAGE_ENRICHMENT),
        "__builtins__": __builtins__,
    }
    try:
        compiled = compile(patched_source, str(STAGE_ENRICHMENT), "exec")
        exec(compiled, namespace)
        ok = True
    except SystemExit as exc:
        code = exc.code
        ok = code is None or code == 0
        if not ok:
            print(f"\nStage exited with code {code}", file=sys.stderr)
    except Exception:
        print(f"\nStage raised an exception:", file=sys.stderr)
        traceback.print_exc()
        ok = False

    elapsed = time.perf_counter() - t_start
    print()
    print(
        f"  → Stage 1 finished in {_format_duration(elapsed)} "
        f"({'OK' if ok else 'FAILED'})"
    )
    return ok, elapsed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    print()
    print("#" * 72)
    print("#  bb5kbc — Pipeline runner")
    print("#" * 72)
    print(f"  Project root:    {ROOT}")
    print(
        f"  Stage 1 (enrich): "
        f"{'ON, mode=' + repr(ENRICHMENT_MODE) if RUN_ENRICHMENT else 'SKIP'}"
    )
    print(f"  Stage 2 (LOD):    {'ON' if RUN_LOD else 'SKIP'}")
    print(f"  Stage 3 (verify): {'ON' if RUN_VALIDATE else 'SKIP'}")

    results: list[tuple[str, bool, float]] = []
    overall_start = time.perf_counter()

    # Stage 1 — CSV enrichment
    if RUN_ENRICHMENT:
        ok, elapsed = _run_enrichment_stage(ENRICHMENT_MODE)
        results.append(("CSV enrichment", ok, elapsed))
        if not ok:
            print("\nAborting pipeline: Stage 1 failed.", file=sys.stderr)
            _print_summary(results, time.perf_counter() - overall_start)
            return 1
    else:
        _print_skip(
            1,
            "CSV enrichment",
            "RUN_ENRICHMENT=False — using existing data/fst_wgs84.csv",
        )
        results.append(("CSV enrichment", True, 0.0))

    # Stage 2 — LOD pipeline
    if RUN_LOD:
        ok, elapsed = _run_stage(2, "LOD generation", STAGE_LOD)
        results.append(("LOD generation", ok, elapsed))
        if not ok:
            print("\nAborting pipeline: Stage 2 failed.", file=sys.stderr)
            _print_summary(results, time.perf_counter() - overall_start)
            return 1
    else:
        _print_skip(2, "LOD generation", "RUN_LOD=False")
        results.append(("LOD generation", True, 0.0))

    # Stage 3 — Validation report
    if RUN_VALIDATE:
        ok, elapsed = _run_stage(3, "Validation report", STAGE_VALIDATE)
        results.append(("Validation report", ok, elapsed))
    else:
        _print_skip(3, "Validation report", "RUN_VALIDATE=False")
        results.append(("Validation report", True, 0.0))

    total_elapsed = time.perf_counter() - overall_start
    _print_summary(results, total_elapsed)

    # Exit code reflects whether *any* executed stage failed.
    all_ok = all(ok for _, ok, _ in results)
    return 0 if all_ok else 1


def _print_summary(
    results: list[tuple[str, bool, float]],
    total_elapsed: float,
) -> None:
    """Final block printed at the end of the run."""
    print()
    print("=" * 72)
    print("  PIPELINE SUMMARY")
    print("=" * 72)
    for name, ok, elapsed in results:
        status = "PASS" if ok else "FAIL"
        duration = _format_duration(elapsed) if elapsed > 0 else "skipped"
        print(f"  {status:5}  {name:25}  {duration}")
    print("-" * 72)
    print(f"  Total elapsed: {_format_duration(total_elapsed)}")
    print("=" * 72)
    print()


if __name__ == "__main__":
    sys.exit(main())
