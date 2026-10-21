#!/usr/bin/env python3
"""
H3-Earth-State Entity Resolution Engine
Converts mathematical H3 anomalies back into physical coordinates and 
queries Wikipedia GeoSearch to extract the Named Entities affected by the crisis.
"""

import os
import json
import logging
import time
from datetime import datetime, timezone
import requests
import h3

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

INPUT_ANOMALIES = "latest/anomalies.json"
OUTPUT_ENTITIES = "latest/entities.jsonl"

def reverse_geocode_h3(h3_id: str) -> tuple:
    """Converts an H3 string back to a (lat, lon) tuple."""
    try:
        # h3 v4.x method
        return h3.cell_to_latlng(h3_id)
    except Exception as e:
        logging.error(f"H3 decode failed for {h3_id}: {e}")
        return None, None

def fetch_nearby_entities(lat: float, lon: float, radius_meters: int = 10000) -> list:
    """Queries Wikipedia for significant entities near the coordinates."""
    url = (
        f"https://en.wikipedia.org/w/api.php?action=query&list=geosearch"
        f"&gscoord={lat}|{lon}&gsradius={radius_meters}&gslimit=5&format=json"
    )
    headers = {
        "User-Agent": "H3-Earth-State-Agent-Wire/1.0 (https://github.com/yourusername/h3-earth-state)"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        places = data.get("query", {}).get("geosearch", [])
        return [place["title"] for place in places]
    except Exception as e:
        logging.warning(f"Wikipedia GeoSearch failed for {lat},{lon}: {e}")
        return []

def run():
    logging.info("Starting Entity Resolution Engine...")

    if not os.path.exists(INPUT_ANOMALIES) or os.path.getsize(INPUT_ANOMALIES) == 0:
        logging.warning("No anomalies found. Skipping entity resolution.")
        return

    try:
        with open(INPUT_ANOMALIES, "r", encoding="utf-8") as f:
            anomalies = json.load(f)
    except json.JSONDecodeError:
        logging.error("Failed to parse anomalies.json.")
        return

    records = []
    for anomaly in anomalies:
        h3_id = anomaly.get("h3_res6_id")
        if not h3_id:
            continue
            
        lat, lon = reverse_geocode_h3(h3_id)
        if lat is None or lon is None:
            continue
            
        entities = fetch_nearby_entities(lat, lon)
        
        # Be polite to the free Wikipedia API
        time.sleep(0.1)

        record = {
            "entity_graph_id": f"graph_{h3_id}_{anomaly.get('anomaly_date', '').replace('-','')}",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "h3_res6_id": h3_id,
            "coordinates": {"lat": round(lat, 4), "lon": round(lon, 4)},
            "anomaly_type": anomaly.get("anomaly_type"),
            "affected_entities": entities,
            "relationship": "AFFECTED_BY" if entities else "NO_KNOWN_ENTITIES"
        }
        records.append(record)

    os.makedirs(os.path.dirname(OUTPUT_ENTITIES), exist_ok=True)
    with open(OUTPUT_ENTITIES, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    logging.info(f"Resolved entities for {len(records)} anomalies.")

if __name__ == "__main__":
    run()
