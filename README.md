# Attest — M-AGENTS Hackathon (Track 01)
#Demo: https://app.trupeer.ai/view/IK5wLIGoK/attest
*Note* Trupeer video didn't work.



*Find, fix, and explain broken data before your audit.* (Demo client: Harven Manufacturing.)

A pre-audit data-integrity tool for **the compliance officer who has never opened a database.**
Four agents find, rank, act on, and explain broken warehouse data — every decision in plain
language with a visible reason. See `PRODUCT_BRIEF.md`.

## The 4 agents (real handoffs through a shared memory layer)
1. **Find It** (`rescue/agent_find.py`) — scans 5,000 records; flags duplicates, orphaned
   references, impossible values, future/out-of-order dates, unit/weight outliers — each with a
   concrete reason.
2. **Rank It** (`rescue/agent_rank.py`) — worst-first severity (bumped if the bad record already shipped).
3. **Act On It** (`rescue/agent_act.py`) — fix / flag / escalate, with a reason.
4. **Explain It** (`rescue/agent_explain.py`) — writes a one-page **signable, downloadable** audit summary (LLM narrative over the agents' real numbers).

Agents never call each other — each reads the previous one's output from `rescue/memory.py` and
writes its own back (`output/memory/*.json`). Handoffs are real and inspectable.

## Run
```bash
pip install -r requirements.txt
python -m rescue.pipeline      # runs all 4 agents → output/audit_summary.md
python -m rescue.web           # the product → http://127.0.0.1:8000
```
Data: `data/` (Kaggle Track 01 benchmark). API key: put `ANTHROPIC_API_KEY=...` in `.env`.

## Memory layer (Cognee)
`rescue/memory.py` is the shared bus every agent uses. The **Cognee** backend is wired
(`RESCUE_USE_COGNEE=1`) but, in the hackathon window, Cognee's bundled `openai/httpx` versions hit a
`proxies` conflict; we ship on the reliable JSON-file backend (identical read/write interface). The
Cognee path is one fixed dependency pin away.

## Judging coverage
- **Agents work on real data** — runs on the 5,000-record Kaggle benchmark, nothing hardcoded.
- **Explainable** — every finding, ranking, and action has a visible, human-followable reason.
- **End user can use it cold** — `rescue/web.py` is a worst-first worklist a non-technical officer reads top-down.
- **Matches the brief** — see `PRODUCT_BRIEF.md` success conditions.
- **Collaboration** — staged handoffs through the shared memory layer.
