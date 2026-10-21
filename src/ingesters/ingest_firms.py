#!/usr/bin/env python3
import os
import json
import logging
from datetime import datetime, timezone
import pandas as pd
from .h3_utils import get_h3_id

logging.basicConfig(level=logging.INFO)

# Unauthenticated rolling 24h VIIRS active fire CSV from NASA
URL = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv"
OUTPUT_FILE = "latest/events.jsonl"

def run():
    logging.info("Ingesting NASA FIRMS Thermal Data...")
    try:
        df = pd.read_csv(URL)
    except Exception as e:
        logging.error(f"Failed to fetch FIRMS CSV: {e}")
        return

    # Filter for high-confidence anomalies (nominal or high) to reduce noise
    df = df[df['confidence'].isin(['n', 'h'])]
    
    events = []
    for _, row in df.iterrows():
        lat, lon = row['latitude'], row['longitude']
        h3_id = get_h3_id(lat, lon, 6)
        
        # Combine ACQ_DATE and ACQ_TIME into ISO UTC
        # FIRMS time is "HHMM"
        time_str = f"{row['acq_date']} {str(row['acq_time']).zfill(4)}"
        dt = datetime.strptime(time_str, "%Y-%m-%d %H%M").replace(tzinfo=timezone.utc)
        
        event = {
            "event_id": f"firms_{lat}_{lon}_{row['acq_time']}",
            "timestamp": dt.isoformat(),
            "h3_res6_id": h3_id,
            "source": "NASA_FIRMS",
            "modality": "thermal_events",
            "attributes": {
                "frp_mw": float(row['frp']), # Fire Radiative Power (MW)
                "confidence": row['confidence']
            }
        }
        events.append(event)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
            
    logging.info(f"Appended {len(events)} thermal events.")

if __name__ == "__main__":
    run()
