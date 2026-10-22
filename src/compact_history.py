#!/usr/bin/env python3
"""
H3-Earth-State Long-Term Compaction Engine
Autonomously consolidates completed historical months into a single,
high-density ZSTD-compressed Parquet archive with atomic row-count verification.
"""

import os
import glob
import logging
from datetime import datetime, timezone
import duckdb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SNAPSHOTS_DIR = "snapshots"

def get_completed_month_directories() -> list:
    """
    Finds all year/month directory paths that belong to past calendar months.
    Does not compact the current ongoing month.
    """
    now = datetime.now(timezone.utc)
    current_year_str = now.strftime("%Y")
    current_month_str = now.strftime("%m")
    current_active_folder = f"year={current_year_str}/month={current_month_str}"

    month_dirs = []
    pattern = os.path.join(SNAPSHOTS_DIR, "year=*", "month=*")
    
    for path in glob.glob(pattern):
        # Normalize path separators for cross-platform matching
        norm_path = path.replace("\\", "/")
        if not norm_path.endswith(current_active_folder):
            month_dirs.append(norm_path)

    return sorted(month_dirs)

def compact_month_directory(month_dir: str):
    """Combines daily Parquet files into a single consolidated.parquet."""
    consolidated_path = os.path.join(month_dir, "consolidated.parquet").replace("\\", "/")
    
    # Locate all individual daily parquet files, excluding consolidated.parquet
    daily_files = [
        f.replace("\\", "/") for f in glob.glob(os.path.join(month_dir, "*.parquet"))
        if not f.endswith("consolidated.parquet")
    ]

    if not daily_files:
        logging.info(f"Directory {month_dir} already consolidated or empty. Skipping.")
        return

    logging.info(f"Starting compaction for {month_dir} ({len(daily_files)} daily files detected)...")

    con = duckdb.connect(database=":memory:")
    try:
        # 1. Calculate pre-compaction total row count across all daily files
        total_source_rows = 0
        for f in daily_files:
            rows = con.execute(f"SELECT COUNT(*) FROM read_parquet('{f}')").fetchone()[0]
            total_source_rows += rows

        logging.info(f"Source files verified: {total_source_rows} total rows to consolidate.")

        # 2. Write consolidated Parquet file with high-ratio ZSTD compression
        temp_consolidated_path = consolidated_path + ".tmp"
        daily_glob = os.path.join(month_dir, "20*.parquet").replace("\\", "/")

        con.execute(f"""
            COPY (
                SELECT * 
                FROM read_parquet('{daily_glob}')
                ORDER BY date ASC, h3_res6_id ASC
            ) TO '{temp_consolidated_path}' (
                FORMAT PARQUET, 
                COMPRESSION ZSTD, 
                COMPRESSION_LEVEL 15
            );
        """)

        # 3. Assert atomic row parity
        consolidated_rows = con.execute(f"SELECT COUNT(*) FROM read_parquet('{temp_consolidated_path}')").fetchone()[0]

        if consolidated_rows != total_source_rows:
            os.remove(temp_consolidated_path)
            raise AssertionError(
                f"Row parity mismatch in {month_dir}! Source had {total_source_rows}, "
                f"but consolidated file had {consolidated_rows}. Compaction aborted."
            )

        # 4. Safely replace with confirmed consolidated file
        if os.path.exists(consolidated_path):
            os.remove(consolidated_path)
        os.rename(temp_consolidated_path, consolidated_path)

        # 5. Remove original loose daily files
        removed_bytes = 0
        for f in daily_files:
            removed_bytes += os.path.getsize(f)
            os.remove(f)

        new_size_bytes = os.path.getsize(consolidated_path)
        compression_ratio = ((removed_bytes - new_size_bytes) / removed_bytes) * 100 if removed_bytes else 0

        logging.info(
            f"✓ Compaction successful for {month_dir}: {len(daily_files)} files -> 1 file. "
            f"Preserved {consolidated_rows} rows. Size reduced by {compression_ratio:.1f}%."
        )

    except Exception as e:
        logging.error(f"Compaction failed for {month_dir}: {e}")
        temp_file = consolidated_path + ".tmp"
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise
    finally:
        con.close()

def run():
    logging.info("Checking for completed calendar months requiring historical compaction...")
    target_months = get_completed_month_directories()

    if not target_months:
        logging.info("No completed historical months eligible for compaction.")
        return

    for month_dir in target_months:
        compact_month_directory(month_dir)

if __name__ == "__main__":
    run()
