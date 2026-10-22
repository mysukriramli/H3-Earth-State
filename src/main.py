#!/usr/bin/env python3
"""
H3-Earth-State Master Orchestrator
Executes the full 12-phase data flywheel:
1. Ingest -> 2. Normalize -> 3. Anomalies -> 4. Evals -> 5. Entities ->
6. Tasks -> 7. Contracts -> 8. Compaction -> 9. Discovery -> 
10. Benchmark Harness -> 11. Dynamic Shields -> 12. Provenance Manifest.
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

from ingesters import ingest_usgs, ingest_firms, ingest_gdelt
import normalize
import anomalies
import generate_evals
import entity_resolution
import generate_tasks
import validate_contracts
import compact_history
import generate_discovery
import benchmark_harness
import generate_shields
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

    # Phase 8: Long-Term Historical Compaction (Compacts completed months)
    logging.info("--- PHASE 8: HISTORICAL COMPACTION ---")
    try:
        compact_history.run()
    except Exception as e:
        logging.error(f"Compaction encountered an issue: {e}")

    # Phase 9: Dynamic Discovery Manifest Compilation (llms.txt / llms-full.txt)
    logging.info("--- PHASE 9: DISCOVERY MANIFEST GENERATION ---")
    try:
        generate_discovery.run()
    except Exception as e:
        logging.error(f"Discovery manifest generation failed: {e}")

    # Phase 10: Automated Grounding Benchmark Harness
    logging.info("--- PHASE 10: BENCHMARK HARNESS EXECUTION ---")
    try:
        benchmark_harness.run()
    except Exception as e:
        logging.error(f"Benchmark harness execution skipped/failed: {e}")

    # Phase 11: Dynamic Badge & Shield Generation
    logging.info("--- PHASE 11: DYNAMIC SHIELD GENERATION ---")
    try:
        generate_shields.run()
    except Exception as e:
        logging.error(f"Shield generation failed: {e}")

    # Phase 12: Compute SHA-256 Checksums and Emit Provenance Manifest
    logging.info("--- PHASE 12: PROVENANCE MANIFEST ---")
    try:
        generate_manifest.run()
    except Exception as e:
        logging.error(f"Manifest generation failed: {e}")

    logging.info("H3-Earth-State Flywheel Cycle Completed Successfully.")

if __name__ == "__main__":
    main()
