"""
Shared helpers for the data processing pipeline.

Provides file discovery, bulk-insert, conflict-tracking, and
data-directory organisation utilities used across all loaders and mappers.
"""

import os
import shutil
import zipfile
import logging
from typing import Optional, Set, Tuple

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
STAGING_DIR = os.path.join(DATA_DIR, "staging")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")
DOWNLOAD_DIR = os.path.join(DATA_DIR, "downloads")   # legacy – used by organize_data_files

BATCH_SIZE = 5000

# Staging sub-directory names
STAGING_SUBDIRS = ["snomed", "icd10cm", "hcc", "cpt", "hcpcs", "rxnorm", "ndc"]

# Map from zip-file keyword → staging subdirectory (used during initial move
# from downloads/).  Files are later filtered by _STAGING_KEEP_RULES.
_ZIP_STAGING_MAP = {
    "SnomedCT_ManagedServiceUS_PRODUCTION": "snomed",
    "RxNorm_full":                          "rxnorm",
    "dhs_code_list":                        "cpt",
    "icd-10-cm-mappings":                   "hcc",
    "initial-model-software":               "hcc",
    "midyear-final-icd-10-mappings":        "hcc",
    "code-descriptions-tabular-order":      "icd10cm",
    "alpha-numeric-hcpcs-file":             "hcpcs",
    "ndctext":                              "ndc",
}

# ── Per-directory keep rules ──────────────────────────────────────────────────
# A file stays in staging ONLY if the rule returns True.
# Everything else is moved to archive.  Rules mirror exactly what loaders read.

def _keep_snomed(f: str) -> bool:
    """SnomedLoader reads the SNOMED US-edition ZIP directly."""
    return f.endswith(".zip") and "SnomedCT" in f

def _keep_icd10cm(f: str) -> bool:
    """ICD10Loader reads *order*.txt (excluding addenda)."""
    return (f.lower().endswith(".txt")
            and "order" in f.lower()
            and "addenda" not in f.lower())

def _keep_hcc(f: str) -> bool:
    """HCCLoader + Icd10HccMapper read *.csv with 'Mappings' in the name."""
    return f.endswith(".csv") and "Mappings" in f

def _keep_cpt(f: str) -> bool:
    """CPTLoader reads the DHS Code List ZIP directly."""
    return f.endswith(".zip") and "dhs_code_list" in f.lower()

def _keep_hcpcs(f: str) -> bool:
    """HCPCSLoader reads the CMS ANWEB fixed-width .txt file."""
    return "ANWEB" in f.upper() and f.endswith(".txt")

def _keep_rxnorm(f: str) -> bool:
    """RxNormLoader reads the RxNorm full-release ZIP directly."""
    return f.endswith(".zip") and "RxNorm_full" in f

def _keep_ndc(f: str) -> bool:
    """NDCLoader reads the ndctext.zip file directly."""
    return f.endswith(".zip") and "ndctext" in f.lower()

_STAGING_KEEP_RULES = {
    "snomed":  _keep_snomed,
    "icd10cm": _keep_icd10cm,
    "hcc":     _keep_hcc,
    "cpt":     _keep_cpt,
    "hcpcs":   _keep_hcpcs,
    "rxnorm":  _keep_rxnorm,
    "ndc":     _keep_ndc,
}


# ──────────────────────────────────────────────────────────────────────────────
#  Data-directory organisation
# ──────────────────────────────────────────────────────────────────────────────

def organize_data_files() -> None:
    """Reorganise *downloads* → *staging* + *archive*, then prune staging.

    Phase 1 – Move from downloads/:
      * Extracted sub-directories (icd10cm, hcc, cpt, …) → staging/<type>/
      * ZIP files matched by keyword → staging/<type>/
      * Everything else → archive/

    Phase 2 – Prune staging/:
      * Each staging sub-directory is filtered by ``_STAGING_KEEP_RULES``.
      * Only files the pipeline actually ingests remain; the rest are
        moved to archive/ so staging stays clean.
    """
    # Create directories
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    for sub in STAGING_SUBDIRS:
        os.makedirs(os.path.join(STAGING_DIR, sub), exist_ok=True)

    # ── Phase 1: move from downloads/ ─────────────────────────────────────
    if os.path.isdir(DOWNLOAD_DIR):
        # Move extracted sub-directories
        for subdir in STAGING_SUBDIRS:
            src_dir = os.path.join(DOWNLOAD_DIR, subdir)
            dst_dir = os.path.join(STAGING_DIR, subdir)
            if os.path.isdir(src_dir):
                for fname in os.listdir(src_dir):
                    src = os.path.join(src_dir, fname)
                    dst = os.path.join(dst_dir, fname)
                    if not os.path.exists(dst):
                        shutil.move(src, dst)
                        logger.info(f"  staging/{subdir}/{fname}")
                if not os.listdir(src_dir):
                    os.rmdir(src_dir)

        # Move remaining files (ZIPs → staging or archive, others → archive)
        for fname in os.listdir(DOWNLOAD_DIR):
            fpath = os.path.join(DOWNLOAD_DIR, fname)
            if os.path.isdir(fpath):
                continue

            if fname.endswith(".zip"):
                placed = False
                for keyword, subdir in _ZIP_STAGING_MAP.items():
                    if keyword.lower() in fname.lower():
                        dst = os.path.join(STAGING_DIR, subdir, fname)
                        if not os.path.exists(dst):
                            shutil.move(fpath, dst)
                            logger.info(f"  staging/{subdir}/{fname}")
                        placed = True
                        break
                if not placed:
                    _archive_file(fpath, fname)
            else:
                _archive_file(fpath, fname)

        if os.path.isdir(DOWNLOAD_DIR) and not os.listdir(DOWNLOAD_DIR):
            os.rmdir(DOWNLOAD_DIR)
            logger.info("  Removed empty downloads/ directory")

    # ── Phase 2: prune staging (keep only ingested files) ─────────────────
    _prune_staging()

    logger.info("Data files organised into staging/ and archive/.")


def _archive_file(src: str, fname: str) -> None:
    """Move a single file to ARCHIVE_DIR."""
    dst = os.path.join(ARCHIVE_DIR, fname)
    if not os.path.exists(dst):
        shutil.move(src, dst)
        logger.info(f"  archive/{fname}")


def _prune_staging() -> None:
    """Move non-ingested files out of staging sub-directories into archive."""
    for subdir, keep_fn in _STAGING_KEEP_RULES.items():
        sub_path = os.path.join(STAGING_DIR, subdir)
        if not os.path.isdir(sub_path):
            continue

        for fname in os.listdir(sub_path):
            fpath = os.path.join(sub_path, fname)
            if os.path.isdir(fpath):
                continue
            if not keep_fn(fname):
                # Archive into a sub-folder to avoid name collisions
                archive_sub = os.path.join(ARCHIVE_DIR, subdir)
                os.makedirs(archive_sub, exist_ok=True)
                dst = os.path.join(archive_sub, fname)
                if not os.path.exists(dst):
                    shutil.move(fpath, dst)
                    logger.info(f"  archive/{subdir}/{fname}")


# ──────────────────────────────────────────────────────────────────────────────
#  File helpers
# ──────────────────────────────────────────────────────────────────────────────

def find_zip(pattern: str) -> Optional[str]:
    """Find a zip file under STAGING_DIR (recursively) matching *pattern*."""
    if not os.path.isdir(STAGING_DIR):
        return None
    for root, _dirs, files in os.walk(STAGING_DIR):
        for fname in files:
            if pattern in fname and fname.endswith(".zip"):
                return os.path.join(root, fname)
    return None


def find_zip_entry(zf: zipfile.ZipFile, *keywords: str) -> Optional[str]:
    """Find a zip entry whose path contains ALL specified keywords."""
    for name in zf.namelist():
        if all(kw in name for kw in keywords):
            return name
    return None


# ──────────────────────────────────────────────────────────────────────────────
#  Database helpers
# ──────────────────────────────────────────────────────────────────────────────

def bulk_insert_ignore(session, model_class, objects: list) -> int:
    """Insert ORM objects, silently skipping duplicates (SQLite OR IGNORE)."""
    if not objects:
        return 0
    table = model_class.__table__
    data = []
    for obj in objects:
        row = {}
        for col in table.columns:
            val = getattr(obj, col.key, None)
            if val is None and col.default is not None:
                val = col.default.arg if not callable(col.default.arg) else col.default.arg(None)
            row[col.key] = val
        data.append(row)
    stmt = table.insert().prefix_with("OR IGNORE")
    session.execute(stmt, data)
    session.flush()
    return len(data)


def flush_conflicts(
    session,
    conflict_batch: list,
    seen_conflicts: Set[Tuple[str, str]],
) -> int:
    """Deduplicate and insert mapping conflicts into DB."""
    added = 0
    for c in conflict_batch:
        key = (c.source_code, c.target_code or "")
        if key in seen_conflicts:
            continue
        seen_conflicts.add(key)
        session.add(c)
        added += 1
    if added:
        session.flush()
    return added


def format_icd10_code(code: str) -> str:
    """Format ICD-10-CM code with decimal point after the 3rd character.

    Standard ICD-10-CM format: 3-character category + '.' + remaining chars.
    E.g. 'A000' -> 'A00.0', 'E1165' -> 'E11.65', 'M7931' -> 'M79.31'.
    3-character category codes (headers like 'A00') are returned as-is.
    """
    code = code.strip().replace(".", "")
    if len(code) > 3:
        return code[:3] + "." + code[3:]
    return code
