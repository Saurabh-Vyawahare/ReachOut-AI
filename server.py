"""
ReachOut-AI v2.0 — FastAPI Backend
Serves real data to the React dashboard.
Caches Google Sheets reads to avoid SSL errors from over-polling.
"""
import sys
import os
import json
import shutil
import logging
import tempfile
import time
from datetime import datetime, date
from pathlib import Path
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from config import GMAIL_ACCOUNTS, DATA_DIR, STATUS
from sheets_handler import (
    get_sheets_service, read_cold_email_rows, read_universe_row,
    update_cold_email_row, update_follow_up_dates,
)
from gmail_drafter import get_daily_status
from validator import get_standoff_stats
from reply_monitor import get_follow_up_dates, is_business_day
from auth import get_current_user

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

executor = ThreadPoolExecutor(max_workers=2)
sheets = None

# ─── Cache to avoid hammering Google Sheets ──────────────────
_cache = {"rows": None, "rows_time": 0, "gmail": None, "gmail_time": 0}
CACHE_TTL = 300  # seconds

def get_cached_rows():
    now = time.time()
    if _cache["rows"] is not None and now - _cache["rows_time"] < CACHE_TTL:
        return _cache["rows"]
    try:
        rows = read_cold_email_rows(sheets)
        _cache["rows"] = rows
        _cache["rows_time"] = now
        return rows
    except Exception as e:
        logger.error(f"Sheets read failed: {e}")
        return _cache["rows"] or []

def get_cached_gmail():
    now = time.time()
    if _cache["gmail"] is not None and now - _cache["gmail_time"] < CACHE_TTL:
        return _cache["gmail"]
    try:
        gmail = get_daily_status()
        _cache["gmail"] = gmail
        _cache["gmail_time"] = now
        return gmail
    except Exception as e:
        logger.error(f"Gmail status failed: {e}")
        return _cache["gmail"] or {"date": str(date.today()), "accounts": [], "total_used": 0, "total_remaining": 0}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global sheets
    try:
        sheets = get_sheets_service()
        logger.info("Sheets connected")
    except Exception as e:
        logger.error(f"Sheets connection failed: {e}")
    yield

app = FastAPI(title="ReachOut-AI v2.0", lifespan=lifespan)

ALLOWED_ORIGINS = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
if railway_domain:
    ALLOWED_ORIGINS.append(f"https://{railway_domain}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://reach-out-ai-nine.vercel.app",
        "https://reach-out-ai-git-main-vyawahares-northeasterns-projects.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0", "sheets": sheets is not None}


class AddJobRequest(BaseModel):
    jd_url: str
    universe_row: int

class UpdateStatusRequest(BaseModel):
    row: int
    status: str

class ChatRequest(BaseModel):
    message: str


@app.get("/api/dashboard")
def get_dashboard(user=Depends(get_current_user)):
    rows = get_cached_rows()
    gmail = get_cached_gmail()
    standoff = get_standoff_stats()

    active = [r for r in rows if r["status"] not in ["DONE", "REPLIED", ""]]
    drafts_ready = [r for r in rows if r["status"] == "DRAFTS_READY"]
    sent = [r for r in rows if r["status"] in ["SENT", "FU1", "FU2"]]
    replied = [r for r in rows if r["status"] == "REPLIED"]

    return {
        "stats": {
            "active_pipeline": len(active),
            "drafts_ready": len(drafts_ready),
            "sent": len(sent),
            "replies": len(replied),
            "reply_rate": round(len(replied) / max(len(sent) + len(replied), 1) * 100),
        },
        "gmail": gmail,
        "standoff": standoff,
        "today": date.today().isoformat(),
        "is_business_day": is_business_day(),
    }


@app.get("/api/pipeline")
def get_pipeline(user=Depends(get_current_user)):
    rows = get_cached_rows()
    jobs = []
    for row in rows:
        if not row.get("company"):
            continue
        contacts = []
        for i in range(1, 4):
            name = row.get(f"contact_{i}", "")
            email = row.get(f"email_{i}", "")
            if name:
                contacts.append({"name": name, "email": email or None})
        jobs.append({
            "id": row["sheet_row"],
            "row": row["sheet_row"],
            "universe_row": row.get("universe_row", ""),
            "company": row["company"],
            "job_title": row.get("job_title", ""),
            "location": row.get("location", ""),
            "sector": row.get("sector", ""),
            "status": row["status"],
            "contacts": contacts,
            "gmail_used": row.get("gmail_used", ""),
            "sent_date": row.get("sent_date", ""),
            "notes": row.get("notes", ""),
            "scout_winner": row.get("scout_winner", ""),
            "quality_score": row.get("quality_score", ""),
            "fu1_date": row.get("fu1_date", ""),
            "fu2_date": row.get("fu2_date", ""),
            "reply_from": row.get("reply_from", ""),
        })
    return {"jobs": jobs}


@app.get("/api/standoff")
def get_standoff(user=Depends(get_current_user)):
    stats = get_standoff_stats()
    log_file = DATA_DIR / "standoff_log.json"
    history = []
    if log_file.exists():
        with open(log_file) as f:
            history = json.load(f)
    return {"stats": stats, "history": history[-50:]}


@app.get("/api/gmail-health")
def get_gmail_health(user=Depends(get_current_user)):
    return get_cached_gmail()


@app.get("/api/activity")
def get_activity(user=Depends(get_current_user)):
    log_file = DATA_DIR / "automation_v2.log"
    if not log_file.exists():
        return {"events": []}
    events = []
    try:
        with open(log_file) as f:
            lines = f.readlines()
        for line in reversed(lines[-100:]):
            line = line.strip()
            if not line: continue
            parts = line.split(" | ", 2)
            if len(parts) >= 3:
                time_str, level, message = parts
                event_type = "info"
                ml = message.lower()
                if "reply" in ml or "replied" in ml: event_type = "reply"
                elif "draft" in ml: event_type = "draft"
                elif "error" in ml or "failed" in ml: event_type = "error"
                elif "qg:" in ml or "quality" in ml: event_type = "quality"
                elif "standoff" in ml or "winner" in ml: event_type = "standoff"
                elif "follow" in ml or "fu" in ml: event_type = "followup"
                elif "scout" in ml or "find" in ml: event_type = "scout"
                events.append({"time": time_str, "level": level.strip(), "message": message.strip(), "type": event_type})
            if len(events) >= 50: break
    except Exception as e:
        logger.error(f"Activity log parse error: {e}")
    return {"events": events}


@app.post("/api/trigger-find")
def trigger_find(req: AddJobRequest, user=Depends(get_current_user)):
    try:
        update_cold_email_row(sheets, req.universe_row, {"B": STATUS["FIND"], "P": "Triggered from dashboard"})
        _cache["rows"] = None  # bust cache
        return {"status": "ok", "message": f"FIND triggered for row {req.universe_row}"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/update-status")
def update_status(req: UpdateStatusRequest, user=Depends(get_current_user)):
    try:
        update_cold_email_row(sheets, req.row, {"B": req.status})
        _cache["rows"] = None
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/run-pipeline")
def run_pipeline_endpoint(user=Depends(get_current_user)):
    try:
        from main import process_all
        process_all(sheets)
        _cache["rows"] = None
        return {"status": "ok", "message": "Pipeline executed"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/run-monitor")
def run_monitor_endpoint(user=Depends(get_current_user)):
    try:
        from main import run_monitor
        run_monitor(sheets)
        _cache["rows"] = None
        return {"status": "ok", "message": "Monitor executed"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/attach-resume")
async def attach_resume(file: UploadFile = File(...), row: int = Form(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files accepted")
    tmp_dir = Path(tempfile.mkdtemp())
    tmp_path = tmp_dir / file.filename
    with open(tmp_path, "wb") as f:
        content = await file.read()
        f.write(content)
    try:
        rows = get_cached_rows()
        target = next((r for r in rows if r["sheet_row"] == row), None)
        if not target: raise HTTPException(404, f"Row {row} not found")
        return {"status": "ok", "message": f"Resume ready for {target.get('company', 'unknown')} drafts", "file_size": len(content)}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/api/chat")
def chat_assistant(req: ChatRequest, user=Depends(get_current_user)):
    try:
        from anthropic import Anthropic
        from config import ANTHROPIC_API_KEY, SCOUT_HAIKU_MODEL
        rows = get_cached_rows()
        gmail = get_cached_gmail()
        standoff = get_standoff_stats()
        active = len([r for r in rows if r["status"] not in ["DONE", "REPLIED", ""]])
        sent = len([r for r in rows if r["status"] in ["SENT", "FU1", "FU2"]])
        replied = len([r for r in rows if r["status"] == "REPLIED"])
        context = f"Pipeline: {active} active, {sent} sent, {replied} replied. Gmail: {gmail.get('total_used',0)} sent today. Standoff: Grok {standoff['grok']} vs SerpAPI {standoff['serpapi']}. Recent: {', '.join(r['company'] + ' (' + r['status'] + ')' for r in rows[-5:] if r.get('company'))}"
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(model=SCOUT_HAIKU_MODEL, max_tokens=300,
            system=f"You are ReachOut AI's assistant. Answer about the cold email pipeline. Be concise.\n\n{context}",
            messages=[{"role": "user", "content": req.message}])
        return {"response": response.content[0].text}
    except Exception as e:
        return {"response": f"Error: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    dist_dir = Path(__file__).parent / "frontend" / "dist"
    if dist_dir.exists():
        from fastapi.responses import FileResponse
        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            file_path = dist_dir / full_path
            if file_path.exists() and file_path.is_file(): return FileResponse(file_path)
            return FileResponse(dist_dir / "index.html")
        logger.info(f"Serving frontend from {dist_dir}")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
