"""
HCC (Hierarchical Condition Category) Loader

Reads the CMS HCC mapping CSV to extract unique HCC categories with
risk-adjustment coefficients.
"""

import csv
import os
import logging

from pipeline.base import BaseLoader
from pipeline.helpers import STAGING_DIR
from pipeline.models import HCCCode

logger = logging.getLogger(__name__)


class HCCLoader(BaseLoader):
    system_name = "HCC"
    model_class = HCCCode

    # ── Primary source ────────────────────────────────────────────────────

    def _load_from_source(self, session) -> int:
        hcc_dir = os.path.join(STAGING_DIR, "hcc")
        if not os.path.exists(hcc_dir):
            return 0

        csv_files = [
            f for f in os.listdir(hcc_dir)
            if f.endswith(".csv") and "Mappings" in f
        ]
        csv_files.sort(key=lambda x: ("Final" not in x, x))
        if not csv_files:
            return 0

        filepath = os.path.join(hcc_dir, csv_files[0])
        return self._parse_cms_mapping_csv(session, filepath)

    def _parse_cms_mapping_csv(self, session, filepath: str) -> int:
        """Parse CMS HCC mapping CSV to extract unique HCC categories."""
        count = 0
        hcc_categories: dict = {}

        try:
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
                    hcc_v28 = row[6].strip() if len(row) > 6 else ""
                    if hcc_v28 and hcc_v28.isdigit():
                        hcc_code = f"HCC{hcc_v28}"
                        if hcc_code not in hcc_categories:
                            hcc_categories[hcc_code] = row[1].strip()[:100]

            for hcc_code in sorted(
                hcc_categories.keys(), key=lambda x: int(x.replace("HCC", ""))
            ):
                if not session.query(HCCCode).filter_by(code=hcc_code).first():
                    session.add(HCCCode(
                        code=hcc_code,
                        description=f"CMS-HCC Category {hcc_code.replace('HCC', '')}",
                        category="CMS-HCC V28",
                        model_version="V28",
                        payment_year=2026,
                        active=True,
                    ))
                    count += 1
            logger.info(f"  Parsed {len(hcc_categories)} unique HCC categories from CMS CSV")
        except Exception as e:
            logger.warning(f"Error parsing HCC CSV {filepath}: {e}")
        return count


