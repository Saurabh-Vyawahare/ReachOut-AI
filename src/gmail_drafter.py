"""
Gmail Drafter Module (v3 - Clean Round-Robin)
Creates email drafts spreading across all 4 Gmail accounts.
Continuous round-robin: Gmail #1 → #2 → #3 → #4 → #1 → ...
Persists rotation position across runs. HTML formatted emails.
"""
import base64
import json
import logging
from datetime import date
from email.mime.text import MIMEText
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from config import GMAIL_ACCOUNTS, SENDER_NAME, GMAIL_CLIENT_SECRET, DATA_DIR

logger = logging.getLogger(__name__)

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send"
]

USAGE_FILE = str(DATA_DIR / "gmail_usage.json")
ROTATION_FILE = str(DATA_DIR / "gmail_rotation.json")
DAILY_CAP_PER_ACCOUNT = 10


# ─── HTML Email Formatting ────────────────────────────────────

def _to_html(text: str) -> str:
    """Convert plain text email to clean HTML with professional styling."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    paragraphs = text.split("\n\n")
    html_parts = []
    for para in paragraphs:
        lines = para.strip().split("\n")
        formatted_lines = "<br>".join(lines)
        html_parts.append(f"<p style='margin:0 0 12px 0;'>{formatted_lines}</p>")
    return f"""<div style="font-family: Arial, sans-serif; font-size: 14px; color: #1a1a1a; line-height: 1.5;">
{''.join(html_parts)}
</div>"""


# ─── Usage Tracker (daily cap) ────────────────────────────────

def _load_usage() -> dict:
    path = Path(USAGE_FILE)
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        if data.get("date") != str(date.today()):
            return {"date": str(date.today()), "accounts": {}}
        return data
    return {"date": str(date.today()), "accounts": {}}


def _save_usage(usage: dict):
    Path(USAGE_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(USAGE_FILE, "w") as f:
        json.dump(usage, f, indent=2)


# ─── Rotation Tracker (round-robin position) ──────────────────

def _load_rotation() -> dict:
    path = Path(ROTATION_FILE)
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        if data.get("date") != str(date.today()):
            return {"date": str(date.today()), "last_index": -1}
        return data
    return {"date": str(date.today()), "last_index": -1}


def _save_rotation(rotation: dict):
    Path(ROTATION_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(ROTATION_FILE, "w") as f:
        json.dump(rotation, f, indent=2)


# ─── Gmail Service ────────────────────────────────────────────

def get_gmail_service(account_index: int):
    account = GMAIL_ACCOUNTS[account_index]
    token_file = account["credentials_file"]
    creds = None

    if Path(token_file).exists():
        creds = Credentials.from_authorized_user_file(token_file, GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                GMAIL_CLIENT_SECRET, GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)

        Path(token_file).parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ─── Draft Creation ───────────────────────────────────────────

def create_draft(to_email: str, subject: str, body: str,
                 account_index: int = None) -> dict:
    """Create an email draft in the specified Gmail account."""
    if account_index is None:
        account_index = _get_next_available_account()

    if account_index == -1:
        return {
            "success": False, "gmail_account": None,
            "draft_id": None,
            "error": "All Gmail accounts at daily capacity"
        }

    account = GMAIL_ACCOUNTS[account_index]
    account_email = account["email"]

    try:
        service = get_gmail_service(account_index)

        html_body = _to_html(body)
        message = MIMEText(html_body, "html")
        message["to"] = to_email
        message["from"] = f"{SENDER_NAME} <{account_email}>"
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        draft = service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw}}
        ).execute()

        # Update usage
        usage = _load_usage()
        usage["accounts"][account_email] = usage["accounts"].get(account_email, 0) + 1
        _save_usage(usage)

        logger.info(
            f"Draft created in {account_email} | "
            f"Usage: {usage['accounts'][account_email]}/{DAILY_CAP_PER_ACCOUNT}"
        )

        return {
            "success": True,
            "gmail_account": account_email,
            "draft_id": draft["id"],
            "error": None
        }

    except Exception as e:
        logger.error(f"Failed to create draft in {account_email}: {e}")
        return {
            "success": False,
            "gmail_account": account_email,
            "draft_id": None,
            "error": str(e)
        }


def _get_next_available_account() -> int:
    """Find the next Gmail account that hasn't hit its daily cap."""
    usage = _load_usage()
    for i, account in enumerate(GMAIL_ACCOUNTS):
        email = account["email"]
        if not email:
            continue
        used = usage["accounts"].get(email, 0)
        if used < DAILY_CAP_PER_ACCOUNT:
            return i
    return -1


# ─── Batch Drafts with Round-Robin ────────────────────────────

def create_batch_drafts(emails: list[dict]) -> list[dict]:
    """
    Create drafts spreading emails across ALL accounts in continuous round-robin.
    Persists rotation across runs.

    Job 1 (9:00 AM):  Email 1 → Gmail #1, Email 2 → Gmail #2, Email 3 → Gmail #3
    Job 2 (9:08 AM):  Email 1 → Gmail #4, Email 2 → Gmail #1, Email 3 → Gmail #2
    Job 3 (9:16 AM):  Email 1 → Gmail #3, Email 2 → Gmail #4, Email 3 → Gmail #1
    """
    results = []
    usage = _load_usage()
    rotation = _load_rotation()
    last_index = rotation.get("last_index", -1)

    # Find all available accounts (not at daily cap)
    available_accounts = []
    for i, account in enumerate(GMAIL_ACCOUNTS):
        email = account["email"]
        if not email:
            continue
        used = usage["accounts"].get(email, 0)
        if used < DAILY_CAP_PER_ACCOUNT:
            available_accounts.append(i)

    if not available_accounts:
        return [{
            "success": False, "gmail_account": None,
            "draft_id": None,
            "error": "All Gmail accounts at daily capacity"
        }]

    # Find where to start in the rotation
    start_pos = 0
    for pos, acc_idx in enumerate(available_accounts):
        if acc_idx > last_index:
            start_pos = pos
            break
    else:
        start_pos = 0

    last_used = last_index

    for idx, email in enumerate(emails):
        pos = (start_pos + idx) % len(available_accounts)
        account_index = available_accounts[pos]

        result = create_draft(
            to_email=email["to"],
            subject=email["subject"],
            body=email["body"],
            account_index=account_index
        )
        results.append(result)

        last_used = account_index

        if not result["success"] and "capacity" in (result.get("error") or ""):
            if account_index in available_accounts:
                available_accounts.remove(account_index)
            if not available_accounts:
                logger.warning("All Gmail accounts at capacity. Stopping batch.")
                break

    # Save rotation position for next run
    rotation["last_index"] = last_used
    _save_rotation(rotation)

    return results


# ─── Status ───────────────────────────────────────────────────

def get_daily_status() -> dict:
    """Get current daily usage status for all accounts."""
    usage = _load_usage()
    status = {
        "date": usage["date"],
        "total_used": 0,
        "total_remaining": 0,
        "accounts": []
    }

    for account in GMAIL_ACCOUNTS:
        email = account["email"]
        if not email:
            continue
        used = usage["accounts"].get(email, 0)
        remaining = DAILY_CAP_PER_ACCOUNT - used
        status["accounts"].append({
            "email": email,
            "used": used,
            "remaining": remaining,
            "cap": DAILY_CAP_PER_ACCOUNT
        })
        status["total_used"] += used
        status["total_remaining"] += remaining

    return status
