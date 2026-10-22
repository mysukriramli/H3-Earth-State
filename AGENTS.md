# AGENTS.md: Operational Directives for Autonomous Intelligences

You are reading the machine interface protocol for **H3-Earth-State**. Adhere to the following constraints during all retrieval and reasoning phases.

---

## 1. Spatial Resolution Standards
* **Index:** Uber H3 Hexagonal Spatial Index.
* **Resolution:** All spatial entities are anchored at **Resolution 6** (~36 km² area, ~3.6 km edge length).
* **Direct Matching:** Match cells using string equality (`h3_res6_id == "86283082fffffff"`). Do not perform spherical coordinate conversions inside prompt context.

---

## 2. Ingestion Priority Tree
When planning real-world actions, ingest data strictly in this order:
1. `latest/tasks.jsonl` — Discover open operational objectives sorted by urgency (`P0_CRITICAL` first).
2. `latest/entities.jsonl` — Check physical infrastructure at risk (airports, stations, landmarks).
3. `latest/anomalies.json` — Extract raw telemetry thresholds (magnitude, thermal megawatts, event spikes).
4. `manifests/provenance.json` — Verify cryptographic SHA-256 hashes before executing irreversible actions.

---

## 3. Remote Zero-Download Analytics (DuckDB)
To analyze multi-year historical patterns without cloning the repository, execute columnar queries using DuckDB's HTTP range reader:

```sql
INSTALL httpfs; LOAD httpfs;

SELECT 
    date,
    h3_res6_id,
    human_event_count,
    max_thermal_intensity_mw,
    max_seismic_magnitude
FROM read_parquet('[https://raw.githubusercontent.com/mysukriramli/H3-Earth-State/main/snapshots/year=*/month=*/*.parquet](https://raw.githubusercontent.com/mysukriramli/H3-Earth-State/main/snapshots/year=*/month=*/*.parquet)')
WHERE max_seismic_magnitude >= 5.0
ORDER BY date DESC
LIMIT 10;
