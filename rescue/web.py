"""The product — a worklist for "the compliance officer who has never opened a database".

Reads what the 4 agents wrote to memory and shows: the headline, what each agent did, and a
worst-first worklist where every row explains itself (the problem, in plain words, and what to do).
The signed audit summary (Agent 4) is downloadable.

Run:  python -m rescue.web   →  http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import html
import json

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse

from . import config
from .memory import Memory

app = FastAPI(title="Harven Data Rescue")

_SEV = {"critical": "#dc2626", "high": "#ea580c", "medium": "#ca8a04", "low": "#64748b"}
_ACT = {"fix": "#16a34a", "flag": "#ca8a04", "escalate": "#dc2626"}


def _data():
    mem = Memory()
    acted = mem.read("acted") or []
    stats = mem.read("summary_stats") or {}
    return mem, acted, stats


@app.get("/", response_class=HTMLResponse)
def index():
    mem, acted, stats = _data()
    crit = sum(1 for f in acted if f["severity_label"] == "critical")
    high = sum(1 for f in acted if f["severity_label"] == "high")
    total_records = max([stats.get("total", 0)], default=0)

    rows = []
    for f in acted:
        sc = _SEV.get(f["severity_label"], "#64748b")
        ac = _ACT.get(f["action"], "#64748b")
        rows.append(f"""
        <tr class="row" data-sev="{f['severity_label']}" data-act="{f['action']}">
          <td><span class="pill" style="background:{sc}">{f['severity_label']}</span></td>
          <td class="mono">{html.escape(f['record_id'])}<br><span class="muted">plant {html.escape(f['plant_id'])}</span></td>
          <td>{html.escape(f['category'])}</td>
          <td>{html.escape(f['reason'])}</td>
          <td><span class="pill" style="background:{ac}">{f['action']}</span><br>
              <span class="muted">{html.escape(f['action_detail'])}</span></td>
        </tr>""")

    agents = [
        ("1 · Find", f"read {stats.get('total','?')} issues across {len(stats.get('plants',{}))} plants"),
        ("2 · Rank", f"{crit} critical, {high} high — worst first, with reasons"),
        ("3 · Act", " · ".join(f"{k}: {v}" for k, v in stats.get("by_action", {}).items())),
        ("4 · Explain", "wrote a signed summary you can download"),
    ]
    strip = "".join(f'<div class="agent"><b>Agent {a}</b><div class="muted">{html.escape(b)}</div></div>'
                    for a, b in agents)

    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Harven Data Rescue</title>
<style>
 body{{margin:0;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;color:#0f172a;background:#f8fafc}}
 header{{background:#0f172a;color:#fff;padding:16px 22px}}
 header h1{{margin:0;font-size:20px}} header .muted{{color:#94a3b8}}
 .bar{{display:flex;gap:18px;padding:14px 22px;background:#fff;border-bottom:1px solid #e2e8f0;flex-wrap:wrap}}
 .stat b{{font-size:22px}} .stat{{min-width:90px}}
 .agents{{display:flex;gap:10px;padding:12px 22px;flex-wrap:wrap}}
 .agent{{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:8px 12px;flex:1;min-width:160px}}
 .wrap{{padding:12px 22px}}
 .filters{{margin:8px 0}} .filters button{{margin-right:6px;padding:5px 11px;border:1px solid #cbd5e1;border-radius:20px;background:#fff;cursor:pointer}}
 .filters button.on{{background:#0f172a;color:#fff;border-color:#0f172a}}
 table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden}}
 th,td{{text-align:left;padding:9px 12px;border-bottom:1px solid #f1f5f9;vertical-align:top}}
 th{{background:#f8fafc;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#64748b}}
 .pill{{color:#fff;border-radius:20px;padding:1px 9px;font-size:12px}}
 .muted{{color:#64748b;font-size:12px}} .mono{{font-family:ui-monospace,monospace;font-size:12px}}
 .dl{{display:inline-block;background:#16a34a;color:#fff;text-decoration:none;padding:8px 14px;border-radius:8px;font-weight:600}}
</style></head><body>
<header>
  <h1>Harven Data Rescue <span class="muted">— pre-audit data integrity</span></h1>
  <div class="muted">These are the data problems we found before your audit, worst first.
    Every row explains itself and what to do. No database knowledge needed.</div>
</header>
<div class="bar">
  <div class="stat"><b>{stats.get('total','?')}</b><br><span class="muted">issues found</span></div>
  <div class="stat"><b style="color:#dc2626">{crit}</b><br><span class="muted">critical</span></div>
  <div class="stat"><b style="color:#ea580c">{high}</b><br><span class="muted">high</span></div>
  <div class="stat"><b>{stats.get('by_action',{}).get('fix',0)}</b><br><span class="muted">auto-fixable</span></div>
  <div class="stat" style="margin-left:auto"><a class="dl" href="/download">⬇ Download signed summary</a></div>
</div>
<div class="agents">{strip}</div>
<div class="wrap">
  <div class="filters">
    <b>Show:</b>
    <button class="on" onclick="flt(this,'sev','all')">all</button>
    <button onclick="flt(this,'sev','critical')">critical</button>
    <button onclick="flt(this,'sev','high')">high</button>
    <button onclick="flt(this,'act','fix')">auto-fixable</button>
    <button onclick="flt(this,'act','escalate')">escalate</button>
  </div>
  <table>
    <thead><tr><th>Severity</th><th>Record</th><th>Problem type</th><th>What's wrong (why)</th><th>What to do</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</div>
<script>
function flt(btn,kind,val){{
  document.querySelectorAll('.filters button').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on');
  document.querySelectorAll('.row').forEach(r=>{{
    const show = (val==='all') || (kind==='sev'&&r.dataset.sev===val) || (kind==='act'&&r.dataset.act===val);
    r.style.display = show ? '' : 'none';
  }});
}}
</script>
</body></html>"""


@app.get("/download")
def download():
    return FileResponse(config.OUTPUT / "audit_summary.md", media_type="text/markdown",
                        filename="Harven_Audit_Summary.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
