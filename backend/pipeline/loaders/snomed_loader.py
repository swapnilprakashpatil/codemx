"""
SNOMED CT Loader

Reads the SNOMED CT US-edition release ZIP (Concept + Description snapshots)
and inserts active concepts with FSN, preferred term, semantic tag,
module_id, and effective_date.
"""

import io
import re
import zipfile
import logging
from typing import Dict, Set, Tuple

from pipeline.base import BaseLoader
from pipeline.helpers import (
    find_zip, find_zip_entry, bulk_insert_ignore, BATCH_SIZE,
)
from pipeline.models import SnomedCode

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
SNOMED_ZIP_PATTERN = "SnomedCT_ManagedServiceUS_PRODUCTION"
FSN_TYPE_ID = "900000000000003001"
SYN_TYPE_ID = "900000000000013009"


class SnomedLoader(BaseLoader):
    system_name = "SNOMED CT"
    model_class = SnomedCode

    # ── Primary source ────────────────────────────────────────────────────

    def _load_from_source(self, session) -> int:
        zip_path = find_zip(SNOMED_ZIP_PATTERN)
        if not zip_path:
            return 0
        return self._parse_zip(session, zip_path)

    def _parse_zip(self, session, zip_path: str) -> int:
        logger.info(f"  Reading SNOMED CT from: {zip_path}")
        count = 0

        with zipfile.ZipFile(zip_path, "r") as zf:
            concept_entry = find_zip_entry(zf, "Snapshot", "Terminology", "sct2_Concept_Snapshot")
            desc_entry = find_zip_entry(zf, "Snapshot", "Terminology", "sct2_Description_Snapshot")

            if not concept_entry or not desc_entry:
                logger.error("  Could not find Concept or Description Snapshot files in SNOMED zip")
                return 0

            # Step 1 – active concept IDs
            logger.info("  Reading active concept IDs...")
            active_ids: Set[str] = set()
            with zf.open(concept_entry) as f:
                reader = io.TextIOWrapper(f, "utf-8")
                next(reader)
                for line in reader:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) >= 3 and parts[2] == "1":
                        active_ids.add(parts[0])
            logger.info(f"  Active concepts: {len(active_ids):,}")

            # Step 2 – descriptions (FSN + preferred synonym)
            logger.info("  Reading descriptions...")
            desc_map: Dict[str, Dict[str, str]] = {}
            with zf.open(desc_entry) as f:
                reader = io.TextIOWrapper(f, "utf-8")
                next(reader)
                for line in reader:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) < 8 or parts[2] != "1":
                        continue
                    concept_id = parts[4]
                    if concept_id not in active_ids:
                        continue
                    if parts[5] != "en":
                        continue
                    type_id = parts[6]
                    term = parts[7]

                    if concept_id not in desc_map:
                        desc_map[concept_id] = {}

                    if type_id == FSN_TYPE_ID:
                        desc_map[concept_id]["fsn"] = term
                    elif type_id == SYN_TYPE_ID:
                        if "pt" not in desc_map[concept_id]:
                            desc_map[concept_id]["pt"] = term
            logger.info(f"  Descriptions collected for {len(desc_map):,} concepts")

            # Step 2b – module_id + effective_date
            logger.info("  Re-reading concept file for module_id and effective_date...")
            concept_meta: Dict[str, Tuple[str, str]] = {}
            with zf.open(concept_entry) as f:
                reader = io.TextIOWrapper(f, "utf-8")
                next(reader)
                for line in reader:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) >= 4 and parts[2] == "1":
                        concept_meta[parts[0]] = (parts[1], parts[3])
            logger.info(f"  Concept metadata collected for {len(concept_meta):,} concepts")

            # Step 3 – bulk insert
            logger.info("  Inserting SNOMED concepts...")
            batch = []
            inserted_ids: Set[str] = set()
            for concept_id in active_ids:
                descs = desc_map.get(concept_id, {})
                fsn = descs.get("fsn", "")
                pt = descs.get("pt", fsn)

                semantic_tag = ""
                if fsn:
                    m = re.search(r"\(([^)]+)\)\s*$", fsn)
                    if m:
                        semantic_tag = m.group(1)

                if not pt and not fsn:
                    continue
                if concept_id in inserted_ids:
                    continue
                inserted_ids.add(concept_id)

                meta = concept_meta.get(concept_id, ("", ""))
                batch.append(SnomedCode(
                    code=concept_id,
                    description=pt or fsn,
                    fully_specified_name=fsn,
                    semantic_tag=semantic_tag,
                    active=True,
                    module_id=meta[1] or None,
                    effective_date=meta[0] or None,
                ))
                count += 1

                if len(batch) >= BATCH_SIZE:
                    bulk_insert_ignore(session, SnomedCode, batch)
                    batch.clear()
                    if count % 50000 == 0:
                        logger.info(f"    ... inserted {count:,} SNOMED concepts")

            if batch:
                bulk_insert_ignore(session, SnomedCode, batch)

        return count


