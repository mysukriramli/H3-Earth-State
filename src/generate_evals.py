#!/usr/bin/env python3
"""
H3-Earth-State Zero-Day Evaluation Engine
Converts today's anomalies into uncontaminated multiple-choice questions 
for testing AI agent grounding and RAG capabilities.
"""

import os
import json
import random
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

INPUT_ANOMALIES = "latest/anomalies.json"
OUTPUT_EVALS = "latest/evals.jsonl"

# Standard anomaly types from Part 4
POSSIBLE_ANOMALIES = [
    "Major Seismic Event",
    "Fire-Geopolitical Intersection",
    "Severe Geopolitical Spike",
    "Extreme Weather Disruptions"
]

def generate_question(anomaly: dict) -> dict:
    h3_id = anomaly.get("h3_res6_id", "Unknown")
    date_str = anomaly.get("anomaly_date", "Unknown")
    actual_anomaly = anomaly.get("anomaly_type", "Unknown Anomaly")
    
    # Generate distractors (wrong answers)
    distractors = [a for a in POSSIBLE_ANOMALIES if a != actual_anomaly]
    random.shuffle(distractors)
    
    # Select 3 distractors and the correct answer
    choices = distractors[:3] + [actual_anomaly]
    random.shuffle(choices)
    correct_idx = choices.index(actual_anomaly)
    
    return {
        "eval_id": f"eval_{h3_id}_{date_str.replace('-','')}",
        "question": f"Based on the H3-Earth-State global graph, what specific cross-domain anomaly was detected in H3 Hexagon '{h3_id}' on {date_str}?",
        "choices": choices,
        "answer_index": correct_idx,
        "metadata": {
            "h3_res6_id": h3_id,
            "date": date_str,
            "human_event_count": anomaly.get("human_event_count"),
            "max_seismic_magnitude": anomaly.get("max_seismic_magnitude")
        }
    }

def run():
    logging.info("Starting Zero-Day Benchmark Generation...")

    if not os.path.exists(INPUT_ANOMALIES):
        logging.warning(f"No anomalies file found at {INPUT_ANOMALIES}. Cannot generate evals.")
        return

    with open(INPUT_ANOMALIES, "r", encoding="utf-8") as f:
        try:
            anomalies = json.load(f)
        except json.JSONDecodeError:
            logging.error("Failed to parse anomalies JSON.")
            return

    if not anomalies:
        logging.info("Zero anomalies today. Emitting empty evals file.")
        evals = []
    else:
        evals = [generate_question(a) for a in anomalies]

    os.makedirs(os.path.dirname(OUTPUT_EVALS), exist_ok=True)
    with open(OUTPUT_EVALS, "w", encoding="utf-8") as f:
        for ev in evals:
            f.write(json.dumps(ev) + "\n")

    logging.info(f"Generated {len(evals)} zero-day evaluation questions.")

if __name__ == "__main__":
    run()
