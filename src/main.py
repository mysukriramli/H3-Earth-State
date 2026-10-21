#!/usr/bin/env python3
"""
H3-Earth-State Master Orchestrator
Executes the data flywheel with integrated schema contract gatekeeping:
1. Ingest -> 2. Normalize -> 3. Anomalies -> 4. Evals -> 5. Entities ->
6. Tasks -> 7. Quality & Contract Validation -> 8. Cryptographic Manifest.
"""

import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)

for p in [current_dir, root_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from ingesters import ingest_usgs, ingest_firms, ingest_gdelt
import normalize
import anomalies
import generate_evals
import entity_resolution
import generate_tasks
import validate_contracts
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
        sys.exit(1)

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

    # Phase 7: Automated Quality Validation & Schema Contract Testing
    logging.info("--- PHASE 7: AUTOMATED QA & CONTRACT TESTING ---")
    try:
        validate_contracts.run()
    except Exception as e:
        logging.error(f"CRITICAL CONTRACT BREACH: Pipeline aborted prior to staging: {e}")
        sys.exit(1)

    # Phase 8: Compute SHA-256 Checksums and Emit Provenance Manifest
    logging.info("--- PHASE 8: PROVENANCE MANIFEST ---")
    try:
        generate_manifest.run()
    except Exception as e:
        logging.error(f"Manifest generation failed: {e}")

    logging.info("H3-Earth-State Flywheel Cycle Completed Successfully.")

if __name__ == "__main__":
    main()
