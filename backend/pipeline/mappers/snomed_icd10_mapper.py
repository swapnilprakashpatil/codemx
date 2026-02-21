"""
SNOMED CT → ICD-10-CM Mapper

Parses the ExtendedMap refset from the SNOMED CT US-edition ZIP to build
SNOMED-to-ICD-10-CM mappings with map group, priority, rule, and advice.
Records mapping conflicts when source or target codes are missing.
"""

import io
import logging
from typing import Set, Tuple

from pipeline.base import BaseMapper
from pipeline.helpers import (
    find_zip, find_zip_entry, flush_conflicts, format_icd10_code, BATCH_SIZE,
)
from pipeline.models import (
    SnomedCode, ICD10Code, MappingConflict, snomed_icd10_mapping,
)

logger = logging.getLogger(__name__)

SNOMED_ZIP_PATTERN = "SnomedCT_ManagedServiceUS_PRODUCTION"
ICD10CM_MAP_REFSET_ID = "6011000124106"


class SnomedIcd10Mapper(BaseMapper):
    mapping_name = "SNOMED → ICD-10-CM"

    # ── Primary source ────────────────────────────────────────────────────

    def _build_from_source(self, session) -> int:
        snomed_zip = find_zip(SNOMED_ZIP_PATTERN)
        if not snomed_zip:
            return 0
        return self._parse_extended_map(session, snomed_zip)

    def _parse_extended_map(self, session, zip_path: str) -> int:
        count = 0

        # Pre-load valid code sets
        logger.info("  Pre-loading valid SNOMED and ICD-10 code sets...")
        valid_snomed: Set[str] = {r[0] for r in session.query(SnomedCode.code).all()}
        valid_icd10: Set[str] = {r[0] for r in session.query(ICD10Code.code).all()}
        logger.info(f"  Valid SNOMED: {len(valid_snomed):,}, Valid ICD-10: {len(valid_icd10):,}")

        import zipfile
        with zipfile.ZipFile(zip_path, "r") as zf:
            emap_entry = find_zip_entry(zf, "Snapshot", "Refset", "Map", "ExtendedMap")
            if not emap_entry:
                logger.error("  ExtendedMap file not found in SNOMED zip")
                return 0

            logger.info("  Reading ExtendedMap refset...")
            batch = []
            conflict_batch = []
            seen_pairs: Set[Tuple[str, str]] = set()
            seen_conflicts: Set[Tuple[str, str]] = set()

            with zf.open(emap_entry) as f:
                reader = io.TextIOWrapper(f, "utf-8")
                next(reader)  # skip header

                for line in reader:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) < 13:
                        continue

                    active = parts[2]
                    refset_id = parts[4]
                    snomed_code = parts[5]
                    map_group = parts[6]
                    map_priority = parts[7]
                    map_rule = parts[8]
                    map_advice = parts[9]
                    map_target = parts[10].strip()
                    correlation_id = parts[11]
                    map_category_id = parts[12]

                    if active != "1" or refset_id != ICD10CM_MAP_REFSET_ID:
                        continue
                    if not map_target:
                        continue

                    icd10_formatted = format_icd10_code(map_target)

                    # Validate both ends exist
                    if snomed_code not in valid_snomed:
                        conflict_batch.append(MappingConflict(
                            source_system="SNOMED",
                            target_system="ICD-10",
                            source_code=snomed_code,
                            target_code=icd10_formatted,
                            reason="source_not_found",
                            details=f"SNOMED code not in database. map_rule: {map_rule[:200]}",
                        ))
                        continue
                    if icd10_formatted not in valid_icd10:
                        conflict_batch.append(MappingConflict(
                            source_system="SNOMED",
                            target_system="ICD-10",
                            source_code=snomed_code,
                            target_code=icd10_formatted,
                            reason="target_not_found",
                            details=f"ICD-10 code '{icd10_formatted}' not in database. map_advice: {map_advice[:200]}",
                        ))
                        continue

                    pair = (snomed_code, icd10_formatted)
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)

                    batch.append({
                        "snomed_code": snomed_code,
                        "icd10_code": icd10_formatted,
                        "map_group": int(map_group) if map_group.isdigit() else 1,
                        "map_priority": int(map_priority) if map_priority.isdigit() else 1,
                        "map_rule": (map_rule or "")[:255],
                        "map_advice": (map_advice or "")[:500],
                        "correlation_id": correlation_id or "",
                        "map_category_id": map_category_id or "",
                        "active": True,
                        "effective_date": parts[1],
                    })

                    if len(batch) >= BATCH_SIZE:
                        session.execute(snomed_icd10_mapping.insert(), batch)
                        session.flush()
                        count += len(batch)
                        batch.clear()
                        if count % 20000 == 0:
                            logger.info(f"    ... inserted {count:,} SNOMED->ICD-10 mappings")

                    if len(conflict_batch) >= BATCH_SIZE:
                        flush_conflicts(session, conflict_batch, seen_conflicts)
                        conflict_batch.clear()

            if batch:
                session.execute(snomed_icd10_mapping.insert(), batch)
                session.flush()
                count += len(batch)

            if conflict_batch:
                flush_conflicts(session, conflict_batch, seen_conflicts)
            if seen_conflicts:
                logger.info(f"  Captured {len(seen_conflicts):,} SNOMED->ICD-10 mapping conflicts")

        logger.info(f"  Inserted {count:,} SNOMED->ICD-10-CM mappings from ExtendedMap")
        return count


