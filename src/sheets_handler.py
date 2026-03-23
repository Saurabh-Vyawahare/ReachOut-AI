"""
Google Sheets Handler Module
Reads from Universe tab, reads/writes Cold Email tab.
Uses Google Sheets API v4.
"""
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from config import SPREADSHEET_ID, UNIVERSE_TAB, COLD_EMAIL_TAB, SHEETS_SERVICE_ACCOUNT

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_sheets_service(credentials_file: str = None):
    """Initialize Google Sheets API service."""
    if credentials_file is None:
        credentials_file = SHEETS_SERVICE_ACCOUNT
    creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)
    return service.spreadsheets()


def read_universe_row(sheets, row_number: int) -> dict:
    """
    Read a row from the Universe tab.
    Returns: {company, job_title, date, location, jd_input}
    """
    range_str = f"'{UNIVERSE_TAB}'!A{row_number}:G{row_number}"
    try:
        result = sheets.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_str
        ).execute()
        values = result.get("values", [[]])[0]

        # Pad to 7 columns if needed
        while len(values) < 7:
            values.append("")

        return {
            "company": values[0].strip() if values[0] else "",
            "job_title": values[1].strip() if values[1] else "",
            "date": values[2].strip() if values[2] else "",
            "location": values[3].strip() if values[3] else "",
            "status": values[4].strip() if values[4] else "",
            "resume_version": values[5].strip() if values[5] else "",
            "jd_input": values[6].strip() if values[6] else "",
        }
    except Exception as e:
        logger.error(f"Failed to read Universe row {row_number}: {e}")
        return None


def read_cold_email_rows(sheets, status_filter: str = None) -> list[dict]:
    """
    Read all rows from Cold Email tab.
    If status_filter is provided, only return rows matching that status.
    """
    range_str = f"'{COLD_EMAIL_TAB}'!A2:P500"
    try:
        result = sheets.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_str
        ).execute()
        rows = result.get("values", [])

        parsed = []
        for i, row in enumerate(rows, start=2):
            # Pad to 16 columns
            while len(row) < 16:
                row.append("")

            row_data = {
                "sheet_row": i,
                "universe_row": row[0].strip() if row[0] else "",
                "status": row[1].strip().upper() if row[1] else "",
                "company": row[2].strip() if row[2] else "",
                "job_title": row[3].strip() if row[3] else "",
                "location": row[4].strip() if row[4] else "",
                "sector": row[5].strip() if row[5] else "",
                "contact_1": row[6].strip() if row[6] else "",
                "contact_2": row[7].strip() if row[7] else "",
                "contact_3": row[8].strip() if row[8] else "",
                "email_1": row[9].strip() if row[9] else "",
                "email_2": row[10].strip() if row[10] else "",
                "email_3": row[11].strip() if row[11] else "",
                "reply_from": row[12].strip() if row[12] else "",
                "gmail_used": row[13].strip() if row[13] else "",
                "sent_date": row[14].strip() if row[14] else "",
                "notes": row[15].strip() if row[15] else "",
            }

            if status_filter and row_data["status"] != status_filter.upper():
                continue

            parsed.append(row_data)

        return parsed

    except Exception as e:
        logger.error(f"Failed to read Cold Email tab: {e}")
        return []


def update_cold_email_row(sheets, row_number: int, updates: dict):
    """
    Update specific columns in a Cold Email row.
    updates: dict mapping column letter to value, e.g. {"G": "John - Director"}
    """
    column_map = {
        "A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5,
        "G": 6, "H": 7, "I": 8, "J": 9, "K": 10, "L": 11,
        "M": 12, "N": 13, "O": 14, "P": 15
    }

    for col_letter, value in updates.items():
        col_index = column_map.get(col_letter.upper())
        if col_index is None:
            continue

        cell_range = f"'{COLD_EMAIL_TAB}'!{col_letter.upper()}{row_number}"
        try:
            sheets.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=cell_range,
                valueInputOption="USER_ENTERED",
                body={"values": [[value]]}
            ).execute()
        except Exception as e:
            logger.error(f"Failed to update {cell_range}: {e}")


def write_cold_email_row(sheets, row_number: int, data: dict):
    """
    Write a complete Cold Email row.
    data should have keys matching column names from config.
    """
    row_values = [
        data.get("universe_row", ""),
        data.get("status", ""),
        data.get("company", ""),
        data.get("job_title", ""),
        data.get("location", ""),
        data.get("sector", ""),
        data.get("contact_1", ""),
        data.get("contact_2", ""),
        data.get("contact_3", ""),
        data.get("email_1", ""),
        data.get("email_2", ""),
        data.get("email_3", ""),
        data.get("reply_from", ""),
        data.get("gmail_used", ""),
        data.get("sent_date", ""),
        data.get("notes", ""),
    ]

    range_str = f"'{COLD_EMAIL_TAB}'!A{row_number}:P{row_number}"
    try:
        sheets.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_str,
            valueInputOption="USER_ENTERED",
            body={"values": [row_values]}
        ).execute()
        logger.info(f"Wrote Cold Email row {row_number}")
    except Exception as e:
        logger.error(f"Failed to write row {row_number}: {e}")


def fill_contacts(sheets, row_number: int, contacts: list,
                  sector: str, notes: str):
    """
    Fill contacts and metadata into Cold Email row.
    Called after contact finder runs.
    """
    updates = {
        "F": sector.capitalize(),
        "P": notes,
    }

    # Fill up to 3 contacts
    contact_cols = ["G", "H", "I"]
    for i, contact in enumerate(contacts[:3]):
        updates[contact_cols[i]] = contact.display_string()

    update_cold_email_row(sheets, row_number, updates)
    logger.info(f"Filled contacts for row {row_number}")


def fill_job_info(sheets, row_number: int, universe_data: dict):
    """
    Auto-fill company, title, location from Universe row.
    """
    updates = {
        "C": universe_data.get("company", ""),
        "D": universe_data.get("job_title", ""),
        "E": universe_data.get("location", ""),
    }
    update_cold_email_row(sheets, row_number, updates)


def check_duplicate(sheets, email: str) -> bool:
    """
    Check if an email address has been used before
    across all Cold Email rows.
    """
    rows = read_cold_email_rows(sheets)
    for row in rows:
        for field in [row["email_1"], row["email_2"], row["email_3"]]:
            if field.lower().strip() == email.lower().strip():
                return True
    return False


def get_next_empty_row(sheets) -> int:
    """Find the next empty row in Cold Email tab."""
    range_str = f"'{COLD_EMAIL_TAB}'!A:A"
    try:
        result = sheets.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_str
        ).execute()
        values = result.get("values", [])
        return len(values) + 1
    except Exception as e:
        logger.error(f"Failed to get next empty row: {e}")
        return 2  # Default to row 2 (after header)


# ─── v2 Extensions ──────────────────────────────────────────

def update_standoff_result(sheets, row_number: int, winner: str, quality_score: float):
    """Update the scout winner and quality score columns."""
    update_cold_email_row(sheets, row_number, {
        "Q": winner,
        "R": str(round(quality_score, 1)),
    })


def update_follow_up_dates(sheets, row_number: int, fu1_date: str, fu2_date: str):
    """Set scheduled follow-up dates."""
    update_cold_email_row(sheets, row_number, {
        "S": fu1_date,
        "T": fu2_date,
    })


def log_standoff_to_sheet(sheets, company: str, winner: str, reason: str):
    """Log standoff result to the Standoff Tracker tab."""
    from config import SPREADSHEET_ID, STANDOFF_TAB
    from datetime import datetime
    try:
        range_str = f"'{STANDOFF_TAB}'!A:D"
        result = sheets.values().get(spreadsheetId=SPREADSHEET_ID, range=range_str).execute()
        next_row = len(result.get("values", [])) + 1

        sheets.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{STANDOFF_TAB}'!A{next_row}:D{next_row}",
            valueInputOption="USER_ENTERED",
            body={"values": [[datetime.now().isoformat(), company, winner, reason]]}
        ).execute()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Standoff log to sheet failed: {e}")
