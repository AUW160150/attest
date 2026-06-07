"""Agent 3 — Act On It.

Reads the ranked findings and decides an action for each: FIX (safe, deterministic correction),
FLAG (needs a human to supply the right value), or ESCALATE (needs a decision/owner outside the
data). Every action carries a reason and a concrete proposed change where possible.
"""
from __future__ import annotations

# category -> (action, how)
POLICY = {
    "duplicate": ("fix", "remove the duplicate row and keep the original record"),
    "impossible_value": ("flag", "a human must supply a valid value (cannot be auto-corrected safely)"),
    "orphaned_reference": ("escalate", "verify the customer or create the missing master record"),
    "future_date": ("flag", "correct the mistyped date with the real production/ship date"),
    "date_order": ("flag", "correct the dates so ship is on/after production"),
    "unit_conflict": ("flag", "confirm the weight/unit with the plant; likely a unit or typo error"),
    "attribute_conflict": ("escalate", "agree one canonical part name across plants"),
}


def act(ranked: list[dict]) -> list[dict]:
    out = []
    for f in ranked:
        action, how = POLICY.get(f["category"], ("flag", "needs human review"))
        g = dict(f)
        g["action"] = action
        g["action_detail"] = how
        g["action_reason"] = f"{f['category']} ({f['severity_label']}): {how}"
        out.append(g)
    return out
