#!/usr/bin/env python3
"""
H3-Earth-State Task Generation Engine
Synthesizes physical anomalies and named entities into actionable,
prioritized execution directives for autonomous agents.
"""

import os
import json
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

INPUT_ANOMALIES = "latest/anomalies.json"
INPUT_ENTITIES = "latest/entities.jsonl"
OUTPUT_TASKS = "latest/tasks.jsonl"

def load_entities_map() -> dict:
    """Creates a lookup mapping h3_res6_id -> list of affected named entities."""
    entities_map = {}
    if not os.path.exists(INPUT_ENTITIES):
        return entities_map

    with open(INPUT_ENTITIES, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                h3_id = rec.get("h3_res6_id")
                entities = rec.get("affected_entities", [])
                if h3_id:
                    entities_map[h3_id] = entities
            except Exception:
                continue
    return entities_map

def derive_task_for_anomaly(anomaly: dict, entities: list) -> dict:
    """Maps an anomaly signature into a prioritized machine task."""
    h3_id = anomaly.get("h3_res6_id", "Unknown")
    date_str = anomaly.get("anomaly_date", "")
    anomaly_type = anomaly.get("anomaly_type", "Unknown Anomaly")
    mag = anomaly.get("max_seismic_magnitude", 0.0)
    frp = anomaly.get("max_thermal_intensity_mw", 0.0)
    human_count = anomaly.get("human_event_count", 0)

    entity_context = ", ".join(entities[:3]) if entities else "unpopulated/remote region"

    # Rule Matrix: Priority, Capabilities, and Directive
    if mag >= 6.0 or (mag >= 5.0 and entities):
        priority = "P0_CRITICAL"
        capabilities = ["structural_damage_assessment", "emergency_dispatch", "orbital_radar_tasking"]
        objective = (
            f"INITIATE RAPID SEISMIC RESPONSE: Confirm structural integrity of critical infrastructure "
            f"near [{entity_context}] (Hexagon: {h3_id}). Magnitude {mag} detected. "
            f"Task high-resolution Synthetic Aperture Radar (SAR) pass."
        )
    elif "Fire" in anomaly_type or frp >= 80.0:
        priority = "P1_HIGH"
        capabilities = ["thermal_perimeter_tracking", "evacuation_routing", "air_quality_alert"]
        objective = (
            f"FIRE PERIMETER DELINEATION: High-intensity thermal signature ({frp:.1f} MW) detected near [{entity_context}]. "
            f"Calculate downwind plume dispersion and audit transport evacuation corridors within 25 km."
        )
    elif "Geopolitical" in anomaly_type or human_count >= 150:
        priority = "P1_HIGH"
        capabilities = ["supply_chain_rerouting", "consular_alert", "asset_protection"]
        objective = (
            f"DISRUPTION MONITORING: Severe geopolitical activity spike ({human_count} events) near [{entity_context}]. "
            f"Audit open commercial freight routes and issue asset advisory flags for localized supply chains."
        )
    else:
        priority = "P2_ELEVATED"
        capabilities = ["telemetry_verification", "sensor_recalibration"]
        objective = (
            f"ROUTINE SENSOR AUDIT: Anomaly registered in Hexagon {h3_id} near [{entity_context}]. "
            f"Cross-verify secondary satellite passes to confirm signal validity."
        )

    return {
        "task_id": f"task_{h3_id}_{date_str.replace('-', '')}",
        "priority": priority,
        "target_h3": h3_id,
        "anomaly_type": anomaly_type,
        "affected_entities": entities,
        "actionable_objective": objective,
        "required_agent_capabilities": capabilities,
        "payload_context": {
            "seismic_magnitude": mag,
            "thermal_mw": frp,
            "human_event_count": human_count
        },
        "created_at_utc": datetime.now(timezone.utc).isoformat()
    }

def run():
    logging.info("Starting Autonomous Task Generation Engine...")

    if not os.path.exists(INPUT_ANOMALIES) or os.path.getsize(INPUT_ANOMALIES) == 0:
        logging.warning("No anomalies file found. Emitting empty task queue.")
        with open(OUTPUT_TASKS, "w", encoding="utf-8") as f:
            pass
        return

    try:
        with open(INPUT_ANOMALIES, "r", encoding="utf-8") as f:
            anomalies = json.load(f)
    except Exception as e:
        logging.error(f"Failed to read anomalies: {e}")
        return

    entities_map = load_entities_map()
    tasks = [derive_task_for_anomaly(a, entities_map.get(a.get("h3_res6_id"), [])) for a in anomalies]

    # Sort tasks so P0_CRITICAL always lands at the top of the stream
    priority_order = {"P0_CRITICAL": 0, "P1_HIGH": 1, "P2_ELEVATED": 2}
    tasks.sort(key=lambda t: priority_order.get(t["priority"], 3))

    os.makedirs(os.path.dirname(OUTPUT_TASKS), exist_ok=True)
    with open(OUTPUT_TASKS, "w", encoding="utf-8") as f:
        for t in tasks:
            f.write(json.dumps(t) + "\n")

    logging.info(f"Published {len(tasks)} prioritized machine tasks to {OUTPUT_TASKS}.")

if __name__ == "__main__":
    run()
