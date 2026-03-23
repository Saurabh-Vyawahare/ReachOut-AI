"""
ReachOut-AI v2.0 — Main Orchestrator
Multi-agent pipeline: JD Analyzer → Dual Scouts → Validator → Composer → Quality Gate → Gmail

Usage:
    cd src
    python main.py                    # Process all pending rows
    python main.py --status           # Show daily status + standoff stats
    python main.py --monitor          # Check replies + trigger follow-ups
    python main.py --standoff-stats   # Show 30-day standoff results
"""
import sys
import logging
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import STATUS, DATA_DIR, QUALITY_GATE_MAX_RETRIES
from sheets_handler import (
    get_sheets_service, read_universe_row, read_cold_email_rows,
    update_cold_email_row, fill_contacts, fill_job_info, check_duplicate,
    update_standoff_result, update_follow_up_dates, log_standoff_to_sheet,
)
from jd_analyzer import analyze_jd
from scout_grok import scout_grok
from scout_serpapi import scout_serpapi
from validator import validate_standoff, get_standoff_stats
from email_generator import generate_emails, generate_follow_up
from quality_gate import score_batch
from gmail_drafter import create_batch_drafts, get_daily_status
from reply_monitor import (
    get_follow_up_dates, get_due_follow_ups, is_business_day,
    check_replies_for_job,
)
from contact import Contact

# ─── Logging ─────────────────────────────────────────────────
log_file = str(DATA_DIR / "automation_v2.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(), logging.FileHandler(log_file, mode="a")]
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# STEP 1: FIND — JD Analysis + Dual Scout + Validator
# ═══════════════════════════════════════════════════════════════

def process_find(sheets, row: dict):
    """Full v2 pipeline from FIND to contacts filled."""
    row_num = row["sheet_row"]
    universe_row = row["universe_row"]

    if not universe_row:
        update_cold_email_row(sheets, row_num, {"B": STATUS["ERROR"], "P": "No Universe row number"})
        return

    logger.info(f"[ROW {row_num}] ═══ FIND triggered ═══")
    update_cold_email_row(sheets, row_num, {"B": STATUS["SCOUTING"], "P": "Pipeline started..."})

    # Read Universe row
    universe_data = read_universe_row(sheets, int(universe_row))
    if not universe_data or not universe_data["company"]:
        update_cold_email_row(sheets, row_num, {"B": STATUS["ERROR"], "P": f"Could not read Universe row {universe_row}"})
        return

    company = universe_data["company"]
    job_title = universe_data["job_title"]
    location = universe_data["location"]
    jd_input = universe_data["jd_input"]

    fill_job_info(sheets, row_num, universe_data)
    logger.info(f"[ROW {row_num}] {job_title} at {company} ({location})")

    # ─── AGENT 1: JD Analyzer ────────────────────────────
    logger.info(f"[ROW {row_num}] Running JD Analyzer...")
    jd_result = analyze_jd(jd_input) if jd_input else {
        "jd_text": "", "team": "Data", "sector": "tech",
        "company_size_hint": "mid_size", "critical_skills": [],
        "fetch_success": False, "error": "No JD input"
    }

    team = jd_result.get("team", "Data")
    sector = jd_result.get("sector", "tech")
    jd_text = jd_result.get("jd_text", "")

    if jd_result["fetch_success"]:
        skills_summary = ", ".join([s["jd_need"][:40] for s in jd_result.get("critical_skills", [])[:3]])
        logger.info(f"[ROW {row_num}] JD: team={team}, sector={sector}, skills=[{skills_summary}]")
    else:
        logger.warning(f"[ROW {row_num}] JD fetch failed: {jd_result.get('error')}")

    # ─── AGENTS 2+3: Dual Scouts (parallel) ──────────────
    logger.info(f"[ROW {row_num}] Running dual scouts in parallel...")
    grok_result = {"contacts": [], "source": "grok"}
    serp_result = {"contacts": [], "source": "serpapi"}

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(scout_grok, company, job_title, location, team): "grok",
            executor.submit(scout_serpapi, company, job_title, location, team): "serpapi",
        }
        for future in as_completed(futures):
            scout_name = futures[future]
            try:
                result = future.result()
                if scout_name == "grok":
                    grok_result = result
                else:
                    serp_result = result
                logger.info(f"[ROW {row_num}] {scout_name}: {len(result.get('contacts', []))} contacts")
            except Exception as e:
                logger.error(f"[ROW {row_num}] {scout_name} failed: {e}")

    # ─── AGENT 4: Validator (standoff) ───────────────────
    logger.info(f"[ROW {row_num}] Running Validator standoff...")
    standoff = validate_standoff(grok_result, serp_result, company, job_title)

    contacts = standoff["contacts"]
    winner = standoff["winner"]
    reason = standoff["reason"]

    if not contacts:
        update_cold_email_row(sheets, row_num, {
            "B": STATUS["ERROR"],
            "P": f"No contacts found. Grok: {grok_result['notes']} | SerpAPI: {serp_result['notes']}"
        })
        return

    logger.info(f"[ROW {row_num}] Standoff winner: {winner} — {reason}")
    logger.info(f"[ROW {row_num}] Selected {len(contacts)} contacts: {', '.join(c.name for c in contacts)}")

    # Fill sheet
    fill_contacts(sheets, row_num, contacts, sector,
                  f"Winner: {winner} | {reason}")
    update_standoff_result(sheets, row_num, winner, 0)
    log_standoff_to_sheet(sheets, company, winner, reason)

    print(f"\n  ✓ Contacts found for {company} (winner: {winner}):")
    for i, c in enumerate(contacts, 1):
        print(f"    {i}. {c.display_string()} [{c.source}]")
    if standoff.get("name_drop"):
        print(f"    Name-drop: {standoff['name_drop'].display_string()}")
    print(f"  Next: Paste emails into J/K/L, then set status to READY\n")


# ═══════════════════════════════════════════════════════════════
# STEP 2: READY — Compose + Quality Gate + Draft
# ═══════════════════════════════════════════════════════════════

def process_ready(sheets, row: dict):
    """Generate emails, run quality gate, create Gmail drafts."""
    row_num = row["sheet_row"]
    universe_row = row["universe_row"]
    company = row["company"]
    job_title = row["job_title"]
    location = row["location"]
    sector = row["sector"] or "tech"

    logger.info(f"[ROW {row_num}] ═══ READY triggered for {company} ═══")
    update_cold_email_row(sheets, row_num, {"B": STATUS["COMPOSING"], "P": "Generating emails..."})

    # Build contact list
    contacts_and_emails = []
    for i in range(1, 4):
        contact = row.get(f"contact_{i}", "")
        email = row.get(f"email_{i}", "")
        if contact and email:
            if check_duplicate(sheets, email):
                logger.warning(f"[ROW {row_num}] Duplicate email: {email}")
            contacts_and_emails.append({
                "name": contact.split(" - ")[0].strip() if " - " in contact else contact,
                "title": contact.split(" - ")[1].strip() if " - " in contact else "",
                "email": email
            })

    if not contacts_and_emails:
        update_cold_email_row(sheets, row_num, {"B": STATUS["ERROR"], "P": "No emails found in J/K/L"})
        return

    # Fetch JD for email generation
    universe_data = read_universe_row(sheets, int(universe_row)) if universe_row else None
    jd_input = universe_data.get("jd_input", "") if universe_data else ""
    jd_result = analyze_jd(jd_input) if jd_input else None
    jd_text = jd_result.get("jd_text", "") if jd_result else ""

    # Build Contact objects
    contact_objects = [
        Contact(name=ce["name"], title=ce["title"], company=company)
        for ce in contacts_and_emails
    ]

    # ─── AGENT 5: Email Composer (Sonnet) ─────────────────
    logger.info(f"[ROW {row_num}] Generating {len(contact_objects)} emails...")
    emails = generate_emails(
        contacts=contact_objects, jd_text=jd_text, company=company,
        job_title=job_title, location=location, sector=sector.lower(),
        company_size="mid_size", name_drop=None
    )

    # ─── AGENT 6: Quality Gate (Haiku) ────────────────────
    logger.info(f"[ROW {row_num}] Running quality gate...")
    scored = score_batch(emails, job_title, company, jd_text)

    # Retry rejected emails
    final_emails = []
    avg_score = 0
    for em in scored:
        if em["passed"]:
            final_emails.append(em)
            avg_score += em["score"]
        else:
            logger.info(f"[ROW {row_num}] Regenerating email for {em['contact_name']} (score: {em['score']})")
            # Find the contact object and regenerate
            for co in contact_objects:
                if co.name == em["contact_name"]:
                    retry_emails = generate_emails(
                        contacts=[co], jd_text=jd_text, company=company,
                        job_title=job_title, location=location, sector=sector.lower(),
                        company_size="mid_size", name_drop=None
                    )
                    if retry_emails:
                        retry_scored = score_batch(retry_emails, job_title, company, jd_text)
                        final_emails.append(retry_scored[0])
                        avg_score += retry_scored[0]["score"]
                    break

    if avg_score > 0:
        avg_score = round(avg_score / len(final_emails), 1)

    # ─── AGENT 7: Gmail Dispatcher ────────────────────────
    draft_requests = []
    for i, email_data in enumerate(final_emails):
        draft_requests.append({
            "to": contacts_and_emails[i]["email"],
            "subject": email_data["subject"],
            "body": email_data["body"]
        })

    logger.info(f"[ROW {row_num}] Creating {len(draft_requests)} Gmail drafts...")
    results = create_batch_drafts(draft_requests)

    gmail_used = set()
    success_count = 0
    for r in results:
        if r["success"]:
            gmail_used.add(r["gmail_account"])
            success_count += 1

    gmail_str = ", ".join(gmail_used) if gmail_used else "Failed"

    # Calculate follow-up dates
    today = date.today().isoformat()
    fu_dates = get_follow_up_dates(today)

    update_cold_email_row(sheets, row_num, {
        "B": STATUS["DRAFTS_READY"] if success_count > 0 else STATUS["ERROR"],
        "N": gmail_str,
        "O": today,
        "P": f"v2: {success_count} drafts | QG avg: {avg_score}/10 | Winner: {row.get('scout_winner', 'n/a')}",
    })
    update_standoff_result(sheets, row_num, row.get("scout_winner", ""), avg_score)
    update_follow_up_dates(sheets, row_num, fu_dates["fu1_date"], fu_dates["fu2_date"])

    logger.info(f"[ROW {row_num}] ✓ {success_count} drafts | QG: {avg_score}/10 | Gmail: {gmail_str}")
    print(f"\n  ✓ Drafts ready for {company}:")
    for i, (req, res) in enumerate(zip(draft_requests, results)):
        status = "DONE" if res["success"] else f"FAILED: {res['error']}"
        print(f"    {i+1}. To: {req['to']} | Score: {final_emails[i]['score']}/10 | {status}")
    print(f"  Next: Review drafts in Gmail, send them, mark SENT\n")


# ═══════════════════════════════════════════════════════════════
# STEP 3: FOLLOW-UPS (automatic via reply monitor)
# ═══════════════════════════════════════════════════════════════

def process_follow_up(sheets, row: dict, follow_up_number: int):
    """Create follow-up drafts for unreplied contacts."""
    row_num = row["sheet_row"]
    company = row["company"]
    job_title = row["job_title"]
    replied = set()

    if row["reply_from"]:
        for r in row["reply_from"].split(","):
            r = r.strip()
            if r.isdigit():
                replied.add(int(r))

    follow_ups = []
    for i in range(1, 4):
        if i in replied:
            continue
        contact = row.get(f"contact_{i}", "")
        email = row.get(f"email_{i}", "")
        if contact and email:
            name = contact.split(" - ")[0].strip() if " - " in contact else contact
            fu = generate_follow_up(name, job_title, follow_up_number)
            follow_ups.append({"to": email, "subject": fu["subject"], "body": fu["body"]})

    if not follow_ups:
        update_cold_email_row(sheets, row_num, {"P": f"FU{follow_up_number}: All replied or no emails"})
        return

    logger.info(f"[ROW {row_num}] Creating {len(follow_ups)} FU{follow_up_number} drafts")
    results = create_batch_drafts(follow_ups)
    success_count = sum(1 for r in results if r["success"])

    new_status = STATUS["FOLLOW_UP_1"] if follow_up_number == 1 else STATUS["FOLLOW_UP_2"]
    update_cold_email_row(sheets, row_num, {
        "B": new_status,
        "P": f"FU{follow_up_number}: {success_count}/{len(follow_ups)} drafts"
    })

    print(f"\n  ✓ Follow-up #{follow_up_number} for {company}: {success_count} drafts\n")


# ═══════════════════════════════════════════════════════════════
# MONITOR MODE — check replies, trigger follow-ups
# ═══════════════════════════════════════════════════════════════

def run_monitor(sheets):
    """Check replies and trigger due follow-ups."""
    if not is_business_day():
        print(f"\n  Today is a weekend — follow-ups queued to Monday\n")
        return

    rows = read_cold_email_rows(sheets)
    due = get_due_follow_ups(rows)

    print(f"\n  Follow-ups due today: FU1={len(due['fu1_rows'])}, FU2={len(due['fu2_rows'])}")

    for row in due["fu1_rows"]:
        process_follow_up(sheets, row, 1)

    for row in due["fu2_rows"]:
        process_follow_up(sheets, row, 2)

    if not due["fu1_rows"] and not due["fu2_rows"]:
        print("  No follow-ups due today.\n")


# ═══════════════════════════════════════════════════════════════
# PROCESS ALL
# ═══════════════════════════════════════════════════════════════

def process_all(sheets):
    """Process all pending rows by status."""
    rows = read_cold_email_rows(sheets)

    find_rows = [r for r in rows if r["status"] == STATUS["FIND"]]
    ready_rows = [r for r in rows if r["status"] == STATUS["READY"]]

    total = len(find_rows) + len(ready_rows)

    if total == 0:
        print("\n  No pending actions. Paste a JD URL in the Universe tab to start.\n")
        return

    print(f"\n  Processing {total} rows: FIND={len(find_rows)} READY={len(ready_rows)}\n")

    for row in find_rows:
        process_find(sheets, row)
    for row in ready_rows:
        process_ready(sheets, row)


def show_status():
    """Show Gmail + standoff status."""
    gmail = get_daily_status()
    standoff = get_standoff_stats()

    print(f"\n  ═══ ReachOut-AI v2.0 Status ═══")
    print(f"\n  Gmail ({gmail['date']})")
    for acc in gmail["accounts"]:
        bar = "█" * acc["used"] + "░" * acc["remaining"]
        print(f"    {acc['email']}: [{bar}] {acc['used']}/{acc['cap']}")
    print(f"    Total: {gmail['total_used']} sent, {gmail['total_remaining']} remaining")

    print(f"\n  Standoff ({standoff['total']} total)")
    if standoff["total"] > 0:
        grok_pct = round(standoff["grok"] / standoff["total"] * 100)
        serp_pct = round(standoff["serpapi"] / standoff["total"] * 100)
        print(f"    Grok:    {standoff['grok']} wins ({grok_pct}%)")
        print(f"    SerpAPI: {standoff['serpapi']} wins ({serp_pct}%)")
    else:
        print("    No standoff data yet")
    print()


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    print("\n" + "=" * 60)
    print("  REACHOUT-AI v2.0 | Multi-Agent Cold Email Automation")
    print("=" * 60)

    if "--status" in sys.argv:
        show_status()
        return

    if "--standoff-stats" in sys.argv:
        stats = get_standoff_stats()
        print(f"\n  Standoff: Grok {stats['grok']} vs SerpAPI {stats['serpapi']} ({stats['total']} total)\n")
        return

    try:
        sheets = get_sheets_service()
        logger.info("Google Sheets connected")
    except Exception as e:
        logger.error(f"Sheets connection failed: {e}")
        print(f"\n  ERROR: {e}\n")
        return

    show_status()

    if "--monitor" in sys.argv:
        run_monitor(sheets)
    else:
        process_all(sheets)

    print("=" * 60)
    print("  Done! Contacts filled → paste emails → set READY → run again.")
    print("  Or run --monitor to check replies and trigger follow-ups.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
