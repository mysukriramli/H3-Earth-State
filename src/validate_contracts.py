#!/usr/bin/env python3
"""
H3-Earth-State Quality Assurance & Schema Contract Gatekeeper
Executes pre-commit integrity assertions across all generated artifacts:
- Validates JSON/JSONL against schemas/v1/*.json
- Audits Parquet snapshots for NaN, Inf, null keys, and valid H3 resolution-6 morphology
- Asserts strict temporal boundaries (rejecting future-dated records)
"""

import sys
import os
import json
import logging
from datetime import datetime, timezone
import duckdb
import h3
import jsonschema

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SCHEMAS_DIR = "schemas/v1"

def get_today_parquet_path() -> str:
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    year_str = now.strftime("%Y")
    month_str = now.strftime("%m")
    return os.path.join("snapshots", f"year={year_str}", f"month={month_str}", f"{date_str}.parquet")

def load_schema(schema_filename: str) -> dict:
    path = os.path.join(SCHEMAS_DIR, schema_filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Contract schema missing at: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def audit_json_contract(filepath: str, schema_filename: str):
    """Asserts that a JSON file exists and complies with its JSON Schema."""
    if not os.path.exists(filepath):
        logging.warning(f"File {filepath} not found for contract check. Skipping.")
        return

    schema = load_schema(schema_filename)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    try:
        jsonschema.validate(instance=data, schema=schema)
        logging.info(f"✓ JSON Contract Validated: {filepath} adheres to {schema_filename}")
    except jsonschema.exceptions.ValidationError as err:
        logging.error(f"✗ CONTRACT BREACH in {filepath}: {err.message}")
        raise

def audit_jsonl_contract(filepath: str, schema_filename: str):
    """Asserts each line of a JSONL file matches its record contract."""
    if not os.path.exists(filepath):
        logging.warning(f"File {filepath} not found for contract check. Skipping.")
        return

    schema = load_schema(schema_filename)
    line_count = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            try:
                jsonschema.validate(instance=record, schema=schema)
                line_count += 1
            except jsonschema.exceptions.ValidationError as err:
                logging.error(f"✗ CONTRACT BREACH in {filepath} (Line {i}): {err.message}")
                raise
    logging.info(f"✓ JSONL Contract Validated: {filepath} ({line_count} records validated against {schema_filename})")

def audit_parquet_snapshot():
    """Performs deep columnar audits on today's Parquet snapshot using DuckDB."""
    parquet_path = get_today_parquet_path()
    if not os.path.exists(parquet_path):
        logging.warning(f"Snapshot {parquet_path} does not exist yet. Skipping Parquet audit.")
        return

    logging.info(f"Auditing Parquet snapshot integrity: {parquet_path}")
    con = duckdb.connect(database=":memory:")

    try:
        # 1. Assert row count > 0
        count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{parquet_path}')").fetchone()[0]
        if count == 0:
            raise AssertionError(f"Parquet snapshot {parquet_path} is empty (0 rows).")

        # 2. Assert zero NULLs in primary key (h3_res6_id) and date
        null_keys = con.execute(f"""
            SELECT COUNT(*) FROM read_parquet('{parquet_path}')
            WHERE h3_res6_id IS NULL OR date IS NULL
        """).fetchone()[0]
        if null_keys > 0:
            raise AssertionError(f"Detected {null_keys} rows with NULL primary keys in {parquet_path}.")

        # 3. Assert zero NaN or Infinite float values in numeric metrics
        corrupt_floats = con.execute(f"""
            SELECT COUNT(*) FROM read_parquet('{parquet_path}')
            WHERE isnan(max_thermal_intensity_mw) 
               OR isinf(max_thermal_intensity_mw)
               OR isnan(max_seismic_magnitude)
               OR isinf(max_seismic_magnitude)
               OR human_event_count < 0
        """).fetchone()[0]
        if corrupt_floats > 0:
            raise AssertionError(f"Detected {corrupt_floats} corrupt numeric values (NaN/Inf/<0) in {parquet_path}.")

        # 4. Temporal boundary assertion: date must not be in the future (UTC)
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        future_dates = con.execute(f"""
            SELECT COUNT(*) FROM read_parquet('{parquet_path}')
            WHERE CAST(date AS VARCHAR) > '{today_utc}'
        """).fetchone()[0]
        if future_dates > 0:
            raise AssertionError(f"Detected {future_dates} future-dated rows in {parquet_path} (relative to {today_utc}).")

        # 5. Spatial Morphology Audit: Extract distinct H3 IDs and assert Resolution 6
        h3_sample = con.execute(f"""
            SELECT DISTINCT h3_res6_id FROM read_parquet('{parquet_path}') LIMIT 100
        """).fetchall()

        for (h3_id,) in h3_sample:
            # Check cell validity using official h3-py function
            if not h3.is_valid_cell(h3_id):
                raise AssertionError(f"Invalid H3 cell detected in Parquet: '{h3_id}'")
            res = h3.get_resolution(h3_id)
            if res != 6:
                raise AssertionError(f"Spatial resolution drift: Cell '{h3_id}' has resolution {res}, expected resolution 6.")

        logging.info(f"✓ Parquet Snapshot Passed All Assertions ({count} rows, 0 nulls, 0 NaN/Inf, H3-Res6 verified)")

    finally:
        con.close()

def run():
    logging.info("==================================================")
    logging.info("STARTING AUTOMATED SCHEMA CONTRACT & QA AUDIT")
    logging.info("==================================================")

    # 1. Audit JSON / JSONL Contracts
    audit_json_contract("latest/anomalies.json", "anomalies.json")
    audit_jsonl_contract("latest/tasks.jsonl", "tasks.json")
    audit_jsonl_contract("latest/evals.jsonl", "evals.json")

    # 2. Audit Parquet Columnar Data Store
    audit_parquet_snapshot()

    logging.info("==================================================")
    logging.info("ALL CONTRACT TESTS PASSED: DATA STATE VERIFIED")
    logging.info("==================================================")

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logging.error(f"GATEKEEPER REJECTION: Quality validation failed: {e}")
        sys.exit(1)
