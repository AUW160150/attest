"""Agent 1 — Find It.

Reads every record and finds what's wrong. Each finding carries a CONCRETE, human-followable
reason (hackathon R07: "every agent decision must have a visible reason"). Detectors are
deterministic so the reasons are auditable, not "the model said so".

Categories (per the README): duplicates, unit/attribute conflicts, impossible values,
orphaned references.

Usage:  python -m rescue.agent_find
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import statistics

from rich.console import Console
from rich.table import Table

from . import config
from .load import load_records, load_customers

console = Console()


def _date(s: str):
    try:
        return dt.datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def _num(s: str):
    try:
        return float(s)
    except Exception:
        return None


def find_issues(records: list[dict], customers: dict[str, dict]) -> list[dict]:
    findings: list[dict] = []
    n = 0

    def add(rec, category, field, value, reason):
        nonlocal n
        n += 1
        findings.append({
            "finding_id": f"F-{n:05d}",
            "record_id": rec.get("record_id"),
            "plant_id": rec.get("plant_id"),
            "part_number": rec.get("part_number"),
            "status": rec.get("status"),
            "category": category,
            "field": field,
            "value": value,
            "reason": reason,
        })

    # --- pre-compute reference structures for duplicate / conflict / outlier detection ---
    dup_key = lambda r: (r["plant_id"], r["part_number"], r["quantity"], r["weight_kg"],
                         r["production_date"], r["ship_date"], r["customer_id"])
    seen_keys: dict = {}
    name_by_part: dict = collections.defaultdict(set)
    weights_by_part: dict = collections.defaultdict(list)
    for r in records:
        name_by_part[r["part_number"]].add(r["part_name"])
        w = _num(r["weight_kg"])
        if w is not None:
            weights_by_part[r["part_number"]].append(w)
    median_w = {p: statistics.median(ws) for p, ws in weights_by_part.items() if ws}

    for r in records:
        rid = r["record_id"]

        # 1) orphaned reference — customer not in master
        cid = r["customer_id"]
        if cid not in customers:
            add(r, "orphaned_reference", "customer_id", cid,
                f"customer_id '{cid}' is not in the customer master ({len(customers)} known customers)")

        # 2) impossible values — quantity / weight
        q = _num(r["quantity"])
        if q is None:
            add(r, "impossible_value", "quantity", r["quantity"], f"quantity '{r['quantity']}' is not a number")
        elif q <= 0:
            add(r, "impossible_value", "quantity", r["quantity"], f"quantity {r['quantity']} must be greater than zero")
        w = _num(r["weight_kg"])
        if w is None:
            add(r, "impossible_value", "weight_kg", r["weight_kg"], f"weight_kg '{r['weight_kg']}' is not a number")
        elif w <= 0:
            add(r, "impossible_value", "weight_kg", r["weight_kg"], f"weight_kg {r['weight_kg']} must be greater than zero")

        # 3) date sanity — order + future
        pd_, sd_ = _date(r["production_date"]), _date(r["ship_date"])
        if pd_ and sd_ and sd_ < pd_:
            add(r, "date_order", "ship_date", r["ship_date"],
                f"ship_date {r['ship_date']} is before production_date {r['production_date']}")
        for fld, d in (("production_date", pd_), ("ship_date", sd_)):
            if d and d > config.AUDIT_DATE:
                add(r, "future_date", fld, r[fld], f"{fld} {r[fld]} is in the future (after audit date {config.AUDIT_DATE})")

        # 4) attribute conflict — same part number, different names
        if len(name_by_part[r["part_number"]]) > 1:
            add(r, "attribute_conflict", "part_name", r["part_name"],
                f"part_number {r['part_number']} appears with conflicting names: "
                f"{sorted(name_by_part[r['part_number']])}")

        # 5) weight/unit outlier — same part, weight far from its median (likely unit/typo error)
        if w is not None and r["part_number"] in median_w:
            med = median_w[r["part_number"]]
            if med > 0 and (w > med * 5 or w < med / 5) and len(weights_by_part[r["part_number"]]) >= 3:
                add(r, "unit_conflict", "weight_kg", r["weight_kg"],
                    f"weight_kg {r['weight_kg']} is far from the usual weight (~{med:.1f}) for part {r['part_number']} "
                    f"— possible unit error or typo")

        # 6) duplicate — identical business content under a different record_id
        k = dup_key(r)
        if k in seen_keys:
            add(r, "duplicate", "record_id", rid,
                f"record {rid} duplicates {seen_keys[k]} (same part, plant, qty, weight, dates, customer)")
        else:
            seen_keys[k] = rid

    return findings


def main() -> None:
    records, customers = load_records(), load_customers()
    findings = find_issues(records, customers)
    (config.OUTPUT / "findings.json").write_text(json.dumps(findings, indent=2))

    by_cat = collections.Counter(f["category"] for f in findings)
    table = Table(title=f"Agent 1 · Find It — {len(findings)} issues in {len(records):,} records")
    table.add_column("Category", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Example reason", overflow="fold")
    for cat, cnt in by_cat.most_common():
        ex = next(f["reason"] for f in findings if f["category"] == cat)
        table.add_row(cat, str(cnt), ex)
    console.print(table)
    console.print(f"[green]Saved[/green] output/findings.json  ·  "
                  f"[bold]{len(findings)}[/bold] findings (README hint: ~850 seeded issues)")


if __name__ == "__main__":
    main()
