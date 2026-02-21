"""
Conflict Resolution Strategies for Medical Coding Pipeline

Provides automated strategies to resolve mapping conflicts detected during
data processing. Each resolver can automatically fix common issues like:
- Missing target codes with fuzzy matching
- Deprecated code versions
- Format mismatches
- Invalid code references
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple
from difflib import SequenceMatcher

from pipeline.models import (
    get_session, MappingConflict, ICD10Code, SnomedCode, HCCCode,
    snomed_icd10_mapping, icd10_hcc_mapping
)

logger = logging.getLogger(__name__)


class ConflictResolver:
    """Base class for conflict resolution strategies."""
    
    def __init__(self, session):
        self.session = session
        self.stats = {
            "total_processed": 0,
            "resolved": 0,
            "ignored": 0,
            "fuzzy_matched": 0,
            "invalid_codes": 0,
        }
    
    def resolve(self, conflict: MappingConflict) -> bool:
        """
        Attempt to resolve a single conflict.
        
        Returns True if resolved, False otherwise.
        Subclasses should override this method.
        """
        raise NotImplementedError
    
    def log_stats(self):
        """Log resolution statistics."""
        logger.info(f"Resolution stats: {self.stats}")


class ICD10FuzzyMatcher(ConflictResolver):
    """
    Resolves SNOMED→ICD-10 conflicts by finding close ICD-10 code matches.
    
    When the exact ICD-10 code doesn't exist, tries to find:
    1. Same code without decimal (e.g., E11.9 → E119)
    2. Same code with decimal added (e.g., E119 → E11.9)
    3. Closest matching code by string similarity
    """
    
    def __init__(self, session, similarity_threshold: float = 0.9):
        super().__init__(session)
        self.similarity_threshold = similarity_threshold
        self._icd10_codes_cache: Optional[Set[str]] = None
        self._icd10_map_cache: Optional[Dict[str, str]] = None
    
    def _load_icd10_codes(self):
        """Load all valid ICD-10 codes into memory for fast lookup."""
        if self._icd10_codes_cache is None:
            codes = self.session.query(ICD10Code.code).all()
            self._icd10_codes_cache = {c[0] for c in codes}
            logger.info(f"Loaded {len(self._icd10_codes_cache)} ICD-10 codes for fuzzy matching")
    
    def _get_icd10_code_map(self) -> Dict[str, str]:
        """Create normalized code map (both with/without decimals)."""
        if self._icd10_map_cache is None:
            self._load_icd10_codes()
            self._icd10_map_cache = {}
            
            for code in self._icd10_codes_cache:
                # Store as-is
                self._icd10_map_cache[code] = code
                
                # Store normalized version (no decimal)
                normalized = code.replace(".", "")
                if normalized not in self._icd10_map_cache:
                    self._icd10_map_cache[normalized] = code
        
        return self._icd10_map_cache
    
    def _format_icd10_variants(self, code: str) -> List[str]:
        """Generate possible format variants of an ICD-10 code."""
        variants = [code]
        
        # Try with/without decimal
        if "." in code:
            variants.append(code.replace(".", ""))
        else:
            # Try adding decimal before last digit, last 2 digits, etc.
            if len(code) >= 4:
                variants.append(f"{code[:3]}.{code[3:]}")
            if len(code) >= 5:
                variants.append(f"{code[:4]}.{code[4:]}")
        
        # Try with uppercase
        variants.append(code.upper())
        
        return list(set(variants))
    
    def _find_close_match(self, target_code: str, max_distance: int = 1) -> Optional[str]:
        """Find closest matching ICD-10 code using fuzzy string matching."""
        self._load_icd10_codes()
        
        best_match = None
        best_ratio = 0.0
        
        # Quick check for exact variants first
        variants = self._format_icd10_variants(target_code)
        code_map = self._get_icd10_code_map()
        
        for variant in variants:
            if variant in code_map:
                return code_map[variant]
        
        # If no exact match, try fuzzy matching on similar length codes
        # Limit candidates by prefix matching for performance
        target_len = len(target_code)
        target_prefix = target_code[:3].upper() if len(target_code) >= 3 else target_code.upper()
        
        candidates = [c for c in self._icd10_codes_cache 
                     if abs(len(c) - target_len) <= 2 
                     and c[:3].upper() == target_prefix]
        
        # If no prefix matches, try broader search but limit to 100 candidates
        if not candidates:
            candidates = [c for c in self._icd10_codes_cache 
                         if abs(len(c) - target_len) <= 1][:100]
        
        for candidate in candidates:
            ratio = SequenceMatcher(None, target_code.upper(), candidate.upper()).ratio()
            if ratio >= self.similarity_threshold and ratio > best_ratio:
                best_ratio = ratio
                best_match = candidate
        
        return best_match
    
    def resolve(self, conflict: MappingConflict) -> bool:
        """Resolve SNOMED→ICD-10 target_not_found conflicts."""
        self.stats["total_processed"] += 1
        
        if conflict.reason != "target_not_found":
            return False
        
        if conflict.source_system != "SNOMED" or conflict.target_system != "ICD-10":
            return False
        
        # Try to find a close match for the missing ICD-10 code
        matched_code = self._find_close_match(conflict.target_code)
        
        if matched_code:
            # Found a match - create the mapping
            try:
                self.session.execute(
                    snomed_icd10_mapping.insert(),
                    [{
                        "snomed_code": conflict.source_code,
                        "icd10_code": matched_code,
                        "map_group": 1,
                        "map_priority": 1,
                        "map_rule": "AUTO-RESOLVED: Fuzzy matched",
                        "map_advice": f"Original target: {conflict.target_code}",
                        "correlation_id": "AUTO",
                        "map_category_id": "AUTO",
                        "active": True,
                    }]
                )
                
                conflict.status = "resolved"
                conflict.resolved_code = matched_code
                conflict.resolution = f"Fuzzy matched '{conflict.target_code}' to '{matched_code}'"
                
                self.stats["resolved"] += 1
                self.stats["fuzzy_matched"] += 1
                return True
                
            except Exception as e:
                logger.warning(f"Failed to create mapping for {conflict.source_code}→{matched_code}: {e}")
                return False
        
        return False


class InvalidCodeIgnorer(ConflictResolver):
    """
    Automatically ignores conflicts with invalid or malformed codes.
    
    Patterns to ignore:
    - Empty codes
    - Placeholder codes (XXXXX, 00000, etc.)
    - Codes with invalid characters
    - Codes that don't match system format rules
    """
    
    INVALID_PATTERNS = [
        r"^X+$",           # XXXXX
        r"^0+$",           # 00000
        r"^\s*$",          # Empty/whitespace
        r"^N/A$",          # N/A
        r"^NONE$",         # NONE
        r"^TBD$",          # TBD
        r"[^A-Z0-9\.]",    # Invalid chars for medical codes
    ]
    
    def __init__(self, session):
        super().__init__(session)
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.INVALID_PATTERNS]
    
    def _is_invalid(self, code: str) -> bool:
        """Check if code matches any invalid pattern."""
        if not code or len(code.strip()) == 0:
            return True
        
        for pattern in self.patterns:
            if pattern.search(code):
                return True
        
        return False
    
    def resolve(self, conflict: MappingConflict) -> bool:
        """Ignore conflicts with invalid codes."""
        self.stats["total_processed"] += 1
        
        if self._is_invalid(conflict.target_code):
            conflict.status = "ignored"
            conflict.resolution = f"Invalid target code format: '{conflict.target_code}'"
            self.stats["ignored"] += 1
            self.stats["invalid_codes"] += 1
            return True
        
        if self._is_invalid(conflict.source_code):
            conflict.status = "ignored"
            conflict.resolution = f"Invalid source code format: '{conflict.source_code}'"
            self.stats["ignored"] += 1
            self.stats["invalid_codes"] += 1
            return True
        
        return False


class MissingICD10Creator(ConflictResolver):
    """
    Creates placeholder ICD-10 code entries for missing codes.
    
    When a SNOMED→ICD-10 mapping references a non-existent ICD-10 code,
    this resolver creates a placeholder entry marked as inactive.
    This allows the mapping to exist while flagging the code as questionable.
    """
    
    def __init__(self, session, create_placeholders: bool = False):
        super().__init__(session)
        self.create_placeholders = create_placeholders
        self._created_codes: Set[str] = set()
    
    def _create_placeholder_icd10(self, code: str) -> bool:
        """Create a placeholder ICD-10 code entry."""
        if code in self._created_codes:
            return True  # Already created
        
        try:
            # Determine category from code prefix
            category = code[:3] if len(code) >= 3 else "UNKNOWN"
            
            icd10 = ICD10Code(
                code=code,
                description=f"[PLACEHOLDER] Code referenced in mapping but not in source data",
                category=category,
                billable=False,
                active=False,  # Mark as inactive
            )
            self.session.add(icd10)
            self._created_codes.add(code)
            return True
            
        except Exception as e:
            logger.warning(f"Failed to create placeholder ICD-10 code {code}: {e}")
            return False
    
    def resolve(self, conflict: MappingConflict) -> bool:
        """Create placeholder codes and resolve mappings."""
        self.stats["total_processed"] += 1
        
        if not self.create_placeholders:
            return False
        
        if conflict.reason != "target_not_found":
            return False
        
        if conflict.source_system != "SNOMED" or conflict.target_system != "ICD-10":
            return False
        
        # Create the placeholder ICD-10 code
        if self._create_placeholder_icd10(conflict.target_code):
            try:
                # Create the mapping
                self.session.execute(
                    snomed_icd10_mapping.insert(),
                    [{
                        "snomed_code": conflict.source_code,
                        "icd10_code": conflict.target_code,
                        "map_group": 1,
                        "map_priority": 1,
                        "map_rule": "AUTO-RESOLVED: Placeholder created",
                        "map_advice": "Target code created as inactive placeholder",
                        "correlation_id": "AUTO",
                        "map_category_id": "AUTO",
                        "active": True,
                    }]
                )
                
                conflict.status = "resolved"
                conflict.resolved_code = conflict.target_code
                conflict.resolution = f"Created placeholder ICD-10 code (inactive)"
                
                self.stats["resolved"] += 1
                return True
                
            except Exception as e:
                logger.warning(f"Failed to create mapping after placeholder: {e}")
                return False
        
        return False


class BulkConflictResolver:
    """
    Orchestrates multiple resolution strategies in priority order.
    
    Usage:
        resolver = BulkConflictResolver(session)
        resolver.add_strategy(InvalidCodeIgnorer(session))
        resolver.add_strategy(ICD10FuzzyMatcher(session, similarity_threshold=0.85))
        resolver.resolve_all(limit=10000)
    """
    
    def __init__(self, session):
        self.session = session
        self.strategies: List[ConflictResolver] = []
    
    def add_strategy(self, strategy: ConflictResolver):
        """Add a resolution strategy (order matters - first match wins)."""
        self.strategies.append(strategy)
    
    def resolve_all(
        self, 
        limit: Optional[int] = None,
        status: str = "open",
        commit_interval: int = 1000
    ) -> Dict[str, int]:
        """
        Resolve all conflicts using registered strategies.
        
        Args:
            limit: Maximum number of conflicts to process
            status: Only process conflicts with this status ('open' by default)
            commit_interval: Commit changes every N conflicts
        
        Returns:
            Dictionary with resolution statistics
        """
        query = self.session.query(MappingConflict).filter(
            MappingConflict.status == status
        )
        
        if limit:
            query = query.limit(limit)
        
        conflicts = query.all()
        total = len(conflicts)
        
        logger.info(f"Processing {total} conflicts with {len(self.strategies)} strategies")
        
        resolved_count = 0
        ignored_count = 0
        unresolved_count = 0
        
        for idx, conflict in enumerate(conflicts, 1):
            resolved = False
            
            # Try each strategy in order
            for strategy in self.strategies:
                if strategy.resolve(conflict):
                    resolved = True
                    if conflict.status == "resolved":
                        resolved_count += 1
                    elif conflict.status == "ignored":
                        ignored_count += 1
                    break
            
            if not resolved:
                unresolved_count += 1
            
            # Periodic commit
            if idx % commit_interval == 0:
                self.session.commit()
                logger.info(f"Progress: {idx}/{total} conflicts processed "
                           f"(resolved: {resolved_count}, ignored: {ignored_count})")
        
        # Final commit
        self.session.commit()
        
        # Log strategy stats
        for strategy in self.strategies:
            strategy.log_stats()
        
        stats = {
            "total_processed": total,
            "resolved": resolved_count,
            "ignored": ignored_count,
            "unresolved": unresolved_count,
        }
        
        logger.info(f"Conflict resolution complete: {stats}")
        return stats


def auto_resolve_conflicts(
    limit: Optional[int] = None,
    dry_run: bool = False,
    fuzzy_threshold: float = 0.85,
    create_placeholders: bool = False
) -> Dict[str, int]:
    """
    Convenience function to auto-resolve conflicts with default strategies.
    
    Args:
        limit: Max conflicts to process (None = all)
        dry_run: If True, rollback changes (for testing)
        fuzzy_threshold: Similarity threshold for fuzzy matching (0.0-1.0)
        create_placeholders: If True, create placeholder codes for missing targets
    
    Returns:
        Dictionary with resolution statistics
    """
    session = get_session()
    
    try:
        resolver = BulkConflictResolver(session)
        
        # Strategy 1: Ignore obviously invalid codes
        resolver.add_strategy(InvalidCodeIgnorer(session))
        
        # Strategy 2: Fuzzy match ICD-10 codes
        resolver.add_strategy(ICD10FuzzyMatcher(session, similarity_threshold=fuzzy_threshold))
        
        # Strategy 3: Create placeholders (if enabled)
        if create_placeholders:
            resolver.add_strategy(MissingICD10Creator(session, create_placeholders=True))
        
        stats = resolver.resolve_all(limit=limit)
        
        if dry_run:
            session.rollback()
            logger.info("Dry run complete - changes rolled back")
        else:
            session.commit()
            logger.info("Changes committed to database")
        
        return stats
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error during conflict resolution: {e}")
        raise
    finally:
        session.close()
