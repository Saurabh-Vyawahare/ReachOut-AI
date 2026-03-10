"""
Google Cloud Function Entry Point
This is the serverless version that gets triggered by Google Apps Script
when you change the status in your Cold Email sheet.

Deploy with:
    gcloud functions deploy cold_email_automation \
        --runtime python312 \
        --trigger-http \
        --allow-unauthenticated \
        --entry-point handle_request \
        --timeout 120
"""
import json
import logging
import functions_framework
from main import process_find, process_ready, process_follow_up
from sheets_handler import get_sheets_service, read_cold_email_rows
from config import STATUS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@functions_framework.http
def handle_request(request):
    """
    HTTP Cloud Function entry point.
    Called by Google Apps Script when status changes in the sheet.

    Expected JSON body:
    {
        "action": "FIND" | "READY" | "FU1" | "FU2",
        "row": 5  // Optional: specific row to process
    }
    """
    try:
        request_json = request.get_json(silent=True)
        action = request_json.get("action", "ALL") if request_json else "ALL"
        target_row = request_json.get("row") if request_json else None

        sheets = get_sheets_service()

        if target_row:
            # Process specific row
            rows = read_cold_email_rows(sheets)
            matching = [r for r in rows if r["sheet_row"] == target_row]
            if not matching:
                return json.dumps({"status": "error", "message": f"Row {target_row} not found"}), 404

            row = matching[0]
            if row["status"] == STATUS["FIND"]:
                process_find(sheets, row)
            elif row["status"] == STATUS["READY"]:
                process_ready(sheets, row)
            elif row["status"] == STATUS["FOLLOW_UP_1"]:
                process_follow_up(sheets, row, 1)
            elif row["status"] == STATUS["FOLLOW_UP_2"]:
                process_follow_up(sheets, row, 2)

            return json.dumps({"status": "ok", "processed": target_row}), 200

        else:
            # Process all pending
            rows = read_cold_email_rows(sheets)

            processed = 0
            for row in rows:
                if row["status"] == STATUS["FIND"]:
                    process_find(sheets, row)
                    processed += 1
                elif row["status"] == STATUS["READY"]:
                    process_ready(sheets, row)
                    processed += 1
                elif row["status"] == STATUS["FOLLOW_UP_1"]:
                    process_follow_up(sheets, row, 1)
                    processed += 1
                elif row["status"] == STATUS["FOLLOW_UP_2"]:
                    process_follow_up(sheets, row, 2)
                    processed += 1

            return json.dumps({"status": "ok", "processed": processed}), 200

    except Exception as e:
        logger.error(f"Cloud Function error: {e}")
        return json.dumps({"status": "error", "message": str(e)}), 500
