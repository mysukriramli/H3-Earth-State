#!/usr/bin/env python3
"""
H3-Earth-State Model Context Protocol (MCP) Server
Exposes spatial hexagon queries, cross-domain anomalies, and prioritized 
machine task queues to AI agents via standard stdio and SSE interfaces.
"""

import os
import sys
import json
import logging
import argparse
from typing import Optional, List, Dict, Any
import requests
import h3
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.ERROR)

# Initialize MCP Server
mcp = FastMCP("H3-Earth-State")

DEFAULT_REPO = "mysukriramli/H3-Earth-State"
DEFAULT_BRANCH = "main"
RAW_BASE_URL = f"https://raw.githubusercontent.com/{DEFAULT_REPO}/{DEFAULT_BRANCH}"

def _fetch_data(relative_path: str) -> Any:
    """
    Attempts to read data from local disk first. 
    Falls back to fetching from GitHub Raw CDN over HTTPS.
    """
    local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), relative_path)
    if os.path.exists(local_path):
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                if relative_path.endswith(".jsonl"):
                    return [json.loads(line) for line in f if line.strip()]
                return json.load(f)
        except Exception:
            pass

    # Remote Fallback
    url = f"{RAW_BASE_URL}/{relative_path}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            if relative_path.endswith(".jsonl"):
                return [json.loads(line) for line in res.text.splitlines() if line.strip()]
            return res.json()
    except Exception:
        pass

    return [] if relative_path.endswith(".jsonl") else {}


# --- Tool 1: Inspect Specific Hexagon ---

@mcp.tool()
def get_world_state_by_h3(h3_res6_id: str) -> str:
    """
    Retrieve the current normalized physical and geopolitical state for a specific H3 Resolution-6 hexagon.
    
    Args:
        h3_res6_id: The 15-character H3 cell identifier string (e.g., '86283082fffffff').
    """
    h3_clean = h3_res6_id.strip()
    if not h3.is_valid_cell(h3_clean):
        return json.dumps({"error": f"Invalid H3 cell identifier: '{h3_res6_id}'"})

    world_state = _fetch_data("latest/world_state.json")
    for cell in world_state:
        if cell.get("h3_res6_id") == h3_clean:
            return json.dumps(cell, indent=2)

    return json.dumps({
        "status": "nominal",
        "h3_res6_id": h3_clean,
        "message": "No active physical or geopolitical disruptions registered in this cell."
    })


# --- Tool 2: List High-Impact Anomalies ---

@mcp.tool()
def list_recent_anomalies(
    min_seismic_mag: float = 0.0,
    min_thermal_mw: float = 0.0,
    limit: int = 10
) -> str:
    """
    List active cross-domain statistical anomalies filtered by seismic or thermal severity thresholds.
    
    Args:
        min_seismic_mag: Minimum earthquake magnitude (Richter scale). Default is 0.0.
        min_thermal_mw: Minimum fire radiative power in Megawatts (MW). Default is 0.0.
        limit: Maximum records to return (1 to 50, default 10).
    """
    anomalies = _fetch_data("latest/anomalies.json")
    filtered = []

    for a in anomalies:
        mag = a.get("max_seismic_magnitude", 0.0)
        thermal = a.get("max_thermal_intensity_mw", 0.0)
        if mag >= min_seismic_mag and thermal >= min_thermal_mw:
            filtered.append(a)

    filtered = filtered[:max(1, min(limit, 50))]
    return json.dumps({
        "matched_count": len(filtered),
        "anomalies": filtered
    }, indent=2)


# --- Tool 3: Filter Actionable Tasks by Agent Capability ---

@mcp.tool()
def query_tasks_by_capability(
    required_capability: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 5
) -> str:
    """
    Query the prioritized autonomous task queue matching specific agent tool capabilities or priority tiers.
    
    Args:
        required_capability: Specific tool capability filter (e.g., 'orbital_radar_tasking', 'evacuation_routing', 'supply_chain_rerouting').
        priority: Priority tier filter: 'P0_CRITICAL', 'P1_HIGH', or 'P2_ELEVATED'.
        limit: Maximum tasks to retrieve (1 to 20, default 5).
    """
    tasks = _fetch_data("latest/tasks.jsonl")
    matched = []

    for t in tasks:
        if priority and t.get("priority") != priority.strip().upper():
            continue
        if required_capability:
            caps = t.get("required_agent_capabilities", [])
            if not any(required_capability.strip().lower() in c.lower() for c in caps):
                continue
        matched.append(t)

    matched = matched[:max(1, min(limit, 20))]
    return json.dumps({
        "matched_task_count": len(matched),
        "tasks": matched
    }, indent=2)


# --- Tool 4: Spatial Neighborhood Coordinate Inspection ---

@mcp.tool()
def inspect_spatial_neighborhood(
    latitude: float,
    longitude: float,
    k_ring_radius: int = 1
) -> str:
    """
    Convert geographic coordinates to H3 Resolution-6, compute neighboring hexagon rings, 
    and aggregate compound physical/political disruption metrics across the entire cluster.
    
    Args:
        latitude: Decimal latitude (-90.0 to 90.0).
        longitude: Decimal longitude (-180.0 to 180.0).
        k_ring_radius: Number of concentric hexagonal rings to inspect (1 = ~7 cells, 2 = ~19 cells, default 1).
    """
    try:
        origin_cell = h3.latlng_to_cell(float(latitude), float(longitude), 6)
    except Exception as e:
        return json.dumps({"error": f"Coordinate conversion failed: {str(e)}"})

    k_clean = max(0, min(k_ring_radius, 3))
    # h3 v4.x grid_disk produces concentric neighbor cells
    cluster_cells = set(h3.grid_disk(origin_cell, k_clean))

    world_state = _fetch_data("latest/world_state.json")
    anomalies = _fetch_data("latest/anomalies.json")

    matched_cells = [c for c in world_state if c.get("h3_res6_id") in cluster_cells]
    matched_anomalies = [a for a in anomalies if a.get("h3_res6_id") in cluster_cells]

    total_human = sum(c.get("human_event_count", 0) for c in matched_cells)
    peak_seismic = max([c.get("max_seismic_magnitude", 0.0) for c in matched_cells], default=0.0)
    peak_thermal = max([c.get("max_thermal_intensity_mw", 0.0) for c in matched_cells], default=0.0)

    return json.dumps({
        "query_center": {"lat": latitude, "lon": longitude},
        "origin_h3_res6": origin_cell,
        "k_ring_applied": k_clean,
        "total_cells_inspected": len(cluster_cells),
        "active_disrupted_cells": len(matched_cells),
        "cluster_aggregate_impact": {
            "total_human_events": total_human,
            "peak_seismic_magnitude": peak_seismic,
            "peak_thermal_intensity_mw": peak_thermal
        },
        "anomalies_detected": matched_anomalies
    }, indent=2)


def main():
    parser = argparse.ArgumentParser(description="H3-Earth-State MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio", help="Communication transport protocol")
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE server (default 8000)")
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
