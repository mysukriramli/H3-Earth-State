#!/usr/bin/env python3
"""
H3-Earth-State Automated Benchmark & Grounding Evaluation Harness
Executes dual-condition evaluation (Unassisted vs Grounded RAG) against zero-day
physical anomalies and updates the public leaderboard.
"""

import sys
import os
import json
import logging
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

EVALS_FILE = "latest/evals.jsonl"
WORLD_STATE_FILE = "latest/world_state.json"
LEADERBOARD_MD = "evals/leaderboard.md"
LATEST_RESULTS_JSON = "evals/latest_results.json"

os.makedirs("evals", exist_ok=True)

def load_world_state_lookup() -> Dict[str, Dict[str, Any]]:
    """Loads current world state into a lookup map indexed by H3 ID."""
    lookup = {}
    if os.path.exists(WORLD_STATE_FILE):
        try:
            with open(WORLD_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for cell in data:
                    h3_id = cell.get("h3_res6_id")
                    if h3_id:
                        lookup[h3_id] = cell
        except Exception as e:
            logging.warning(f"Could not load world state lookup: {e}")
    return lookup

def call_llm(messages: List[Dict[str, str]], model: str, api_key: str, api_base: str) -> Optional[int]:
    """Queries target model with constrained JSON response format to extract choice index."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
        "messages": messages
    }
    try:
        res = requests.post(f"{api_base}/chat/completions", headers=headers, json=payload, timeout=20)
        res.raise_for_status()
        content = res.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return int(parsed.get("selected_index", -1))
    except Exception as e:
        logging.warning(f"Inference error with model {model}: {e}")
        return None

def evaluate_question(
    eval_item: Dict[str, Any],
    world_state_lookup: Dict[str, Dict[str, Any]],
    model: str,
    api_key: str,
    api_base: str
) -> Tuple[bool, bool]:
    """
    Evaluates a single question under:
      1. Unassisted condition (No external context)
      2. Grounded condition (Context injected via H3 lookup)
    Returns: (unassisted_correct, grounded_correct)
    """
    question = eval_item["question"]
    choices = eval_item["choices"]
    answer_idx = eval_item["answer_index"]
    h3_id = eval_item.get("metadata", {}).get("h3_res6_id")

    choices_text = "\n".join([f"{i}. {choice}" for i, choice in enumerate(choices)])

    # 1. Condition A: Unassisted Prompt
    unassisted_messages = [
        {
            "role": "system",
            "content": (
                "You are an evaluation participant. Answer the multiple choice question based on your knowledge. "
                "Output JSON strictly in the format: {\"selected_index\": <integer>}."
            )
        },
        {
            "role": "user",
            "content": f"Question:\n{question}\n\nChoices:\n{choices_text}"
        }
    ]

    # 2. Condition B: Grounded RAG Prompt
    context_data = world_state_lookup.get(h3_id, {})
    context_str = json.dumps(context_data, indent=2) if context_data else "No telemetry found for this hexagon."

    grounded_messages = [
        {
            "role": "system",
            "content": (
                "You are an evidence-grounded reasoning agent. Answer the question relying strictly on the "
                "provided H3-Earth-State context telemetry. Output JSON: {\"selected_index\": <integer>}."
            )
        },
        {
            "role": "user",
            "content": (
                f"Context Telemetry for Cell {h3_id}:\n{context_str}\n\n"
                f"Question:\n{question}\n\nChoices:\n{choices_text}"
            )
        }
    ]

    ans_unassisted = call_llm(unassisted_messages, model, api_key, api_base)
    ans_grounded = call_llm(grounded_messages, model, api_key, api_base)

    unassisted_correct = (ans_unassisted == answer_idx)
    grounded_correct = (ans_grounded == answer_idx)

    return unassisted_correct, grounded_correct

def update_leaderboard(summary: Dict[str, Any]):
    """Appends or updates benchmark records in evals/leaderboard.md."""
    now_str = summary["timestamp_utc"].split("T")[0]
    new_entry = (
        f"| {now_str} | `{summary['model']}` | {summary['evaluations_run']} | "
        f"{summary['unassisted_accuracy']:.1f}% | {summary['grounded_accuracy']:.1f}% | "
        f"+{summary['grounding_lift_pct']:.1f}% |\n"
    )

    header = (
        "# H3-Earth-State Zero-Day Grounding Leaderboard\n"
        "> Continuous evaluation measuring LLM hallucination on zero-day real-world events.\n\n"
        "| Date | Evaluated Model | Items | Unassisted (Closed-Book) | Grounded (H3 Context) | Grounding Lift | \n"
        "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
    )

    existing_rows = []
    if os.path.exists(LEADERBOARD_MD):
        with open(LEADERBOARD_MD, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Preserve existing row history excluding headers
            existing_rows = [l for l in lines if l.startswith("| 20")]

    with open(LEADERBOARD_MD, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(new_entry)
        for r in existing_rows[:20]:
            if not r.strip() == new_entry.strip():
                f.write(r)

def run(model: str = "gpt-4o-mini", limit: int = 10):
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")

    if not api_key:
        logging.info("LLM_API_KEY is not configured. Skipping automated evaluation pass.")
        return

    if not os.path.exists(EVALS_FILE) or os.path.getsize(EVALS_FILE) == 0:
        logging.info("No evaluations found in latest/evals.jsonl. Skipping benchmark pass.")
        return

    world_state_lookup = load_world_state_lookup()

    eval_items = []
    with open(EVALS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    eval_items.append(json.loads(line))
                except Exception:
                    continue

    eval_items = eval_items[:limit]
    if not eval_items:
        logging.info("Zero evaluation records to process.")
        return

    logging.info(f"Executing benchmark harness on {len(eval_items)} zero-day items with model: {model}...")

    unassisted_score = 0
    grounded_score = 0

    for i, item in enumerate(eval_items, start=1):
        unassisted_ok, grounded_ok = evaluate_question(item, world_state_lookup, model, api_key, api_base)
        if unassisted_ok:
            unassisted_score += 1
        if grounded_ok:
            grounded_score += 1

    total = len(eval_items)
    unassisted_pct = (unassisted_score / total) * 100
    grounded_pct = (grounded_score / total) * 100
    lift_pct = grounded_pct - unassisted_pct

    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "evaluations_run": total,
        "unassisted_correct": unassisted_score,
        "unassisted_accuracy": round(unassisted_pct, 1),
        "grounded_correct": grounded_score,
        "grounded_accuracy": round(grounded_pct, 1),
        "grounding_lift_pct": round(lift_pct, 1)
    }

    with open(LATEST_RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    update_leaderboard(summary)
    logging.info(
        f"✓ Benchmark complete: Unassisted: {unassisted_pct:.1f}% | "
        f"Grounded: {grounded_pct:.1f}% | Lift: +{lift_pct:.1f}%"
    )

def main():
    parser = argparse.ArgumentParser(description="H3-Earth-State Zero-Day Evaluation Harness")
    parser.add_argument("--model", default=os.getenv("LLM_MODEL", "gpt-4o-mini"), help="Model identifier")
    parser.add_argument("--limit", type=int, default=10, help="Maximum questions to test per cycle")
    args = parser.parse_args()
    run(model=args.model, limit=args.limit)

if __name__ == "__main__":
    main()
