#!/usr/bin/env python3
"""
H3-Earth-State Spatiotemporal Embedding Engine
Synthesizes normalized, dense 8-dimensional feature vectors for every active H3 hexagon
to enable vector similarity search across planetary physical/geopolitical states.
"""

import os
import logging
import duckdb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

WORLD_STATE_FILE = "latest/world_state.json"
ANOMALIES_FILE = "latest/anomalies.json"
OUTPUT_PARQUET = "latest/embeddings.parquet"

def run():
    logging.info("Starting Multimodal Vector Embedding Projection...")

    if not os.path.exists(WORLD_STATE_FILE) or os.path.getsize(WORLD_STATE_FILE) == 0:
        logging.warning(f"Source file {WORLD_STATE_FILE} missing or empty. Skipping embeddings.")
        return

    os.makedirs(os.path.dirname(OUTPUT_PARQUET), exist_ok=True)
    con = duckdb.connect(database=":memory:")

    try:
        # 1. Ingest latest world state
        con.execute(f"""
            CREATE TEMP TABLE active_grid AS
            SELECT 
                h3_res6_id,
                date,
                COALESCE(human_event_count, 0) AS human_count,
                COALESCE(max_thermal_intensity_mw, 0.0) AS thermal_mw,
                COALESCE(max_seismic_magnitude, 0.0) AS seismic_mag,
                COALESCE(TRY_CAST(dominant_cameo_event_code AS DOUBLE), 0.0) AS cameo_code
            FROM read_json_auto('{WORLD_STATE_FILE}');
        """)

        # 2. Check if anomalies file exists to attach anomaly multiplier
        if os.path.exists(ANOMALIES_FILE) and os.path.getsize(ANOMALIES_FILE) > 0:
            con.execute(f"""
                CREATE TEMP TABLE anomaly_lookup AS
                SELECT DISTINCT h3_res6_id, 1.0 AS is_anomaly
                FROM read_json_auto('{ANOMALIES_FILE}');
            """)
        else:
            con.execute("CREATE TEMP TABLE anomaly_lookup (h3_res6_id VARCHAR, is_anomaly DOUBLE);")

        # 3. Project into normalized 8-dimensional dense vector space
        # Features:
        # [0] Normalized Seismic: min(mag / 9.0, 1.0)
        # [1] Normalized Thermal: min(mw / 500.0, 1.0)
        # [2] Normalized Human Events: min(log10(count + 1) / 4.0, 1.0)
        # [3] Anomaly Flag Weight: 1.0 if anomalous else 0.0
        # [4] CAMEO Event Category Vector: min(cameo_code / 200.0, 1.0)
        # [5] Compound Risk Multiplier: (seismic * thermal)
        # [6] Geopolitical Kinetic Multiplier: (human_count * anomaly_flag)
        # [7] Stability Index: 1.0 - max(normalized features)
        con.execute("""
            CREATE TEMP TABLE projected_embeddings AS
            WITH raw_features AS (
                SELECT 
                    g.h3_res6_id,
                    g.date,
                    LEAST(g.seismic_mag / 9.0, 1.0) AS f_seismic,
                    LEAST(g.thermal_mw / 500.0, 1.0) AS f_thermal,
                    LEAST(LOG10(g.human_count + 1) / 4.0, 1.0) AS f_human,
                    COALESCE(a.is_anomaly, 0.0) AS f_anomaly,
                    LEAST(g.cameo_code / 200.0, 1.0) AS f_cameo
                FROM active_grid g
                LEFT JOIN anomaly_lookup a ON g.h3_res6_id = a.h3_res6_id
            ),
            synthesized AS (
                SELECT 
                    h3_res6_id,
                    date,
                    f_seismic,
                    f_thermal,
                    f_human,
                    f_anomaly,
                    f_cameo,
                    ROUND(f_seismic * f_thermal, 4) AS f_compound,
                    ROUND(f_human * f_anomaly, 4) AS f_kinetic,
                    ROUND(1.0 - GREATEST(f_seismic, f_thermal, f_human), 4) AS f_stability
                FROM raw_features
            )
            SELECT 
                h3_res6_id,
                date,
                [
                    ROUND(f_seismic, 4),
                    ROUND(f_thermal, 4),
                    ROUND(f_human, 4),
                    ROUND(f_anomaly, 4),
                    ROUND(f_cameo, 4),
                    ROUND(f_compound, 4),
                    ROUND(f_kinetic, 4),
                    ROUND(f_stability, 4)
                ] AS feature_vector
            FROM synthesized;
        """)

        # 4. Export to Columnar Parquet
        con.execute(f"""
            COPY projected_embeddings TO '{OUTPUT_PARQUET}' (
                FORMAT PARQUET, 
                COMPRESSION ZSTD
            );
        """)

        row_count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{OUTPUT_PARQUET}')").fetchone()[0]
        logging.info(f"✓ Projected {row_count} hexagons into 8D vector space at {OUTPUT_PARQUET}")

    except Exception as e:
        logging.error(f"Embedding generation failed: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    run()
