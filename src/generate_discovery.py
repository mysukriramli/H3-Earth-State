#!/usr/bin/env python3
"""
H3-Earth-State Discovery Manifest Engine
Dynamically compiles llms.txt and llms-full.txt containing live repository
metrics, spatial resolution parameters, and zero-shot context payloads.
"""

import os
import json
import logging
from datetime import datetime, timezone
import duckdb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ANOMALIES_FILE = "latest/anomalies.json"
TASKS_FILE = "latest/tasks.jsonl"
ENTITIES_FILE = "latest/entities.jsonl"
SNAPSHOTS_PATTERN = "snapshots/year=*/month=*/*.parquet"

LLMS_TXT_OUT = "llms.txt"
LLMS_FULL_TXT_OUT = "llms-full.txt"

def get_repository_metrics() -> dict:
    """Computes total records, distinct hexagons, and date bounds using DuckDB."""
    metrics = {
        "total_historical_records": 0,
        "distinct_hexagons_tracked": 0,
        "earliest_date": "N/A",
        "latest_date": "N/A",
        "active_anomalies_count": 0,
        "active_tasks_count": 0
    }

    # 1. Check active anomaly counts
    if os.path.exists(ANOMALIES_FILE):
        try:
            with open(ANOMALIES_FILE, "r", encoding="utf-8") as f:
                anomalies = json.load(f)
                metrics["active_anomalies_count"] = len(anomalies)
        except Exception:
            pass

    # 2. Check active task counts
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                metrics["active_tasks_count"] = sum(1 for line in f if line.strip())
        except Exception:
            pass

    # 3. Query historical Parquet store for aggregate scale
    con = duckdb.connect(database=":memory:")
    try:
        res = con.execute(f"""
            SELECT 
                COUNT(*) AS total_rows,
                COUNT(DISTINCT h3_res6_id) AS total_hexagons,
                MIN(date) AS min_date,
                MAX(date) AS max_date
            FROM read_parquet('{SNAPSHOTS_PATTERN}')
        """).fetchone()

        if res and res[0] is not None:
            metrics["total_historical_records"] = res[0]
            metrics["distinct_hexagons_tracked"] = res[1]
            metrics["earliest_date"] = str(res[2])
            metrics["latest_date"] = str(res[3])
    except Exception as e:
        logging.warning(f"Could not compute historical Parquet metrics: {e}")
    finally:
        con.close()

    return metrics

def build_llms_txt(metrics: dict, now_iso: str) -> str:
    """Generates standard llms.txt index."""
    return f"""# H3-Earth-State: The Autonomous Spatiotemporal World Graph
> Machine-readable digital twin of Earth fusing physical telemetry and geopolitical dynamics into Uber's H3 spatial index.
> Maintained autonomously via GitHub Actions. Updated every 6 hours.

## Live Operational Statistics
- **Last Synchronized (UTC):** {now_iso}
- **Active Anomalies (Today):** {metrics['active_anomalies_count']}
- **Pending Autonomous Tasks:** {metrics['active_tasks_count']}
- **Historical Observations:** {metrics['total_historical_records']:,} rows across {metrics['distinct_hexagons_tracked']:,} hexagons
- **Temporal Range:** {metrics['earliest_date']} to {metrics['latest_date']}

## Canonical Endpoints (Zero-Auth, Fastly Edge CDN)
- [Active Anomaly Feed (JSON)](latest/anomalies.json): High-confidence 3-sigma cross-domain disruptions.
- [Prioritized Task Queue (JSONL)](latest/tasks.jsonl): Actionable objectives categorized P0 to P2.
- [Zero-Day Evaluation Harness (JSONL)](latest/evals.jsonl): Uncontaminated benchmark questions derived from today's events.
- [Resolved Physical Entities (JSONL)](latest/entities.jsonl): Wikipedia landmarks and infrastructure mapped to H3 hexagons.
- [Latest Grid Snapshot (JSON)](latest/world_state.json): Normalized state of all active hexagons.
- [Cryptographic Manifest (JSON)](manifests/provenance.json): SHA-256 integrity checksums and upstream source links.
- [OpenAPI Specification (JSON)](schemas/openapi.json): Standard API interface description for agent tooling.

## Machine Execution Guidelines
- Read `AGENTS.md` for strict protocol boundaries, function calling schemas, and DuckDB range query recipes.
- Do NOT parse raw coordinates with trigonometry; filter via exact string matching on `h3_res6_id`.
"""

def build_llms_full_txt(metrics: dict, now_iso: str) -> str:
    """Generates rich zero-shot context payload for direct agent prompt injection."""
    lines = [
        "# H3-Earth-State Full Situational Briefing",
        f"Generated UTC: {now_iso}",
        f"Active Anomaly Pool: {metrics['active_anomalies_count']} | Active Task Pool: {metrics['active_tasks_count']}",
        "",
        "## Current High-Priority Autonomous Directives"
    ]

    # Inject top tasks
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    t = json.loads(line)
                    lines.extend([
                        f"### [{t.get('priority')}] {t.get('task_id')}",
                        f"- **Target Hexagon:** `{t.get('target_h3')}`",
                        f"- **Anomaly Type:** {t.get('anomaly_type')}",
                        f"- **Affected Infrastructure:** {', '.join(t.get('affected_entities', [])) or 'Remote'}",
                        f"- **Objective:** {t.get('actionable_objective')}",
                        f"- **Required Capabilities:** `{', '.join(t.get('required_agent_capabilities', []))}`",
                        ""
                    ])
        except Exception as e:
            lines.append(f"_Error parsing task queue: {e}_\n")

    lines.extend([
        "## Active Physical & Political Disruptions",
        ""
    ]

    if os.path.exists(ANOMALIES_FILE):
        try:
            with open(ANOMALIES_FILE, "r", encoding="utf-8") as f:
                anomalies = json.load(f)
                for a in anomalies[:25]:
                    lines.append(
                        f"- `{a.get('h3_res6_id')}` | **{a.get('anomaly_type')}** | "
                        f"Quake: M{a.get('max_seismic_magnitude', 0.0)} | "
                        f"Thermal: {a.get('max_thermal_intensity_mw', 0.0)} MW | "
                        f"Human Events: {a.get('human_event_count', 0)}"
                    )
        except Exception as e:
            lines.append(f"_Error parsing anomalies: {e}_\n")

    return "\n".join(lines) + "\n"

def run():
    logging.info("Starting Discovery Manifest Compilation...")
    now_iso = datetime.now(timezone.utc).isoformat()
    metrics = get_repository_metrics()

    # 1. Generate llms.txt
    llms_content = build_llms_txt(metrics, now_iso)
    with open(LLMS_TXT_OUT, "w", encoding="utf-8") as f:
        f.write(llms_content)
    logging.info(f"✓ Generated {LLMS_TXT_OUT}")

    # 2. Generate llms-full.txt
    llms_full_content = build_llms_full_txt(metrics, now_iso)
    with open(LLMS_FULL_TXT_OUT, "w", encoding="utf-8") as f:
        f.write(llms_full_content)
    logging.info(f"✓ Generated {LLMS_FULL_TXT_OUT}")

if __name__ == "__main__":
    run()
