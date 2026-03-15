"""
Cold Email Automation - Main Orchestrator
Reads the Cold Email sheet, processes triggers, coordinates all modules.

Usage:
    cd src
    python main.py              # Process all pending rows
    python main.py --status     # Show daily status
    python main.py --test       # Test with a sample row
"""
import sys
import logging
from datetime import datetime, timedelta

from config import STATUS, DATA_DIR
from sheets_handler import (
    get_sheets_service, read_universe_row, read_cold_email_rows,
    update_cold_email_row, fill_contacts, fill_job_info, check_duplicate
)
from contact_finder import find_contacts
from jd_fetcher import fetch_jd
from email_generator import generate_emails, generate_follow_up
from gmail_drafter import create_batch_drafts, get_daily_status

# ─── Logging Setup ────────────────────────────────────────────
log_file = str(DATA_DIR / "automation.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, mode="a")
    ]
)
logger = logging.getLogger(__name__)


def process_find(sheets, row: dict):
    """
    FIND trigger: Find contacts for this job.
    1. Read Universe row for job details
    2. Fetch JD from link or raw text
    3. Find contacts (Apollo + Google/LinkedIn)
    4. Fill contacts into sheet
    """
    row_num = row["sheet_row"]
    universe_row = row["universe_row"]

    if not universe_row:
        update_cold_email_row(sheets, row_num, {
            "B": STATUS["ERROR"],
            "P": "Error: No Universe row number in column A"
        })
        return

    logger.info(f"[ROW {row_num}] FIND triggered for Universe row {universe_row}")

    # Step 1: Read Universe row
    universe_data = read_universe_row(sheets, int(universe_row))
    if not universe_data or not universe_data["company"]:
        update_cold_email_row(sheets, row_num, {
            "B": STATUS["ERROR"],
            "P": f"Error: Could not read Universe row {universe_row}"
        })
        return

    company = universe_data["company"]
    job_title = universe_data["job_title"]
    location = universe_data["location"]
    jd_input = universe_data["jd_input"]

    logger.info(f"[ROW {row_num}] {job_title} at {company} ({location})")

    # Auto-fill company, title, location from Universe
    fill_job_info(sheets, row_num, universe_data)

    # Step 2: Fetch JD
    jd_result = fetch_jd(jd_input) if jd_input else None

    if jd_result and jd_result["fetch_success"]:
        sector = jd_result["sector"]
        jd_text = jd_result["jd_text"]
        logger.info(f"[ROW {row_num}] JD fetched ({jd_result['source']}), sector: {sector}")
    elif jd_result and not jd_result["fetch_success"]:
        # URL fetch failed
        update_cold_email_row(sheets, row_num, {
            "P": f"JD fetch failed: {jd_result['error']}. Paste JD text in Universe col G."
        })
        sector = "tech"  # default
        jd_text = ""
        logger.warning(f"[ROW {row_num}] JD fetch failed: {jd_result['error']}")
    else:
        sector = "tech"
        jd_text = ""
        logger.warning(f"[ROW {row_num}] No JD link/text in Universe col G")

    # Step 3: Find contacts
    result = find_contacts(company, job_title, location)
    contacts = result["contacts"]

    if not contacts:
        update_cold_email_row(sheets, row_num, {
            "B": STATUS["ERROR"],
            "P": "No contacts found. Try adding JD text to Universe col G."
        })
        return

    # Step 4: Fill contacts into sheet
    fill_contacts(sheets, row_num, contacts, sector, result["notes"])

    # Update status: waiting for user to paste emails
    note = result["notes"]
    if not jd_text:
        note += " | WARNING: No JD, paste text in Universe col G then re-FIND"

    update_cold_email_row(sheets, row_num, {
        "P": note
    })

    logger.info(
        f"[ROW {row_num}] Found {len(contacts)} contacts: "
        + ", ".join(c.display_string() for c in contacts)
    )
    print(f"\n  Contacts found for {company}:")
    for i, c in enumerate(contacts, 1):
        print(f"    {i}. {c.display_string()} [{c.source}]")
    if result["name_drop"]:
        print(f"    Name-drop: {result['name_drop'].display_string()}")
    print(f"  Next: Paste emails into columns J/K/L, then set status to READY\n")


def process_ready(sheets, row: dict):
    """
    READY trigger: Generate emails and create Gmail drafts.
    1. Read contacts and emails from sheet
    2. Fetch JD for email generation
    3. Generate emails using AI
    4. Create Gmail drafts
    """
    row_num = row["sheet_row"]
    universe_row = row["universe_row"]
    company = row["company"]
    job_title = row["job_title"]
    location = row["location"]
    sector = row["sector"] or "tech"

    logger.info(f"[ROW {row_num}] READY triggered for {job_title} at {company}")

    # Check we have emails
    contacts_and_emails = []
    for i in range(1, 4):
        contact = row.get(f"contact_{i}", "")
        email = row.get(f"email_{i}", "")
        if contact and email:
            # Check for duplicates
            if check_duplicate(sheets, email):
                logger.warning(f"[ROW {row_num}] Duplicate email: {email}")
                print(f"  WARNING: {email} was already used in a previous outreach!")

            contacts_and_emails.append({
                "name": contact.split(" - ")[0].strip() if " - " in contact else contact,
                "title": contact.split(" - ")[1].strip() if " - " in contact else "",
                "email": email
            })

    if not contacts_and_emails:
        update_cold_email_row(sheets, row_num, {
            "B": STATUS["ERROR"],
            "P": "Error: No emails found in columns J/K/L"
        })
        return

    # Fetch JD
    universe_data = read_universe_row(sheets, int(universe_row)) if universe_row else None
    jd_input = universe_data.get("jd_input", "") if universe_data else ""
    jd_result = fetch_jd(jd_input) if jd_input else None
    jd_text = jd_result["jd_text"] if jd_result and jd_result["fetch_success"] else ""

    if not jd_text:
        logger.warning(f"[ROW {row_num}] No JD available, generating with basic info")

    # Build contact objects for email generator
    from contact_finder import Contact
    contact_objects = []
    for ce in contacts_and_emails:
        c = Contact(
            name=ce["name"],
            title=ce["title"],
            company=company
        )
        contact_objects.append(c)

    # Find name-drop (use a contact we're NOT emailing)
    name_drop = None

    # Generate emails
    logger.info(f"[ROW {row_num}] Generating {len(contact_objects)} emails...")
    emails = generate_emails(
        contacts=contact_objects,
        jd_text=jd_text,
        company=company,
        job_title=job_title,
        location=location,
        sector=sector.lower(),
        company_size="mid_size",
        name_drop=name_drop
    )

    # Create Gmail drafts
    draft_requests = []
    for i, email_data in enumerate(emails):
        draft_requests.append({
            "to": contacts_and_emails[i]["email"],
            "subject": email_data["subject"],
            "body": email_data["body"]
        })

    logger.info(f"[ROW {row_num}] Creating {len(draft_requests)} Gmail drafts...")
    results = create_batch_drafts(draft_requests)

    # Update sheet
    gmail_used = set()
    success_count = 0
    for r in results:
        if r["success"]:
            gmail_used.add(r["gmail_account"])
            success_count += 1

    gmail_str = ", ".join(gmail_used) if gmail_used else "Failed"

    update_cold_email_row(sheets, row_num, {
        "N": gmail_str,
        "P": f"Generated {success_count}/{len(draft_requests)} drafts"
    })

    logger.info(f"[ROW {row_num}] {success_count} drafts created in {gmail_str}")
    print(f"\n  Drafts created for {company}:")
    for i, (req, res) in enumerate(zip(draft_requests, results)):
        status = "DONE" if res["success"] else f"FAILED: {res['error']}"
        print(f"    {i+1}. To: {req['to']} | Subject: {req['subject']} | {status}")
    print(f"  Gmail accounts used: {gmail_str}")
    print(f"  Next: Review drafts in Gmail, send them, then set status to SENT\n")


def process_follow_up(sheets, row: dict, follow_up_number: int):
    """
    FOLLOW-UP trigger: Create follow-up draft for unreplied contacts.
    """
    row_num = row["sheet_row"]
    company = row["company"]
    job_title = row["job_title"]
    replied = set()

    # Parse reply_from field
    if row["reply_from"]:
        for r in row["reply_from"].split(","):
            r = r.strip()
            if r.isdigit():
                replied.add(int(r))

    # Build follow-up list (only unreplied contacts)
    follow_ups = []
    for i in range(1, 4):
        if i in replied:
            continue
        contact = row.get(f"contact_{i}", "")
        email = row.get(f"email_{i}", "")
        if contact and email:
            name = contact.split(" - ")[0].strip() if " - " in contact else contact
            fu = generate_follow_up(name, job_title, follow_up_number)
            follow_ups.append({
                "to": email,
                "subject": fu["subject"],
                "body": fu["body"]
            })

    if not follow_ups:
        update_cold_email_row(sheets, row_num, {
            "P": f"FU{follow_up_number}: All contacts replied or no emails found"
        })
        return

    logger.info(f"[ROW {row_num}] Creating {len(follow_ups)} follow-up #{follow_up_number} drafts")
    results = create_batch_drafts(follow_ups)

    success_count = sum(1 for r in results if r["success"])
    update_cold_email_row(sheets, row_num, {
        "P": f"FU{follow_up_number}: {success_count}/{len(follow_ups)} drafts created"
    })

    print(f"\n  Follow-up #{follow_up_number} for {company}:")
    for fu, res in zip(follow_ups, results):
        status = "DONE" if res["success"] else f"FAILED: {res['error']}"
        print(f"    To: {fu['to']} | {status}")


def process_all(sheets):
    """Process all pending rows based on their status."""
    rows = read_cold_email_rows(sheets)

    find_rows = [r for r in rows if r["status"] == STATUS["FIND"]]
    ready_rows = [r for r in rows if r["status"] == STATUS["READY"]]
    fu1_rows = [r for r in rows if r["status"] == STATUS["FOLLOW_UP_1"]]
    fu2_rows = [r for r in rows if r["status"] == STATUS["FOLLOW_UP_2"]]

    total = len(find_rows) + len(ready_rows) + len(fu1_rows) + len(fu2_rows)

    if total == 0:
        print("\n  No pending actions found. All rows are up to date.")
        print("  To add a new job: Put the Universe row number in col A, set status to FIND\n")
        return

    print(f"\n  Processing {total} rows:")
    print(f"    FIND: {len(find_rows)} | READY: {len(ready_rows)} "
          f"| FU1: {len(fu1_rows)} | FU2: {len(fu2_rows)}")
    print()

    for row in find_rows:
        process_find(sheets, row)

    for row in ready_rows:
        process_ready(sheets, row)

    for row in fu1_rows:
        process_follow_up(sheets, row, 1)

    for row in fu2_rows:
        process_follow_up(sheets, row, 2)


def show_status():
    """Show current daily status."""
    gmail_status = get_daily_status()
    print(f"\n  Gmail Daily Status ({gmail_status['date']})")
    print(f"  {'='*50}")
    for acc in gmail_status["accounts"]:
        bar = "█" * acc["used"] + "░" * acc["remaining"]
        print(f"    {acc['email']}: [{bar}] {acc['used']}/{acc['cap']}")
    print(f"    Total: {gmail_status['total_used']} used, "
          f"{gmail_status['total_remaining']} remaining")
    print()


def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("  REACHOUT-AI | Cold Email Automation v1.0")
    print("="*60)

    # Parse args
    if "--status" in sys.argv:
        show_status()
        return

    if "--test" in sys.argv:
        print("\n  Running in TEST mode (no actual API calls)")
        print("  TODO: Implement test mode with mock data\n")
        return

    # Initialize sheets
    try:
        sheets = get_sheets_service()
        logger.info("Google Sheets connected")
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        print(f"\n  ERROR: Could not connect to Google Sheets: {e}")
        print("  Have you set up credentials/sheets_service_account.json?")
        print("  Run: python setup_check.py for setup guide\n")
        return

    # Show Gmail status
    show_status()

    # Process all pending rows
    process_all(sheets)

    print("="*60)
    print("  Done! Check your Gmail drafts.")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
