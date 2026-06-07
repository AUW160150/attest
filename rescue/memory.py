"""Shared memory layer — the bus every agent reads from and writes to (hackathon R02).

Agents never call each other directly: Agent 1 writes findings to memory, Agent 2 reads them,
ranks, writes back, etc. This makes the handoffs real and inspectable.

Backend: Cognee when available/configured (set RESCUE_USE_COGNEE=1), else a transparent JSON store
with the SAME interface so the pipeline always runs. `backend` reports which is active.
"""
from __future__ import annotations

import json
import os

from . import config


class Memory:
    def __init__(self):
        self.backend = "json-file"
        self._cognee = None
        if os.environ.get("RESCUE_USE_COGNEE") == "1":
            try:
                import cognee  # noqa
                self._cognee = cognee
                self.backend = "cognee"
            except Exception as e:  # pragma: no cover
                print(f"[memory] Cognee unavailable ({e}); using json-file backend")

    def write(self, namespace: str, obj) -> None:
        (config.MEMORY_DIR / f"{namespace}.json").write_text(json.dumps(obj, indent=2))
        if self._cognee is not None:  # pragma: no cover
            try:
                import asyncio
                asyncio.run(self._cognee.add(json.dumps(obj), node_set=[namespace]))
            except Exception as e:
                print(f"[memory] cognee.add failed for {namespace}: {e}")

    def read(self, namespace: str):
        p = config.MEMORY_DIR / f"{namespace}.json"
        return json.loads(p.read_text()) if p.exists() else None
