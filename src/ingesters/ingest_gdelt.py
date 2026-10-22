#!/usr/bin/env python3
import os
import json
import logging
import zipfile
import io
import pandas as pd
from datetime import datetime, timezone
from .h3_utils import get_h3_id
from circuit_breaker import resilient_get

logging.basicConfig(level=logging.INFO)

MASTER_LIST_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
OUTPUT_FILE = "latest/events.jsonl"

def run() -> bool:
    logging.info("Ingesting GDELT Geopolitical Data...")
    
    res = resilient_get(MASTER_LIST_URL, circuit_name="GDELT_GEOPOLITICAL", timeout=12.0)
    if res is None:
        logging.error("GDELT master list fetch skipped due to circuit failure.")
        return False

    try:
        export_url = res.text.split("\n")[0].split(" ")[-1]
        zip_res = resilient_get(export_url, circuit_name="GDELT_EXPORT", timeout=18.0)
        if zip_res is None:
            return False

        with zipfile.ZipFile(io.BytesIO(zip_res.content)) as z:
            csv_filename = z.namelist()[0]
            with z.open(csv_filename) as f:
                df = pd.read_csv(f, sep='\t', header=None, on_bad_lines='skip', low_memory=False)
    except Exception as e:
        logging.error(f"GDELT decompression/parse failed: {e}")
        return False

    events = []
    for _, row in df.iterrows():
        try:
            lat = float(row[53])
            lon = float(row[54])
        except (ValueError, TypeError):
            continue
            
        if pd.isna(lat) or pd.isna(lon):
            continue
            
        h3_id = get_h3_id(lat, lon, 6)
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
    return True

if __name__ == "__main__":
    run()
