/**
 * Google Apps Script - Cold Email Automation Trigger
 * 
 * HOW TO INSTALL:
 * 1. In your Google Sheet, go to Extensions > Apps Script
 * 2. Paste this entire script
 * 3. Replace CLOUD_FUNCTION_URL with your deployed function URL
 * 4. Save and run setupTrigger() once
 * 5. Authorize the script when prompted
 * 
 * This script watches the "Cold Email" tab's Status column (B).
 * When you change it to FIND, READY, FU1, or FU2, it automatically
 * calls your Cloud Function to process that row.
 */

// Replace this with your actual Cloud Function URL after deployment
const CLOUD_FUNCTION_URL = "https://YOUR-REGION-YOUR-PROJECT.cloudfunctions.net/cold_email_automation";

// Sheet and column config
const COLD_EMAIL_TAB = "Cold Email";
const STATUS_COLUMN = 2;  // Column B

// Trigger statuses
const TRIGGER_STATUSES = ["FIND", "READY", "FU1", "FU2"];

/**
 * Run this ONCE to set up the automatic trigger.
 */
function setupTrigger() {
  // Remove existing triggers
  const triggers = ScriptApp.getProjectTriggers();
  for (const trigger of triggers) {
    if (trigger.getHandlerFunction() === 'onEdit') {
      ScriptApp.deleteTrigger(trigger);
    }
  }
  
  // Create new installable onEdit trigger
  ScriptApp.newTrigger('onStatusChange')
    .forSpreadsheet(SpreadsheetApp.getActive())
    .onEdit()
    .create();
    
  Logger.log("Trigger installed successfully!");
  SpreadsheetApp.getUi().alert("Trigger installed! The automation will now run when you change the Status column.");
}

/**
 * Triggered automatically when any cell is edited.
 * Only processes changes in the Cold Email tab's Status column.
 */
function onStatusChange(e) {
  try {
    const sheet = e.source.getActiveSheet();
    const range = e.range;
    
    // Only process Cold Email tab
    if (sheet.getName() !== COLD_EMAIL_TAB) return;
    
    // Only process Status column (B)
    if (range.getColumn() !== STATUS_COLUMN) return;
    
    const newValue = range.getValue().toString().trim().toUpperCase();
    const row = range.getRow();
    
    // Only trigger for specific statuses
    if (!TRIGGER_STATUSES.includes(newValue)) return;
    
    Logger.log(`Status changed to ${newValue} in row ${row}`);
    
    // Show processing indicator
    const notesCell = sheet.getRange(row, 16); // Column P (Notes)
    notesCell.setValue(`Processing ${newValue}...`);
    SpreadsheetApp.flush();
    
    // Call Cloud Function
    const payload = {
      action: newValue,
      row: row
    };
    
    const options = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(CLOUD_FUNCTION_URL, options);
    const responseCode = response.getResponseCode();
    const responseBody = response.getContentText();
    
    if (responseCode === 200) {
      Logger.log(`Success: ${responseBody}`);
    } else {
      Logger.log(`Error ${responseCode}: ${responseBody}`);
      notesCell.setValue(`Error: ${responseBody}`);
    }
    
  } catch (error) {
    Logger.log(`Script error: ${error.message}`);
  }
}

/**
 * Manual trigger - process all pending rows.
 * Run this from the Apps Script editor if needed.
 */
function processAll() {
  const options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify({ action: "ALL" }),
    muteHttpExceptions: true
  };
  
  const response = UrlFetchApp.fetch(CLOUD_FUNCTION_URL, options);
  Logger.log(`Process all: ${response.getContentText()}`);
  SpreadsheetApp.getUi().alert(`Result: ${response.getContentText()}`);
}

/**
 * Add a custom menu to the sheet for manual controls.
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('Cold Email')
    .addItem('Process All Pending', 'processAll')
    .addItem('Setup Trigger', 'setupTrigger')
    .addItem('Show Gmail Status', 'showGmailStatus')
    .addToUi();
}

/**
 * Show Gmail daily usage status.
 */
function showGmailStatus() {
  const options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify({ action: "STATUS" }),
    muteHttpExceptions: true
  };
  
  try {
    const response = UrlFetchApp.fetch(CLOUD_FUNCTION_URL, options);
    SpreadsheetApp.getUi().alert(response.getContentText());
  } catch (e) {
    SpreadsheetApp.getUi().alert("Could not reach the automation server. Is it deployed?");
  }
}
