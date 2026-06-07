"""Agent 4 — Explain It.

Reads everything the other agents wrote to memory and produces a human-readable audit summary the
compliance officer can read and sign. Downloadable (R08). Uses one LLM call for the narrative; all
the underlying numbers/reasons come from the deterministic agents, so nothing is "made up".
"""
from __future__ import annotations

import collections
import datetime as dt

import anthropic

from . import config

MODEL = "claude-sonnet-4-6"


def _stats(acted: list[dict]) -> dict:
    by_cat = collections.Counter(f["category"] for f in acted)
    by_sev = collections.Counter(f["severity_label"] for f in acted)
    by_act = collections.Counter(f["action"] for f in acted)
    plants = collections.Counter(f["plant_id"] for f in acted)
    records = {f["record_id"] for f in acted}
    return {"total": len(acted), "by_category": dict(by_cat), "by_severity": dict(by_sev),
            "by_action": dict(by_act), "plants": dict(plants), "records_affected": len(records)}


def explain(acted: list[dict], total_records: int, model: str = MODEL) -> tuple[str, dict]:
    stats = _stats(acted)
    top = [f for f in acted if f["severity_label"] in ("critical", "high")][:12]
    top_lines = "\n".join(f"- [{f['severity_label']}] {f['record_id']} ({f['plant_id']}): "
                          f"{f['reason']} → {f['action'].upper()}: {f['action_detail']}" for f in top)

    prompt = (
        "You are writing a one-page data-integrity audit summary for a NON-TECHNICAL compliance "
        "officer at Harven Manufacturing, four days before a regulatory audit. Be clear, calm, and "
        "specific. Use plain language, no jargon. Structure: (1) one-line bottom line, (2) what we "
        "checked, (3) what we found (use the numbers), (4) what is being done, (5) what still needs "
        "a human decision, (6) a sign-off line with a blank for name/date. Do not invent numbers.\n\n"
        f"Records checked: {total_records}\n"
        f"Total issues: {stats['total']}\n"
        f"By severity: {stats['by_severity']}\n"
        f"By category: {stats['by_category']}\n"
        f"By recommended action: {stats['by_action']}\n"
        f"Plants affected: {stats['plants']}\n\n"
        f"Most serious issues:\n{top_lines}\n"
    )
    client = anthropic.Anthropic(api_key=config.get_env("ANTHROPIC_API_KEY", required=True))
    resp = client.messages.create(model=model, max_tokens=1500,
                                  messages=[{"role": "user", "content": prompt}])
    narrative = resp.content[0].text

    md = (f"# Harven Manufacturing — Data Integrity Audit Summary\n\n"
          f"*Generated {dt.date.today()} · {total_records} records reviewed · "
          f"{stats['total']} issues · backend: deterministic agents + LLM narrative*\n\n"
          f"{narrative}\n")
    (config.OUTPUT / "audit_summary.md").write_text(md, encoding="utf-8")
    return md, stats
