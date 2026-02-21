"""
HCPCS (Healthcare Common Procedure Coding System) Level II Loader

Reads the CMS ANWEB fixed-width text file from staging/hcpcs/.
"""

import os
import re
import logging

from pipeline.base import BaseLoader
from pipeline.helpers import bulk_insert_ignore, STAGING_DIR, BATCH_SIZE
from pipeline.models import HCPCSCode

logger = logging.getLogger(__name__)

# Category map derived from HCPCS first-letter prefix
_CAT_MAP = {
    "A": "Transportation/Medical Supplies", "B": "Enteral/Parenteral Therapy",
    "C": "Outpatient PPS", "D": "Dental", "E": "DME",
    "G": "Procedures/Professional Services", "H": "Behavioral Health",
    "J": "Drugs (Non-Oral)", "K": "DME Temporary", "L": "Orthotics/Prosthetics",
    "M": "Medical Services", "P": "Pathology/Lab", "Q": "Temporary Codes",
    "R": "Diagnostic Radiology", "S": "Temporary National Codes",
    "T": "State Medicaid", "U": "Coronavirus Testing", "V": "Vision/Hearing",
}


class HCPCSLoader(BaseLoader):
    system_name = "HCPCS"
    model_class = HCPCSCode

    # ── Primary source ────────────────────────────────────────────────────

    def _load_from_source(self, session) -> int:
        hcpcs_dir = os.path.join(STAGING_DIR, "hcpcs")
        if not os.path.exists(hcpcs_dir):
            return 0

        # Try CMS ANWEB file first
        anweb_files = [
            f for f in os.listdir(hcpcs_dir)
            if "ANWEB" in f.upper() and f.endswith(".txt")
        ]
        if not anweb_files:
            logger.warning("No ANWEB .txt file found in staging/hcpcs/")
            return 0

        filepath = os.path.join(hcpcs_dir, anweb_files[0])
        return self._parse_cms_file(session, filepath)

    def _parse_cms_file(self, session, filepath: str) -> int:
        """Parse CMS HCPCS fixed-width text file (latin-1 encoding)."""
        count = 0
        seen: dict = {}

        try:
            with open(filepath, "r", encoding="latin-1") as f:
                for line in f:
                    if len(line) < 82:
                        continue
                    code = line[0:5].strip()
                    if not re.match(r'^[A-V]\d{4}$', code):
                        continue
                    long_desc = line[11:82].strip()
                    short_desc = line[82:110].strip() if len(line) > 82 else ""

                    if code not in seen:
                        seen[code] = {
                            "short_description": short_desc,
                            "long_description": long_desc,
                        }
                    else:
                        if long_desc:
                            seen[code]["long_description"] += " " + long_desc

            batch = []
            for code, data in seen.items():
                batch.append(HCPCSCode(
                    code=code,
                    short_description=data["short_description"][:255],
                    long_description=data["long_description"][:500],
                    category=_CAT_MAP.get(code[0], "Other"),
                    status="Active",
                    active=True,
                ))
                count += 1

                if len(batch) >= BATCH_SIZE:
                    bulk_insert_ignore(session, HCPCSCode, batch)
                    batch.clear()
            if batch:
                bulk_insert_ignore(session, HCPCSCode, batch)
            logger.info(f"  Parsed {len(seen)} unique HCPCS codes from CMS file")
        except Exception as e:
            logger.warning(f"Error parsing HCPCS file {filepath}: {e}")
        return count


