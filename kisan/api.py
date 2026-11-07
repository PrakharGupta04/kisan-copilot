"""FastAPI service + minimal demo page (React dashboard comes in the next phase)."""
import threading

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from . import config, db
from .crew import run_pipeline
from .security import GuardrailViolation, RateLimiter

app = FastAPI(title="Kisan Copilot", version="0.4")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://localhost:8000"],
                   allow_methods=["GET", "POST"], allow_headers=["*"])
limiter, run_lock = RateLimiter(12, 60), threading.Semaphore(1)


def auth(x_api_key: str = Header(default="")):
    if config.API_KEY and x_api_key != config.API_KEY:
        raise HTTPException(401, "invalid API key")


api = APIRouter(prefix="/api", dependencies=[Depends(auth)])


class RecommendRequest(BaseModel):
    farmer_id: str = Field(max_length=10)
    question: str | None = Field(default=None, max_length=300)


class ReviewRequest(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    reviewer: str = Field(default="officer", max_length=60)
    note: str = Field(default="", max_length=500)


@api.get("/farmers")
def farmers():
    return db.list_farmers()


@api.post("/recommend")
def recommend(req: RecommendRequest, request: Request):
    if not limiter.allow(request.client.host if request.client else "anon"):
        raise HTTPException(429, "too many requests")
    if not run_lock.acquire(timeout=3):
        raise HTTPException(429, "system busy, try again shortly")
    try:
        return run_pipeline(req.farmer_id, req.question)
    except GuardrailViolation as e:
        raise HTTPException(400, f"blocked by guardrail: {e}")
    except LookupError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"internal error ({type(e).__name__})")
    finally:
        run_lock.release()


@api.get("/runs/{run_id}")
def get_run(run_id: str):
    r = db.get_run(run_id[:32])
    if not r:
        raise HTTPException(404, "run not found")
    return r


@api.post("/runs/{run_id}/review")
def review(run_id: str, body: ReviewRequest):
    if not db.get_run(run_id[:32]):
        raise HTTPException(404, "run not found")
    db.save_review(run_id[:32], body.decision, body.reviewer, body.note)
    return {"run_id": run_id, "recorded": body.decision}


app.include_router(api)


@app.get("/health")
def health():
    return {"ok": True}


PAGE = """<!doctype html><meta charset=utf-8><title>Kisan Copilot</title>
<style>body{font-family:system-ui;max-width:920px;margin:2rem auto;padding:0 1rem}table{border-collapse:collapse;width:100%}
td,th{border:1px solid #ccc;padding:6px;text-align:left;vertical-align:top}.pill{padding:2px 8px;border-radius:9px;background:#eee}
.warn{background:#ffe9b3}pre{background:#f5f5f5;padding:8px;overflow:auto;max-height:240px}</style>
<h2>Kisan Copilot</h2>
<select id=f></select> <input id=q placeholder="optional question" size=36> <input id=k placeholder="API key" type=password size=12>
<button id=go>Get advice</button> <div id=out></div>
<script>
const $=i=>document.getElementById(i);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const H=()=>({'Content-Type':'application/json','x-api-key':$('k').value});
fetch('/api/farmers',{headers:H()}).then(r=>r.json()).then(a=>{$('f').innerHTML=a.map(x=>`<option value="${esc(x.farmer_id)}">${esc(x.farmer_id)} - ${esc(x.name)} (${esc(x.crop)}, ${esc(x.state)})</option>`).join('')});
let rid='';
async function review(d){await fetch(`/api/runs/${rid}/review`,{method:'POST',headers:H(),body:JSON.stringify({decision:d})});alert('Recorded: '+d)}
$('go').onclick=async()=>{
 $('out').textContent='Running agents... (can take 1-2 minutes on free tiers)';
 const r=await fetch('/api/recommend',{method:'POST',headers:H(),body:JSON.stringify({farmer_id:$('f').value,question:$('q').value||null})});
 const j=await r.json(); if(!r.ok){$('out').textContent='Error: '+esc(j.detail);return}
 rid=j.run_id;
 $('out').innerHTML=`<p><span class="pill ${j.requires_human_review?'warn':''}">${esc(j.status)}</span> mode: ${esc(j.mode)} | confidence: ${esc(j.overall_confidence)} | agents: ${esc(j.agents_run.join(', '))} | ${esc(j.metrics.latency_s)}s</p>
 <p>${esc(j.summary)}</p><table><tr><th>#</th><th>Recommendation</th><th>Sources</th><th>Conf.</th></tr>${j.recommendations.map(x=>`<tr><td>${x.priority}</td><td><b>${esc(x.title)}</b><br>${esc(x.detail)}</td><td>${esc(x.source_agents.join(', '))}</td><td>${esc(x.confidence)}</td></tr>`).join('')}</table>
 ${j.message?`<h4>Farmer message</h4><p>${esc(j.message.hindi)}</p><p>${esc(j.message.english)}</p><p><i>SMS: ${esc(j.message.sms)}</i></p>`:''}
 <p><b>Risks:</b> ${esc(j.risks.join(' | '))}</p>${j.requires_human_review?`<p><b>Needs review:</b> ${esc(j.review_reasons.join(' '))}<br><button onclick="review('approve')">Approve</button> <button onclick="review('reject')">Reject</button></p>`:''}
 <details><summary>Evidence (tool outputs)</summary><pre>${esc(JSON.stringify(j.evidence,null,1))}</pre></details><small>${esc(j.disclaimer)}</small>`}
</script>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE