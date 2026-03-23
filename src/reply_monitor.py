"""
Reply Monitor Agent
Polls Gmail for replies, schedules follow-ups on business days.
Saturday/Sunday activity queued to Monday.
"""
import json
import logging
from datetime import datetime, timedelta, date
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config import (
    GMAIL_ACCOUNTS, GMAIL_CLIENT_SECRET, DATA_DIR,
    FOLLOW_UP_1_BIZ_DAYS, FOLLOW_UP_2_BIZ_DAYS
)

logger = logging.getLogger(__name__)

REPLY_STATE_FILE = DATA_DIR / "reply_state.json"


# ─── Business Day Utilities ──────────────────────────────────

def add_business_days(start_date: date, biz_days: int) -> date:
    """Add N business days to a date, skipping weekends."""
    current = start_date
    added = 0
    while added < biz_days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Mon-Fri = 0-4
            added += 1
    return current


def is_business_day(d: date = None) -> bool:
    """Check if a date is a business day (Mon-Fri)."""
    if d is None:
        d = date.today()
    return d.weekday() < 5


def next_business_day(d: date = None) -> date:
    """Get the next business day from a date."""
    if d is None:
        d = date.today()
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


# ─── Reply Detection ─────────────────────────────────────────

def check_replies_for_job(sent_emails: list, sent_date_str: str, gmail_account_idx: int) -> dict:
    """
    Check if any of the sent emails received replies.
    sent_emails: [{to, subject}]
    Returns: {replied: [email_addresses], unreplied: [email_addresses]}
    """
    try:
        service = _get_gmail_service(gmail_account_idx)
        if not service:
            return {"replied": [], "unreplied": [e["to"] for e in sent_emails]}

        replied = []
        unreplied = []

        for email in sent_emails:
            # Search for replies from this specific contact
            query = f"from:{email['to']} subject:Re: {email['subject']}"
            results = service.users().messages().list(
                userId="me", q=query, maxResults=1
            ).execute()

            if results.get("messages"):
                replied.append(email["to"])
                logger.info(f"Reply detected from {email['to']}")
            else:
                unreplied.append(email["to"])

        return {"replied": replied, "unreplied": unreplied}

    except Exception as e:
        logger.error(f"Reply check failed: {e}")
        return {"replied": [], "unreplied": [e["to"] for e in sent_emails]}


# ─── Follow-up Scheduling ────────────────────────────────────

def get_follow_up_dates(sent_date_str: str) -> dict:
    """
    Calculate follow-up dates based on business days from sent date.
    Returns: {fu1_date: "YYYY-MM-DD", fu2_date: "YYYY-MM-DD"}
    """
    try:
        sent_date = datetime.strptime(sent_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        sent_date = date.today()

    fu1 = add_business_days(sent_date, FOLLOW_UP_1_BIZ_DAYS)
    fu2 = add_business_days(sent_date, FOLLOW_UP_1_BIZ_DAYS + FOLLOW_UP_2_BIZ_DAYS)

    return {
        "fu1_date": fu1.isoformat(),
        "fu2_date": fu2.isoformat(),
    }


def get_due_follow_ups(rows: list) -> dict:
    """
    Check which rows need follow-ups today.
    rows: list of sheet row dicts with fu1_date, fu2_date, status, reply_from
    Returns: {fu1_rows: [...], fu2_rows: [...]}
    """
    today = date.today()

    # If today is weekend, don't trigger anything
    if not is_business_day(today):
        logger.info(f"Today is {today.strftime('%A')} — no follow-ups on weekends")
        return {"fu1_rows": [], "fu2_rows": []}

    fu1_rows = []
    fu2_rows = []

    for row in rows:
        status = row.get("status", "").upper()
        fu1_date_str = row.get("fu1_date", "")
        fu2_date_str = row.get("fu2_date", "")

        # Skip already-done or error rows
        if status in ["REPLIED", "DONE", "ERROR"]:
            continue

        # FU1 due
        if status == "SENT" and fu1_date_str:
            try:
                fu1_date = datetime.strptime(fu1_date_str, "%Y-%m-%d").date()
                if today >= fu1_date:
                    fu1_rows.append(row)
            except ValueError:
                pass

        # FU2 due
        if status == "FU1" and fu2_date_str:
            try:
                fu2_date = datetime.strptime(fu2_date_str, "%Y-%m-%d").date()
                if today >= fu2_date:
                    fu2_rows.append(row)
            except ValueError:
                pass

    return {"fu1_rows": fu1_rows, "fu2_rows": fu2_rows}


# ─── Gmail Service ────────────────────────────────────────────

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def _get_gmail_service(account_index: int):
    """Get Gmail read-only service for reply checking."""
    try:
        account = GMAIL_ACCOUNTS[account_index]
        token_file = account["credentials_file"]
        creds = None

        if Path(token_file).exists():
            creds = Credentials.from_authorized_user_file(token_file)

        if not creds or not creds.valid:
            return None

        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        logger.error(f"Gmail service init failed: {e}")
        return None


# ─── State Persistence ────────────────────────────────────────

def load_reply_state() -> dict:
    if REPLY_STATE_FILE.exists():
        with open(REPLY_STATE_FILE) as f:
            return json.load(f)
    return {"checked_at": None, "results": {}}


def save_reply_state(state: dict):
    state["checked_at"] = datetime.now().isoformat()
    with open(REPLY_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
