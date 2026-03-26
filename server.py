"""
ReachOut-AI v2.0 — FastAPI Backend
Full interactive pipeline: add jobs, find contacts, generate drafts — all from the dashboard.
"""
import sys
import os
import json
import shutil
import logging
import tempfile
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from config import GMAIL_ACCOUNTS, DATA_DIR, STATUS, SPREADSHEET_ID, ANTHROPIC_API_KEY
from sheets_handler import (
    get_sheets_service, read_cold_email_rows, read_universe_row,
    update_cold_email_row, update_follow_up_dates, write_cold_email_row,
    fill_contacts, fill_job_info, get_next_empty_row, log_standoff_to_sheet,
)
from gmail_drafter import get_daily_status
from validator import get_standoff_stats
from reply_monitor import get_follow_up_dates, is_business_day
from auth import get_current_user

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

executor = ThreadPoolExecutor(max_workers=4)
sheets = None

# ─── Temp resume storage (in-memory for Render) ──────────────
_resume_store = {}  # row -> {"path": ..., "filename": ...}

# ─── Cache to avoid hammering Google Sheets ──────────────────
_cache = {"rows": None, "rows_time": 0, "gmail": None, "gmail_time": 0}
CACHE_TTL = 300

UNIVERSE_TAB = os.getenv("UNIVERSE_TAB", "Universe")
COLD_EMAIL_TAB = os.getenv("COLD_EMAIL_TAB", "Cold Email")


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


def bust_cache():
    _cache["rows"] = None
    _cache["rows_time"] = 0


# ─── Helper: Get next empty Universe row ─────────────────────
def get_next_universe_row():
    try:
        result = sheets.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{UNIVERSE_TAB}'!A:A"
        ).execute()
        values = result.get("values", [])
        return len(values) + 1
    except Exception as e:
        logger.error(f"Failed to get next Universe row: {e}")
        return None


# ─── Helper: Write Universe row ──────────────────────────────
def write_universe_row(row_number, company, job_title, date_str, location, status, resume_version, jd_url):
    try:
        sheets.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{UNIVERSE_TAB}'!A{row_number}:G{row_number}",
            valueInputOption="USER_ENTERED",
            body={"values": [[company, job_title, date_str, location, status, resume_version, jd_url]]}
        ).execute()
        logger.info(f"Wrote Universe row {row_number}: {company}")
    except Exception as e:
        logger.error(f"Failed to write Universe row: {e}")
        raise


# ─── Helper: Extract job info from URL using Haiku ───────────
def extract_job_info(jd_url):
    """Fetch JD page and extract company, title, location using Haiku."""
    # Fetch the page
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(jd_url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove scripts and styles
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        page_text = soup.get_text(separator="\n", strip=True)[:6000]
    except Exception as e:
        logger.error(f"Failed to fetch JD page: {e}")
        # Try to extract from URL
        page_text = f"Job listing URL: {jd_url}"

    # Use Haiku to extract
    from anthropic import Anthropic
    from config import SCOUT_HAIKU_MODEL

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=SCOUT_HAIKU_MODEL,
        max_tokens=300,
        system="Extract job information. Return ONLY valid JSON with keys: company, job_title, location. If location not found, return 'Remote'. Be precise with company name (not the ATS platform name).",
        messages=[{"role": "user", "content": f"Extract company name, job title, and location from this job listing:\n\n{page_text}"}],
    )
    text = response.content[0].text.strip()

    # Parse JSON from response
    try:
        # Handle markdown code blocks
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        info = json.loads(text)
        return {
            "company": info.get("company", "Unknown"),
            "job_title": info.get("job_title", "Unknown"),
            "location": info.get("location", "Remote"),
        }
    except json.JSONDecodeError:
        logger.error(f"Failed to parse Haiku response: {text}")
        return {"company": "Unknown", "job_title": "Unknown", "location": "Remote"}


# ─── Helper: Run scouts for a single row ─────────────────────
def run_scouts_for_row(cold_email_row):
    """Run dual scouts for a specific Cold Email row. Called in background."""
    try:
        from jd_analyzer import analyze_jd
        from scout_grok import scout_grok
        from scout_serpapi import scout_serpapi
        from validator import validate_standoff
        from contact import Contact

        # Read the row
        rows = read_cold_email_rows(sheets)
        target = next((r for r in rows if r["sheet_row"] == cold_email_row), None)
        if not target:
            logger.error(f"Row {cold_email_row} not found")
            return

        # Get Universe row for JD URL
        uni_row = int(target.get("universe_row", 0))
        if uni_row:
            uni_data = read_universe_row(sheets, uni_row)
            jd_url = uni_data.get("jd_input", "") if uni_data else ""
        else:
            jd_url = ""

        if not jd_url:
            update_cold_email_row(sheets, cold_email_row, {"P": "No JD URL found"})
            return

        # Update status to SCOUTING
        update_cold_email_row(sheets, cold_email_row, {"B": "SCOUTING"})

        # Analyze JD
        company = target.get("company", "")
        location = target.get("location", "Remote")
        jd_analysis = analyze_jd(jd_url)

        # Run scouts in parallel
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=2) as pool:
            grok_future = pool.submit(scout_grok, company, jd_analysis, location)
            serp_future = pool.submit(scout_serpapi, company, jd_analysis, location)

            grok_contacts = []
            serp_contacts = []
            try:
                grok_contacts = grok_future.result(timeout=60)
            except Exception as e:
                logger.error(f"Grok scout failed: {e}")
            try:
                serp_contacts = serp_future.result(timeout=60)
            except Exception as e:
                logger.error(f"SerpAPI scout failed: {e}")

        # Ensure contacts are Contact objects (scouts may return strings or dicts)
        def ensure_contacts(raw_list):
            result = []
            for item in (raw_list or []):
                if isinstance(item, Contact):
                    result.append(item)
                elif isinstance(item, str):
                    result.append(Contact(name=item, title="", contact_type="unknown"))
                elif isinstance(item, dict):
                    result.append(Contact(
                        name=item.get("name", ""),
                        title=item.get("title", ""),
                        contact_type=item.get("contact_type", "unknown"),
                        linkedin_url=item.get("linkedin_url", ""),
                    ))
            return result

        grok_contacts = ensure_contacts(grok_contacts)
        serp_contacts = ensure_contacts(serp_contacts)

        # Run standoff
        job_title = target.get("job_title", "")
        result = validate_standoff(
            {"contacts": grok_contacts},
            {"contacts": serp_contacts},
            company,
            job_title=job_title,
        )
        winner = result["winner"]
        contacts = result["contacts"]
        reason = result["reason"]

        # Fill contacts into sheet
        if contacts:
            fill_contacts(sheets, cold_email_row, contacts, "", f"Scout: {winner}")
            # Log standoff
            try:
                log_standoff_to_sheet(sheets, company, winner, reason)
            except:
                pass

        # Update status
        update_cold_email_row(sheets, cold_email_row, {"B": "CONTACTS", "Q": winner})
        bust_cache()
        logger.info(f"Scouts complete for row {cold_email_row}: {winner} won, {len(contacts)} contacts")

    except Exception as e:
        logger.error(f"Scout pipeline failed for row {cold_email_row}: {e}")
        update_cold_email_row(sheets, cold_email_row, {"B": "FIND", "P": f"Scout error: {str(e)[:100]}"})
        bust_cache()


# ─── Helper: Generate drafts for a row ───────────────────────
def generate_drafts_for_row(cold_email_row, resume_path=None):
    """Run email composer + quality gate + gmail drafts for a row."""
    try:
        from jd_analyzer import analyze_jd
        from email_generator import generate_emails
        from quality_gate import check_quality
        from gmail_drafter import create_draft

        # Read the row
        rows = read_cold_email_rows(sheets)
        target = next((r for r in rows if r["sheet_row"] == cold_email_row), None)
        if not target:
            raise Exception(f"Row {cold_email_row} not found")

        # Get JD analysis
        uni_row = int(target.get("universe_row", 0))
        uni_data = read_universe_row(sheets, uni_row) if uni_row else {}
        jd_url = uni_data.get("jd_input", "") if uni_data else ""

        company = target.get("company", "")
        job_title = target.get("job_title", "")

        # Collect contacts with emails
        contacts_with_emails = []
        for i in range(1, 4):
            name = target.get(f"contact_{i}", "")
            email = target.get(f"email_{i}", "")
            if name and email:
                contacts_with_emails.append({"name": name, "email": email})

        if not contacts_with_emails:
            raise Exception("No contacts with emails found")

        # Update status
        update_cold_email_row(sheets, cold_email_row, {"B": "COMPOSING"})
        bust_cache()

        # Analyze JD for context
        jd_analysis = None
        if jd_url:
            try:
                jd_analysis = analyze_jd(jd_url)
            except:
                pass

        # Generate emails for each contact
        emails = generate_emails(
            company=company,
            job_title=job_title,
            contacts=contacts_with_emails,
            jd_analysis=jd_analysis,
        )

        # Quality gate
        update_cold_email_row(sheets, cold_email_row, {"B": "QG_CHECK"})
        bust_cache()

        approved_emails = []
        total_score = 0
        for email_data in emails:
            score, feedback = check_quality(email_data)
            total_score += score
            if score >= 7:
                approved_emails.append(email_data)
            else:
                logger.warning(f"QG rejected email (score {score}): {feedback}")
                # Regenerate once
                emails_retry = generate_emails(
                    company=company,
                    job_title=job_title,
                    contacts=[email_data["contact"]],
                    jd_analysis=jd_analysis,
                    feedback=feedback,
                )
                if emails_retry:
                    score2, _ = check_quality(emails_retry[0])
                    total_score = max(total_score, score2)
                    approved_emails.append(emails_retry[0])

        avg_score = total_score / max(len(emails), 1)

        # Create Gmail drafts
        update_cold_email_row(sheets, cold_email_row, {"B": "DRAFTS_READY"})
        bust_cache()

        drafts_created = 0
        gmail_used = ""
        for email_data in approved_emails:
            try:
                result = create_draft(
                    to_email=email_data["contact"]["email"],
                    subject=email_data.get("subject", f"Re: {job_title} at {company}"),
                    body=email_data.get("body", ""),
                    attachment_path=resume_path,
                )
                drafts_created += 1
                gmail_used = result.get("gmail_account", gmail_used)
            except Exception as e:
                logger.error(f"Draft creation failed: {e}")

        # Update sheet with results
        today = date.today().strftime("%m/%d/%Y")
        update_cold_email_row(sheets, cold_email_row, {
            "B": "DRAFTS_READY" if drafts_created > 0 else "ERROR",
            "N": gmail_used,
            "O": today,
            "P": f"Generated {drafts_created}/{len(approved_emails)} drafts",
            "R": str(round(avg_score, 1)),
        })
        bust_cache()
        logger.info(f"Drafts complete for row {cold_email_row}: {drafts_created} drafts, avg QG={avg_score:.1f}")

        return {"drafts_created": drafts_created, "quality_score": avg_score, "gmail_used": gmail_used}

    except Exception as e:
        logger.error(f"Draft generation failed for row {cold_email_row}: {e}")
        update_cold_email_row(sheets, cold_email_row, {"P": f"Draft error: {str(e)[:100]}"})
        bust_cache()
        raise


# ─── App Setup ───────────────────────────────────────────────

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


# ─── Models ──────────────────────────────────────────────────

class AddJobRequest(BaseModel):
    jd_url: str

class UpdateStatusRequest(BaseModel):
    row: int
    status: str

class UpdateContactRequest(BaseModel):
    row: int
    contact_index: int  # 1, 2, or 3
    name: str
    email: str = ""

class AddContactRequest(BaseModel):
    row: int
    name: str

class RemoveContactRequest(BaseModel):
    row: int
    contact_index: int  # 1, 2, or 3

class ChatRequest(BaseModel):
    message: str

class WebhookRequest(BaseModel):
    cold_email_row: int
    universe_row: int = 0
    company: str = ""
    secret: str = ""

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "reachout-webhook-2026")


# ═══════════════════════════════════════════════════════════════
# WEBHOOK (called by Apps Script — no auth required, uses secret)
# ═══════════════════════════════════════════════════════════════

@app.post("/api/webhook/new-job")
def webhook_new_job(req: WebhookRequest, background_tasks: BackgroundTasks):
    """
    Called by Google Apps Script when a JD URL is pasted.
    Busts cache and triggers scouts in background.
    No Supabase auth — uses shared secret instead.
    """
    if req.secret != WEBHOOK_SECRET:
        raise HTTPException(403, "Invalid webhook secret")

    logger.info(f"Webhook: new job row {req.cold_email_row} ({req.company})")
    bust_cache()

    # Trigger scouts in background
    background_tasks.add_task(run_scouts_for_row, req.cold_email_row)

    return {
        "status": "ok",
        "message": f"Cache busted, scouts dispatched for row {req.cold_email_row}",
    }


# ═══════════════════════════════════════════════════════════════
# EXISTING ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0", "sheets": sheets is not None}


@app.get("/api/dashboard")
def get_dashboard(user=Depends(get_current_user), range: str = "all"):
    rows = get_cached_rows()
    gmail = get_cached_gmail()
    standoff = get_standoff_stats()

    # Time range filtering
    if range != "all":
        today = date.today()
        if range == "today":
            cutoff = today
        elif range == "week":
            cutoff = today - timedelta(days=7)
        elif range == "2weeks":
            cutoff = today - timedelta(days=14)
        elif range == "month":
            cutoff = today - timedelta(days=30)
        else:
            cutoff = None

        if cutoff:
            filtered = []
            for r in rows:
                sent = r.get("sent_date", "")
                if sent:
                    try:
                        # Try common date formats
                        for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%d %b", "%d/%m/%Y"]:
                            try:
                                d = datetime.strptime(sent.strip(), fmt).date()
                                if fmt == "%d %b":
                                    d = d.replace(year=today.year)
                                if d >= cutoff:
                                    filtered.append(r)
                                break
                            except ValueError:
                                continue
                    except:
                        filtered.append(r)  # Include if can't parse date
                else:
                    filtered.append(r)  # Include rows without sent date
            rows = filtered

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
                contacts.append({"name": name, "email": email or ""})
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
            if not line:
                continue
            parts = line.split(" | ", 2)
            if len(parts) >= 3:
                time_str, level, message = parts
                event_type = "info"
                ml = message.lower()
                if "reply" in ml or "replied" in ml:
                    event_type = "reply"
                elif "draft" in ml:
                    event_type = "draft"
                elif "error" in ml or "failed" in ml:
                    event_type = "error"
                elif "qg:" in ml or "quality" in ml:
                    event_type = "quality"
                elif "standoff" in ml or "winner" in ml:
                    event_type = "standoff"
                elif "follow" in ml or "fu" in ml:
                    event_type = "followup"
                elif "scout" in ml or "find" in ml:
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


# ═══════════════════════════════════════════════════════════════
# NEW ENDPOINTS — Interactive Pipeline
# ═══════════════════════════════════════════════════════════════

@app.post("/api/add-job")
def add_job(req: AddJobRequest, background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    """
    Add a new job from a JD URL.
    1. Fetches page, extracts company/title/location using Haiku
    2. Writes to Universe tab
    3. Creates Cold Email row with FIND status
    4. Kicks off scouts in background
    """
    try:
        # Extract job info
        info = extract_job_info(req.jd_url)
        company = info["company"]
        job_title = info["job_title"]
        location = info["location"]
        today_str = date.today().strftime("%d %b")

        # Write to Universe
        uni_row = get_next_universe_row()
        if not uni_row:
            raise HTTPException(500, "Could not find next Universe row")

        write_universe_row(
            uni_row,
            company=company,
            job_title=job_title,
            date_str=today_str,
            location=location,
            status="APPLIED",
            resume_version="Data Scientist Claude V5",
            jd_url=req.jd_url,
        )

        # Create Cold Email row
        ce_row = get_next_empty_row(sheets)
        write_cold_email_row(sheets, ce_row, {
            "universe_row": str(uni_row),
            "status": "FIND",
            "company": company,
            "job_title": job_title,
            "location": location,
        })

        bust_cache()

        # Run scouts in background
        background_tasks.add_task(run_scouts_for_row, ce_row)

        return {
            "company": company,
            "job_title": job_title,
            "location": location,
            "universe_row": uni_row,
            "cold_email_row": ce_row,
            "message": f"Added {company} — scouts dispatched",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add job failed: {e}")
        raise HTTPException(500, str(e))


@app.post("/api/run-scouts/{cold_email_row}")
def run_scouts_endpoint(cold_email_row: int, background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    """Run scouts for a specific Cold Email row in background."""
    update_cold_email_row(sheets, cold_email_row, {"B": "SCOUTING"})
    bust_cache()
    background_tasks.add_task(run_scouts_for_row, cold_email_row)
    return {"status": "running", "message": "Scouts dispatched"}


@app.post("/api/update-contact")
def update_contact(req: UpdateContactRequest, user=Depends(get_current_user)):
    """Update a contact's name and/or email in Cold Email sheet."""
    # Contact 1: G (name), J (email)
    # Contact 2: H (name), K (email)
    # Contact 3: I (name), L (email)
    name_cols = {1: "G", 2: "H", 3: "I"}
    email_cols = {1: "J", 2: "K", 3: "L"}

    if req.contact_index not in (1, 2, 3):
        raise HTTPException(400, "contact_index must be 1, 2, or 3")

    updates = {}
    if req.name:
        updates[name_cols[req.contact_index]] = req.name
    if req.email is not None:
        updates[email_cols[req.contact_index]] = req.email

    try:
        update_cold_email_row(sheets, req.row, updates)
        bust_cache()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/add-contact")
def add_contact(req: AddContactRequest, user=Depends(get_current_user)):
    """Add a new contact to the next empty slot (G/H/I)."""
    rows = get_cached_rows()
    target = next((r for r in rows if r["sheet_row"] == req.row), None)
    if not target:
        raise HTTPException(404, f"Row {req.row} not found")

    # Find next empty contact slot
    for i in range(1, 4):
        if not target.get(f"contact_{i}"):
            name_col = {1: "G", 2: "H", 3: "I"}[i]
            update_cold_email_row(sheets, req.row, {name_col: req.name})
            bust_cache()
            return {"status": "ok", "slot": i}

    raise HTTPException(400, "All 3 contact slots are full")


@app.post("/api/remove-contact")
def remove_contact(req: RemoveContactRequest, user=Depends(get_current_user)):
    """Clear a contact's name and email."""
    name_cols = {1: "G", 2: "H", 3: "I"}
    email_cols = {1: "J", 2: "K", 3: "L"}

    if req.contact_index not in (1, 2, 3):
        raise HTTPException(400, "contact_index must be 1, 2, or 3")

    updates = {
        name_cols[req.contact_index]: "",
        email_cols[req.contact_index]: "",
    }
    try:
        update_cold_email_row(sheets, req.row, updates)
        bust_cache()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/generate-drafts")
async def generate_drafts_endpoint(
    background_tasks: BackgroundTasks,
    row: int = Form(...),
    resume: UploadFile = File(None),
    user=Depends(get_current_user),
):
    """
    Generate personalized emails, run quality gate, create Gmail drafts.
    Optionally attach a resume PDF.
    """
    resume_path = None
    if resume:
        # Save resume to temp file
        tmp_dir = Path(tempfile.mkdtemp())
        resume_path = str(tmp_dir / resume.filename)
        with open(resume_path, "wb") as f:
            content = await resume.read()
            f.write(content)
        _resume_store[row] = {"path": resume_path, "filename": resume.filename}

    # Run in background
    try:
        result = generate_drafts_for_row(row, resume_path)
        return {
            "status": "ok",
            "message": f"Created {result['drafts_created']} drafts (QG avg: {result['quality_score']:.1f})",
            "drafts_created": result["drafts_created"],
            "quality_score": result["quality_score"],
            "gmail_used": result["gmail_used"],
        }
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        # Cleanup resume
        if resume_path and os.path.exists(resume_path):
            try:
                shutil.rmtree(os.path.dirname(resume_path), ignore_errors=True)
            except:
                pass


# ═══════════════════════════════════════════════════════════════
# LEGACY ENDPOINTS (kept for compatibility)
# ═══════════════════════════════════════════════════════════════

@app.post("/api/trigger-find")
def trigger_find(req: AddJobRequest, user=Depends(get_current_user)):
    try:
        # Legacy: just update status
        bust_cache()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/update-status")
def update_status(req: UpdateStatusRequest, user=Depends(get_current_user)):
    try:
        update_cold_email_row(sheets, req.row, {"B": req.status})
        bust_cache()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/run-pipeline")
def run_pipeline_endpoint(user=Depends(get_current_user)):
    try:
        from main import process_all
        process_all(sheets)
        bust_cache()
        return {"status": "ok", "message": "Pipeline executed"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/run-monitor")
def run_monitor_endpoint(user=Depends(get_current_user)):
    try:
        from main import run_monitor
        run_monitor(sheets)
        bust_cache()
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
        _resume_store[row] = {"path": str(tmp_path), "filename": file.filename}
        return {"status": "ok", "message": f"Resume stored for row {row}", "file_size": len(content)}
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(500, str(e))


@app.post("/api/chat")
def chat_assistant(req: ChatRequest, user=Depends(get_current_user)):
    try:
        from anthropic import Anthropic
        from config import SCOUT_HAIKU_MODEL
        rows = get_cached_rows()
        gmail = get_cached_gmail()
        standoff = get_standoff_stats()
        active = len([r for r in rows if r["status"] not in ["DONE", "REPLIED", ""]])
        sent = len([r for r in rows if r["status"] in ["SENT", "FU1", "FU2"]])
        replied = len([r for r in rows if r["status"] == "REPLIED"])
        context = f"Pipeline: {active} active, {sent} sent, {replied} replied. Gmail: {gmail.get('total_used',0)} sent today. Standoff: Grok {standoff['grok']} vs SerpAPI {standoff['serpapi']}. Recent: {', '.join(r['company'] + ' (' + r['status'] + ')' for r in rows[-5:] if r.get('company'))}"
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=SCOUT_HAIKU_MODEL,
            max_tokens=300,
            system=f"You are ReachOut AI's assistant. Answer about the cold email pipeline. Be concise.\n\n{context}",
            messages=[{"role": "user", "content": req.message}],
        )
        return {"response": response.content[0].text}
    except Exception as e:
        return {"response": f"Error: {str(e)}"}


# ─── Main ────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    dist_dir = Path(__file__).parent / "frontend" / "dist"
    if dist_dir.exists():
        from fastapi.responses import FileResponse

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            file_path = dist_dir / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(dist_dir / "index.html")
        logger.info(f"Serving frontend from {dist_dir}")

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
