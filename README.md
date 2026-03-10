# Cold Email Automation

Automated cold outreach system that finds contacts, generates personalized emails, and creates Gmail drafts — all triggered from a Google Sheet.

## What It Does

1. **You paste a job into your Google Sheet** (company, title, location, JD link)
2. **System finds contacts** using Apollo People API + Google/LinkedIn search
3. **You paste emails** (90 seconds on Apollo)
4. **System generates personalized emails** using AI with sector-specific resume points
5. **System creates Gmail drafts** across 4 accounts (10/account/day cap)
6. **Auto follow-ups** at 5 and 14 days for unreplied contacts

## Architecture

```
Google Sheet (Cold Email tab)
    │
    ├── Status: FIND → Contact Finder (Apollo API + Google LinkedIn Search)
    ├── Status: READY → Email Generator (OpenAI) → Gmail Drafter (4 accounts)
    ├── Status: FU1 → Follow-up #1 drafts (5-7 days)
    └── Status: FU2 → Follow-up #2 drafts (14 days)
```

## Tech Stack

- **Python** — Core automation logic
- **Apollo.io API** — Contact discovery (People Search, free tier)
- **Google Custom Search API** — LinkedIn profile discovery
- **OpenAI API (GPT-4o)** — Email generation with sector-specific content
- **Google Sheets API** — Read/write job data
- **Gmail API** — Create drafts across multiple accounts
- **Google Cloud Functions** — Serverless deployment (optional)

## Sheet Structure

### Universe Tab (existing)
| A | B | C | D | E | F | G (NEW) |
|---|---|---|---|---|---|---------|
| Company | Job Title | Date | Location | Status | Resume Ver | JD Link/Text |

### Cold Email Tab (new)
| Col | Header | Filled By |
|-----|--------|-----------|
| A | Universe Row # | You |
| B | Status | You (dropdown) |
| C-E | Company, Title, Location | Auto |
| F | Sector | Auto |
| G-I | Contact 1-3 | Auto |
| J-L | Email 1-3 | You (Apollo) |
| M | Reply From | You |
| N | Gmail Used | Auto |
| O | Sent Date | Auto |
| P | Notes | Auto |

### Status Flow
`FIND` → `READY` → `SENT` → `FU1` → `FU2` → `REPLIED` / `DONE`

## Setup

### 1. Clone and Install
```bash
git clone https://github.com/YOUR_USERNAME/cold-email-automation.git
cd cold-email-automation
pip install -r requirements.txt
```

### 2. API Keys
```bash
cp .env.example .env
# Fill in all API keys (see Setup Guide below)
```

### 3. Google Cloud Setup
- Create project at console.cloud.google.com
- Enable: Sheets API, Gmail API, Custom Search API
- Create Service Account for Sheets
- Create OAuth Client for Gmail
- Download credentials to `credentials/` folder

### 4. Verify Setup
```bash
python setup_check.py
```

### 5. Run
```bash
python main.py           # Process all pending rows
python main.py --status  # Show Gmail usage
```

## Deployment (Google Cloud Functions)

For hands-free operation where typing FIND/READY in the sheet auto-triggers processing:

1. Deploy the Cloud Function
2. Paste `apps_script.js` into your Google Sheet (Extensions > Apps Script)
3. Run `setupTrigger()` once
4. Done — status changes now trigger automatically

## Email Generation

Emails follow a structured anti-spam approach:
- **Sector detection** — Healthcare, Finance, Retail, or Tech
- **Resume points** — Matched to JD requirements using sector-specific experience
- **Variation rotation** — Different subject lines, transitions, CTAs across a batch
- **Company size logic** — Large enterprise prioritizes hiring managers; small companies go direct to founders
- **No attachments** — Resume offered at end, sent only if they reply

## Cost

| Service | Cost |
|---------|------|
| Apollo People Search API | Free (no credits consumed) |
| Google Custom Search | Free (100 queries/day) |
| Google Sheets API | Free |
| Gmail API | Free |
| OpenAI API | ~$0.01-0.03 per email |
| Google Cloud Functions | Free (2M invocations/month) |

**Total: ~$0.50-1.00/day** for 12 jobs × 3 emails each.

## License

MIT
