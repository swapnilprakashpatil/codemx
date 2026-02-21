"""
NDC ↔ RxNorm Mapper

Creates mapping between NDC (National Drug Code) and RxNorm concepts.
RxNorm records from RXNCONSO.RRF include NDC codes in the file, which we
extract and link to loaded NDC codes.

The mapping uses the `ndc_codes` field from RxNormCode, which contains
pipe-separated NDC codes embedded in the RxNorm data.

Also performs intelligent name-based matching to supplement explicit mappings.
"""

import logging
import re
from typing import Set, Tuple

from pipeline.base import BaseMapper
from pipeline.helpers import BATCH_SIZE
from pipeline.models import (
    RxNormCode, NDCCode, ndc_rxnorm_mapping,
)

logger = logging.getLogger(__name__)


class NdcRxNormMapper(BaseMapper):
    mapping_name = "NDC ↔ RxNorm"

    def _build_from_source(self, session) -> int:
        """Build NDC-RxNorm mappings from the ndc_codes field in RxNorm records."""
        
        # Pre-load valid code sets
        valid_ndc = {r[0] for r in session.query(NDCCode.code).all()}
        valid_rxnorm_with_ndc = session.query(RxNormCode.code, RxNormCode.ndc_codes).filter(
            RxNormCode.ndc_codes.isnot(None),
            RxNormCode.ndc_codes != ""
        ).all()
        
        logger.info(f"  Valid NDC codes: {len(valid_ndc):,}")
        logger.info(f"  RxNorm codes with NDC references: {len(valid_rxnorm_with_ndc):,}")

        count = 0
        seen_pairs: Set[Tuple[str, str]] = set()
        batch = []
        skipped = 0

        for rxcui, ndc_codes_str in valid_rxnorm_with_ndc:
            # Split pipe-separated NDC codes
            ndc_list = [ndc.strip() for ndc in ndc_codes_str.split("|") if ndc.strip()]
            
            for ndc_code in ndc_list:
                # Normalize NDC code (remove dashes, ensure 11 digits)
                normalized_ndc = ndc_code.replace("-", "").strip()
                
                # Skip if not in valid NDC set
                if normalized_ndc not in valid_ndc:
                    skipped += 1
                    continue
                
                pair = (normalized_ndc, rxcui)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                batch.append({
                    "ndc_code": normalized_ndc,
                    "rxnorm_code": rxcui,
                    "source": "rxnorm_ndc_codes",
                    "active": True,
                })

                if len(batch) >= BATCH_SIZE:
                    session.execute(ndc_rxnorm_mapping.insert(), batch)
                    session.flush()
                    count += len(batch)
                    logger.info(f"    Inserted {count:,} NDC-RxNorm mappings...")
                    batch.clear()

        # Insert remaining batch
        if batch:
            session.execute(ndc_rxnorm_mapping.insert(), batch)
            session.flush()
            count += len(batch)

        logger.info(f"  Total NDC-RxNorm mappings from ndc_codes field: {count:,}")
        if skipped > 0:
            logger.info(f"  Skipped {skipped:,} NDC codes not found in NDC table")

        # Add name-based matching for NDCs not in RxNorm ndc_codes field
        name_matches = self._add_name_based_mappings(session, seen_pairs)
        count += name_matches

        return count

    def _normalize_name(self, name: str) -> str:
        """Normalize drug name for matching."""
        if not name:
            return ""
        # Lowercase and strip
        normalized = name.lower().strip()
        # Remove dosage forms and strengths for broader matching
        normalized = re.sub(r'\d+\s*(mg|ml|mcg|g|%|units?)', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\s*\d+\.?\d*\s*', ' ', normalized)  # Remove numbers
        # Remove common packaging terms
        normalized = re.sub(r'\s*(tablet|capsule|injection|solution|vial|kit|auto-injector)s?\s*', ' ', normalized, flags=re.IGNORECASE)
        # Remove brand name indicators
        normalized = re.sub(r'\s*\[.*?\]\s*', ' ', normalized)
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def _add_name_based_mappings(self, session, seen_pairs: Set[Tuple[str, str]]) -> int:
        """Add mappings based on name similarity."""
        logger.info("  Adding name-based NDC-RxNorm mappings...")
        
        # Load NDC codes (focus on those without existing mappings)
        all_ndc_codes = session.query(NDCCode.code, NDCCode.product_name, NDCCode.non_proprietary_name).filter(
            NDCCode.product_name.isnot(None)
        ).all()
        
        # Load RxNorm codes (focus on clinical and branded drugs)
        rxnorm_codes = session.query(RxNormCode.code, RxNormCode.name, RxNormCode.term_type).filter(
            RxNormCode.active == True,
            RxNormCode.term_type.in_(['SCD', 'SBD', 'SCDF', 'SBDF', 'IN', 'BN'])  # Drug products and ingredients
        ).all()
        
        logger.info(f"  Comparing {len(all_ndc_codes):,} NDC vs {len(rxnorm_codes):,} RxNorm codes")
        
        # Build name index for RxNorm
        rxnorm_by_name = {}
        for code, name, tty in rxnorm_codes:
            norm_name = self._normalize_name(name)
            if norm_name and len(norm_name) > 3:  # Minimum length to avoid false matches
                if norm_name not in rxnorm_by_name:
                    rxnorm_by_name[norm_name] = []
                rxnorm_by_name[norm_name].append(code)
        
        # Match NDC names against RxNorm
        count = 0
        batch = []
        
        for ndc_code, product_name, non_proprietary_name in all_ndc_codes:
            # Try matching both product name and non-proprietary (generic) name
            names_to_try = [product_name]
            if non_proprietary_name and non_proprietary_name != product_name:
                names_to_try.append(non_proprietary_name)
            
            for name in names_to_try:
                norm_name = self._normalize_name(name)
                if not norm_name or len(norm_name) <= 3:
                    continue
                
                # Check for exact normalized name match
                if norm_name in rxnorm_by_name:
                    for rxcui in rxnorm_by_name[norm_name]:
                        pair = (ndc_code, rxcui)
                        if pair in seen_pairs:
                            continue
                        seen_pairs.add(pair)
                        
                        batch.append({
                            "ndc_code": ndc_code,
                            "rxnorm_code": rxcui,
                            "source": "name-match",
                            "active": True,
                        })
                        
                        if len(batch) >= BATCH_SIZE:
                            session.execute(ndc_rxnorm_mapping.insert(), batch)
                            session.flush()
                            count += len(batch)
                            logger.info(f"    Added {count:,} name-based NDC-RxNorm mappings...")
                            batch.clear()
        
        if batch:
            session.execute(ndc_rxnorm_mapping.insert(), batch)
            session.flush()
            count += len(batch)
        
        logger.info(f"  Added {count:,} name-based NDC-RxNorm mappings")
        return count
