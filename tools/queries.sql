-- ==============================================================================
-- H3-EARTH-STATE SQL DIRECTORY FOR AUTONOMOUS AGENTS
-- Use {{SOURCE}} as the file path placeholder when running via tools/query_remote.py.
-- Replace {{SOURCE}} with 'https://raw.githubusercontent.com/<OWNER>/<REPO>/main/snapshots/*/*/*.parquet'
-- ==============================================================================

-- 1. Targeted Hexagon History
-- Use to evaluate temporal trends for a single city or facility
SELECT 
    date,
    h3_res6_id,
    human_event_count,
    max_thermal_intensity_mw,
    max_seismic_magnitude,
    dominant_cameo_event_code
FROM read_parquet({{SOURCE}})
WHERE h3_res6_id = '86283082fffffff'
ORDER BY date DESC;

-- 2. Multi-Hazard Co-occurrence (Earthquake + Fire or Conflict)
-- Use to identify compound catastrophe regions
SELECT 
    date,
    h3_res6_id,
    max_seismic_magnitude,
    max_thermal_intensity_mw,
    human_event_count
FROM read_parquet({{SOURCE}})
WHERE max_seismic_magnitude >= 4.5 
  AND (max_thermal_intensity_mw > 20.0 OR human_event_count > 50)
ORDER BY date DESC, max_seismic_magnitude DESC;

-- 3. Top 10 Most Volatile Global Hexagons
-- Aggregates total recorded activity over all historical snapshots
SELECT 
    h3_res6_id,
    COUNT(DISTINCT date) AS active_days,
    SUM(human_event_count) AS total_human_events,
    MAX(max_seismic_magnitude) AS peak_magnitude,
    MAX(max_thermal_intensity_mw) AS peak_fire_mw
FROM read_parquet({{SOURCE}})
GROUP BY h3_res6_id
ORDER BY total_human_events DESC
LIMIT 10;

-- 4. Temporal Drift Detection (Week-over-Week Spike)
-- Detects hexagons experiencing emerging geopolitical escalation
WITH daily_counts AS (
    SELECT 
        h3_res6_id,
        date,
        human_event_count,
        AVG(human_event_count) OVER (
            PARTITION BY h3_res6_id 
            ORDER BY date 
            ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
        ) AS trailing_7d_avg
    FROM read_parquet({{SOURCE}})
)
SELECT 
    date,
    h3_res6_id,
    human_event_count,
    ROUND(trailing_7d_avg, 1) AS baseline_avg,
    ROUND((human_event_count - trailing_7d_avg) / NULLIF(trailing_7d_avg, 0) * 100, 1) AS percent_spike
FROM daily_counts
WHERE human_event_count > (trailing_7d_avg * 2.5) AND human_event_count >= 50
ORDER BY percent_spike DESC
LIMIT 20;
