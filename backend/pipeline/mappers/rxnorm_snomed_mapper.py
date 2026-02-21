"""
RxNorm ↔ SNOMED CT Mapper

Scans RXNCONSO.RRF for ``SAB=SNOMEDCT_US`` rows and builds cross-reference
links between RxNorm concepts (RXCUI) and SNOMED concepts (SCUI).

Also performs intelligent name-based matching to supplement explicit mappings.
"""

import zipfile
import logging
import re
from typing import Set, Tuple

from pipeline.base import BaseMapper
from pipeline.helpers import find_zip, BATCH_SIZE
from pipeline.models import (
    RxNormCode, SnomedCode, rxnorm_snomed_mapping,
)

logger = logging.getLogger(__name__)

RXNORM_ZIP_PATTERN = "RxNorm_full"


class RxNormSnomedMapper(BaseMapper):
    mapping_name = "RxNorm ↔ SNOMED CT"

    def _build_from_source(self, session) -> int:
        rxnorm_zip = find_zip(RXNORM_ZIP_PATTERN)
        if not rxnorm_zip:
            logger.warning("  RxNorm zip not found — skipping RxNorm-SNOMED mappings")
            return 0

        # Pre-load valid code sets
        valid_rxnorm = {r[0] for r in session.query(RxNormCode.code).all()}
        valid_snomed = {r[0] for r in session.query(SnomedCode.code).all()}
        logger.info(f"  Valid RxNorm: {len(valid_rxnorm):,}, Valid SNOMED: {len(valid_snomed):,}")

        count = 0
        seen_pairs: Set[Tuple[str, str]] = set()
        batch = []

        with zipfile.ZipFile(rxnorm_zip, "r") as zf:
            conso_entry = None
            for n in zf.namelist():
                if n == "rrf/RXNCONSO.RRF":
                    conso_entry = n
                    break
            if not conso_entry:
                logger.error("  RXNCONSO.RRF not found")
                return 0

            logger.info("  Scanning RXNCONSO.RRF for SNOMEDCT_US cross-references...")
            with zf.open(conso_entry) as f:
                for raw_line in f:
                    line = raw_line.decode("utf-8", errors="replace")
                    parts = line.split("|")
                    if len(parts) < 14:
                        continue

                    if parts[11] != "SNOMEDCT_US":
                        continue

                    rxcui = parts[0]
                    snomed_code = parts[9]  # SCUI field

                    if not rxcui or not snomed_code:
                        continue
                    if rxcui not in valid_rxnorm or snomed_code not in valid_snomed:
                        continue

                    pair = (rxcui, snomed_code)
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)

                    batch.append({
                        "rxnorm_code": rxcui,
                        "snomed_code": snomed_code,
                        "relationship": "cross-reference",
                        "active": True,
                    })

                    if len(batch) >= BATCH_SIZE:
                        session.execute(rxnorm_snomed_mapping.insert(), batch)
                        session.flush()
                        count += len(batch)
                        batch.clear()

        if batch:
            session.execute(rxnorm_snomed_mapping.insert(), batch)
            session.flush()
            count += len(batch)

        logger.info(f"  Found {count:,} explicit mappings from RXNCONSO.RRF")

        # Add name-based matching for newer drugs not in explicit mappings
        name_matches = self._add_name_based_mappings(session, seen_pairs)
        count += name_matches

        return count

    def _normalize_name(self, name: str) -> str:
        """Normalize drug name for matching."""
        if not name:
            return ""
        # Lowercase and strip
        normalized = name.lower().strip()
        # Remove common SNOMED suffixes
        normalized = re.sub(r'\s*\(substance\)\s*$', '', normalized)
        normalized = re.sub(r'\s*\(product\)\s*$', '', normalized)
        normalized = re.sub(r'\s*\(medicinal product\)\s*$', '', normalized)
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized

    def _add_name_based_mappings(self, session, seen_pairs: Set[Tuple[str, str]]) -> int:
        """Add mappings based on exact name matches."""
        logger.info("  Adding name-based mappings for exact matches...")
        
        # Load all RxNorm codes with names (focus on ingredients and clinical drugs)
        rxnorm_codes = session.query(RxNormCode.code, RxNormCode.name, RxNormCode.term_type).filter(
            RxNormCode.active == True,
            RxNormCode.term_type.in_(['IN', 'PIN', 'MIN', 'SCD', 'SBD'])  # Key term types
        ).all()
        
        # Load all SNOMED codes (focus on substances and products)
        snomed_codes = session.query(SnomedCode.code, SnomedCode.description, SnomedCode.semantic_tag).filter(
            SnomedCode.active == True,
            SnomedCode.semantic_tag.in_(['substance', 'product', 'medicinal product', 'medicinal product form'])
        ).all()
        
        logger.info(f"  Comparing {len(rxnorm_codes):,} RxNorm vs {len(snomed_codes):,} SNOMED codes")
        
        # Build name index for SNOMED
        snomed_by_name = {}
        for code, desc, tag in snomed_codes:
            norm_name = self._normalize_name(desc)
            if norm_name:
                if norm_name not in snomed_by_name:
                    snomed_by_name[norm_name] = []
                snomed_by_name[norm_name].append(code)
        
        # Match RxNorm names against SNOMED
        count = 0
        batch = []
        
        for rxcui, rxname, tty in rxnorm_codes:
            norm_rxname = self._normalize_name(rxname)
            if not norm_rxname:
                continue
                
            # Check for exact name match
            if norm_rxname in snomed_by_name:
                for snomed_code in snomed_by_name[norm_rxname]:
                    pair = (rxcui, snomed_code)
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)
                    
                    batch.append({
                        "rxnorm_code": rxcui,
                        "snomed_code": snomed_code,
                        "relationship": "name-match",
                        "active": True,
                    })
                    
                    if len(batch) >= BATCH_SIZE:
                        session.execute(rxnorm_snomed_mapping.insert(), batch)
                        session.flush()
                        count += len(batch)
                        logger.info(f"    Added {count:,} name-based mappings...")
                        batch.clear()
        
        if batch:
            session.execute(rxnorm_snomed_mapping.insert(), batch)
            session.flush()
            count += len(batch)
        
        logger.info(f"  Added {count:,} name-based mappings")
        return count
