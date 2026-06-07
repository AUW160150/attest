"""Shared memory layer — the bus every agent reads from and writes to (hackathon R02).

Agents never call each other directly: Agent 1 writes findings to memory, Agent 2 reads them,
ranks, writes back, etc. Handoffs are real and inspectable.

Cognee is the memory layer (enabled with RESCUE_USE_COGNEE=1, default on via .env). Every write is
published to Cognee so the agents share one knowledge store; a JSON mirror is always kept so the
pipeline is deterministic for the live demo. Publishing supports two paths:
  - a **static cognee CLI** (set COGNEE_CLI=/path/to/cognee) — shells out `COGNEE_CLI add <file> --dataset <ns>`
  - the Python SDK (cognee.add) as a fallback
Both are best-effort and never crash the demo.
"""
from __future__ import annotations

import json
import os
import subprocess

from . import config


class Memory:
    def __init__(self):
        config.load_env()
        self.use_cognee = os.environ.get("RESCUE_USE_COGNEE") == "1"
        self.cognee_cli = os.environ.get("COGNEE_CLI")  # path to the static cognee CLI, if provided
        self.backend = "cognee" if self.use_cognee else "json-file"

    def write(self, namespace: str, obj) -> None:
        path = config.MEMORY_DIR / f"{namespace}.json"
        path.write_text(json.dumps(obj, indent=2))           # reliable mirror (pipeline reads this)
        if self.use_cognee:
            self._publish(namespace, path, obj)

    def read(self, namespace: str):
        p = config.MEMORY_DIR / f"{namespace}.json"
        return json.loads(p.read_text()) if p.exists() else None

    # --- Cognee publishing (best-effort) ---------------------------------------------------------
    def _publish(self, namespace: str, path, obj) -> None:
        # Path 1: static cognee CLI (what the team is using)
        if self.cognee_cli:
            try:
                subprocess.run([self.cognee_cli, "add", str(path), "--dataset", namespace],
                               check=False, capture_output=True, timeout=120)
                return
            except Exception as e:
                print(f"[memory] cognee CLI publish failed for {namespace}: {e}")
        # Path 2: Python SDK fallback
        try:
            import asyncio
            import cognee
            asyncio.run(cognee.add(json.dumps(obj), dataset_name=namespace))
        except Exception as e:
            print(f"[memory] cognee SDK publish skipped for {namespace}: {str(e)[:80]}")

    def query(self, question: str):
        """Ask the shared memory a question (for the demo). Best-effort."""
        if not self.use_cognee:
            return None
        try:
            import asyncio
            import cognee
            return asyncio.run(cognee.search(question))
        except Exception as e:
            print(f"[memory] cognee query skipped: {str(e)[:80]}")
            return None
