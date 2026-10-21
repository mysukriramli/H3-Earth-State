#!/usr/bin/env python3
"""
H3-Earth-State Anomaly Engine
Reads the permanent Parquet archives to calculate historical baselines 
and emits cross-domain statistical anomalies for the current day.
"""

import os
import duckdb
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ARCHIVE_PATH = "snapshots/year=*/month=*/*.parquet"
OUTPUT_FILE = "latest/anomalies.json"

def run():
    logging.info("Starting Cross-Domain Anomaly Engine...")

    # We use in-memory DuckDB to process potentially gigabytes of Parquet files
    con = duckdb.connect(database=':memory:')

    try:
        # Step 1: Check if we have enough historical data to run
        try:
            row_count = con.execute(f"SELECT COUNT(*) FROM '{ARCHIVE_PATH}'").fetchone()[0]
            if row_count < 100:
                logging.warning("Insufficient historical data for anomaly detection. Accumulate more days.")
                return
        except Exception:
            logging.warning("No parquet archives found yet. Skipping anomalies.")
            return

        # Step 2: Build the baseline model using DuckDB Window Functions
        # We calculate the mean and standard deviation for human events and thermal intensity
        con.execute(f"""
            CREATE TEMP TABLE historical_baselines AS
            SELECT 
                h3_res6_id,
                date,
                human_event_count,
                max_thermal_intensity_mw,
                max_seismic_magnitude,
                dominant_cameo_event_code,
                AVG(human_event_count) OVER w AS mean_human,
                STDDEV_POP(human_event_count) OVER w AS stddev_human,
                AVG(max_thermal_intensity_mw) OVER w AS mean_thermal,
                STDDEV_POP(max_thermal_intensity_mw) OVER w AS stddev_thermal
            FROM read_parquet('{ARCHIVE_PATH}')
            WINDOW w AS (PARTITION BY h3_res6_id ORDER BY date ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING)
        """)

        # Determine the most recent date in the dataset (today's run)
        latest_date = con.execute("SELECT MAX(date) FROM historical_baselines").fetchone()[0]

        # Step 3: Extract Anomalies for the Latest Day
        # Trigger 1: Human events are 3 standard deviations above the 30-day mean.
        # Trigger 2: Cross-domain crisis (Earthquake > 5.0 OR Severe Fire > 100 MW) 
        #            AND simultaneous spike in human/geopolitical events.
        con.execute(f"""
            CREATE TEMP TABLE todays_anomalies AS
            SELECT 
                h3_res6_id,
                date AS anomaly_date,
                human_event_count,
                max_thermal_intensity_mw,
                max_seismic_magnitude,
                dominant_cameo_event_code,
                CASE 
                    WHEN max_seismic_magnitude >= 5.0 THEN 'Major Seismic Event'
                    WHEN max_thermal_intensity_mw >= 50.0 AND human_event_count > (mean_human + (3 * stddev_human)) THEN 'Fire-Geopolitical Intersection'
                    WHEN human_event_count > (mean_human + (4 * stddev_human)) THEN 'Severe Geopolitical Spike'
                    ELSE 'Unknown Anomaly'
                END AS anomaly_type
            FROM historical_baselines
            WHERE date = '{latest_date}'
            AND (
                human_event_count > (mean_human + (3 * COALESCE(stddev_human, 1))) 
                OR max_seismic_magnitude >= 5.0
                OR (max_thermal_intensity_mw >= 50.0 AND human_event_count > mean_human)
            );
        """)

        # Step 4: Export to JSON for downstream agents
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        con.execute(f"COPY todays_anomalies TO '{OUTPUT_FILE}' (FORMAT JSON, ARRAY TRUE);")
        
        count = con.execute("SELECT COUNT(*) FROM todays_anomalies").fetchone()[0]
        logging.info(f"Anomaly Engine completed. Emitted {count} cross-domain anomalies for {latest_date}.")

    except Exception as e:
        logging.error(f"Anomaly detection failed: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    run()
