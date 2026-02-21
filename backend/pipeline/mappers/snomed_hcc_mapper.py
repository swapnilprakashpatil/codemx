"""
SNOMED CT → HCC Mapper (transitive via ICD-10-CM)

Builds SNOMED→HCC mappings transitively:
  SNOMED → ICD-10 → HCC
using the already-populated ``snomed_icd10_mapping`` and ``icd10_hcc_mapping``
association tables.
"""

import logging
from typing import Dict, Set, Tuple

from pipeline.base import BaseMapper
from pipeline.helpers import BATCH_SIZE
from pipeline.models import (
    snomed_icd10_mapping, icd10_hcc_mapping, snomed_hcc_mapping,
)

logger = logging.getLogger(__name__)


class SnomedHccMapper(BaseMapper):
    mapping_name = "SNOMED → HCC (transitive)"

    def _build_from_source(self, session) -> int:
        count = 0

        # Step 1: build ICD-10 → HCC index
        icd10_to_hcc: Dict[str, list] = {}
        rows = session.execute(icd10_hcc_mapping.select()).fetchall()
        for r in rows:
            icd10_to_hcc.setdefault(r.icd10_code, []).append(r.hcc_code)
        logger.info(f"  ICD-10->HCC index: {len(icd10_to_hcc):,} ICD-10 codes map to HCC")

        # Step 2: iterate every SNOMED→ICD-10 mapping
        si_rows = session.execute(snomed_icd10_mapping.select()).fetchall()
        logger.info(f"  Processing {len(si_rows):,} SNOMED->ICD-10 mappings...")

        seen: Set[Tuple[str, str]] = set()
        batch = []

        for si_row in si_rows:
            snomed_code = si_row.snomed_code
            icd10_code = si_row.icd10_code

            for hcc_code in icd10_to_hcc.get(icd10_code, []):
                pair = (snomed_code, hcc_code)
                if pair in seen:
                    continue
                seen.add(pair)

                batch.append({
                    "snomed_code": snomed_code,
                    "hcc_code": hcc_code,
                    "via_icd10_code": icd10_code,
                    "active": True,
                })

                if len(batch) >= BATCH_SIZE:
                    session.execute(snomed_hcc_mapping.insert(), batch)
                    session.flush()
                    count += len(batch)
                    batch.clear()

        if batch:
            session.execute(snomed_hcc_mapping.insert(), batch)
            session.flush()
            count += len(batch)

        return count
