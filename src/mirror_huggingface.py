#!/usr/bin/env python3
"""
H3-Earth-State Hugging Face Mirror Engine
Autonomously synchronizes normalized Parquet snapshots and active state
to a public Hugging Face Dataset repository for high-throughput ML pipelines.
"""

import os
import sys
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

HF_TOKEN = os.getenv("HF_TOKEN")
HF_DATASET_REPO = os.getenv("HF_DATASET_REPO")

def build_dataset_card_content() -> str:
    """Generates YAML frontmatter and technical documentation for Hugging Face."""
    card_lines = [
        "---",
        "license: cc-by-4.0",
        "task_categories:",
        "- tabular",
        "- time-series",
        "- feature-extraction",
        "tags:",
        "- spatiotemporal",
        "- h3",
        "- earth-observation",
        "- agentic-ai",
        "- disaster-intelligence",
        "pretty_name: H3-Earth-State Spatiotemporal World Graph",
        "size_categories:",
        "- 10K<n<100K",
        "---",
        "",
        "# H3-Earth-State: The Autonomous Spatiotemporal World Graph",
        "",
        "## Dataset Summary",
        "This dataset provides a continuous, machine-readable digital twin of Earth combining physical telemetry and geopolitical dynamics into Uber's H3 Hexagonal Spatial Index (Resolution 6).",
        "",
        "- **Update Frequency:** Every 6 hours",
        "- **Canonical Repository:** https://github.com/mysukriramli/H3-Earth-State",
        "- **Spatial Indexing:** Uber H3 (Resolution 6, ~36 km² per hexagon)",
        "",
        "## Quick Start (Python)",
        "```python",
        "from datasets import load_dataset",
        "",
        "# Load all historical Parquet snapshots directly",
        'dataset = load_dataset("parquet", data_files="snapshots/**/*.parquet")',
        "print(dataset)",
        "```",
        ""
    ]
    return "\n".join(card_lines)

def run():
    logging.info("Checking Hugging Face Dataset mirror configuration...")

    if not HF_TOKEN or not HF_DATASET_REPO:
        logging.info("HF_TOKEN or HF_DATASET_REPO not configured. Mirroring step skipped.")
        return

    try:
        from huggingface_hub import HfApi
    except ImportError:
        logging.error("huggingface_hub is not installed. Skipping mirror sync.")
        return

    api = HfApi(token=HF_TOKEN)

    # 1. Ensure target repository exists on Hugging Face
    try:
        api.create_repo(
            repo_id=HF_DATASET_REPO,
            repo_type="dataset",
            exist_ok=True,
            private=False
        )
    except Exception as e:
        logging.error(f"Failed to access or create Hugging Face dataset repository: {e}")
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    logging.info(f"Uploading files to Hugging Face: {HF_DATASET_REPO}...")

    # 2. Upload latest/ directory files
    for root, _, files in os.walk("latest"):
        for filename in files:
            local_path = os.path.join(root, filename)
            remote_path = f"latest/{filename}"
            try:
                api.upload_file(
                    path_or_fileobj=local_path,
                    path_in_repo=remote_path,
                    repo_id=HF_DATASET_REPO,
                    repo_type="dataset",
                    commit_message=f"Autonomous sync latest: {now_iso}"
                )
            except Exception as e:
                logging.warning(f"Failed to mirror {local_path}: {e}")

    # 3. Upload snapshots/ directory (Parquet files)
    for root, _, files in os.walk("snapshots"):
        for filename in files:
            if filename.endswith(".parquet"):
                local_path = os.path.join(root, filename)
                rel_path = os.path.relpath(local_path, start=".")
                try:
                    api.upload_file(
                        path_or_fileobj=local_path,
                        path_in_repo=rel_path.replace("\\", "/"),
                        repo_id=HF_DATASET_REPO,
                        repo_type="dataset",
                        commit_message=f"Autonomous sync snapshot: {filename}"
                    )
                except Exception as e:
                    logging.warning(f"Failed to mirror {local_path}: {e}")

    # 4. Upload standard dataset card
    dataset_card_path = "dataset_card_temp.md"
    with open(dataset_card_path, "w", encoding="utf-8") as f:
        f.write(build_dataset_card_content())

    try:
        api.upload_file(
            path_or_fileobj=dataset_card_path,
            path_in_repo="README.md",
            repo_id=HF_DATASET_REPO,
            repo_type="dataset",
            commit_message=f"Update dataset card: {now_iso}"
        )
    except Exception as e:
        logging.warning(f"Failed to update dataset card: {e}")
    finally:
        if os.path.exists(dataset_card_path):
            os.remove(dataset_card_path)

    logging.info(f"✓ Hugging Face mirror completed successfully for {HF_DATASET_REPO}.")

if __name__ == "__main__":
    run()
