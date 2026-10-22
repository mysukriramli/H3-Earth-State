#!/usr/bin/env python3
"""
H3-Earth-State Resilient Networking & Circuit Breaker Engine
Provides adaptive retry with exponential backoff, circuit breaker state tracking,
secret token scrubbing, and fallback cache preservation.
"""

import os
import time
import json
import random
import logging
from typing import Optional, Dict, Any
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

HEALTH_FILE = "latest/health.json"

class CircuitState:
    CLOSED = "CLOSED"        # Normal operation
    OPEN = "OPEN"            # Failing, fast-reject requests
    HALF_OPEN = "HALF_OPEN"  # Testing recovery

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_time_secs: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_time_secs = recovery_time_secs
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_time_secs:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True  # HALF_OPEN permits a trial probe

CIRCUITS: Dict[str, CircuitBreaker] = {}

def scrub_sensitive_tokens(text: str) -> str:
    """Masks secret tokens from logs and error strings."""
    for env_var in ["GITHUB_TOKEN", "LLM_API_KEY", "HF_TOKEN"]:
        val = os.getenv(env_var)
        if val and len(val) > 4:
            text = text.replace(val, f"[SCRUBBED_{env_var}]")
    return text

def resilient_get(
    url: str,
    circuit_name: str,
    timeout: float = 12.0,
    max_retries: int = 3,
    backoff_factor: float = 1.5,
    headers: Optional[Dict[str, str]] = None
) -> Optional[requests.Response]:
    """
    Executes resilient HTTP GET with jittered backoff, circuit breaking,
    and sensitive token redaction.
    """
    if circuit_name not in CIRCUITS:
        CIRCUITS[circuit_name] = CircuitBreaker()

    cb = CIRCUITS[circuit_name]

    if not cb.allow_request():
        logging.warning(f"Circuit '{circuit_name}' is OPEN. Fast-failing request to {url}")
        return None

    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(url, headers=headers, timeout=timeout)
            if res.status_code == 429:  # Rate limited
                retry_after = float(res.headers.get("Retry-After", 2.0))
                jitter = random.uniform(0.1, 0.5)
                sleep_duration = retry_after + jitter
                logging.warning(f"[{circuit_name}] HTTP 429 Rate limited. Sleeping {sleep_duration:.2f}s...")
                time.sleep(sleep_duration)
                continue

            res.raise_for_status()
            cb.record_success()
            return res

        except Exception as e:
            last_exc = e
            clean_err = scrub_sensitive_tokens(str(e))
            logging.warning(f"[{circuit_name}] Request failed (attempt {attempt}/{max_retries}): {clean_err}")
            
            if attempt < max_retries:
                sleep_duration = (backoff_factor ** attempt) + random.uniform(0.1, 0.5)
                time.sleep(sleep_duration)

    cb.record_failure()
    logging.error(f"[{circuit_name}] Circuit tripped after {max_retries} failed attempts. Error: {scrub_sensitive_tokens(str(last_exc))}")
    return None

def write_health_status(upstream_statuses: Dict[str, bool]):
    """Emits machine-readable health state for autonomous monitors."""
    os.makedirs(os.path.dirname(HEALTH_FILE), exist_ok=True)
    all_healthy = all(upstream_statuses.values()) if upstream_statuses else True

    health_record = {
        "status": "HEALTHY" if all_healthy else "DEGRADED",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "upstream_providers": upstream_statuses,
        "circuit_states": {name: cb.state for name, cb in CIRCUITS.items()}
    }

    with open(HEALTH_FILE, "w", encoding="utf-8") as f:
        json.dump(health_record, f, indent=2)
    logging.info(f"✓ Health status written to {HEALTH_FILE} (System: {health_record['status']})")
