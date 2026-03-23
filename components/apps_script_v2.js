/**
 * ReachOut-AI v2.0 — Google Apps Script
 *
 * AUTO-TRIGGER: Detects when a JD URL is pasted into the Universe tab
 * and automatically sets FIND status in the Cold Email tab.
 * No more manual FIND/READY typing.
 *
 * INSTALL:
 * 1. In your Google Sheet → Extensions → Apps Script
 * 2. Paste this entire script
 * 3. Replace CLOUD_FUNCTION_URL if using cloud deployment
 * 4. Run setupTriggers() once
 * 5. Authorize when prompted
 */

const UNIVERSE_TAB = "Universe";
const COLD_EMAIL_TAB = "Cold Email";
const JD_COLUMN = 7;          // Column G in Universe tab
const STATUS_COLUMN = 2;      // Column B in Cold Email tab
const TRIGGER_STATUSES = ["FIND", "READY", "FU1", "FU2"];

// Set to your Cloud Function URL if deployed, otherwise leave empty for local mode
const CLOUD_FUNCTION_URL = "";

/**
 * Run ONCE to set up all triggers.
 */
function setupTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  for (const trigger of triggers) {
    ScriptApp.deleteTrigger(trigger);
  }

  // Watch for edits (JD URL paste + manual status changes)
  ScriptApp.newTrigger('onSheetEdit')
    .forSpreadsheet(SpreadsheetApp.getActive())
    .onEdit()
    .create();

  Logger.log("Triggers installed!");
  SpreadsheetApp.getUi().alert("v2 triggers installed! Paste a JD URL to auto-trigger the pipeline.");
}

/**
 * Triggered on ANY edit. Routes to the right handler.
 */
function onSheetEdit(e) {
  try {
    const sheet = e.source.getActiveSheet();
    const range = e.range;
    const sheetName = sheet.getName();

    // ─── AUTO-TRIGGER: JD URL pasted in Universe tab ────────
    if (sheetName === UNIVERSE_TAB && range.getColumn() === JD_COLUMN) {
      const url = range.getValue().toString().trim();
      if (url.startsWith("http://") || url.startsWith("https://")) {
        autoTriggerFind(e.source, range.getRow(), url);
      }
      return;
    }

    // ─── MANUAL TRIGGER: Status changed in Cold Email tab ───
    if (sheetName === COLD_EMAIL_TAB && range.getColumn() === STATUS_COLUMN) {
      const newValue = range.getValue().toString().trim().toUpperCase();
      if (TRIGGER_STATUSES.includes(newValue)) {
        handleStatusChange(newValue, range.getRow(), sheet);
      }
      return;
    }
  } catch (error) {
    Logger.log("Edit handler error: " + error.message);
  }
}

/**
 * Auto-trigger FIND when a JD URL is pasted in Universe tab.
 * Creates/updates the corresponding Cold Email row.
 */
function autoTriggerFind(spreadsheet, universeRow, jdUrl) {
  const coldSheet = spreadsheet.getSheetByName(COLD_EMAIL_TAB);
  if (!coldSheet) return;

  // Check if this Universe row already has a Cold Email row
  const coldData = coldSheet.getRange("A2:A500").getValues();
  let targetRow = -1;
  for (let i = 0; i < coldData.length; i++) {
    if (coldData[i][0].toString().trim() === universeRow.toString()) {
      targetRow = i + 2; // +2 for 1-indexed + header
      break;
    }
  }

  if (targetRow === -1) {
    // Create new row
    targetRow = coldSheet.getLastRow() + 1;
    coldSheet.getRange(targetRow, 1).setValue(universeRow);
  }

  // Set status to FIND
  coldSheet.getRange(targetRow, 2).setValue("FIND");

  // Set notes
  coldSheet.getRange(targetRow, 16).setValue("Auto-triggered from JD URL paste");

  SpreadsheetApp.flush();
  Logger.log("Auto-triggered FIND for Universe row " + universeRow);

  // If cloud function is configured, call it
  if (CLOUD_FUNCTION_URL) {
    callCloudFunction("FIND", targetRow);
  }
}

/**
 * Handle manual status changes in Cold Email tab.
 */
function handleStatusChange(status, row, sheet) {
  const notesCell = sheet.getRange(row, 16);
  notesCell.setValue("Processing " + status + "...");
  SpreadsheetApp.flush();

  if (CLOUD_FUNCTION_URL) {
    callCloudFunction(status, row);
  } else {
    Logger.log(status + " triggered for row " + row + " (run python main.py to process)");
  }
}

/**
 * Call the Cloud Function (if deployed).
 */
function callCloudFunction(action, row) {
  if (!CLOUD_FUNCTION_URL) return;

  try {
    const response = UrlFetchApp.fetch(CLOUD_FUNCTION_URL, {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify({ action: action, row: row }),
      muteHttpExceptions: true,
    });
    Logger.log("Cloud function response: " + response.getContentText());
  } catch (e) {
    Logger.log("Cloud function call failed: " + e.message);
  }
}

/**
 * Manual: process all pending rows.
 */
function processAll() {
  if (CLOUD_FUNCTION_URL) {
    const response = UrlFetchApp.fetch(CLOUD_FUNCTION_URL, {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify({ action: "ALL" }),
      muteHttpExceptions: true,
    });
    SpreadsheetApp.getUi().alert(response.getContentText());
  } else {
    SpreadsheetApp.getUi().alert("Run 'python src/main.py' locally to process all pending rows.");
  }
}

/**
 * Custom menu.
 */
function onOpen() {
  SpreadsheetApp.getUi().createMenu('ReachOut AI v2')
    .addItem('Process All Pending', 'processAll')
    .addItem('Setup Triggers', 'setupTriggers')
    .addToUi();
}
