"""
ICD-10-CM Loader

Reads the CMS ICD-10-CM order file (fixed-width) and inserts all codes with
chapter, category, header/billable flag.  Uses ``get_chapter_for_code()`` to
derive chapter from the formatted code.
"""

import os
import re
import logging
from typing import Set

from pipeline.base import BaseLoader
from pipeline.helpers import (
    bulk_insert_ignore, format_icd10_code, STAGING_DIR, BATCH_SIZE,
)
from pipeline.models import ICD10Code
from api.services.icd10_chapters import get_chapter_for_code

logger = logging.getLogger(__name__)


class ICD10Loader(BaseLoader):
    system_name = "ICD-10-CM"
    model_class = ICD10Code

    # ── Primary source ────────────────────────────────────────────────────

    def _load_from_source(self, session) -> int:
        icd10_dir = os.path.join(STAGING_DIR, "icd10cm")
        if not os.path.exists(icd10_dir):
            return 0

        count = 0
        for fname in os.listdir(icd10_dir):
            if (fname.lower().endswith(".txt")
                    and "order" in fname.lower()
                    and "addenda" not in fname.lower()):
                filepath = os.path.join(icd10_dir, fname)
                count += self._parse_order_file(session, filepath)
        return count

    def _parse_order_file(self, session, filepath: str) -> int:
        """Parse the CMS ICD-10-CM order file (fixed-width format)."""
        count = 0
        batch = []
        seen_codes: Set[str] = set()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if len(line) < 20:
                        continue
                    code = line[6:14].strip().replace(" ", "")
                    is_header = line[14:15].strip() == "1"
                    short_desc = line[16:77].strip()
                    long_desc = line[77:].strip()

                    if not code or not re.match(r'^[A-Z]\d{2,}', code):
                        continue
                    if code in seen_codes:
                        continue
                    seen_codes.add(code)

                    formatted_code = format_icd10_code(code)
                    chapter_info = get_chapter_for_code(formatted_code)
                    batch.append(ICD10Code(
                        code=formatted_code,
                        description=long_desc or short_desc,
                        short_description=short_desc,
                        category=code[:3],
                        chapter=chapter_info["name"] if chapter_info else None,
                        is_header=is_header,
                        active=True,
                    ))
                    count += 1

                    if len(batch) >= BATCH_SIZE:
                        bulk_insert_ignore(session, ICD10Code, batch)
                        batch.clear()
            if batch:
                bulk_insert_ignore(session, ICD10Code, batch)
                session.flush()
        except Exception as e:
            logger.warning(f"  Error parsing ICD-10 file {filepath}: {e}")
        return count


