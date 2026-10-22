# H3-Earth-State: The Autonomous Spatiotemporal World Graph

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![MCP Server](https://img.shields.io/badge/MCP-Protocol_Compliant-blue.svg)](https://modelcontextprotocol.io/)
[![Spatial Index: H3-Res6](https://img.shields.io/badge/Spatial_Index-Uber_H3_Res6-orange.svg)](https://h3geo.org/)
[![Live Map Dashboard](https://img.shields.io/badge/Live_Dashboard-GitHub_Pages-green.svg)](https://mysukriramli.github.io/H3-Earth-State/)

An autonomous spatiotemporal digital twin engineered exclusively for consumption by **AI agents, robotics pipelines, and foundation model researchers**. 

Every 6 hours, the system ingests seismic telemetry (USGS), thermal anomalies (NASA FIRMS), and geopolitical dynamics (GDELT), collapsing observations into Uber's **H3 Hexagonal Spatial Index (Resolution 6)**. It computes rolling statistical baselines, detects multi-domain anomalies, emits an actionable machine task queue, and generates zero-day evaluation benchmarks.

---

## 🛰️ Live Machine Endpoints (Zero-Auth / Fastly Edge CDN)

All endpoints update automatically and are hosted without rate limits:

| Endpoint | Format | Machine Purpose |
| :--- | :--- | :--- |
| [`latest/tasks.jsonl`](latest/tasks.jsonl) | JSONL | Prioritized task dispatch queue for tool-using agents (`P0_CRITICAL` to `P2`). |
| [`latest/anomalies.json`](latest/anomalies.json) | JSON | Active $3\sigma$ cross-domain physical disruptions. |
| [`latest/evals.jsonl`](latest/evals.jsonl) | JSONL | Zero-day multiple-choice grounding benchmarks derived from today's events. |
| [`latest/entities.jsonl`](latest/entities.jsonl) | JSONL | Wikipedia landmarks and infrastructure bound to affected H3 hexagons. |
| [`latest/world_state.json`](latest/world_state.json) | JSON | Full active normalized state for all reporting global hexagons. |
| [`manifests/provenance.json`](manifests/provenance.json) | JSON | SHA-256 cryptographic checksums and source custody chains. |
| [`llms.txt`](llms.txt) | Text | Structured navigation manifest for LLM web crawlers. |
| [`llms-full.txt`](llms-full.txt) | Text | Complete situational context briefing for direct prompt injection. |

---

## ⚡ Zero-Download Remote SQL Analytics (DuckDB)

Query years of historical Parquet snapshots over HTTPS using DuckDB's HTTP range reader without cloning the repository:

```sql
INSTALL httpfs; LOAD httpfs;

-- Query multi-hazard co-occurrence across the globe
SELECT 
    date,
    h3_res6_id,
    max_seismic_magnitude,
    max_thermal_intensity_mw,
    human_event_count
FROM read_parquet('[https://raw.githubusercontent.com/mysukriramli/H3-Earth-State/main/snapshots/year=*/month=*/*.parquet](https://raw.githubusercontent.com/mysukriramli/H3-Earth-State/main/snapshots/year=*/month=*/*.parquet)')
WHERE max_seismic_magnitude >= 5.0 
  AND max_thermal_intensity_mw >= 50.0
ORDER BY date DESC;
