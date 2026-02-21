"""
Coding Manager – Pipeline Orchestrator

Assembles all loaders and mappers into a ``CodingPipeline`` and exposes
the top-level ``run_pipeline()`` entry point.

The pipeline performs four phases:
  0. Organise data files into staging/archive directories
  1. Validate all expected source files
  2. Load code sets
  3. Build mappings

Usage::

    python -m pipeline.pipeline          # direct execution
    from pipeline.pipeline import run_pipeline
    run_pipeline()                       # programmatic

"""

import logging
import os

from pipeline.base import BasePipeline

from pipeline.loaders import (
    SnomedLoader,
    ICD10Loader,
    HCCLoader,
    CPTLoader,
    HCPCSLoader,
    RxNormLoader,
    NDCLoader,
)
from pipeline.mappers import (
    SnomedIcd10Mapper,
    Icd10HccMapper,
    SnomedHccMapper,
    RxNormSnomedMapper,
    NdcRxNormMapper,
)
from pipeline.helpers import organize_data_files
from pipeline.validators import validate_all_sources

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


class CodingPipeline(BasePipeline):
    """Concrete pipeline wiring all loaders & mappers in execution order."""

    def __init__(self):
        super().__init__(
            loaders=[
                SnomedLoader(),
                ICD10Loader(),
                HCCLoader(),
                CPTLoader(),
                HCPCSLoader(),
                RxNormLoader(),
                NDCLoader(),
            ],
            direct_mappers=[
                SnomedIcd10Mapper(),
                Icd10HccMapper(),
            ],
            derived_mappers=[
                SnomedHccMapper(),
                RxNormSnomedMapper(),
                NdcRxNormMapper(),
            ],
        )


# ── Canonical keys for --only / --skip filtering ─────────────────────────────
# Keys are lowercase labels users pass on the CLI.
# Values are the class objects used by CodingPipeline.

LOADER_KEYS = {
    "snomed":  SnomedLoader,
    "icd10":   ICD10Loader,
    "hcc":     HCCLoader,
    "cpt":     CPTLoader,
    "hcpcs":   HCPCSLoader,
    "rxnorm":  RxNormLoader,
    "ndc":     NDCLoader,
}

MAPPER_KEYS = {
    "snomed-icd10":  SnomedIcd10Mapper,
    "icd10-hcc":     Icd10HccMapper,
    "snomed-hcc":    SnomedHccMapper,
    "rxnorm-snomed": RxNormSnomedMapper,
    "ndc-rxnorm":    NdcRxNormMapper,
}

ALL_KEYS = {**LOADER_KEYS, **MAPPER_KEYS}


def clean_db() -> bool:
    """Delete the SQLite database file.  Returns True if a file was removed."""
    from pipeline.models import DB_PATH
    if os.path.isfile(DB_PATH):
        os.remove(DB_PATH)
        logger.info(f"Database deleted: {DB_PATH}")
        return True
    logger.info("No database file found — nothing to clean.")
    return False


def run_pipeline(
    strict: bool = False,
    only: list[str] | None = None,
    skip: list[str] | None = None,
    validate_only: bool = False,
    no_organize: bool = False,
    clean: bool = False,
    auto_resolve: bool = False,
    resolve_limit: int | None = None,
    fuzzy_threshold: float = 0.85,
) -> None:
    """Public entry point — organise files, validate, then run pipeline.

    Parameters
    ----------
    strict : bool
        If ``True``, the pipeline aborts when any validation check fails.
        Default ``False`` — warnings are logged but processing continues
        for whichever sources *are* available.
    only : list[str] | None
        If provided, run **only** these loaders/mappers (by key name).
    skip : list[str] | None
        If provided, skip these loaders/mappers (by key name).
    validate_only : bool
        Run validation and exit without loading/mapping.
    no_organize : bool
        Skip Phase 0 (file organisation).
    clean : bool
        Delete the database before running (fresh start).
    auto_resolve : bool
        Automatically resolve conflicts after pipeline completes.
    resolve_limit : int | None
        Maximum number of conflicts to resolve (None = all).
    fuzzy_threshold : float
        Similarity threshold for fuzzy code matching (0.0-1.0).
    """
    # Phase -1: clean database if requested
    if clean:
        clean_db()

    # Phase 0: organise downloads → staging + archive
    if not no_organize:
        organize_data_files()

    # Phase 1: pre-flight validation
    results = validate_all_sources(strict=strict)
    failed = [r for r in results if not r.ok]
    if failed and not strict:
        logger.info(
            f"  ⚠ {len(failed)} validation warning(s) — "
            "pipeline will skip missing sources."
        )

    if validate_only:
        logger.info("Validation-only mode — exiting without loading data.")
        return

    # Build filtered pipeline
    pipeline = CodingPipeline()

    if only:
        only_set = {k.lower() for k in only}
        pipeline.loaders = [
            l for l in pipeline.loaders
            if type(l) in {LOADER_KEYS[k] for k in only_set if k in LOADER_KEYS}
        ]
        pipeline.direct_mappers = [
            m for m in pipeline.direct_mappers
            if type(m) in {MAPPER_KEYS[k] for k in only_set if k in MAPPER_KEYS}
        ]
        pipeline.derived_mappers = [
            m for m in pipeline.derived_mappers
            if type(m) in {MAPPER_KEYS[k] for k in only_set if k in MAPPER_KEYS}
        ]
    elif skip:
        skip_set = {k.lower() for k in skip}
        skip_classes = {ALL_KEYS[k] for k in skip_set if k in ALL_KEYS}
        pipeline.loaders = [l for l in pipeline.loaders if type(l) not in skip_classes]
        pipeline.direct_mappers = [m for m in pipeline.direct_mappers if type(m) not in skip_classes]
        pipeline.derived_mappers = [m for m in pipeline.derived_mappers if type(m) not in skip_classes]

    # Phase 2-4: load + map
    pipeline.run()
    
    # Phase 5 (optional): auto-resolve conflicts
    if auto_resolve:
        logger.info("")
        logger.info("="*60)
        logger.info("Phase 5: Auto-Resolving Conflicts")
        logger.info("="*60)
        
        from pipeline.conflict_resolvers import auto_resolve_conflicts
        
        try:
            stats = auto_resolve_conflicts(
                limit=resolve_limit,
                dry_run=False,
                fuzzy_threshold=fuzzy_threshold,
                create_placeholders=False,
            )
            
            logger.info(f"Conflict resolution complete:")
            logger.info(f"  - Processed: {stats['total_processed']}")
            logger.info(f"  - Resolved: {stats['resolved']}")
            logger.info(f"  - Ignored: {stats['ignored']}")
            logger.info(f"  - Unresolved: {stats['unresolved']}")
            
        except Exception as e:
            logger.error(f"Conflict resolution failed: {e}")
            if strict:
                raise


logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="CodeMx Data Processing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available keys for --only / --skip:
  Loaders:  snomed, icd10, hcc, cpt, hcpcs, rxnorm, ndc
  Mappers:  snomed-icd10, icd10-hcc, snomed-hcc, rxnorm-snomed

Examples:
  python -m pipeline.pipeline                        # full pipeline
  python -m pipeline.pipeline --only snomed icd10    # only SNOMED + ICD-10
  python -m pipeline.pipeline --skip rxnorm          # everything except RxNorm
  python -m pipeline.pipeline --validate             # validate sources only
  python -m pipeline.pipeline --only cpt --strict    # CPT only, abort on errors
  python -m pipeline.pipeline --clean                # delete DB + full reload
  python -m pipeline.pipeline --clean --only cpt     # delete DB + reload CPT only
  python -m pipeline.pipeline --auto-resolve         # auto-resolve conflicts after load
  python -m pipeline.pipeline --auto-resolve --resolve-limit 10000  # resolve up to 10K conflicts
  python -m pipeline.pipeline --auto-resolve --fuzzy-threshold 0.9  # stricter fuzzy matching
""",
    )
    parser.add_argument(
        "--auto-resolve", action="store_true",
        help="Automatically resolve mapping conflicts after pipeline completes",
    )
    parser.add_argument(
        "--resolve-limit", type=int, metavar="N",
        help="Maximum number of conflicts to resolve (default: all)",
    )
    parser.add_argument(
        "--fuzzy-threshold", type=float, default=0.85, metavar="0.0-1.0",
        help="Similarity threshold for fuzzy code matching (default: 0.85)",
    )
    parser.add_argument(
        "--only", nargs="+", metavar="KEY",
        help="Run only these loaders/mappers (space-separated keys)",
    )
    parser.add_argument(
        "--skip", nargs="+", metavar="KEY",
        help="Skip these loaders/mappers (space-separated keys)",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Abort pipeline if any validation check fails",
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Run validation only — do not load or map data",
    )
    parser.add_argument(
        "--no-organize", action="store_true",
        help="Skip file-organisation step (Phase 0)",
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="Delete the database before running (fresh start)",
    )
    parser.add_argument(
        "--list", action="store_true", dest="list_keys",
        help="List available loader/mapper keys and exit",
    )

    args = parser.parse_args()

    if args.list_keys:
        print("\nAvailable pipeline keys:")
        print("  Loaders:")
        for k in LOADER_KEYS:
            print(f"    {k}")
        print("  Mappers:")
        for k in MAPPER_KEYS:
            print(f"    {k}")
        raise SystemExit(0)

    if args.only and args.skip:
    # Validate fuzzy threshold
    if not 0.0 <= args.fuzzy_threshold <= 1.0:
        parser.error("--fuzzy-threshold must be between 0.0 and 1.0")
    
    run_pipeline(
        strict=args.strict,
        only=args.only,
        skip=args.skip,
        validate_only=args.validate,
        no_organize=args.no_organize,
        clean=args.clean,
        auto_resolve=args.auto_resolve,
        resolve_limit=args.resolve_limit,
        fuzzy_threshold=args.fuzzy_thresholder() not in ALL_KEYS:
                    parser.error(
                        f"Unknown key '{k}'. "
                        f"Valid keys: {', '.join(sorted(ALL_KEYS))}"
                    )

    run_pipeline(
        strict=args.strict,
        only=args.only,
        skip=args.skip,
        validate_only=args.validate,
        no_organize=args.no_organize,
        clean=args.clean,
    )
