#!/usr/bin/env python
"""
Resolve Mapping Conflicts

Command-line tool to automatically resolve mapping conflicts using various strategies:
- Fuzzy matching for close code matches
- Invalid code detection and ignoring
- Placeholder code creation (optional)

Usage:
    python -m backend.pipeline.resolve_conflicts --help
    python -m backend.pipeline.resolve_conflicts --dry-run --limit 100
    python -m backend.pipeline.resolve_conflicts --fuzzy-threshold 0.9
    python -m backend.pipeline.resolve_conflicts --create-placeholders
"""

import argparse
import logging
import sys
from datetime import datetime

from pipeline.conflict_resolvers import auto_resolve_conflicts


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Automatically resolve mapping conflicts in the coding manager database"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of conflicts to process (default: all)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test resolution without saving changes"
    )
    
    parser.add_argument(
        "--fuzzy-threshold",
        type=float,
        default=0.85,
        help="Similarity threshold for fuzzy matching (0.0-1.0, default: 0.85)"
    )
    
    parser.add_argument(
        "--skip-fuzzy",
        action="store_true",
        help="Skip fuzzy matching (faster, only ignore invalid codes)"
    )
    
    parser.add_argument(
        "--create-placeholders",
        action="store_true",
        help="Create placeholder codes for missing targets (marks them inactive)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate args
    if not 0.0 <= args.fuzzy_threshold <= 1.0:
        logger.error("Fuzzy threshold must be between 0.0 and 1.0")
        sys.exit(1)
    
    # Run resolution
    logger.info("="*60)
    logger.info("Conflict Resolution Started")
    logger.info("="*60)
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Limit: {args.limit or 'All conflicts'}")
    logger.info(f"Skip fuzzy matching: {args.skip_fuzzy}")
    if not args.skip_fuzzy:
        logger.info(f"Fuzzy threshold: {args.fuzzy_threshold}")
    logger.info(f"Create placeholders: {args.create_placeholders}")
    logger.info("")
    
    start_time = datetime.now()
    
    try:
        from pipeline.conflict_resolvers import (
            BulkConflictResolver, InvalidCodeIgnorer, ICD10FuzzyMatcher,
            MissingICD10Creator
        )
        from pipeline.models import get_session
        
        session = get_session()
        resolver = BulkConflictResolver(session)
        
        # Strategy 1: Ignore obviously invalid codes (always enabled)
        resolver.add_strategy(InvalidCodeIgnorer(session))
        
        # Strategy 2: Fuzzy match ICD-10 codes (optional)
        if not args.skip_fuzzy:
            resolver.add_strategy(ICD10FuzzyMatcher(session, similarity_threshold=args.fuzzy_threshold))
        
        # Strategy 3: Create placeholders (if enabled)
        if args.create_placeholders:
            resolver.add_strategy(MissingICD10Creator(session, create_placeholders=True))
        
        stats = resolver.resolve_all(limit=args.limit)
        
        if args.dry_run:
            session.rollback()
            logger.info("Dry run complete - changes rolled back")
        else:
            session.commit()
            logger.info("Changes committed to database")
        
        session.close()
        
        # Print results
        elapsed = (datetime.now() - start_time).total_seconds()
        
        logger.info("")
        logger.info("="*60)
        logger.info("Resolution Complete")
        logger.info("="*60)
        logger.info(f"Total processed: {stats['total_processed']}")
        logger.info(f"Resolved: {stats['resolved']}")
        logger.info(f"Ignored: {stats['ignored']}")
        logger.info(f"Unresolved: {stats['unresolved']}")
        logger.info(f"Time elapsed: {elapsed:.2f}s")
        
        if args.dry_run:
            logger.info("")
            logger.info(" DRY RUN - No changes saved to database")
        
        logger.info("="*60)
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Resolution failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
