import os
import json
import logging
import zipfile
import io
import requests
import pandas as pd
from datetime import datetime, timezone
from h3_utils import get_h3_id

logging.basicConfig(level=logging.INFO)

MASTER_LIST_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
OUTPUT_FILE = "latest/events.jsonl"

def run():
    logging.info("Ingesting GDELT Geopolitical Data...")
    
    # 1. Get the URL for the latest 15-minute export zip
    res = requests.get(MASTER_LIST_URL, timeout=10)
    res.raise_for_status()
    # Format: size hash url
    export_url = res.text.split("\n")[0].split(" ")[-1]
    
    # 2. Download and unzip in memory
    zip_res = requests.get(export_url, timeout=15)
    with zipfile.ZipFile(io.BytesIO(zip_res.content)) as z:
        csv_filename = z.namelist()[0]
        with z.open(csv_filename) as f:
            # GDELT v2 Export has 61 columns, no header
            # Col 1: DATEADDED, Col 26: EventCode, Col 53: ActionGeo_Lat, Col 54: ActionGeo_Long
            df = pd.read_csv(f, sep='\t', header=None, on_bad_lines='skip', low_memory=False)

    events = []
    for _, row in df.iterrows():
        try:
            lat = float(row[53])
            lon = float(row[54])
        except (ValueError, TypeError):
            continue # Skip events without coordinates
            
        if pd.isna(lat) or pd.isna(lon):
            continue
            
        h3_id = get_h3_id(lat, lon, 6)
        
        # GDELT timestamps: YYYYMMDDHHMMSS
        date_str = str(row[1])
        if len(date_str) == 14:
            dt = datetime.strptime(date_str, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
            
        event = {
            "event_id": f"gdelt_{row[0]}",
            "timestamp": dt.isoformat(),
            "h3_res6_id": h3_id,
            "source": "GDELT",
            "modality": "human_events",
            "attributes": {
                "cameo_event_code": str(row[26]),
                "goldstein_scale": float(row[30]) if not pd.isna(row[30]) else 0.0,
                "num_mentions": int(row[31]) if not pd.isna(row[31]) else 1
            }
        }
        events.append(event)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
            
    logging.info(f"Appended {len(events)} geopolitical events.")

if __name__ == "__main__":
    run()
