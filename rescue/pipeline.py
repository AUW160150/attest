"""The 4-agent pipeline, wired through shared memory (R01 + R02).

Find → Rank → Act → Explain. Each agent reads the previous agent's output FROM memory and writes
its own back, so the handoffs are real and inspectable.

Usage:  python -m rescue.pipeline
"""
from __future__ import annotations

import collections

from rich.console import Console
from rich.rule import Rule

from . import config
from .load import load_records, load_customers
from .memory import Memory
from .agent_find import find_issues
from .agent_rank import rank
from .agent_act import act
from .agent_explain import explain

console = Console()


def run() -> dict:
    mem = Memory()
    console.print(f"[dim]memory backend: {mem.backend}[/dim]")
    records, customers = load_records(), load_customers()

    console.print(Rule("Agent 1 · Find It"))
    findings = find_issues(records, customers)
    mem.write("findings", findings)
    console.print(f"found [bold]{len(findings)}[/bold] issues → memory['findings']")

    console.print(Rule("Agent 2 · Rank It"))
    ranked = rank(mem.read("findings"))          # reads Agent 1 from memory
    mem.write("ranked", ranked)
    sev = collections.Counter(f["severity_label"] for f in ranked)
    console.print(f"prioritized worst-first → memory['ranked']  ({dict(sev)})")

    console.print(Rule("Agent 3 · Act On It"))
    acted = act(mem.read("ranked"))              # reads Agent 2 from memory
    mem.write("acted", acted)
    actc = collections.Counter(f["action"] for f in acted)
    console.print(f"assigned actions → memory['acted']  ({dict(actc)})")

    console.print(Rule("Agent 4 · Explain It"))
    md, stats = explain(mem.read("acted"), len(records))   # reads Agent 3 from memory
    mem.write("summary_stats", stats)
    console.print(f"wrote signable summary → [green]output/audit_summary.md[/green] "
                  f"({len(md)} chars)")

    console.print(Rule("Done"))
    console.print(f"[bold]{len(records):,}[/bold] records · [bold]{len(acted)}[/bold] issues · "
                  f"critical+high: [bold]{sum(1 for f in acted if f['severity_label'] in ('critical','high'))}[/bold]")
    return {"records": len(records), "findings": len(acted), "stats": stats}


if __name__ == "__main__":
    run()
