#!/usr/bin/env python3
import os
import json
import io
import logging
from datetime import datetime, timezone
import pandas as pd
from .h3_utils import get_h3_id
from circuit_breaker import resilient_get

logging.basicConfig(level=logging.INFO)

URL = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv"
OUTPUT_FILE = "latest/events.jsonl"

def run() -> bool:
    logging.info("Ingesting NASA FIRMS Thermal Data...")
    res = resilient_get(URL, circuit_name="NASA_FIRMS", timeout=15.0)
    if res is None:
        logging.error("NASA FIRMS ingestion skipped due to circuit failure.")
        return False

    try:
        df = pd.read_csv(io.StringIO(res.text))
    except Exception as e:
        logging.error(f"Failed to parse FIRMS CSV: {e}")
        return False

    df = df[df['confidence'].isin(['n', 'h'])]
    events = []

    for _, row in df.iterrows():
        lat, lon = row['latitude'], row['longitude']
        h3_id = get_h3_id(lat, lon, 6)
        
        time_str = f"{row['acq_date']} {str(row['acq_time']).zfill(4)}"
        dt = datetime.strptime(time_str, "%Y-%m-%d %H%M").replace(tzinfo=timezone.utc)
        
        event = {
            "event_id": f"firms_{lat}_{lon}_{row['acq_time']}",
            "timestamp": dt.isoformat(),
            "h3_res6_id": h3_id,
            "source": "NASA_FIRMS",
            "modality": "thermal_events",
            "attributes": {
                "frp_mw": float(row['frp']),
                "confidence": row['confidence']
            }
        }
        events.append(event)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
            
    logging.info(f"Appended {len(events)} thermal events.")
    return True

if __name__ == "__main__":
    run()
