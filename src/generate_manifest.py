#!/usr/bin/env python3
"""
H3-Earth-State Provenance Engine
Generates cryptographic checksums (SHA-256) of the latest artifacts
and explicitly defines upstream data provenance for machine verification.
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

MANIFEST_DIR = "manifests"
MANIFEST_FILE = os.path.join(MANIFEST_DIR, "provenance.json")

# Core files to track for integrity
TRACKED_FILES = [
    "latest/world_state.json",
    "latest/anomalies.json",
    "latest/evals.jsonl"
]

# Hardcoded upstream sources establishing the chain of custody
SOURCES = {
    "NASA_FIRMS": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv",
    "USGS_SEISMIC": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
    "GDELT_GEOPOLITICAL": "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
}

def compute_sha256(filepath: str) -> str:
    """Reads a file in chunks to compute its SHA-256 hash safely without OOM."""
    if not os.path.exists(filepath):
        return None
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read in 4KB chunks
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_latest_parquet() -> str:
    """Determines the path of today's permanent Parquet snapshot."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    year_str = now.strftime("%Y")
    month_str = now.strftime("%m")
    return os.path.join("snapshots", f"year={year_str}", f"month={month_str}", f"{date_str}.parquet")

def run():
    logging.info("Generating Cryptographic Provenance Manifest...")
    os.makedirs(MANIFEST_DIR, exist_ok=True)
    
    artifacts = {}
    
    # 1. Hash static 'latest' files
    for filepath in TRACKED_FILES:
        file_hash = compute_sha256(filepath)
        if file_hash:
            artifacts[filepath] = {"sha256": file_hash, "size_bytes": os.path.getsize(filepath)}
            
    # 2. Hash dynamic daily parquet archive
    parquet_path = get_latest_parquet()
    parquet_hash = compute_sha256(parquet_path)
    if parquet_hash:
        artifacts[parquet_path] = {"sha256": parquet_hash, "size_bytes": os.path.getsize(parquet_path)}

    manifest = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0.0",
            "license": "CC-BY-4.0",
            "repository": "H3-Earth-State",
            "description": "Cryptographic verification manifest for autonomous agent trust."
        },
        "sources": SOURCES,
        "artifacts": artifacts
    }

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logging.info(f"Manifest saved to {MANIFEST_FILE} tracking {len(artifacts)} files.")

if __name__ == "__main__":
    run()
