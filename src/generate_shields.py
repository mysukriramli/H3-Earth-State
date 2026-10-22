#!/usr/bin/env python3
"""
H3-Earth-State Dynamic Badge Generator
Compiles repository metrics into Shields.io Endpoint v0 JSON format
so the README displays live stats without commit churning.
"""

import os
import json
import logging
import duckdb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SHIELDS_OUT = "docs/shields.json"
TASKS_FILE = "latest/tasks.jsonl"
EVALS_RESULT_FILE = "evals/latest_results.json"
SNAPSHOTS_PATTERN = "snapshots/year=*/month=*/*.parquet"

def get_row_count() -> int:
    con = duckdb.connect(database=":memory:")
    try:
        res = con.execute(f"SELECT COUNT(*) FROM read_parquet('{SNAPSHOTS_PATTERN}')").fetchone()
        return res[0] if res and res[0] is not None else 0
    except Exception:
        return 0
    finally:
        con.close()

def get_p0_task_count() -> int:
    if not os.path.exists(TASKS_FILE):
        return 0
    count = 0
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if '"priority": "P0_CRITICAL"' in line:
                    count += 1
    except Exception:
        pass
    return count

def get_grounding_lift() -> float:
    if not os.path.exists(EVALS_RESULT_FILE):
        return 0.0
    try:
        with open(EVALS_RESULT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return float(data.get("grounding_lift_pct", 0.0))
    except Exception:
        return 0.0

def run():
    logging.info("Compiling dynamic Shields.io metadata...")
    os.makedirs(os.path.dirname(SHIELDS_OUT), exist_ok=True)

    rows = get_row_count()
    p0_tasks = get_p0_task_count()
    lift = get_grounding_lift()

    payload = {
        "records_badge": {
            "schemaVersion": 1,
            "label": "spatial records",
            "message": f"{rows:,}",
            "color": "blue"
        },
        "tasks_badge": {
            "schemaVersion": 1,
            "label": "active P0 tasks",
            "message": str(p0_tasks),
            "color": "red" if p0_tasks > 0 else "brightgreen"
        },
        "lift_badge": {
            "schemaVersion": 1,
            "label": "grounding lift",
            "message": f"+{lift:.1f}%",
            "color": "brightgreen" if lift >= 50 else "yellow"
        }
    }

    with open(SHIELDS_OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    logging.info(f"✓ Shields metadata saved to {SHIELDS_OUT}")

if __name__ == "__main__":
    run()
