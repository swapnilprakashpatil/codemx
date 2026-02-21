"""
Data Processing Pipeline for Coding Manager.

**Thin entry point** -- delegates to the refactored pipeline package.
Kept for backwards compatibility with `python -m backend.pipeline.process_data`.

The real implementation lives in:
    pipeline/base.py          -- BaseLoader, BaseMapper, BasePipeline
    pipeline/helpers.py       -- shared utilities (find_zip, bulk_insert, etc.)
    pipeline/loaders/         -- one loader per coding system
    pipeline/mappers/         -- one mapper per cross-system mapping
    pipeline/pipeline.py      -- CodingPipeline orchestrator
"""

import os
import sys

# Add parent directory to path (preserves existing CLI behaviour)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.pipeline import run_pipeline  # noqa: F401, E402


if __name__ == "__main__":
    run_pipeline()
