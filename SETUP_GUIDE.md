# Setup Guide — Cold Email Automation

Follow these steps in order. Total time: ~30 minutes.

---

## Step 1: Google Cloud Project (5 min)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click "Select a Project" > "New Project"
3. Name: `cold-email-automation`
4. Click "Create"
5. Make sure the new project is selected

### Enable APIs:
Go to "APIs & Services" > "Library" and enable:
- **Google Sheets API**
- **Gmail API**
- **Custom Search API**

---

## Step 2: Google Sheets Service Account (5 min)

This lets the script read/write your Google Sheet without your browser being open.

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Name: `sheets-reader`
4. Click "Create and Continue" > "Done"
5. Click on the service account you just created
6. Go to "Keys" tab > "Add Key" > "Create new key" > JSON
7. Download the file
8. Rename it to `sheets_service_account.json`
9. Put it in the `credentials/` folder

### Share your Google Sheet:
1. Open the downloaded JSON file, find the `client_email` field
2. Open your Job Applications Sheet in Google Sheets
3. Click "Share" > paste the service account email > "Editor" > "Share"

---

## Step 3: Gmail OAuth (10 min)

This lets the script create drafts in your Gmail accounts.

1. In Google Cloud Console > "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If asked for consent screen: choose "External", fill in app name, your email, save
4. Application type: "Desktop app"
5. Name: `cold-email-gmail`
6. Click "Create"
7. Download the JSON
8. Rename to `gmail_client_secret.json`
9. Put it in the `credentials/` folder

### First-time Gmail auth:
When you run `python main.py` for the first time, it will open a browser window
for EACH Gmail account asking you to authorize. Do this once per account.
The tokens are saved so you won't need to do it again.

**Important:** You need to authorize all 4 Gmail accounts. The script will prompt
you one at a time.

---

## Step 4: Apollo API Key (2 min)

1. Go to [app.apollo.io](https://app.apollo.io)
2. Log in (free account works)
3. Go to Settings (gear icon) > "API Keys" (under Integrations)
4. Click "Create API Key"
5. Copy the key
6. Paste into `.env` as `APOLLO_API_KEY`

---

## Step 5: Google Custom Search Engine (5 min)

This is for searching LinkedIn profiles via Google.

### Create the Search Engine:
1. Go to [programmablesearchengine.google.com](https://programmablesearchengine.google.com)
2. Click "Add" (or "New Search Engine")
3. Sites to search: `linkedin.com/in/*`
4. Name: `linkedin-search`
5. Click "Create"
6. Copy the "Search engine ID" (cx value)
7. Paste into `.env` as `GOOGLE_CSE_ID`

### Get the API Key:
1. Go back to Google Cloud Console > "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "API Key"
3. Copy the key
4. Paste into `.env` as `GOOGLE_CSE_API_KEY`

**Optional:** Restrict the API key to only Custom Search API for security.

---

## Step 6: OpenAI API Key (2 min)

1. Go to [platform.openai.com](https://platform.openai.com)
2. Click your profile > "API Keys"
3. Create a new key
4. Paste into `.env` as `OPENAI_API_KEY`

You already have this from AutoGuard, so use the same key.

---

## Step 7: Google Sheet ID (1 min)

1. Open your Job Applications Sheet
2. Look at the URL: `https://docs.google.com/spreadsheets/d/XXXXXX/edit`
3. The `XXXXXX` part is your Sheet ID
4. Paste into `.env` as `SPREADSHEET_ID`

---

## Step 8: Create the Cold Email Tab

In your Job Applications Sheet:

1. Click the "+" button at the bottom to add a new sheet tab
2. Name it exactly: `Cold Email`
3. Add headers in Row 1:

| A | B | C | D | E | F | G | H | I | J | K | L | M | N | O | P |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Row # | Status | Company | Job Title | Location | Sector | Contact 1 | Contact 2 | Contact 3 | Email 1 | Email 2 | Email 3 | Reply From | Gmail Used | Sent Date | Notes |

4. Set up Data Validation for column B (Status):
   - Select column B (from B2 downward)
   - Go to Data > Data validation
   - Criteria: "List of items"
   - Enter: `FIND,READY,SENT,FU1,FU2,REPLIED,DONE,ERROR`
   - Click "Save"

5. Add column G to your Universe tab header: `JD Link`

---

## Step 9: Add Gmail Accounts to .env

```
GMAIL_1=your.first.email@gmail.com
GMAIL_2=your.second.email@gmail.com
GMAIL_3=your.third.email@gmail.com
GMAIL_4=your.fourth.email@gmail.com
```

---

## Step 10: Verify Everything

```bash
mkdir -p credentials data
python setup_check.py
```

All checks should pass. If any fail, the checker tells you exactly what to fix.

---

## Step 11: First Run

```bash
python main.py
```

The first run will:
1. Open a browser for Gmail auth (do this for each account)
2. Connect to your Google Sheet
3. Look for rows with FIND or READY status
4. Process them

---

## Step 12: Deploy to Google Cloud Functions (Optional)

For auto-triggering when you change the status in the sheet:

```bash
# Install gcloud CLI if needed
# https://cloud.google.com/sdk/docs/install

gcloud auth login
gcloud config set project cold-email-automation

# Deploy
gcloud functions deploy cold_email_automation \
    --runtime python312 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point handle_request \
    --source . \
    --timeout 120 \
    --set-env-vars APOLLO_API_KEY=xxx,GOOGLE_CSE_API_KEY=xxx,...

# Note the URL it gives you
```

Then paste `apps_script.js` into your Google Sheet:
1. Extensions > Apps Script
2. Paste the code
3. Replace `CLOUD_FUNCTION_URL` with your function URL
4. Run `setupTrigger()` once
5. Authorize when prompted

Done. Now typing FIND/READY in the sheet auto-processes.

---

## Troubleshooting

**"Could not connect to Google Sheets"**
- Check that `sheets_service_account.json` is in `credentials/`
- Check that you shared the Google Sheet with the service account email

**"Apollo search returned 0 results"**
- The company name might be different in Apollo's database
- Try the exact company name as it appears on LinkedIn

**"Gmail auth failed"**
- Delete the token file in `credentials/` and re-authorize
- Make sure the Gmail account has "less secure app access" or OAuth is set up

**"JD fetch failed"**
- The URL might be behind a login wall (JobRight, some LinkedIn pages)
- Paste the JD text directly into Universe column G instead

**"All Gmail accounts at capacity"**
- You've hit 40 emails for the day (10 per account)
- Wait until tomorrow or add more Gmail accounts
