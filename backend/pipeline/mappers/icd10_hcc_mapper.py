"""
ICD-10-CM → HCC Mapper

Parses the CMS ICD-10-CM to HCC Mappings CSV (V28) and inserts rows into
``icd10_hcc_mapping``.  Records mapping conflicts for missing codes.
"""

import csv
import os
import logging
from typing import Set, Tuple

from pipeline.base import BaseMapper
from pipeline.helpers import (
    flush_conflicts, format_icd10_code, STAGING_DIR, BATCH_SIZE,
)
from pipeline.models import (
    ICD10Code, HCCCode, MappingConflict, icd10_hcc_mapping,
)

logger = logging.getLogger(__name__)


class Icd10HccMapper(BaseMapper):
    mapping_name = "ICD-10-CM → HCC"

    # ── Primary source ────────────────────────────────────────────────────

    def _build_from_source(self, session) -> int:
        hcc_dir = os.path.join(STAGING_DIR, "hcc")
        if not os.path.isdir(hcc_dir):
            return 0

        csv_files = [
            f for f in os.listdir(hcc_dir)
            if f.lower().endswith(".csv")
            and "icd-10" in f.lower()
            and "mapping" in f.lower()
        ]
        csv_files.sort(key=lambda x: (0 if "final" in x.lower() else 1, x))

        for csv_file in csv_files:
            filepath = os.path.join(hcc_dir, csv_file)
            logger.info(f"  Loading ICD-10->HCC mappings from: {csv_file}")
            try:
                count = self._parse_csv(session, filepath)
                if count > 0:
                    return count
            except Exception as e:
                logger.warning(f"  Error parsing {csv_file}: {e}")
        return 0

    def _parse_csv(self, session, filepath: str) -> int:
        count = 0
        valid_icd10 = {r[0] for r in session.query(ICD10Code.code).all()}
        valid_hcc = {r[0] for r in session.query(HCCCode.code).all()}

        batch = []
        conflict_batch = []
        seen_conflicts: Set[Tuple[str, str]] = set()

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header_found = False
            for row in reader:
                if not header_found:
                    if row and "Diagnosis" in str(row[0]):
                        header_found = True
                    continue
                if len(row) < 7 or not row[0].strip():
                    continue
                icd10_code = format_icd10_code(row[0].strip())
                hcc_v28 = row[6].strip() if len(row) > 6 else ""

                if not (hcc_v28 and hcc_v28.isdigit()):
                    continue
                hcc_code = f"HCC{hcc_v28}"

                icd_missing = icd10_code not in valid_icd10
                hcc_missing = hcc_code not in valid_hcc
                if icd_missing or hcc_missing:
                    desc = row[1].strip() if len(row) > 1 else ""
                    if icd_missing:
                        conflict_batch.append(MappingConflict(
                            source_system="ICD-10",
                            target_system="HCC",
                            source_code=icd10_code,
                            target_code=hcc_code,
                            source_description=desc[:500] if desc else None,
                            reason="source_not_found",
                            details=f"ICD-10 code '{icd10_code}' not in database",
                        ))
                    elif hcc_missing:
                        conflict_batch.append(MappingConflict(
                            source_system="ICD-10",
                            target_system="HCC",
                            source_code=icd10_code,
                            target_code=hcc_code,
                            source_description=desc[:500] if desc else None,
                            reason="target_not_found",
                            details=f"HCC code '{hcc_code}' not in database",
                        ))
                    if len(conflict_batch) >= BATCH_SIZE:
                        flush_conflicts(session, conflict_batch, seen_conflicts)
                        conflict_batch.clear()
                    continue

                batch.append({
                    "icd10_code": icd10_code,
                    "hcc_code": hcc_code,
                    "payment_year": 2026,
                    "model_version": "V28",
                    "active": True,
                })

                if len(batch) >= BATCH_SIZE:
                    session.execute(icd10_hcc_mapping.insert(), batch)
                    session.flush()
                    count += len(batch)
                    batch.clear()

        if batch:
            session.execute(icd10_hcc_mapping.insert(), batch)
            session.flush()
            count += len(batch)

        if conflict_batch:
            flush_conflicts(session, conflict_batch, seen_conflicts)
        if seen_conflicts:
            logger.info(f"  Captured {len(seen_conflicts):,} ICD-10->HCC mapping conflicts")

        logger.info(f"  Parsed {count:,} ICD-10->HCC V28 mappings from CMS CSV")
        return count


