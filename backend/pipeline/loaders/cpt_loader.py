"""
CPT (Current Procedural Terminology) Loader

Reads the CMS DHS Code List Addendum zip from staging/cpt/ and loads
CPT codes (5-digit numeric) and enriches HCPCS codes with their
Stark-Law DHS category.

This is the primary CPT source — the DHS Code List contains both
CPT and HCPCS codes tagged with Designated Health Service categories.
"""

import re
import zipfile
import logging
import traceback

from pipeline.base import BaseLoader
from pipeline.helpers import find_zip
from pipeline.models import CPTCode, HCPCSCode

logger = logging.getLogger(__name__)

CPT_ZIP_PATTERN = "2026_dhs_code_list"

# DHS category header keywords (all-caps lines in the source text file)
_DHS_CATEGORY_HEADERS = {
    "CLINICAL LABORATORY SERVICES": "Clinical Laboratory Services",
    "PHYSICAL THERAPY, OCCUPATIONAL THERAPY, AND OUTPATIENT SPEECH-LANGUAGE PATHOLOGY SERVICES":
        "Physical Therapy/OT/Speech-Language Pathology",
    "RADIOLOGY AND CERTAIN OTHER IMAGING SERVICES": "Radiology & Imaging Services",
    "RADIATION THERAPY SERVICES AND SUPPLIES": "Radiation Therapy Services & Supplies",
    "PREVENTIVE SCREENING TESTS": "Preventive Screening Tests",
    "OUTPATIENT PRESCRIPTION DRUGS": "Outpatient Prescription Drugs",
    "DURABLE MEDICAL EQUIPMENT AND SUPPLIES": "DME & Supplies",
    "PROSTHETICS, ORTHOTICS, AND PROSTHETIC DEVICES": "Prosthetics/Orthotics",
    "HOME HEALTH SERVICES": "Home Health Services",
    "INPATIENT AND OUTPATIENT HOSPITAL SERVICES": "Inpatient & Outpatient Hospital Services",
}


class CPTLoader(BaseLoader):
    """Loads CPT codes and enriches HCPCS codes with DHS categories.

    Reads the CMS DHS Code List Addendum zip which contains both
    CPT (5-digit numeric) and HCPCS (alpha + 4 digits) codes.
    Overrides ``load()`` because it operates on two model classes.
    """

    system_name = "CPT"
    model_class = None  # operates on CPTCode + HCPCSCode

    # Override the full load() because we don't follow the normal
    # "load rows into one table" pattern.
    def load(self, session) -> int:
        import time
        logger.info(f"Loading {self.system_name}...")
        start = time.perf_counter()

        count = self._load_from_source(session)

        session.commit()
        elapsed = time.perf_counter() - start
        logger.info(f"Loaded {count:,} {self.system_name} codes ({elapsed:.1f}s).")
        return count

    def _load_from_source(self, session) -> int:
        cpt_zip = find_zip(CPT_ZIP_PATTERN)
        if not cpt_zip:
            logger.warning("CPT source zip not found — skipping CPT loading")
            return 0

        cpt_new = 0
        cpt_updated = 0
        hcpcs_new = 0
        hcpcs_updated = 0
        current_category = "Unknown DHS Category"

        try:
            with zipfile.ZipFile(cpt_zip, "r") as zf:
                txt_entry = None
                for name in zf.namelist():
                    if name.lower().endswith(".txt"):
                        txt_entry = name
                        break
                if not txt_entry:
                    logger.warning("No .txt file found in CPT zip")
                    return 0

                logger.info(f"  Reading CPT file: {txt_entry}")
                raw = zf.read(txt_entry)
                text = raw.decode("latin-1")

                for line in text.splitlines():
                    line = line.strip()
                    if not line:
                        continue

                    # Category header detection
                    upper_line = line.upper()
                    for header_key, cat_value in _DHS_CATEGORY_HEADERS.items():
                        if header_key in upper_line:
                            current_category = cat_value
                            break

                    parts = line.split("\t")
                    if len(parts) < 2:
                        continue

                    code_candidate = parts[0].strip().strip('"')
                    desc = parts[1].strip().strip('"')

                    # CPT (5-digit numeric)
                    if re.match(r'^\d{5}$', code_candidate):
                        existing = session.query(CPTCode).filter_by(code=code_candidate).first()
                        if existing:
                            if not existing.dhs_category:
                                existing.dhs_category = current_category
                                cpt_updated += 1
                        else:
                            session.add(CPTCode(
                                code=code_candidate,
                                short_description=desc[:255],
                                long_description=desc,
                                category="CPT",
                                dhs_category=current_category,
                                status="Active",
                                active=True,
                            ))
                            cpt_new += 1

                    # HCPCS (alpha + 4 digits)
                    elif re.match(r'^[A-V]\d{4}$', code_candidate):
                        existing = session.query(HCPCSCode).filter_by(code=code_candidate).first()
                        if existing:
                            if not existing.dhs_category:
                                existing.dhs_category = current_category
                                hcpcs_updated += 1
                        else:
                            session.add(HCPCSCode(
                                code=code_candidate,
                                short_description=desc[:255],
                                long_description=desc,
                                category="CPT",
                                dhs_category=current_category,
                                status="Active",
                                active=True,
                            ))
                            hcpcs_new += 1

            total = cpt_new + cpt_updated + hcpcs_new + hcpcs_updated
            logger.info(f"  CPT codes:  {cpt_new} new, {cpt_updated} updated with DHS category")
            logger.info(f"  HCPCS codes: {hcpcs_new} new, {hcpcs_updated} updated with DHS category")
            logger.info(f"  Total CPT codes processed: {total}")
            return total

        except Exception as e:
            logger.error(f"Error loading CPT codes: {e}")
            traceback.print_exc()
            session.rollback()
            return 0
