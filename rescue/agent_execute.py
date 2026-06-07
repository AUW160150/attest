"""Agent 5 — Remediation Executor (Take Action).

The final pipeline step. Two parts:
  1. Auto-fix: safely applies the deterministic fixes (removes duplicate rows) and writes a cleaned
     dataset the officer can download.
  2. Human-in-the-loop: a data expert describes, in plain language, how to automate a fix for one of
     the remaining categories; an LLM turns that instruction into a concrete, previewable rule
     (what it would change, and what it would skip as too risky). Nothing is applied blindly.
"""
from __future__ import annotations

import csv
import json

import anthropic

from . import config

MODEL = "claude-sonnet-4-6"


def execute_auto_fixes(records: list[dict], acted: list[dict]) -> tuple[list[dict], list[dict]]:
    """Remove records flagged action == 'fix' (duplicates). Returns (cleaned_records, fix_log)."""
    fix_ids = {f["record_id"] for f in acted if f["action"] == "fix"}
    cleaned = [r for r in records if r["record_id"] not in fix_ids]
    fix_log = [{"record_id": f["record_id"], "category": f["category"], "reason": f["reason"]}
               for f in acted if f["action"] == "fix"]
    if records:
        cols = list(records[0].keys())
        with open(config.DATA / "track01_cleaned.csv", "w", newline="") as fp:
            w = csv.DictWriter(fp, fieldnames=cols)
            w.writeheader()
            w.writerows(cleaned)
    (config.OUTPUT / "fix_log.json").write_text(json.dumps(fix_log, indent=2))
    return cleaned, fix_log


def propose_fix(category: str, instruction: str, acted: list[dict], model: str = MODEL) -> dict:
    """Turn a human's plain-language instruction into a concrete, previewable automated fix."""
    affected = [f for f in acted if f["category"] == category]
    samples = [{"record_id": f["record_id"], "value": f.get("value"), "reason": f["reason"]}
               for f in affected[:8]]
    prompt = (
        f"A data steward wants to automate fixing '{category}' issues in manufacturing warehouse "
        f"records before a regulatory audit.\n"
        f"Their instruction: \"{instruction}\"\n\n"
        f"{len(affected)} records have this issue. Examples:\n{json.dumps(samples, indent=2)}\n\n"
        "Respond in 3 short labeled parts:\n"
        "RULE: one plain-English sentence describing the automated fix.\n"
        "TRANSFORM: the exact change as short pseudocode.\n"
        "SAFETY: which records it would change vs. SKIP as too risky for a human to confirm.\n"
        "Be concrete and conservative. Never fabricate values."
    )
    client = anthropic.Anthropic(api_key=config.get_env("ANTHROPIC_API_KEY", required=True))
    resp = client.messages.create(model=model, max_tokens=700,
                                  messages=[{"role": "user", "content": prompt}])
    return {"category": category, "affected": len(affected), "proposal": resp.content[0].text}
