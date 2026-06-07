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

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

from . import config
from .load import load_records, load_customers
from .memory import Memory
from .agent_execute import propose_fix

app = FastAPI(title="Attest")

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
.agent{cursor:pointer}
.chev{color:#0D9488;font-size:12px;display:inline-block;transition:.2s;margin-left:4px}
.agent.open .chev{transform:rotate(90deg)}
.detail{display:none;margin-top:12px;border-top:1px dashed #E7E5E0;padding-top:10px}
.agent.open .detail{display:block}
.drow{display:flex;gap:12px;padding:5px 0;font-size:13px;align-items:flex-start}
.drow>b{min-width:130px;color:#57534E;font-weight:600;flex-shrink:0}
.drow>span{flex:1;color:#1C1917}
.drow ul{margin:0;padding-left:16px}.drow li{margin:2px 0;color:#57534E}
.hint{color:#A8A29E;font-size:12px;margin-top:6px}
.sel,.inp{padding:9px 12px;border:1px solid #E7E5E0;border-radius:9px;font:14px 'DM Sans';background:#fff}
.inp{flex:1;min-width:260px}
#autoout{margin-top:14px}
#autoout .proposal{background:#F8FAF9;border:1px solid #D7E5E2;border-radius:12px;padding:14px 16px}
#autoout pre{white-space:pre-wrap;font:13px/1.5 'DM Mono',monospace;color:#1C1917;margin-top:8px}
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
function toggleDetail(id){
  const d=document.getElementById('detail-'+id);
  if(d){d.closest('.agent').classList.toggle('open');}
}
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
async function automate(){
  const cat=document.getElementById('autocat').value;
  const ins=document.getElementById('autoinp').value;
  const out=document.getElementById('autoout');
  if(!ins.trim()){out.innerHTML='<div class="hint">Type how you\\'d fix these first.</div>';return;}
  out.innerHTML='<div class="hint"><span class="spinner"></span> turning your instruction into a fix rule…</div>';
  try{
    const r=await fetch('/automate',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},
      body:'category='+encodeURIComponent(cat)+'&instruction='+encodeURIComponent(ins)});
    const d=await r.json();
    out.innerHTML='<div class="proposal"><b>'+esc(d.category)+'</b> · '+d.affected+
      ' records affected<pre>'+esc(d.proposal)+'</pre></div>';
  }catch(e){out.innerHTML='<div class="hint">Could not reach the model. Check the API key.</div>';}
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
    findings = mem.read("findings") or []
    ranked = mem.read("ranked") or []
    acted = mem.read("acted") or []
    executed = mem.read("executed") or {}
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

    # --- agent flow (functional names + full per-agent trace) ---
    # samples pulled from the real run
    det_s = [f["reason"] for f in findings[:3]]
    pri_s = [f'{f["severity_label"].upper()} (rank {f.get("rank","?")}) — {f["reason"][:70]} · why: {f["rank_reason"]}'
             for f in ranked[:2]]
    rem_s = [f'{f["action"].upper()} {f["record_id"]}: {f["action_detail"]}' for f in acted[:2]]
    # reporter sample: first couple of substantive lines of the summary
    sum_path = config.OUTPUT / "audit_summary.md"
    rep_s = []
    if sum_path.exists():
        for ln in sum_path.read_text(encoding="utf-8").splitlines():
            s = ln.strip()
            if s and not s.startswith("#") and not s.startswith("*") and not s.startswith("---"):
                rep_s.append(s)
            if len(rep_s) >= 2:
                break

    AG = [
        {"id": "detector", "ic": "🔎", "name": "Issue Detector",
         "role": "Scans every record and flags what's wrong, with a reason for each.",
         "out": f"{len(acted)} issues found",
         "tool": "Ran 7 deterministic integrity checks across all rows: orphaned customer refs, "
                 "impossible values, ship-before-production, future dates, duplicates, weight/unit "
                 "outliers, attribute conflicts.",
         "inp": f"5,000 raw warehouse records + the {len(customers)}-row customer master.",
         "outp": f"{len(findings)} findings — each with record id, category, the bad value, and a plain reason.",
         "handoff": "Writes memory['findings'] → read by the Risk Prioritizer.",
         "why": "Deterministic checks make every finding auditable — never \"the model said so\".",
         "samples": det_s},
        {"id": "prioritizer", "ic": "📊", "name": "Risk Prioritizer",
         "role": "Sorts the problems worst-first and explains every ranking.",
         "out": f"{crit} critical · {high} high",
         "tool": "Scored each finding: base severity by category, +1 when the bad record already "
                 "shipped/completed (the error likely escaped before the audit).",
         "inp": f"memory['findings'] — {len(findings)} issues from the Issue Detector.",
         "outp": f"Same issues ranked 1..{len(acted)} with a severity label + a reason for the rank.",
         "handoff": "Writes memory['ranked'] → read by the Remediation Planner.",
         "why": "A compliance officer has minutes — surface what can hurt the audit first.",
         "samples": pri_s},
        {"id": "remediator", "ic": "🛠️", "name": "Remediation Planner",
         "role": "Decides what to do with each issue: fix, flag, or escalate.",
         "out": f"{fix} auto-fixable · rest flagged/escalated",
         "tool": "Mapped each category to an action policy (duplicate→fix, impossible value→flag, "
                 "orphaned customer→escalate, …) with a concrete next step.",
         "inp": f"memory['ranked'] — {len(acted)} ranked issues.",
         "outp": "Each issue tagged fix / flag / escalate with what to do.",
         "handoff": "Writes memory['acted'] → read by the Audit Reporter.",
         "why": "Separates what software can safely fix from what needs a human decision.",
         "samples": rem_s},
        {"id": "reporter", "ic": "📝", "name": "Audit Reporter",
         "role": "Writes a one-page summary the officer can read, sign, and download.",
         "out": "signed audit memo ready",
         "tool": "Tool call → Claude (claude-sonnet-4-6): a plain-language narrative written over the "
                 "agents' real numbers (no invented figures).",
         "inp": "memory['acted'] + the tallies (by severity, category, action).",
         "outp": "output/audit_summary.md — bottom line, what we checked, findings, actions, sign-off.",
         "handoff": "Downloadable from the product — the officer signs it.",
         "why": "The end user can't read SQL; they need a memo they can hand to auditors.",
         "samples": rep_s},
        {"id": "executor", "ic": "✅", "name": "Remediation Executor",
         "role": "Applies the safe fixes and hands the rest to a human — see the Take action step.",
         "out": f"{fix} auto-fixed · cleaned dataset ready",
         "tool": "Removed duplicate rows automatically; left flag/escalate items for a person. Can also "
                 "turn a human's plain-language instruction into an automated fix rule.",
         "inp": "memory['acted'] + the original 5,000 records.",
         "outp": f"data/track01_cleaned.csv ({executed.get('original_rows', total):,} → "
                 f"{executed.get('cleaned_rows', total - fix):,} rows) + a fix log.",
         "handoff": "Cleaned dataset + human-in-the-loop automation in the Take action step.",
         "why": "Software should only auto-apply what's provably safe; the rest needs a human's call.",
         "samples": [f"removed {fix} duplicate rows automatically",
                     "flag/escalate items wait for human review"]},
    ]
    flow = ""
    for a in AG:
        samp = "".join(f"<li>{html.escape(str(s))}</li>" for s in a["samples"]) or "<li>(run the pipeline)</li>"
        flow += (
            f'<div class="agent" data-out="{html.escape(a["out"])}" onclick="toggleDetail(\'{a["id"]}\')">'
            f'<div class="ic">{a["ic"]}</div><div style="flex:1">'
            f'<h3>{html.escape(a["name"])} <span class="chev">▸</span></h3>'
            f'<div class="role">{html.escape(a["role"])}</div>'
            f'<div class="out"></div>'
            f'<div class="mem">↕ reads &amp; writes the shared memory layer (Cognee)</div>'
            f'<div class="detail" id="detail-{a["id"]}">'
            f'<div class="drow"><b>Tool / operation</b><span>{html.escape(a["tool"])}</span></div>'
            f'<div class="drow"><b>Input</b><span>{html.escape(a["inp"])}</span></div>'
            f'<div class="drow"><b>Output</b><span>{html.escape(a["outp"])}</span></div>'
            f'<div class="drow"><b>Handoff to next</b><span>{html.escape(a["handoff"])}</span></div>'
            f'<div class="drow"><b>Analysis &amp; why</b><span>{html.escape(a["why"])}</span></div>'
            f'<div class="drow"><b>Examples</b><span><ul>{samp}</ul></span></div>'
            f'</div></div></div>')

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

    # --- take-action step data ---
    clean_rows = executed.get("cleaned_rows", total - fix)
    human_cats = sorted({f["category"] for f in acted if f["action"] in ("flag", "escalate")})
    cat_options = "".join(f'<option value="{c}">{c.replace("_"," ")}</option>' for c in human_cats)

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Attest — find, fix, and explain broken data</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&family=Playfair+Display:wght@500;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header><div class="wrap">
  <h1>Attest <span style="font-weight:400;color:#9DB2CE;font-size:16px">· find, fix &amp; explain broken data before your audit</span></h1>
  <p>Demo: Harven Manufacturing, four days before a regulatory audit. Attest finds every problem,
     explains it in plain words, tells you what to do — and fixes what's safe. No database knowledge needed.</p>
</div></header>
<div class="wrap">
  <div class="steps">
    <div class="step on" onclick="go(0)"><span class="n">1</span><b>See the data</b><span>what we're working with</span></div>
    <div class="step" onclick="go(1)"><span class="n">2</span><b>Watch the agents</b><span>5 agents, step by step</span></div>
    <div class="step" onclick="go(2)"><span class="n">3</span><b>Review & sign</b><span>worklist + summary</span></div>
    <div class="step" onclick="go(3)"><span class="n">4</span><b>Take action</b><span>fix + automate</span></div>
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
      <div class="hint">Tip: click any agent to see exactly what it did — its tool call, input, output, and what it handed to the next agent.</div>
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
    <button class="btn" onclick="go(3)">Next: take action →</button>
  </div>

  <!-- STEP 4: TAKE ACTION -->
  <div class="pane">
    <div class="card">
      <h2>Apply the safe fixes</h2>
      <div class="muted">The {fix} duplicate records are safe to remove automatically. Everything
        else needs your judgment — that's the next card.</div>
      <div class="grid">
        <div class="kpi"><b>{total:,}</b><span>original rows</span></div>
        <div class="kpi"><b style="color:#059669">{clean_rows:,}</b><span>after auto-fix</span></div>
        <div class="kpi"><b>{fix}</b><span>duplicates removed</span></div>
        <div class="kpi" style="margin-left:auto;display:flex;align-items:center">
          <a class="btn dl" href="/download-clean">⬇ Download cleaned dataset</a></div>
      </div>
    </div>
    <div class="card">
      <h2>🧑‍🔧 Automate a fix <span class="muted" style="font-weight:400">— human in the loop</span></h2>
      <div class="muted">For the issues that need a person, describe in plain language how you'd fix
        them. An expert stays in control — we turn your instruction into a concrete, previewable rule
        and flag anything too risky to auto-apply.</div>
      <div style="display:flex;gap:10px;margin-top:12px;flex-wrap:wrap;align-items:center">
        <select id="autocat" class="sel">{cat_options}</select>
        <input id="autoinp" class="inp" placeholder="e.g. if weight is ~1000x the usual for that part, it's a unit typo — divide by 1000">
        <button class="btn" onclick="automate()">Propose automated fix</button>
      </div>
      <div id="autoout"></div>
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


@app.get("/download-clean")
def download_clean():
    return FileResponse(config.DATA / "track01_cleaned.csv", media_type="text/csv",
                        filename="track01_cleaned.csv")


@app.post("/automate")
def automate(category: str = Form(...), instruction: str = Form("")):
    acted = Memory().read("acted") or []
    try:
        return JSONResponse(propose_fix(category, instruction, acted))
    except Exception as e:
        return JSONResponse({"category": category, "affected": 0,
                             "proposal": f"Could not generate a fix: {e}"}, status_code=200)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
