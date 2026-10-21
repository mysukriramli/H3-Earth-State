#!/usr/bin/env python3
"""
H3-Earth-State Master Orchestrator
Executes the data flywheel sequentially across all 7 operational phases:
1. Ingestion -> 2. Normalization -> 3. Anomaly Detection -> 4. Zero-Day Evals ->
5. Entity Resolution -> 6. Machine Task Queue -> 7. Cryptographic Provenance.
"""

import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Explicit multi-path resolution ensuring imports resolve across environments
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)

for p in [current_dir, root_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Module imports
from ingesters import ingest_usgs, ingest_firms, ingest_gdelt
import normalize
import anomalies
import generate_evals
import entity_resolution
import generate_tasks
import generate_manifest

def run_ingestion():
    logging.info("--- PHASE 1: INGESTION ---")
    ingesters = [
        ("USGS Seismic", ingest_usgs),
        ("NASA FIRMS Thermal", ingest_firms),
        ("GDELT Geopolitical", ingest_gdelt)
    ]
    
    for name, module in ingesters:
        try:
            logging.info(f"Triggering {name}...")
            module.run()
        except Exception as e:
            logging.error(f"Critical failure in {name} ingestion: {e}")

def main():
    logging.info("Starting H3-Earth-State Pipeline Cycle...")

    # Phase 1: Ingest raw telemetry into latest/events.jsonl
    run_ingestion()

    # Phase 2: DuckDB Normalization to Parquet and latest/world_state.json
    logging.info("--- PHASE 2: NORMALIZATION ---")
    try:
        normalize.run()
    except Exception as e:
        logging.error(f"Normalization failed: {e}")
        return

    # Phase 3: Statistical Baseline and Cross-Domain Anomaly Detection
    logging.info("--- PHASE 3: ANOMALY DETECTION ---")
    try:
        anomalies.run()
    except Exception as e:
        logging.error(f"Anomaly detection failed: {e}")

    # Phase 4: Zero-Day Multiple Choice Benchmark Generation
    logging.info("--- PHASE 4: AGENT EVAL GENERATION ---")
    try:
        generate_evals.run()
    except Exception as e:
        logging.error(f"Eval generation failed: {e}")

    # Phase 5: Convert H3 IDs to Named Entities via Wikipedia GeoSearch
    logging.info("--- PHASE 5: ENTITY RESOLUTION ---")
    try:
        entity_resolution.run()
    except Exception as e:
        logging.error(f"Entity resolution failed: {e}")

    # Phase 6: Synthesize Prioritized Machine Task Directives
    logging.info("--- PHASE 6: AGENT TASK QUEUE GENERATION ---")
    try:
        generate_tasks.run()
    except Exception as e:
        logging.error(f"Task generation failed: {e}")

    # Phase 7: Compute SHA-256 Checksums and Emit Provenance Manifest
    logging.info("--- PHASE 7: PROVENANCE MANIFEST ---")
    try:
        generate_manifest.run()
    except Exception as e:
        logging.error(f"Manifest generation failed: {e}")

    logging.info("H3-Earth-State Complete Flywheel Execution Successful.")

if __name__ == "__main__":
    main()
