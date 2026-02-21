"""
Data File Validators

Pre-flight checks that verify every expected data source is present,
has the correct format, and contains the required columns/fields
**before** the pipeline starts processing.

Usage::

    from pipeline.validators import validate_all_sources
    results = validate_all_sources()
    if not all(r.ok for r in results):
        ...  # abort

"""

from __future__ import annotations

import csv
import io
import os
import re
import zipfile
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

from pipeline.helpers import find_zip, STAGING_DIR

logger = logging.getLogger(__name__)


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    """Outcome of a single validator."""
    system: str
    ok: bool
    messages: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        status = "PASS" if self.ok else "FAIL"
        msg = "; ".join(self.messages) if self.messages else "OK"
        return f"[{status}] {self.system}: {msg}"


# ── Abstract base ─────────────────────────────────────────────────────────────

class BaseValidator(ABC):
    """Abstract validator – one per data source / mapping file."""
    system_name: str = ""

    @abstractmethod
    def validate(self) -> ValidationResult:
        ...


# ══════════════════════════════════════════════════════════════════════════════
#  Loader validators
# ══════════════════════════════════════════════════════════════════════════════


class SnomedValidator(BaseValidator):
    system_name = "SNOMED CT"

    def validate(self) -> ValidationResult:
        msgs: List[str] = []
        zip_path = find_zip("SnomedCT_ManagedServiceUS_PRODUCTION")
        if not zip_path:
            return ValidationResult(self.system_name, False,
                                    ["SNOMED CT zip not found in staging/snomed/"])
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                has_concept = any("sct2_Concept_Snapshot" in n for n in names)
                has_desc = any("sct2_Description_Snapshot" in n for n in names)
                if not has_concept:
                    msgs.append("Missing sct2_Concept_Snapshot file inside zip")
                if not has_desc:
                    msgs.append("Missing sct2_Description_Snapshot file inside zip")
        except zipfile.BadZipFile:
            msgs.append(f"Corrupt zip file: {os.path.basename(zip_path)}")

        return ValidationResult(self.system_name, not msgs, msgs)


class ICD10Validator(BaseValidator):
    system_name = "ICD-10-CM"

    def validate(self) -> ValidationResult:
        msgs: List[str] = []
        icd10_dir = os.path.join(STAGING_DIR, "icd10cm")
        if not os.path.isdir(icd10_dir):
            return ValidationResult(self.system_name, False,
                                    ["Directory staging/icd10cm/ does not exist"])

        order_files = [
            f for f in os.listdir(icd10_dir)
            if f.lower().endswith(".txt")
            and "order" in f.lower()
            and "addenda" not in f.lower()
        ]
        if not order_files:
            msgs.append("No ICD-10-CM order file (*order*.txt) found in staging/icd10cm/")
        else:
            # Spot-check format: fixed-width, code at position 6–14
            fpath = os.path.join(icd10_dir, order_files[0])
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    sample_lines = [f.readline() for _ in range(5)]
                valid_lines = sum(
                    1 for ln in sample_lines
                    if len(ln) >= 20
                    and re.match(r'^[A-Z]\d{2,}', ln[6:14].strip())
                )
                if valid_lines == 0:
                    msgs.append(f"Order file {order_files[0]} does not match expected fixed-width format")
            except Exception as e:
                msgs.append(f"Cannot read {order_files[0]}: {e}")

        return ValidationResult(self.system_name, not msgs, msgs)


class HCCValidator(BaseValidator):
    system_name = "HCC"

    def validate(self) -> ValidationResult:
        msgs: List[str] = []
        hcc_dir = os.path.join(STAGING_DIR, "hcc")
        if not os.path.isdir(hcc_dir):
            return ValidationResult(self.system_name, False,
                                    ["Directory staging/hcc/ does not exist"])

        csv_files = [
            f for f in os.listdir(hcc_dir)
            if f.endswith(".csv") and "Mappings" in f
        ]
        if not csv_files:
            msgs.append("No HCC Mappings CSV found in staging/hcc/")
        else:
            # Verify header row contains expected columns
            fpath = os.path.join(hcc_dir, csv_files[0])
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row and "Diagnosis" in str(row[0]):
                            # Found header – check it has at least 7 columns
                            if len(row) < 7:
                                msgs.append(f"{csv_files[0]}: expected ≥7 columns, got {len(row)}")
                            break
                    else:
                        msgs.append(f"{csv_files[0]}: could not find header row containing 'Diagnosis'")
            except Exception as e:
                msgs.append(f"Cannot read {csv_files[0]}: {e}")

        return ValidationResult(self.system_name, not msgs, msgs)


class CPTValidator(BaseValidator):
    """Validates the CPT source zip (DHS Code List Addendum) in staging/cpt/."""
    system_name = "CPT"

    def validate(self) -> ValidationResult:
        msgs: List[str] = []
        zip_path = find_zip("dhs_code_list")
        if not zip_path:
            return ValidationResult(self.system_name, False,
                                    ["CPT source zip (DHS Code List) not found in staging/cpt/"])
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                txt_entries = [n for n in zf.namelist() if n.lower().endswith(".txt")]
                if not txt_entries:
                    msgs.append("CPT zip does not contain a .txt file")
        except zipfile.BadZipFile:
            msgs.append(f"Corrupt zip file: {os.path.basename(zip_path)}")

        return ValidationResult(self.system_name, not msgs, msgs)


class HCPCSValidator(BaseValidator):
    system_name = "HCPCS"

    def validate(self) -> ValidationResult:
        msgs: List[str] = []
        hcpcs_dir = os.path.join(STAGING_DIR, "hcpcs")
        if not os.path.isdir(hcpcs_dir):
            return ValidationResult(self.system_name, False,
                                    ["Directory staging/hcpcs/ does not exist"])

        anweb_files = [
            f for f in os.listdir(hcpcs_dir)
            if "ANWEB" in f.upper() and f.endswith(".txt")
        ]

        if not anweb_files:
            msgs.append("No ANWEB .txt file found in staging/hcpcs/")
        else:
            fpath = os.path.join(hcpcs_dir, anweb_files[0])
            try:
                with open(fpath, "r", encoding="latin-1") as f:
                    sample = f.readline()
                if len(sample) < 82:
                    msgs.append(f"{anweb_files[0]}: line too short for expected fixed-width format")
            except Exception as e:
                msgs.append(f"Cannot read HCPCS file: {e}")

        return ValidationResult(self.system_name, not msgs, msgs)


class RxNormValidator(BaseValidator):
    system_name = "RxNorm"

    def validate(self) -> ValidationResult:
        msgs: List[str] = []
        zip_path = find_zip("RxNorm_full")
        if not zip_path:
            return ValidationResult(self.system_name, False,
                                    ["RxNorm zip not found in staging/rxnorm/"])
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                if not any("RXNCONSO.RRF" in n for n in names):
                    msgs.append("Missing RXNCONSO.RRF inside RxNorm zip")
        except zipfile.BadZipFile:
            msgs.append(f"Corrupt zip file: {os.path.basename(zip_path)}")

        return ValidationResult(self.system_name, not msgs, msgs)


class NDCValidator(BaseValidator):
    system_name = "NDC"

    def validate(self) -> ValidationResult:
        msgs: List[str] = []
        zip_path = find_zip("ndctext")
        if not zip_path:
            return ValidationResult(self.system_name, False,
                                    ["NDC zip (ndctext.zip) not found in staging/ndc/"])
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                txt_entries = [n for n in names if n.lower().endswith(".txt")]
                if not txt_entries:
                    msgs.append("NDC zip does not contain a .txt file")
                else:
                    # Check if file has pipe-delimited format (typical NDC format)
                    with zf.open(txt_entries[0]) as f:
                        sample = f.read(500).decode("utf-8", errors="ignore")
                        if "|" not in sample:
                            msgs.append(f"{txt_entries[0]}: does not appear to be pipe-delimited format")
        except zipfile.BadZipFile:
            msgs.append(f"Corrupt zip file: {os.path.basename(zip_path)}")

        return ValidationResult(self.system_name, not msgs, msgs)


# ══════════════════════════════════════════════════════════════════════════════
#  Mapper validators
# ══════════════════════════════════════════════════════════════════════════════


class SnomedIcd10MapValidator(BaseValidator):
    system_name = "SNOMED → ICD-10 Map"

    def validate(self) -> ValidationResult:
        msgs: List[str] = []
        zip_path = find_zip("SnomedCT_ManagedServiceUS_PRODUCTION")
        if not zip_path:
            return ValidationResult(self.system_name, False,
                                    ["SNOMED zip required for ExtendedMap refset not found"])
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                has_emap = any(
                    "ExtendedMap" in n and "Snapshot" in n
                    for n in zf.namelist()
                )
                if not has_emap:
                    msgs.append("ExtendedMap snapshot file not found in SNOMED zip")
        except zipfile.BadZipFile:
            msgs.append("Corrupt SNOMED zip file")

        return ValidationResult(self.system_name, not msgs, msgs)


class Icd10HccMapValidator(BaseValidator):
    system_name = "ICD-10 → HCC Map"

    def validate(self) -> ValidationResult:
        msgs: List[str] = []
        hcc_dir = os.path.join(STAGING_DIR, "hcc")
        if not os.path.isdir(hcc_dir):
            return ValidationResult(self.system_name, False,
                                    ["Directory staging/hcc/ does not exist"])

        csv_files = [
            f for f in os.listdir(hcc_dir)
            if f.lower().endswith(".csv")
            and "icd-10" in f.lower()
            and "mapping" in f.lower()
        ]
        if not csv_files:
            csv_files = [
                f for f in os.listdir(hcc_dir)
                if f.lower().endswith(".csv") and "mappings" in f.lower()
            ]
        if not csv_files:
            msgs.append("No ICD-10-CM to HCC mapping CSV found in staging/hcc/")

        return ValidationResult(self.system_name, not msgs, msgs)


class RxNormSnomedMapValidator(BaseValidator):
    system_name = "RxNorm ↔ SNOMED Map"

    def validate(self) -> ValidationResult:
        msgs: List[str] = []
        zip_path = find_zip("RxNorm_full")
        if not zip_path:
            return ValidationResult(self.system_name, False,
                                    ["RxNorm zip required for SNOMEDCT_US cross-references not found"])
        # RXNCONSO.RRF presence already checked by RxNormValidator
        return ValidationResult(self.system_name, True, msgs)


# ══════════════════════════════════════════════════════════════════════════════
#  Aggregate runner
# ══════════════════════════════════════════════════════════════════════════════

ALL_VALIDATORS: List[BaseValidator] = [
    # Loaders
    SnomedValidator(),
    ICD10Validator(),
    HCCValidator(),
    CPTValidator(),
    HCPCSValidator(),
    RxNormValidator(),
    NDCValidator(),
    # Mappers
    SnomedIcd10MapValidator(),
    Icd10HccMapValidator(),
    RxNormSnomedMapValidator(),
]


def validate_all_sources(strict: bool = False) -> List[ValidationResult]:
    """Run every registered validator and log results.

    Parameters
    ----------
    strict : bool
        If ``True``, a single failure causes a ``SystemExit``.

    Returns
    -------
    list[ValidationResult]
        One result per validator.
    """
    logger.info("\n" + "=" * 70)
    logger.info("  Pre-Flight Validation")
    logger.info("=" * 70)

    results: List[ValidationResult] = []
    for v in ALL_VALIDATORS:
        r = v.validate()
        results.append(r)
        if r.ok:
            logger.info(f"  ✓ {r.system}")
        else:
            for msg in r.messages:
                logger.warning(f"  ✗ {r.system}: {msg}")

    passed = sum(1 for r in results if r.ok)
    failed = len(results) - passed
    logger.info("-" * 70)
    logger.info(f"  Validation: {passed} passed, {failed} failed out of {len(results)} checks")
    logger.info("=" * 70)

    if strict and failed:
        raise SystemExit(
            f"Validation failed for {failed} source(s). "
            "Fix the issues above and re-run."
        )

    return results
