"""
RxNorm Loader

Reads the RxNorm full-release ZIP (RXNCONSO.RRF, RXNSAT.RRF, RXNREL.RRF)
and inserts drug concepts, attributes, and inter-concept relationships.
"""

import os
import zipfile
import logging
from typing import Dict, Set, Tuple

from pipeline.base import BaseLoader
from pipeline.helpers import (
    find_zip, bulk_insert_ignore, BATCH_SIZE,
)
from pipeline.models import RxNormCode, rxnorm_relationships

logger = logging.getLogger(__name__)

# Constants
RXNORM_ZIP_PATTERN = "RxNorm_full"
RXNORM_KEY_TTYS = {"IN", "BN", "SCD", "SBD", "PIN", "MIN", "SCDF", "SBDF", "DF"}

# Attributes to collect from RXNSAT.RRF
WANTED_ATNS = {
    "RXTERM_FORM", "RXN_AVAILABLE_STRENGTH", "RXN_STRENGTH",
    "RXN_HUMAN_DRUG", "RXN_VET_DRUG", "RXN_BN_CARDINALITY",
    "NDC", "RXN_QUANTITY", "RXN_QUALITATIVE_DISTINCTION",
}

# Relationship types from RXNREL.RRF
WANTED_RELAS = {"has_ingredient", "tradename_of", "has_dose_form", "consists_of", "contains"}


class RxNormLoader(BaseLoader):
    """Load RxNorm drug codes from the full-release ZIP.

    Overrides ``load()`` to add attribute-enrichment and relationship-loading
    steps after the main concept load.
    """

    system_name = "RxNorm"
    model_class = RxNormCode

    def load(self, session) -> int:
        import time
        logger.info(f"Loading {self.system_name}...")
        start = time.perf_counter()

        zip_path = find_zip(RXNORM_ZIP_PATTERN)
        if not zip_path:
            logger.warning("RxNorm zip not found — skipping RxNorm loading")
            session.commit()
            return 0

        # Step 1: Load concepts from RXNCONSO.RRF
        count = self._load_concepts(session, zip_path)
        session.commit()

        # Step 2: Enrich with RXNSAT attributes
        attr_count = self._load_attributes(session, zip_path)
        logger.info(f"  Enriched {attr_count:,} codes with RXNSAT attributes")

        # Step 3: Load inter-concept relationships from RXNREL.RRF
        rel_count = self._load_relationships(session, zip_path)
        logger.info(f"  Loaded {rel_count:,} inter-concept relationships")

        elapsed = time.perf_counter() - start
        logger.info(
            f"Loaded {count:,} {self.system_name} codes "
            f"(+ {attr_count:,} attrs, {rel_count:,} rels) ({elapsed:.1f}s)."
        )
        return count

    def _load_from_source(self, session) -> int:
        # Not used — load() is overridden.
        return 0

    # ── RXNCONSO: concepts ────────────────────────────────────────────────

    def _load_concepts(self, session, zip_path: str) -> int:
        logger.info(f"  Reading RxNorm from: {os.path.basename(zip_path)}")
        count = 0

        with zipfile.ZipFile(zip_path, "r") as zf:
            conso_entry = self._find_rrf(zf, "rrf/RXNCONSO.RRF")
            if not conso_entry:
                logger.error("  RXNCONSO.RRF not found in RxNorm zip")
                return 0

            logger.info("  Reading RXNCONSO.RRF (SAB=RXNORM)...")
            batch = []
            seen_rxcui: Set[str] = set()

            with zf.open(conso_entry) as f:
                for raw_line in f:
                    line = raw_line.decode("utf-8", errors="replace")
                    parts = line.split("|")
                    if len(parts) < 17:
                        continue

                    if parts[11] != "RXNORM":
                        continue
                    tty = parts[12]
                    if tty not in RXNORM_KEY_TTYS:
                        continue

                    rxcui = parts[0]
                    if rxcui in seen_rxcui:
                        continue
                    seen_rxcui.add(rxcui)

                    batch.append(RxNormCode(
                        code=rxcui,
                        name=parts[14],
                        term_type=tty,
                        suppress=parts[16],
                        active=(parts[16] != "O"),
                    ))
                    count += 1

                    if len(batch) >= BATCH_SIZE:
                        bulk_insert_ignore(session, RxNormCode, batch)
                        batch.clear()
                        if count % 20000 == 0:
                            logger.info(f"    ... inserted {count:,} RxNorm concepts")

            if batch:
                bulk_insert_ignore(session, RxNormCode, batch)

            logger.info(f"  Loaded {count:,} RxNorm concepts (SAB=RXNORM, key TTYs)")
        return count

    # ── RXNSAT: attributes ────────────────────────────────────────────────

    def _load_attributes(self, session, zip_path: str) -> int:
        logger.info(f"  Reading RXNSAT.RRF for attributes from: {os.path.basename(zip_path)}")
        count = 0

        with zipfile.ZipFile(zip_path, "r") as zf:
            sat_entry = self._find_rrf(zf, "rrf/RXNSAT.RRF")
            if not sat_entry:
                logger.warning("  RXNSAT.RRF not found — skipping attributes")
                return 0

            logger.info("  Reading RXNSAT.RRF (extracting RXTERM_FORM, strengths, drug classification)...")
            attrs: Dict[str, Dict[str, str]] = {}

            with zf.open(sat_entry) as f:
                for raw_line in f:
                    line = raw_line.decode("utf-8", errors="replace")
                    parts = line.split("|")
                    if len(parts) < 13:
                        continue
                    if parts[9] != "RXNORM":
                        continue

                    atn = parts[8]
                    if atn not in WANTED_ATNS:
                        continue

                    rxcui = parts[0]
                    atv = parts[10].strip()

                    if rxcui not in attrs:
                        attrs[rxcui] = {}
                    if atn == "NDC":
                        if "NDC" in attrs[rxcui]:
                            attrs[rxcui]["NDC"] += "|" + atv
                        else:
                            attrs[rxcui]["NDC"] = atv
                    elif atn not in attrs[rxcui]:
                        attrs[rxcui][atn] = atv

            # Batch update existing rows
            logger.info(f"  Updating {len(attrs):,} RxNorm codes with attribute data...")
            for rxcui, attr_dict in attrs.items():
                updates: dict = {}
                if "RXTERM_FORM" in attr_dict:
                    updates["rxterm_form"] = attr_dict["RXTERM_FORM"]
                if "RXN_AVAILABLE_STRENGTH" in attr_dict:
                    updates["available_strength"] = attr_dict["RXN_AVAILABLE_STRENGTH"]
                if "RXN_STRENGTH" in attr_dict:
                    updates["strength"] = attr_dict["RXN_STRENGTH"]
                if "RXN_HUMAN_DRUG" in attr_dict:
                    updates["human_drug"] = attr_dict["RXN_HUMAN_DRUG"] == "1"
                if "RXN_VET_DRUG" in attr_dict:
                    updates["vet_drug"] = attr_dict["RXN_VET_DRUG"] == "1"
                if "RXN_BN_CARDINALITY" in attr_dict:
                    updates["bn_cardinality"] = attr_dict["RXN_BN_CARDINALITY"]
                if "NDC" in attr_dict:
                    updates["ndc_codes"] = attr_dict["NDC"]
                if "RXN_QUANTITY" in attr_dict:
                    updates["quantity"] = attr_dict["RXN_QUANTITY"]
                if "RXN_QUALITATIVE_DISTINCTION" in attr_dict:
                    updates["qualitative_distinction"] = attr_dict["RXN_QUALITATIVE_DISTINCTION"]

                if updates:
                    session.query(RxNormCode).filter_by(code=rxcui).update(updates)
                    count += 1
                    if count % 10000 == 0:
                        session.flush()
                        logger.info(f"    ... updated {count:,} codes with attributes")

            session.commit()
            logger.info(f"  Updated {count:,} RxNorm codes with attributes")
        return count

    # ── RXNREL: relationships ─────────────────────────────────────────────

    def _load_relationships(self, session, zip_path: str) -> int:
        logger.info(f"  Reading RXNREL.RRF for relationships from: {os.path.basename(zip_path)}")
        count = 0

        with zipfile.ZipFile(zip_path, "r") as zf:
            rel_entry = self._find_rrf(zf, "rrf/RXNREL.RRF")
            if not rel_entry:
                logger.warning("  RXNREL.RRF not found — skipping relationships")
                return 0

            loaded_rxcuis = {r[0] for r in session.query(RxNormCode.code).all()}
            logger.info(f"  Have {len(loaded_rxcuis):,} loaded RXCUIs to match against")

            logger.info("  Reading RXNREL.RRF (extracting key relationships)...")
            batch = []
            seen_pairs: Set[Tuple[str, str, str]] = set()

            with zf.open(rel_entry) as f:
                for raw_line in f:
                    line = raw_line.decode("utf-8", errors="replace")
                    parts = line.split("|")
                    if len(parts) < 16:
                        continue
                    if parts[10] != "RXNORM":
                        continue

                    rela = parts[7]
                    if rela not in WANTED_RELAS:
                        continue

                    rxcui1 = parts[0]
                    rxcui2 = parts[4]

                    if rxcui1 not in loaded_rxcuis or rxcui2 not in loaded_rxcuis:
                        continue

                    key = (rxcui1, rxcui2, rela)
                    if key in seen_pairs:
                        continue
                    seen_pairs.add(key)

                    batch.append({
                        "rxcui_source": rxcui1,
                        "rxcui_target": rxcui2,
                        "relationship": rela,
                    })
                    count += 1

                    if len(batch) >= BATCH_SIZE:
                        session.execute(rxnorm_relationships.insert(), batch)
                        batch.clear()
                        if count % 20000 == 0:
                            logger.info(f"    ... inserted {count:,} RxNorm relationships")

            if batch:
                session.execute(rxnorm_relationships.insert(), batch)

            session.commit()
            logger.info(f"  Loaded {count:,} RxNorm relationships")
        return count

    # ── Utility ───────────────────────────────────────────────────────────

    @staticmethod
    def _find_rrf(zf: zipfile.ZipFile, target: str) -> str | None:
        for n in zf.namelist():
            if n == target:
                return n
        return None
