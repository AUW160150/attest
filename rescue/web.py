"""The product — a guided, professional walkthrough for "the compliance officer who has never
opened a database": See the data → Watch the 4 agents work → Review results & download the summary.

Styled after the Demo_3 pipeline UI (DM Sans / Playfair, paper background, teal accent).

Run:  python -m rescue.web   →  http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import collections
import html
import json

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse

from . import config
from .load import load_records, load_customers
from .memory import Memory

app = FastAPI(title="Harven Data Rescue")

SEV = {"critical": "#DC2626", "high": "#D97706", "medium": "#CA8A04", "low": "#78716C"}
ACT = {"fix": "#059669", "flag": "#D97706", "escalate": "#DC2626"}

COL_DESC = {
    "record_id": "unique id for the row", "plant_id": "which plant (A, B, C)",
    "part_number": "the part's code", "quantity": "how many", "weight_kg": "weight in kg",
    "production_date": "date made", "ship_date": "date shipped",
    "customer_id": "which customer (links to the customer list)", "status": "where it is in the process",
}
CAT_DESC = {
    "orphaned_reference": "Points to a customer that isn't in the customer list",
    "impossible_value": "A value that can't be real (e.g. negative quantity)",
    "date_order": "Shipped before it was produced",
    "future_date": "A date in the future, after the audit",
    "duplicate": "The same record entered more than once",
    "unit_conflict": "A weight far from the usual for that part — likely a unit/typo error",
    "attribute_conflict": "The same part described two different ways",
}

CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DM Sans',sans-serif;background:#FAFAF8;color:#1C1917;-webkit-font-smoothing:antialiased;line-height:1.55}
.serif{font-family:'Playfair Display',serif}
.mono{font-family:'DM Mono',monospace}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px}
header{background:#0A1E38;color:#fff;padding:26px 0}
header h1{font-family:'Playfair Display',serif;font-size:30px;font-weight:600;letter-spacing:-.3px}
header p{color:#9DB2CE;margin-top:4px;max-width:680px}
.steps{display:flex;gap:8px;margin:22px 0 8px}
.step{flex:1;background:#fff;border:1px solid #E7E5E0;border-radius:12px;padding:12px 16px;cursor:pointer;transition:.2s}
.step.on{border-color:#0D9488;box-shadow:0 4px 18px rgba(13,148,136,.10)}
.step .n{display:inline-flex;width:22px;height:22px;align-items:center;justify-content:center;border-radius:50%;background:#F5F4F0;color:#78716C;font-size:12px;font-weight:600;margin-right:8px}
.step.on .n{background:#0D9488;color:#fff}
.step b{font-size:14px}.step span{color:#78716C;font-size:12px;display:block;margin-left:30px}
.pane{display:none;animation:fade .35s ease}.pane.on{display:block}
@keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.card{background:#fff;border:1px solid #E7E5E0;border-radius:14px;padding:20px 22px;margin:14px 0}
.card h2{font-family:'Playfair Display',serif;font-size:19px;font-weight:600;margin-bottom:4px}
.muted{color:#78716C;font-size:13px}
.grid{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0}
.kpi{background:#F8FAF9;border:1px solid #E7E5E0;border-radius:12px;padding:12px 16px;min-width:120px}
.kpi b{font-size:24px;display:block}.kpi span{color:#78716C;font-size:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #F1EFEA;vertical-align:top}
th{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#78716C;background:#FAFAF8}
.pill{color:#fff;border-radius:20px;padding:1px 9px;font-size:12px;white-space:nowrap}
.tag{background:#F5F4F0;border-radius:6px;padding:1px 7px;font-size:12px;color:#57534E}
.cat{display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #F1EFEA}
.cat b{min-width:160px}
.flow{display:flex;flex-direction:column;gap:12px;margin-top:8px}
.agent{display:flex;gap:14px;align-items:flex-start;background:#fff;border:1px solid #E7E5E0;border-radius:12px;padding:16px 18px;opacity:.45;transition:.4s}
.agent.live{opacity:1;border-color:#0D9488;box-shadow:0 6px 20px rgba(13,148,136,.08)}
.agent.done{opacity:1}
.agent .ic{font-size:24px;width:42px;height:42px;display:flex;align-items:center;justify-content:center;background:#F5F4F0;border-radius:10px;flex-shrink:0}
.agent.live .ic,.agent.done .ic{background:rgba(13,148,136,.10)}
.agent h3{font-size:15px;font-weight:600}.agent .role{color:#78716C;font-size:12px}
.agent .out{margin-top:6px;font-size:13px;color:#0D9488;font-weight:600;min-height:18px}
.agent .mem{font-size:11px;color:#A8A29E;margin-top:2px}
.spinner{width:14px;height:14px;border:2px solid rgba(13,148,136,.25);border-top-color:#0D9488;border-radius:50%;animation:spin .7s linear infinite;display:inline-block;vertical-align:-2px}
@keyframes spin{to{transform:rotate(360deg)}}
.btn{display:inline-flex;align-items:center;gap:8px;background:#0D9488;color:#fff;border:none;border-radius:9px;padding:11px 20px;font:600 14px 'DM Sans';cursor:pointer}
.btn:hover{filter:brightness(1.05)}.btn.ghost{background:#fff;color:#1C1917;border:1px solid #E7E5E0}
.btn.dl{background:#059669}
.filters{margin:10px 0}.filters button{margin-right:6px;padding:5px 12px;border:1px solid #E7E5E0;border-radius:20px;background:#fff;cursor:pointer;font:inherit;font-size:13px}
.filters button.on{background:#1C1917;color:#fff;border-color:#1C1917}
.hidden{display:none}
"""

JS = """
function go(n){
  document.querySelectorAll('.step').forEach((s,i)=>s.classList.toggle('on',i===n));
  document.querySelectorAll('.pane').forEach((p,i)=>p.classList.toggle('on',i===n));
  window.scrollTo({top:0,behavior:'smooth'});
}
let ran=false;
function runPipeline(){
  if(ran){return;}
  ran=true;
  const stages=document.querySelectorAll('.agent');
  let i=0;
  function step(){
    if(i>0){stages[i-1].classList.remove('live');stages[i-1].classList.add('done');
      stages[i-1].querySelector('.out').innerHTML=stages[i-1].dataset.out;}
    if(i>=stages.length){document.getElementById('toResults').classList.remove('hidden');return;}
    stages[i].classList.add('live');
    stages[i].querySelector('.out').innerHTML='<span class="spinner"></span> working…';
    i++;
    setTimeout(step,1100);
  }
  step();
}
function flt(btn,kind,val){
  document.querySelectorAll('.filters button').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on');
  document.querySelectorAll('.row').forEach(r=>{
    const show=(val==='all')||(kind==='sev'&&r.dataset.sev===val)||(kind==='act'&&r.dataset.act===val);
    r.style.display=show?'':'none';
  });
}
"""


def index_page() -> str:
    records, customers = load_records(), load_customers()
    mem = Memory()
    acted = mem.read("acted") or []
    total = len(records)
    plants = sorted({r["plant_id"] for r in records})
    crit = sum(1 for f in acted if f["severity_label"] == "critical")
    high = sum(1 for f in acted if f["severity_label"] == "high")
    fix = sum(1 for f in acted if f["action"] == "fix")
    by_cat = collections.Counter(f["category"] for f in acted)

    # --- data preview ---
    cols = ["record_id", "plant_id", "part_number", "quantity", "weight_kg",
            "production_date", "ship_date", "customer_id", "status"]
    head = "".join(f"<th>{c}</th>" for c in cols)
    prev = ""
    for r in records[:6]:
        prev += "<tr>" + "".join(f'<td class="mono">{html.escape(str(r[c]))}</td>' for c in cols) + "</tr>"
    coldesc = "".join(f'<div class="cat"><b class="mono">{c}</b><span class="muted">{d}</span></div>'
                      for c, d in COL_DESC.items())
    cats = "".join(f'<div class="cat"><b>{c.replace("_"," ")}</b>'
                   f'<span class="muted">{CAT_DESC.get(c,"")} '
                   f'<span class="tag">{by_cat.get(c,0)} found</span></span></div>'
                   for c in CAT_DESC)

    # --- Geodo domain research (web platform only; pasted by the Domain Expert) ---
    geodo_path = config.DATA / "geodo_notes.md"
    geodo_txt = geodo_path.read_text(encoding="utf-8") if geodo_path.exists() else ""
    geodo_html = "<br>".join(html.escape(l) for l in geodo_txt.splitlines()) if geodo_txt else \
        "Add your Geodo findings to <span class='mono'>data/geodo_notes.md</span>."

    # --- agent flow ---
    agents = [
        ("🔎", "Agent 1 · Find It", "Reads all the records and flags what's wrong, with a reason for each.",
         f"{len(acted)} issues found"),
        ("📊", "Agent 2 · Rank It", "Sorts the problems worst-first, and says why each ranks where it does.",
         f"{crit} critical · {high} high"),
        ("🛠️", "Agent 3 · Act On It", "Decides what to do with each: fix, flag for a person, or escalate.",
         f"{fix} auto-fixable · rest flagged"),
        ("📝", "Agent 4 · Explain It", "Writes a one-page summary the officer can read, sign, and download.",
         "signed audit memo ready"),
    ]
    flow = ""
    for ic, name, role, out in agents:
        flow += (f'<div class="agent" data-out="{html.escape(out)}">'
                 f'<div class="ic">{ic}</div><div style="flex:1">'
                 f'<h3>{name}</h3><div class="role">{role}</div>'
                 f'<div class="out"></div>'
                 f'<div class="mem">↕ reads &amp; writes the shared memory layer (Cognee)</div>'
                 f'</div></div>')

    # --- results worklist (top 60) ---
    rows = ""
    for f in acted[:60]:
        sc, ac = SEV.get(f["severity_label"], "#78716C"), ACT.get(f["action"], "#78716C")
        rows += (f'<tr class="row" data-sev="{f["severity_label"]}" data-act="{f["action"]}">'
                 f'<td><span class="pill" style="background:{sc}">{f["severity_label"]}</span></td>'
                 f'<td class="mono">{html.escape(f["record_id"])}<br><span class="muted">plant {html.escape(f["plant_id"])}</span></td>'
                 f'<td>{html.escape(f["category"].replace("_"," "))}</td>'
                 f'<td>{html.escape(f["reason"])}</td>'
                 f'<td><span class="pill" style="background:{ac}">{f["action"]}</span><br>'
                 f'<span class="muted">{html.escape(f["action_detail"])}</span></td></tr>')

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Harven Data Rescue</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&family=Playfair+Display:wght@500;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header><div class="wrap">
  <h1>Harven Data Rescue</h1>
  <p>Four days before the audit, your warehouse data can't be trusted. This finds every problem,
     explains it in plain words, and tells you what to do — no database knowledge needed.</p>
</div></header>
<div class="wrap">
  <div class="steps">
    <div class="step on" onclick="go(0)"><span class="n">1</span><b>See the data</b><span>what we're working with</span></div>
    <div class="step" onclick="go(1)"><span class="n">2</span><b>Watch the agents</b><span>4 agents, step by step</span></div>
    <div class="step" onclick="go(2)"><span class="n">3</span><b>Review & sign</b><span>worklist + summary</span></div>
  </div>

  <!-- STEP 1: DATA -->
  <div class="pane on">
    <div class="card">
      <h2>The data we're rescuing</h2>
      <div class="muted">Harven Manufacturing warehouse records, pulled in for the pre-audit review.</div>
      <div class="grid">
        <div class="kpi"><b>{total:,}</b><span>records</span></div>
        <div class="kpi"><b>{len(plants)}</b><span>plants ({", ".join(plants)})</span></div>
        <div class="kpi"><b>{len(customers)}</b><span>known customers</span></div>
        <div class="kpi"><b>{len(by_cat)}</b><span>problem types checked</span></div>
      </div>
      <h3 class="serif" style="margin:6px 0">A peek at the records</h3>
      <div style="overflow:auto"><table><thead><tr>{head}</tr></thead><tbody>{prev}</tbody></table></div>
      <div class="muted" style="margin-top:6px">Showing 6 of {total:,} rows.</div>
    </div>
    <div class="card">
      <h2>What each column means</h2>{coldesc}
    </div>
    <div class="card">
      <h2>The problems we look for</h2>{cats}
    </div>
    <div class="card" style="border-color:#0D9488">
      <h2>🌐 Real-world context <span class="muted" style="font-weight:400">— researched with Geodo</span></h2>
      <div class="muted" style="margin-top:8px;white-space:normal">{geodo_html}</div>
    </div>
    <button class="btn" onclick="go(1)">Next: watch the agents →</button>
  </div>

  <!-- STEP 2: AGENTS -->
  <div class="pane">
    <div class="card">
      <h2>How it works — 4 agents, real handoffs</h2>
      <div class="muted">Each agent does one job and passes its work to the next through a shared
        memory layer. Press play to watch.</div>
      <div style="margin:14px 0"><button class="btn" onclick="runPipeline()">▶ Run the rescue</button></div>
      <div class="flow">{flow}</div>
      <div id="toResults" class="hidden" style="margin-top:16px">
        <button class="btn" onclick="go(2)">See the results →</button>
      </div>
    </div>
  </div>

  <!-- STEP 3: RESULTS -->
  <div class="pane">
    <div class="card">
      <h2>Your worklist</h2>
      <div class="grid">
        <div class="kpi"><b>{len(acted)}</b><span>issues</span></div>
        <div class="kpi"><b style="color:#DC2626">{crit}</b><span>critical</span></div>
        <div class="kpi"><b style="color:#D97706">{high}</b><span>high</span></div>
        <div class="kpi"><b style="color:#059669">{fix}</b><span>auto-fixable</span></div>
        <div class="kpi" style="margin-left:auto;display:flex;align-items:center">
          <a class="btn dl" href="/download">⬇ Download signed summary</a></div>
      </div>
      <div class="filters">
        <button class="on" onclick="flt(this,'sev','all')">all</button>
        <button onclick="flt(this,'sev','critical')">critical</button>
        <button onclick="flt(this,'sev','high')">high</button>
        <button onclick="flt(this,'act','fix')">auto-fixable</button>
        <button onclick="flt(this,'act','escalate')">escalate</button>
      </div>
      <table><thead><tr><th>Severity</th><th>Record</th><th>Problem</th><th>What's wrong (why)</th><th>What to do</th></tr></thead>
      <tbody>{rows}</tbody></table>
      <div class="muted" style="margin-top:8px">Showing the top 60 of {len(acted)}, worst first.</div>
    </div>
  </div>
</div>
<script>{JS}</script>
</body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return index_page()


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
