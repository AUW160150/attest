# Product Brief — Attest (Track 01)

**Product:** Attest — *find, fix, and explain broken data before your audit.*
**Team:** rodela (Builder) · **Demo client:** Harven Manufacturing · **Track:** 01 — Data Rescue · **Date:** 2026-06-07

## The user
**The compliance officer who has never opened a database.** Four days before a regulatory audit,
they're told Harven's warehouse data "can't be trusted" — but they can't read SQL, can't spot a
bad join, and can't tell a real problem from noise.

## The crisis → the product
The crisis: 5,000 records across three plants, ~hundreds of seeded errors (duplicates, unit
conflicts, impossible values, orphaned references). **The product:** a pre-audit worklist that
finds every problem, ranks it worst-first, says in plain English *what's wrong and why*, recommends
*what to do*, and produces a **signed summary the officer can download and hand to auditors** — no
database knowledge required.

## How it works — 4 agents, real handoffs through shared memory
1. **Find It** — scans all 5,000 records, flags issues with a concrete reason each.
2. **Rank It** — prioritizes worst-first (severity bumped when a bad record already shipped).
3. **Act On It** — assigns each issue: auto-**fix**, **flag** for a human, or **escalate**.
4. **Explain It** — writes the one-page, signable audit summary.
Agents never call each other directly — each reads the prior agent's output from the **memory
layer** and writes its own back, so collaboration is real and inspectable.

## Success conditions (judge us against these)
- [ ] A compliance officer can open the product **cold** and understand the top issues with no help.
- [ ] **Every** issue shows a plain-language reason — never "the model said so."
- [ ] Issues are **ranked worst-first** with a reason for the ranking.
- [ ] Each issue has a **recommended action** (fix / flag / escalate) with a reason.
- [ ] The agents run on the **real Kaggle data** and hand off through shared memory.
- [ ] The **signed audit summary is downloadable** from the product.

## Out of scope (today)
Writing fixes back to the source system; catching 100% of seeded issues (we optimize for
precision + explainability over recall); fraud/graph analysis (that's Track 02).

## Stack
Memory: **Cognee** · reasoning/narrative: **Anthropic (Claude)** · product: **FastAPI** ·
entity research on customers/plants: **Geodo** · demo: **Trupeer**.
