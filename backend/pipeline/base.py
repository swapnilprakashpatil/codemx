"""
Base classes for the data processing pipeline.

Provides ``BaseLoader``, ``BaseMapper``, and ``BasePipeline`` that
establish the contract every concrete loader / mapper must follow.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import List, Type

from pipeline.models import init_db, get_session, Base

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
#  BaseLoader
# ──────────────────────────────────────────────────────────────────────────────

class BaseLoader(ABC):
    """Abstract base class for loading a single coding system into the DB.

    Subclasses must set ``system_name`` and ``model_class`` and implement
    ``_load_from_source``.
    """

    system_name: str = ""
    """Human-readable system label (e.g. ``'SNOMED CT'``)."""

    model_class: Type[Base] | None = None
    """The ORM model this loader populates (e.g. ``SnomedCode``)."""

    def load(self, session) -> int:
        """Public entry point – loads data & commits."""
        logger.info(f"Loading {self.system_name}...")
        start = time.perf_counter()

        count = self._load_from_source(session)
        if count == 0:
            logger.warning(f"  {self.system_name}: no data loaded from source files")

        session.commit()
        elapsed = time.perf_counter() - start
        logger.info(f"Loaded {count:,} {self.system_name} codes ({elapsed:.1f}s).")
        return count

    @abstractmethod
    def _load_from_source(self, session) -> int:
        """Load from the real data files.  Return number of records loaded."""
        ...


# ──────────────────────────────────────────────────────────────────────────────
#  BaseMapper
# ──────────────────────────────────────────────────────────────────────────────

class BaseMapper(ABC):
    """Abstract base class for building a cross-system mapping.

    Subclasses must set ``mapping_name`` and implement ``_build_from_source``.
    """

    mapping_name: str = ""
    """Human-readable mapping label (e.g. ``'SNOMED → ICD-10-CM'``)."""

    def build(self, session) -> int:
        """Public entry point – builds the mapping & commits."""
        logger.info(f"Building {self.mapping_name} mappings...")
        start = time.perf_counter()

        count = self._build_from_source(session)
        if count == 0:
            logger.warning(f"  {self.mapping_name}: no mappings built from source files")

        session.commit()
        elapsed = time.perf_counter() - start
        logger.info(f"Built {count:,} {self.mapping_name} mappings ({elapsed:.1f}s).")
        return count

    @abstractmethod
    def _build_from_source(self, session) -> int:
        """Build mappings from real data files.  Return count inserted."""
        ...


# ──────────────────────────────────────────────────────────────────────────────
#  BasePipeline
# ──────────────────────────────────────────────────────────────────────────────

class BasePipeline:
    """Orchestrates a sequence of loaders and mappers.

    Parameters
    ----------
    loaders : list[BaseLoader]
        Ordered list of code-set loaders to execute in *Step 1*.
    direct_mappers : list[BaseMapper]
        Direct (file-based) mappers executed in *Step 2*.
    derived_mappers : list[BaseMapper]
        Transitive / cross-system mappers executed in *Step 3*.
    """

    def __init__(
        self,
        loaders: List[BaseLoader],
        direct_mappers: List[BaseMapper],
        derived_mappers: List[BaseMapper],
    ):
        self.loaders = loaders
        self.direct_mappers = direct_mappers
        self.derived_mappers = derived_mappers

    def run(self) -> None:
        """Execute the full pipeline: init → load → map → summarise."""
        logger.info("=" * 70)
        logger.info("  Coding Manager - Data Processing Pipeline")
        logger.info("=" * 70)

        engine = init_db()
        session = get_session()

        try:
            self._run_phase(session, "Step 1: Loading Code Sets", self.loaders, "load")
            self._run_phase(session, "Step 2: Building Direct Mappings", self.direct_mappers, "build")
            self._run_phase(session, "Step 3: Building Transitive & Cross-System Mappings", self.derived_mappers, "build")
            self._print_summary(session)
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            session.rollback()
            raise
        finally:
            session.close()

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _run_phase(session, title: str, steps, method_name: str) -> None:
        logger.info(f"\n-- {title} " + "-" * (52 - len(title)))
        for step in steps:
            label = getattr(step, "system_name", None) or getattr(step, "mapping_name", "?")
            try:
                getattr(step, method_name)(session)
            except Exception as e:
                logger.error(f"  Error in {label}: {e}")
                session.rollback()

    @staticmethod
    def _print_summary(session) -> None:
        from pipeline.models import (
            SnomedCode, ICD10Code, HCCCode, CPTCode, HCPCSCode, RxNormCode, NDCCode,
            snomed_icd10_mapping, icd10_hcc_mapping, snomed_hcc_mapping,
            rxnorm_snomed_mapping,
        )

        snomed_count = session.query(SnomedCode).count()
        icd10_count = session.query(ICD10Code).count()
        hcc_count = session.query(HCCCode).count()
        cpt_count = session.query(CPTCode).count()
        hcpcs_count = session.query(HCPCSCode).count()
        rxnorm_count = session.query(RxNormCode).count()
        ndc_count = session.query(NDCCode).count()
        dhs_cpt = session.query(CPTCode).filter(CPTCode.dhs_category.isnot(None)).count()
        dhs_hcpcs = session.query(HCPCSCode).filter(HCPCSCode.dhs_category.isnot(None)).count()

        si = len(session.execute(snomed_icd10_mapping.select()).fetchall())
        ih = len(session.execute(icd10_hcc_mapping.select()).fetchall())
        sh = len(session.execute(snomed_hcc_mapping.select()).fetchall())
        rs = len(session.execute(rxnorm_snomed_mapping.select()).fetchall())

        logger.info("\n" + "=" * 70)
        logger.info("  Pipeline Summary")
        logger.info("=" * 70)
        logger.info(f"  SNOMED CT codes:      {snomed_count:>10,}")
        logger.info(f"  ICD-10-CM codes:      {icd10_count:>10,}")
        logger.info(f"  HCC codes:            {hcc_count:>10,}")
        logger.info(f"  CPT codes:            {cpt_count:>10,}  (DHS-tagged: {dhs_cpt})")
        logger.info(f"  HCPCS codes:          {hcpcs_count:>10,}  (DHS-tagged: {dhs_hcpcs})")
        logger.info(f"  RxNorm codes:         {rxnorm_count:>10,}")
        logger.info(f"  NDC codes:            {ndc_count:>10,}")
        logger.info(f"  -------------------------------------")
        logger.info(f"  SNOMED->ICD-10 maps:  {si:>10,}")
        logger.info(f"  ICD-10->HCC maps:     {ih:>10,}")
        logger.info(f"  SNOMED->HCC maps:     {sh:>10,}")
        logger.info(f"  RxNorm<->SNOMED maps: {rs:>10,}")
        logger.info("=" * 70)
        logger.info("  Pipeline completed successfully!")
