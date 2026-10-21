#!/usr/bin/env python3
"""
H3-Earth-State Master Orchestrator
Executes the data flywheel: Ingestion -> Normalization -> Anomalies -> Evals.
"""

import logging
from ingesters import ingest_usgs, ingest_firms, ingest_gdelt
import normalize
import anomalies
import generate_evals

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

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

    # Phase 1: Fetch all raw events and append to latest/events.jsonl
    run_ingestion()

    # Phase 2: Sweep JSONL into DuckDB and build the Parquet grid
    logging.info("--- PHASE 2: NORMALIZATION ---")
    try:
        normalize.run()
    except Exception as e:
        logging.error(f"Normalization failed: {e}")
        return # Halt if we cannot build the world state

    # Phase 3: Calculate baselines and detect cross-domain anomalies
    logging.info("--- PHASE 3: ANOMALY DETECTION ---")
    try:
        anomalies.run()
    except Exception as e:
        logging.error(f"Anomaly detection failed: {e}")

    # Phase 4: Generate zero-day multiple-choice tests for AI agents
    logging.info("--- PHASE 4: AGENT EVAL GENERATION ---")
    try:
        generate_evals.run()
    except Exception as e:
        logging.error(f"Eval generation failed: {e}")

    logging.info("Pipeline Cycle Complete.")

if __name__ == "__main__":
    main()
