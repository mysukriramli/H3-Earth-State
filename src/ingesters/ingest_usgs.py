#!/usr/bin/env python3
import os
import json
import logging
from datetime import datetime, timezone
from .h3_utils import get_h3_id
from circuit_breaker import resilient_get

logging.basicConfig(level=logging.INFO)

URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
OUTPUT_FILE = "latest/events.jsonl"

def run() -> bool:
    logging.info("Ingesting USGS Seismic Data...")
    res = resilient_get(URL, circuit_name="USGS_SEISMIC", timeout=12.0)
    if res is None:
        logging.error("USGS ingestion skipped due to circuit failure.")
        return False

    try:
        data = res.json()
    except Exception as e:
        logging.error(f"Failed to parse USGS GeoJSON: {e}")
        return False

    events = []
    for feature in data.get("features", []):
        props = feature["properties"]
        coords = feature["geometry"]["coordinates"]
        
        lon, lat, depth = coords[0], coords[1], coords[2]
        h3_id = get_h3_id(lat, lon, 6)
        event_time = datetime.fromtimestamp(props["time"] / 1000, tz=timezone.utc).isoformat()
        
        event = {
            "event_id": f"usgs_{feature['id']}",
            "timestamp": event_time,
            "h3_res6_id": h3_id,
            "source": "USGS",
            "modality": "seismic_events",
            "attributes": {
                "magnitude": float(props.get("mag", 0.0)),
                "depth_km": float(depth),
                "place": props.get("place", "")
            }
        }
        events.append(event)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
            
    logging.info(f"Appended {len(events)} seismic events.")
    return True

if __name__ == "__main__":
    run()
