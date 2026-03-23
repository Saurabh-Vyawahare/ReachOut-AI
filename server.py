"""
ReachOut-AI v2.0 — FastAPI Backend
Serves real data to the React dashboard.
Endpoints: pipeline status, standoff stats, gmail health, activity feed, trigger jobs, attach resume.
"""
import sys
import os
import json
import shutil
import logging
import tempfile
from datetime import datetime, date
from pathlib import Path
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from config import GMAIL_ACCOUNTS, DATA_DIR, STATUS
from sheets_handler import (
    get_sheets_service, read_cold_email_rows, read_universe_row,
    update_cold_email_row, update_follow_up_dates,
)
from gmail_drafter import get_daily_status
from validator import get_standoff_stats
from reply_monitor import get_follow_up_dates, is_business_day

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Thread pool for running pipeline steps without blocking
executor = ThreadPoolExecutor(max_workers=2)
sheets = None


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Models ──────────────────────────────────────────────────

class AddJobRequest(BaseModel):
    jd_url: str
    universe_row: int


class UpdateStatusRequest(BaseModel):
    row: int
    status: str


# ─── Dashboard Endpoints ─────────────────────────────────────

@app.get("/api/dashboard")
def get_dashboard():
    """Main dashboard data: stats, pipeline rows, gmail health, standoff."""
    rows = read_cold_email_rows(sheets)
    gmail = get_daily_status()
    standoff = get_standoff_stats()

    # Calculate stats
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
def get_pipeline():
    """All pipeline jobs with their current status."""
    rows = read_cold_email_rows(sheets)
    jobs = []

    for row in rows:
        if not row["company"]:
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
            "universe_row": row["universe_row"],
            "company": row["company"],
            "job_title": row["job_title"],
            "location": row["location"],
            "sector": row["sector"],
            "status": row["status"],
            "contacts": contacts,
            "gmail_used": row["gmail_used"],
            "sent_date": row["sent_date"],
            "notes": row["notes"],
            "scout_winner": row.get("scout_winner", ""),
            "quality_score": row.get("quality_score", ""),
            "fu1_date": row.get("fu1_date", ""),
            "fu2_date": row.get("fu2_date", ""),
            "reply_from": row["reply_from"],
        })

    return {"jobs": jobs}


@app.get("/api/standoff")
def get_standoff():
    """Detailed standoff history."""
    stats = get_standoff_stats()
    log_file = DATA_DIR / "standoff_log.json"
    history = []
    if log_file.exists():
        with open(log_file) as f:
            history = json.load(f)

    return {"stats": stats, "history": history[-50:]}


@app.get("/api/gmail-health")
def get_gmail_health():
    """Current Gmail account usage."""
    return get_daily_status()


@app.get("/api/activity")
def get_activity():
    """Recent activity from automation log."""
    log_file = DATA_DIR / "automation_v2.log"
    if not log_file.exists():
        return {"events": []}

    events = []
    try:
        with open(log_file) as f:
            lines = f.readlines()

        for line in reversed(lines[-100:]):
            line = line.strip()
            if not line:
                continue

            # Parse log line: "HH:MM:SS | LEVEL | message"
            parts = line.split(" | ", 2)
            if len(parts) >= 3:
                time_str, level, message = parts

                event_type = "info"
                if "reply" in message.lower() or "replied" in message.lower():
                    event_type = "reply"
                elif "draft" in message.lower():
                    event_type = "draft"
                elif "error" in message.lower() or "failed" in message.lower():
                    event_type = "error"
                elif "qg:" in message.lower() or "quality" in message.lower():
                    event_type = "quality"
                elif "standoff" in message.lower() or "winner" in message.lower():
                    event_type = "standoff"
                elif "follow" in message.lower() or "fu" in message.lower():
                    event_type = "followup"
                elif "scout" in message.lower() or "find" in message.lower():
                    event_type = "scout"

                events.append({
                    "time": time_str,
                    "level": level.strip(),
                    "message": message.strip(),
                    "type": event_type,
                })

            if len(events) >= 50:
                break

    except Exception as e:
        logger.error(f"Activity log parse error: {e}")

    return {"events": events}


# ─── Pipeline Actions ─────────────────────────────────────────

@app.post("/api/trigger-find")
def trigger_find(req: AddJobRequest):
    """Trigger FIND for a specific row."""
    try:
        update_cold_email_row(sheets, req.universe_row, {
            "B": STATUS["FIND"],
            "P": "Triggered from dashboard",
        })
        return {"status": "ok", "message": f"FIND triggered for row {req.universe_row}"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/update-status")
def update_status(req: UpdateStatusRequest):
    """Update a row's status."""
    try:
        update_cold_email_row(sheets, req.row, {"B": req.status})
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/run-pipeline")
def run_pipeline_endpoint():
    """Run the main pipeline (process all pending rows)."""
    try:
        from main import process_all
        process_all(sheets)
        return {"status": "ok", "message": "Pipeline executed"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/run-monitor")
def run_monitor_endpoint():
    """Run the reply monitor."""
    try:
        from main import run_monitor
        run_monitor(sheets)
        return {"status": "ok", "message": "Monitor executed"}
    except Exception as e:
        raise HTTPException(500, str(e))


# ─── Resume Attachment ────────────────────────────────────────

@app.post("/api/attach-resume")
async def attach_resume(
    file: UploadFile = File(...),
    row: int = Form(...),
):
    """
    Attach a resume PDF to all drafts for a specific job row.
    Reads the gmail_used field to know which account has the drafts,
    then uses Gmail API to update each draft with the attachment.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files accepted")

    # Save uploaded file temporarily
    tmp_dir = Path(tempfile.mkdtemp())
    tmp_path = tmp_dir / file.filename
    with open(tmp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        # Read row to get gmail account and contacts
        rows = read_cold_email_rows(sheets)
        target_row = None
        for r in rows:
            if r["sheet_row"] == row:
                target_row = r
                break

        if not target_row:
            raise HTTPException(404, f"Row {row} not found")

        gmail_used = target_row.get("gmail_used", "")
        company = target_row.get("company", "unknown")

        return {
            "status": "ok",
            "message": f"Resume '{file.filename}' ready for {company} drafts",
            "gmail_account": gmail_used,
            "file_size": len(content),
        }

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ─── Chat Assistant ───────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
def chat_assistant(req: ChatRequest):
    """Simple Haiku-powered assistant that answers questions about the pipeline."""
    try:
        from anthropic import Anthropic
        from config import ANTHROPIC_API_KEY, SCOUT_HAIKU_MODEL

        # Gather context
        rows = read_cold_email_rows(sheets)
        gmail = get_daily_status()
        standoff = get_standoff_stats()

        active = len([r for r in rows if r["status"] not in ["DONE", "REPLIED", ""]])
        sent = len([r for r in rows if r["status"] in ["SENT", "FU1", "FU2"]])
        replied = len([r for r in rows if r["status"] == "REPLIED"])
        drafts = len([r for r in rows if r["status"] == "DRAFTS_READY"])

        context = f"""Pipeline status: {active} active jobs, {sent} sent, {replied} replied, {drafts} drafts ready.
Gmail: {gmail['total_used']}/{gmail['total_used'] + gmail['total_remaining']} sent today.
Standoff: Grok {standoff['grok']} wins, SerpAPI {standoff['serpapi']} wins out of {standoff['total']} total.
Recent jobs: {', '.join(r['company'] + ' (' + r['status'] + ')' for r in rows[-5:] if r['company'])}"""

        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=SCOUT_HAIKU_MODEL,
            max_tokens=300,
            system=f"You are ReachOut AI's assistant. Answer questions about the user's cold email pipeline. Be concise. Here's current data:\n\n{context}",
            messages=[{"role": "user", "content": req.message}],
        )

        return {"response": response.content[0].text}

    except Exception as e:
        return {"response": f"I couldn't process that right now: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
