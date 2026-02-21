"""
Export SQLite database for browser consumption via sql.js.

Creates an optimized, indexed SQLite database file that can be loaded
in the browser using sql.js. This file is used for GitHub Pages deployment
where no backend API is available.

Usage:
    cd backend
    python -m pipeline.export_sqlite_browser [--output PATH] [--compress]
"""

import argparse
import gzip
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

# Ensure parent path is available
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.models import DB_PATH

# ─── Configuration ────────────────────────────────────────────────────────────

DEFAULT_OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend", "public", "data", "coding_database.sqlite"
)


# ─── Export Functions ─────────────────────────────────────────────────────────

def get_table_schema(cursor: sqlite3.Cursor, table_name: str) -> str:
    """Get CREATE TABLE SQL statement for a table."""
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    result = cursor.fetchone()
    return result[0] if result else None


def get_all_tables(cursor: sqlite3.Cursor) -> list[str]:
    """Get list of all table names in the database."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return [row[0] for row in cursor.fetchall()]


def get_all_indexes(cursor: sqlite3.Cursor) -> list[tuple[str, str]]:
    """Get list of all indexes with their SQL statements."""
    cursor.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
    )
    return cursor.fetchall()


def copy_table_data(source_cursor: sqlite3.Cursor, target_cursor: sqlite3.Cursor, 
                    table_name: str, batch_size: int = 5000) -> int:
    """Copy all data from source table to target table in batches."""
    # Get column names
    source_cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in source_cursor.fetchall()]
    col_list = ", ".join(columns)
    placeholders = ", ".join(["?"] * len(columns))
    
    # Count total rows
    source_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    total = source_cursor.fetchone()[0]
    
    if total == 0:
        return 0
    
    # Copy data in batches
    offset = 0
    copied = 0
    
    while offset < total:
        source_cursor.execute(
            f"SELECT {col_list} FROM {table_name} LIMIT ? OFFSET ?",
            (batch_size, offset)
        )
        rows = source_cursor.fetchall()
        
        if not rows:
            break
        
        target_cursor.executemany(
            f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})",
            rows
        )
        
        copied += len(rows)
        offset += batch_size
        
        # Progress indicator
        if copied % 10000 == 0 or copied == total:
            print(f"    {table_name}: {copied:,}/{total:,} rows", end="\r")
    
    print(f"    {table_name}: {copied:,}/{total:,} rows ✓")
    return copied


def create_browser_indexes(cursor: sqlite3.Cursor) -> None:
    """Create optimized indexes for browser-side queries."""
    print("\n  Creating optimized indexes...")
    
    indexes = [
        # Code lookups
        ("idx_snomed_code_browser", "snomed_codes", "code"),
        ("idx_icd10_code_browser", "icd10_codes", "code"),
        ("idx_hcc_code_browser", "hcc_codes", "code"),
        ("idx_cpt_code_browser", "cpt_codes", "code"),
        ("idx_hcpcs_code_browser", "hcpcs_codes", "code"),
        ("idx_rxnorm_code_browser", "rxnorm_codes", "code"),
        ("idx_ndc_code_browser", "ndc_codes", "code"),
        
        # Text search indexes
        ("idx_snomed_term_browser", "snomed_codes", "term"),
        ("idx_icd10_desc_browser", "icd10_codes", "description"),
        ("idx_cpt_desc_browser", "cpt_codes", "description"),
        ("idx_hcpcs_desc_browser", "hcpcs_codes", "description"),
        ("idx_rxnorm_name_browser", "rxnorm_codes", "description"),
        
        # Active flag indexes
        ("idx_snomed_active_browser", "snomed_codes", "active"),
        ("idx_icd10_active_browser", "icd10_codes", "active"),
        
        # Mapping lookups
        ("idx_snomed_icd10_snomed_browser", "snomed_icd10_mapping", "snomed_code"),
        ("idx_snomed_icd10_icd10_browser", "snomed_icd10_mapping", "icd10_code"),
        ("idx_snomed_hcc_snomed_browser", "snomed_hcc_mapping", "snomed_code"),
        ("idx_snomed_hcc_hcc_browser", "snomed_hcc_mapping", "hcc_code"),
        ("idx_icd10_hcc_icd10_browser", "icd10_hcc_mapping", "icd10_code"),
        ("idx_icd10_hcc_hcc_browser", "icd10_hcc_mapping", "hcc_code"),
        ("idx_rxnorm_snomed_rxnorm_browser", "rxnorm_snomed_mapping", "rxnorm_code"),
        ("idx_rxnorm_snomed_snomed_browser", "rxnorm_snomed_mapping", "snomed_code"),
        ("idx_ndc_rxnorm_ndc_browser", "ndc_rxnorm_mapping", "ndc_code"),
        ("idx_ndc_rxnorm_rxnorm_browser", "ndc_rxnorm_mapping", "rxnorm_code"),
    ]
    
    for idx_name, table_name, column_name in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name}({column_name})")
            print(f"    ✓ {idx_name}")
        except Exception as e:
            print(f"    ✗ {idx_name}: {e}")


def optimize_database(cursor: sqlite3.Cursor) -> None:
    """Run VACUUM and ANALYZE to optimize the database."""
    print("\n  Optimizing database...")
    cursor.execute("VACUUM")
    cursor.execute("ANALYZE")
    print("    ✓ Database optimized")


def export_browser_sqlite(output_path: str, compress: bool = True) -> None:
    """
    Export the existing SQLite database to a browser-optimized format.
    
    Args:
        output_path: Path to output SQLite file
        compress: If True, also create a gzipped version
    """
    start_time = time.time()
    
    print("=" * 80)
    print("SQLite Browser Export")
    print("=" * 80)
    print(f"\nSource Database: {DB_PATH}")
    print(f"Target Database: {output_path}")
    
    # Check source database exists
    if not os.path.exists(DB_PATH):
        print(f"\n❌ ERROR: Source database not found at {DB_PATH}")
        print("   Run the pipeline first: python -m pipeline.pipeline")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Remove existing output file if it exists
    if os.path.exists(output_path):
        os.remove(output_path)
    
    # Connect to source and target databases
    print("\n1. Connecting to databases...")
    source_conn = sqlite3.connect(DB_PATH)
    target_conn = sqlite3.connect(output_path)
    
    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()
    
    try:
        # Get all tables
        print("\n2. Copying table schemas...")
        tables = get_all_tables(source_cursor)
        print(f"   Found {len(tables)} tables")
        
        for table in tables:
            schema = get_table_schema(source_cursor, table)
            if schema:
                target_cursor.execute(schema)
                print(f"    ✓ {table}")
        
        target_conn.commit()
        
        # Copy data for each table
        print("\n3. Copying table data...")
        total_rows = 0
        
        for table in tables:
            rows_copied = copy_table_data(source_cursor, target_cursor, table)
            total_rows += rows_copied
            target_conn.commit()
        
        print(f"\n   Total rows copied: {total_rows:,}")
        
        # Create browser-optimized indexes
        print("\n4. Creating browser-optimized indexes...")
        create_browser_indexes(target_cursor)
        target_conn.commit()
        
        # Optimize database
        print("\n5. Optimizing database...")
        optimize_database(target_cursor)
        target_conn.commit()
        
    finally:
        source_cursor.close()
        target_cursor.close()
        source_conn.close()
        target_conn.close()
    
    # Get file size
    file_size = os.path.getsize(output_path)
    file_size_mb = file_size / (1024 * 1024)
    
    print(f"\n6. Database export complete!")
    print(f"   Size: {file_size_mb:.2f} MB ({file_size:,} bytes)")
    
    # Compress if requested
    if compress:
        print("\n7. Compressing database...")
        gzip_path = f"{output_path}.gz"
        
        with open(output_path, 'rb') as f_in:
            with gzip.open(gzip_path, 'wb', compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        gzip_size = os.path.getsize(gzip_path)
        gzip_size_mb = gzip_size / (1024 * 1024)
        compression_ratio = (1 - gzip_size / file_size) * 100
        
        print(f"   Compressed size: {gzip_size_mb:.2f} MB ({gzip_size:,} bytes)")
        print(f"   Compression ratio: {compression_ratio:.1f}%")
        print(f"   Gzipped file: {gzip_path}")
    
    elapsed = time.time() - start_time
    print(f"\n✓ Export completed in {elapsed:.1f} seconds")
    print("=" * 80)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Export SQLite database for browser consumption via sql.js"
    )
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_OUTPUT,
        help=f"Output path for SQLite file (default: {DEFAULT_OUTPUT})"
    )
    parser.add_argument(
        "--compress", "-c",
        action="store_true",
        help="Also create a gzipped version (.gz)"
    )
    
    args = parser.parse_args()
    
    export_browser_sqlite(args.output, args.compress)


if __name__ == "__main__":
    main()
