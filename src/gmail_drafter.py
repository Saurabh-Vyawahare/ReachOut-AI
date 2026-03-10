"""
Gmail Drafter Module
Creates email drafts across 4 Gmail accounts.
Rotates accounts with 10 drafts/day cap per account.
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
from config import GMAIL_ACCOUNTS, SENDER_NAME

logger = logging.getLogger(__name__)

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

# Track daily usage per account
USAGE_FILE = "data/gmail_usage.json"


def _load_usage() -> dict:
    """Load daily Gmail usage tracker."""
    path = Path(USAGE_FILE)
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        # Reset if it's a new day
        if data.get("date") != str(date.today()):
            return {"date": str(date.today()), "accounts": {}}
        return data
    return {"date": str(date.today()), "accounts": {}}


def _save_usage(usage: dict):
    """Save daily Gmail usage tracker."""
    Path(USAGE_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(USAGE_FILE, "w") as f:
        json.dump(usage, f, indent=2)


def get_gmail_service(account_index: int):
    """
    Get authenticated Gmail service for a specific account.
    Uses OAuth2 tokens stored per account.
    """
    account = GMAIL_ACCOUNTS[account_index]
    token_file = account["credentials_file"]
    creds = None

    if Path(token_file).exists():
        creds = Credentials.from_authorized_user_file(token_file, GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # First-time auth: opens browser
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials/gmail_client_secret.json", GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token
        Path(token_file).parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def get_next_available_account() -> int:
    """
    Find the next Gmail account that hasn't hit its daily cap.
    Returns account index (0-3) or -1 if all full.
    """
    usage = _load_usage()

    for i, account in enumerate(GMAIL_ACCOUNTS):
        email = account["email"]
        used = usage["accounts"].get(email, 0)
        if used < account["daily_cap"]:
            return i

    return -1  # All accounts at capacity


def create_draft(to_email: str, subject: str, body: str,
                 account_index: int = None) -> dict:
    """
    Create an email draft in the specified Gmail account.

    Returns:
        {
            "success": bool,
            "gmail_account": str,
            "draft_id": str,
            "error": str or None
        }
    """
    # Auto-select account if not specified
    if account_index is None:
        account_index = get_next_available_account()

    if account_index == -1:
        return {
            "success": False,
            "gmail_account": None,
            "draft_id": None,
            "error": "All Gmail accounts at daily capacity (10 each)"
        }

    account = GMAIL_ACCOUNTS[account_index]

    try:
        service = get_gmail_service(account_index)

        # Build the email message
        message = MIMEText(body, "plain")
        message["to"] = to_email
        message["from"] = f"{SENDER_NAME} <{account['email']}>"
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        draft = service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw}}
        ).execute()

        # Update usage tracker
        usage = _load_usage()
        email = account["email"]
        usage["accounts"][email] = usage["accounts"].get(email, 0) + 1
        _save_usage(usage)

        logger.info(
            f"Draft created in {email} "
            f"(usage: {usage['accounts'][email]}/{account['daily_cap']})"
        )

        return {
            "success": True,
            "gmail_account": email,
            "draft_id": draft["id"],
            "error": None
        }

    except Exception as e:
        logger.error(f"Failed to create draft in {account['email']}: {e}")
        return {
            "success": False,
            "gmail_account": account["email"],
            "draft_id": None,
            "error": str(e)
        }


def create_batch_drafts(emails: list[dict]) -> list[dict]:
    """
    Create drafts for a batch of emails.
    Automatically rotates across Gmail accounts.

    emails: list of {"to": str, "subject": str, "body": str}
    Returns: list of draft results
    """
    results = []

    for email in emails:
        result = create_draft(
            to_email=email["to"],
            subject=email["subject"],
            body=email["body"]
        )
        results.append(result)

        if not result["success"] and "capacity" in (result.get("error") or ""):
            logger.warning("All Gmail accounts at capacity. Stopping batch.")
            break

    return results


def get_daily_status() -> dict:
    """
    Get current daily usage status for all accounts.
    Returns: {"total_used": int, "total_remaining": int, "accounts": [...]}
    """
    usage = _load_usage()
    status = {
        "date": usage["date"],
        "total_used": 0,
        "total_remaining": 0,
        "accounts": []
    }

    for account in GMAIL_ACCOUNTS:
        email = account["email"]
        used = usage["accounts"].get(email, 0)
        remaining = account["daily_cap"] - used
        status["accounts"].append({
            "email": email,
            "used": used,
            "remaining": remaining,
            "cap": account["daily_cap"]
        })
        status["total_used"] += used
        status["total_remaining"] += remaining

    return status
