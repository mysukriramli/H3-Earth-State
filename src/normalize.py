#!/usr/bin/env python3
"""
H3-Earth-State Normalization Engine
Uses DuckDB to aggregate raw, multi-modal JSONL event streams into a 
unified, mathematical H3 spatio-temporal grid.
"""

import os
import duckdb
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

INPUT_FILE = "latest/events.jsonl"
LATEST_JSON_OUT = "latest/world_state.json"
SNAPSHOT_BASE_DIR = "snapshots"

def run():
    logging.info("Starting DuckDB Normalization Engine...")

    if not os.path.exists(INPUT_FILE) or os.path.getsize(INPUT_FILE) == 0:
        logging.warning(f"No data found in {INPUT_FILE}. Skipping normalization.")
        return

    # Determine dynamic archive path based on today's UTC date
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    year_str = now.strftime("%Y")
    month_str = now.strftime("%m")

    archive_dir = os.path.join(SNAPSHOT_BASE_DIR, f"year={year_str}", f"month={month_str}")
    os.makedirs(archive_dir, exist_ok=True)
    parquet_out = os.path.join(archive_dir, f"{date_str}.parquet")

    # Connect to an in-memory DuckDB instance
    con = duckdb.connect(database=':memory:')

    try:
        # Step 1: Read heterogeneous JSONL safely as raw JSON objects
        # This prevents schema inference crashes when different events have different attributes.
        con.execute(f"""
            CREATE TEMP TABLE raw_events AS
            SELECT
                json_extract_string(json, '$.h3_res6_id') AS h3_res6_id,
                CAST(json_extract_string(json, '$.timestamp') AS DATE) AS event_date,
                json_extract_string(json, '$.modality') AS modality,
                json_extract_string(json, '$.attributes') AS attributes
            FROM read_json_objects('{INPUT_FILE}');
        """)

        # Step 2: Aggregate into the Canonical World State Grid
        # Group by H3 Hexagon and Date to create a single unified node state.
        con.execute("""
            CREATE TEMP TABLE world_state AS
            SELECT
                h3_res6_id,
                event_date AS date,
                COUNT(CASE WHEN modality = 'human_events' THEN 1 END)::INT AS human_event_count,
                COALESCE(MAX(TRY_CAST(json_extract_string(attributes, '$.frp_mw') AS DOUBLE)), 0.0) AS max_thermal_intensity_mw,
                COALESCE(MAX(TRY_CAST(json_extract_string(attributes, '$.magnitude') AS DOUBLE)), 0.0) AS max_seismic_magnitude,
                MODE(CASE WHEN modality = 'human_events' THEN json_extract_string(attributes, '$.cameo_event_code') END) AS dominant_cameo_event_code
            FROM raw_events
            WHERE h3_res6_id IS NOT NULL AND h3_res6_id != 'invalid_h3'
            GROUP BY h3_res6_id, event_date;
        """)

        # Step 3: Export to Permanent Parquet Archive
        con.execute(f"COPY world_state TO '{parquet_out}' (FORMAT PARQUET);")
        logging.info(f"Successfully wrote permanent grid snapshot to {parquet_out}")

        # Step 4: Export to Latest JSON for fast Web Agent consumption
        os.makedirs(os.path.dirname(LATEST_JSON_OUT), exist_ok=True)
        con.execute(f"COPY world_state TO '{LATEST_JSON_OUT}' (FORMAT JSON, ARRAY TRUE);")
        logging.info(f"Successfully updated active agent endpoint at {LATEST_JSON_OUT}")

    except Exception as e:
        logging.error(f"DuckDB normalization failed: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    run()
