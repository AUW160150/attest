"""Agent 2 — Rank It.

Reads Agent 1's findings (from shared memory) and prioritizes them worst-first, with a reason for
every ranking decision (R07). Severity = base risk of the category, bumped when the bad record is
already shipped/completed (i.e., the error has likely escaped before the audit).
"""
from __future__ import annotations

# base severity 1(low)–4(critical) per category
BASE = {
    "impossible_value": 4,
    "future_date": 4,
    "orphaned_reference": 3,
    "date_order": 3,
    "unit_conflict": 2,
    "attribute_conflict": 2,
    "duplicate": 2,
}
LABEL = {4: "critical", 3: "high", 2: "medium", 1: "low"}
_ESCAPED = {"shipped", "completed"}


def rank(findings: list[dict]) -> list[dict]:
    ranked = []
    for f in findings:
        sev = BASE.get(f["category"], 2)
        reasons = [f"{f['category']} is a base {LABEL[sev]} risk"]
        if f.get("status") in _ESCAPED:
            sev = min(sev + 1, 4)
            reasons.append(f"record is already '{f['status']}', so the error likely escaped before the audit")
        g = dict(f)
        g["severity"] = sev
        g["severity_label"] = LABEL[sev]
        g["rank_reason"] = "; ".join(reasons)
        ranked.append(g)
    # worst first; stable within severity by category then finding_id
    ranked.sort(key=lambda x: (-x["severity"], x["category"], x["finding_id"]))
    for i, g in enumerate(ranked, 1):
        g["rank"] = i
    return ranked
