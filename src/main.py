#!/usr/bin/env python3
"""
H3-Earth-State Master Orchestrator
Executes the data flywheel with multi-path resolution and diagnostic logging.
"""

import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Auto-detect paths: checks both 'src/' and the repo root ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)

for p in [current_dir, root_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Diagnostic: Verify normalize.py location
normalize_found = any(os.path.exists(os.path.join(p, "normalize.py")) for p in [current_dir, root_dir])
if not normalize_found:
    logging.error(f"CRITICAL: normalize.py not found in {current_dir} or {root_dir}")
    logging.error(f"Files in src/: {os.listdir(current_dir) if os.path.exists(current_dir) else 'src missing'}")
    logging.error(f"Files in root: {os.listdir(root_dir) if os.path.exists(root_dir) else 'root missing'}")

# Module imports
from ingesters import ingest_usgs, ingest_firms, ingest_gdelt
import normalize
import anomalies
import generate_evals
import entity_resolution
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

    # Phase 1: Fetch raw events
    run_ingestion()

    # Phase 2: DuckDB Normalization
    logging.info("--- PHASE 2: NORMALIZATION ---")
    try:
        normalize.run()
    except Exception as e:
        logging.error(f"Normalization failed: {e}")
        return

    # Phase 3: Cross-Domain Anomaly Detection
    logging.info("--- PHASE 3: ANOMALY DETECTION ---")
    try:
        anomalies.run()
    except Exception as e:
        logging.error(f"Anomaly detection failed: {e}")

    # Phase 4: Zero-Day Eval Generation
    logging.info("--- PHASE 4: AGENT EVAL GENERATION ---")
    try:
        generate_evals.run()
    except Exception as e:
        logging.error(f"Eval generation failed: {e}")

    # Phase 5: Entity Resolution
    logging.info("--- PHASE 5: ENTITY RESOLUTION ---")
    try:
        entity_resolution.run()
    except Exception as e:
        logging.error(f"Entity resolution failed: {e}")

    # Phase 6: Cryptographic Manifest
    logging.info("--- PHASE 6: PROVENANCE MANIFEST ---")
    try:
        generate_manifest.run()
    except Exception as e:
        logging.error(f"Manifest generation failed: {e}")

    logging.info("Pipeline Cycle Complete.")

if __name__ == "__main__":
    main()
