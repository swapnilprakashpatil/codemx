"""
Export database contents to static JSON files for GitHub Pages deployment.

Generates a complete static data layer that mirrors the Flask API responses,
enabling the Angular frontend to run without a backend server.

Usage:
    cd backend
    python -m pipeline.export_json [--output DIR] [--per-page N]
"""

import json
import math
import os
import sys
import time
from collections import defaultdict

# Ensure parent path is available
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.models import (
    init_db, get_session, SnomedCode, ICD10Code, HCCCode, CPTCode,
    HCPCSCode, RxNormCode, NDCCode, MappingConflict,
    snomed_icd10_mapping, snomed_hcc_mapping, icd10_hcc_mapping,
    snomed_cpt_mapping, snomed_hcpcs_mapping, rxnorm_snomed_mapping,
)
from api.services import CodingService, MappingService, ConflictService

# ─── Configuration ────────────────────────────────────────────────────────────

DEFAULT_OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend", "public", "data",
)
PER_PAGE = 50
DETAIL_BATCH = 500  # Commit progress every N detail records


# ─── Helpers ──────────────────────────────────────────────────────────────────

def write_json(base_dir: str, rel_path: str, data: dict | list) -> None:
    """Write data as JSON to base_dir/rel_path, creating directories as needed."""
    full = os.path.join(base_dir, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)


def progress(msg: str) -> None:
    print(f"  {msg}")


def elapsed(start: float) -> str:
    s = time.time() - start
    return f"{s:.1f}s"


# ─── Export Functions ─────────────────────────────────────────────────────────

def export_stats(out: str, session) -> None:
    """Export /api/stats → stats.json"""
    t = time.time()
    stats = CodingService.get_stats()
    write_json(out, "stats.json", stats)
    progress(f"stats.json ({elapsed(t)})")


def export_resources(out: str) -> None:
    """Export /api/resources → resources.json"""
    t = time.time()
    resources = CodingService.get_resources()
    write_json(out, "resources.json", resources)
    progress(f"resources.json ({elapsed(t)})")


def export_code_list(out: str, type_name: str, list_func, per_page: int = PER_PAGE) -> int:
    """
    Export paginated list files: {type}/list/{page}.json
    Returns total record count.
    """
    t = time.time()
    page = 1
    total = 0
    while True:
        result = list_func(page=page, per_page=per_page, q="")
        write_json(out, f"{type_name}/list/{page}.json", result)
        total = result["total"]
        pages = result["pages"]
        if page >= pages:
            break
        page += 1
    progress(f"{type_name}/list/ — {page} pages, {total} records ({elapsed(t)})")
    return total


def export_code_details(
    out: str, type_name: str, model_cls, detail_func, session
) -> None:
    """
    Export detail data bundled by 2-char code prefix:
      {type}/detail/{prefix}.json → { "code1": {...}, "code2": {...} }
    """
    t = time.time()
    codes = (
        session.query(model_cls.code)
        .filter(model_cls.active == True)
        .order_by(model_cls.code)
        .all()
    )
    code_list = [c[0] for c in codes]

    # Group by prefix
    prefix_groups: dict[str, list[str]] = defaultdict(list)
    for code in code_list:
        prefix = code[:2].upper() if len(code) >= 2 else code.upper()
        prefix_groups[prefix].append(code)

    exported = 0
    for prefix, group_codes in prefix_groups.items():
        bundle: dict[str, dict] = {}
        for code in group_codes:
            try:
                detail = detail_func(code)
                if detail:
                    bundle[code] = detail
            except Exception:
                pass  # Skip codes that fail
            exported += 1
            if exported % DETAIL_BATCH == 0:
                print(f"\r    {type_name} details: {exported}/{len(code_list)}", end="", flush=True)

        if bundle:
            write_json(out, f"{type_name}/detail/{prefix}.json", bundle)

    print(f"\r    {type_name} details: {exported}/{len(code_list)}")
    progress(f"{type_name}/detail/ — {len(prefix_groups)} bundles ({elapsed(t)})")


def export_small_details(
    out: str, type_name: str, model_cls, detail_func, session
) -> None:
    """
    For small datasets (HCC, CPT), export all details in a single file:
      {type}/detail/all.json → { "code1": {...}, "code2": {...} }
    """
    t = time.time()
    codes = (
        session.query(model_cls.code)
        .filter(model_cls.active == True)
        .order_by(model_cls.code)
        .all()
    )
    bundle: dict[str, dict] = {}
    for (code,) in codes:
        try:
            detail = detail_func(code)
            if detail:
                bundle[code] = detail
        except Exception:
            pass
    write_json(out, f"{type_name}/detail/all.json", bundle)
    progress(f"{type_name}/detail/all.json — {len(bundle)} codes ({elapsed(t)})")


def export_icd10_hierarchy(out: str) -> None:
    """Export ICD-10 hierarchy and per-category children."""
    t = time.time()
    # Full hierarchy (all letters)
    hierarchy = CodingService.list_icd10_hierarchy("", "")
    write_json(out, "icd10/hierarchy.json", hierarchy)

    # Per-letter hierarchy
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        h = CodingService.list_icd10_hierarchy(letter, "")
        if h.get("chapters"):
            write_json(out, f"icd10/hierarchy/letter-{letter}.json", h)

    # Category children
    cat_count = 0
    for chapter in hierarchy.get("chapters", []):
        for cat in chapter.get("categories", []):
            code = cat["code"]
            children = CodingService.get_icd10_category_children(code)
            write_json(out, f"icd10/hierarchy/children/{code}.json", children)
            cat_count += 1

    progress(f"icd10/hierarchy — {cat_count} categories ({elapsed(t)})")


def export_directional_mappings(out: str, session) -> None:
    """Export directional mapping endpoints bundled by source code prefix."""
    t = time.time()

    # SNOMED → ICD-10
    snomed_codes_with_icd10 = (
        session.query(snomed_icd10_mapping.c.snomed_code)
        .distinct()
        .all()
    )
    bundles: dict[str, dict] = defaultdict(dict)
    for (code,) in snomed_codes_with_icd10:
        prefix = code[:2]
        result = MappingService.snomed_to_icd10(code)
        bundles[prefix][code] = result
    for prefix, data in bundles.items():
        write_json(out, f"mappings/snomed-to-icd10/{prefix}.json", data)
    progress(f"mappings/snomed-to-icd10/ — {len(bundles)} bundles ({elapsed(t)})")

    # SNOMED → HCC
    t2 = time.time()
    snomed_codes_with_hcc = (
        session.query(snomed_hcc_mapping.c.snomed_code)
        .distinct()
        .all()
    )
    bundles = defaultdict(dict)
    for (code,) in snomed_codes_with_hcc:
        prefix = code[:2]
        result = MappingService.snomed_to_hcc(code)
        bundles[prefix][code] = result
    for prefix, data in bundles.items():
        write_json(out, f"mappings/snomed-to-hcc/{prefix}.json", data)
    progress(f"mappings/snomed-to-hcc/ — {len(bundles)} bundles ({elapsed(t2)})")

    # ICD-10 → HCC
    t3 = time.time()
    icd10_codes_with_hcc = (
        session.query(icd10_hcc_mapping.c.icd10_code)
        .distinct()
        .all()
    )
    bundles = defaultdict(dict)
    for (code,) in icd10_codes_with_hcc:
        prefix = code[:1].upper()
        result = MappingService.icd10_to_hcc(code)
        bundles[prefix][code] = result
    for prefix, data in bundles.items():
        write_json(out, f"mappings/icd10-to-hcc/{prefix}.json", data)
    progress(f"mappings/icd10-to-hcc/ — {len(bundles)} bundles ({elapsed(t3)})")

    # RxNorm → SNOMED
    t4 = time.time()
    rxnorm_codes_with_snomed = (
        session.query(rxnorm_snomed_mapping.c.rxnorm_code)
        .distinct()
        .all()
    )
    bundles = defaultdict(dict)
    for (code,) in rxnorm_codes_with_snomed:
        prefix = code[:2]
        result = MappingService.rxnorm_to_snomed(code)
        bundles[prefix][code] = result
    for prefix, data in bundles.items():
        write_json(out, f"mappings/rxnorm-to-snomed/{prefix}.json", data)
    progress(f"mappings/rxnorm-to-snomed/ — {len(bundles)} bundles ({elapsed(t4)})")


def export_search_index(out: str, session) -> None:
    """
    Build a compact search index for client-side search/autocomplete.
    Format: array of [code, description_truncated, type_abbreviation]
    Type abbreviations: S=SNOMED, I=ICD-10, H=HCC, C=CPT, P=HCPCS, R=RxNorm
    """
    t = time.time()
    index = []
    abbrevs = {
        SnomedCode: "S", ICD10Code: "I", HCCCode: "H",
        CPTCode: "C", HCPCSCode: "P", RxNormCode: "R", NDCCode: "N",
    }
    desc_fields = {
        SnomedCode: "description", ICD10Code: "description",
        HCCCode: "description", CPTCode: "short_description",
        HCPCSCode: "short_description", RxNormCode: "name", NDCCode: "product_name",
    }

    for model, abbr in abbrevs.items():
        desc_attr = getattr(model, desc_fields[model])
        rows = (
            session.query(model.code, desc_attr)
            .filter(model.active == True)
            .all()
        )
        for code, desc in rows:
            index.append([code, (desc or "")[:80], abbr])

    write_json(out, "search-index.json", index)
    progress(f"search-index.json — {len(index)} entries ({elapsed(t)})")


def export_conflicts(out: str, session) -> None:
    """Export conflicts list (paginated) and stats."""
    t = time.time()

    # Stats
    stats = ConflictService.get_stats()
    write_json(out, "conflicts/stats.json", stats)

    # Paginated list
    page = 1
    total = 0
    while True:
        result = ConflictService.list_conflicts(page=page, per_page=PER_PAGE)
        write_json(out, f"conflicts/list/{page}.json", result)
        total = result["total"]
        pages = result["pages"]
        if page >= pages or pages == 0:
            break
        page += 1

    # Individual details
    conflicts = session.query(MappingConflict).all()
    for c in conflicts:
        write_json(out, f"conflicts/detail/{c.id}.json", c.to_dict())

    progress(f"conflicts/ — {total} conflicts, {page} pages ({elapsed(t)})")


def export_mapping_graph_samples(out: str, session) -> None:
    """
    Pre-compute mapping graphs for codes that have mappings.
    Bundles by code prefix: graph/{prefix}.json → { code: graphData }
    Only processes codes with SNOMED/ICD-10/HCC entries (reasonable scope).
    """
    t = time.time()

    # Get HCC codes (small set, good roots)
    hcc_codes = session.query(HCCCode.code).filter(HCCCode.active == True).all()
    bundles: dict[str, dict] = defaultdict(dict)

    for (code,) in hcc_codes:
        try:
            graph = MappingService.get_mapping_graph(code)
            if graph and graph.get("nodes"):
                prefix = code[:2] if len(code) >= 2 else code
                bundles[prefix][code] = graph
        except Exception:
            pass

    # Get a sample of ICD-10 codes with HCC mappings
    icd10_with_hcc = (
        session.query(icd10_hcc_mapping.c.icd10_code)
        .distinct()
        .limit(500)
        .all()
    )
    for (code,) in icd10_with_hcc:
        try:
            graph = MappingService.get_mapping_graph(code)
            if graph and graph.get("nodes"):
                prefix = code[:1].upper()
                bundles[prefix][code] = graph
        except Exception:
            pass

    for prefix, data in bundles.items():
        write_json(out, f"graph/{prefix}.json", data)
    progress(f"graph/ — {sum(len(v) for v in bundles.values())} graphs ({elapsed(t)})")


# ─── Main ─────────────────────────────────────────────────────────────────────

def run_export(output_dir: str = DEFAULT_OUTPUT, per_page: int = PER_PAGE) -> None:
    """Run the full JSON export pipeline."""
    global PER_PAGE
    PER_PAGE = per_page

    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║   CodeMx - Static JSON Export            ║")
    print("  ╚══════════════════════════════════════════╝")
    print()
    print(f"  Output: {output_dir}")
    print(f"  Per-page: {per_page}")
    print()

    init_db()
    session = get_session()

    total_start = time.time()

    try:
        # ── Simple exports ────────────────────────────────────────
        export_stats(output_dir, session)
        export_resources(output_dir)

        # ── Code lists (paginated) ───────────────────────────────
        export_code_list(output_dir, "snomed", CodingService.list_snomed, per_page)
        export_code_list(output_dir, "icd10", CodingService.list_icd10, per_page)
        export_code_list(output_dir, "hcc", CodingService.list_hcc, per_page)
        export_code_list(output_dir, "cpt", CodingService.list_cpt, per_page)
        export_code_list(output_dir, "hcpcs", CodingService.list_hcpcs, per_page)
        export_code_list(output_dir, "rxnorm", CodingService.list_rxnorm, per_page)

        # ── Code details (with mappings) ─────────────────────────
        export_small_details(output_dir, "hcc", HCCCode, MappingService.get_hcc_detail, session)
        export_small_details(output_dir, "cpt", CPTCode, MappingService.get_cpt_detail, session)
        export_code_details(output_dir, "hcpcs", HCPCSCode, MappingService.get_hcpcs_detail, session)
        export_code_details(output_dir, "icd10", ICD10Code, MappingService.get_icd10_detail, session)
        export_code_details(output_dir, "snomed", SnomedCode, MappingService.get_snomed_detail, session)
        export_code_details(output_dir, "rxnorm", RxNormCode, MappingService.get_rxnorm_detail, session)
        export_code_details(output_dir, "ndc", NDCCode, MappingService.get_ndc_detail, session)

        # ── ICD-10 hierarchy ─────────────────────────────────────
        export_icd10_hierarchy(output_dir)

        # ── Directional mappings ─────────────────────────────────
        export_directional_mappings(output_dir, session)

        # ── Mapping graphs (sample) ──────────────────────────────
        export_mapping_graph_samples(output_dir, session)

        # ── Search index ─────────────────────────────────────────
        export_search_index(output_dir, session)

        # ── Conflicts ────────────────────────────────────────────
        export_conflicts(output_dir, session)

    finally:
        session.close()

    print()
    print(f"  ✓ Export completed in {elapsed(total_start)}")
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Export CodeMx database to static JSON files"
    )
    parser.add_argument(
        "--output", "-o", default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--per-page", type=int, default=PER_PAGE,
        help=f"Records per page for list exports (default: {PER_PAGE})",
    )
    args = parser.parse_args()
    run_export(args.output, args.per_page)
