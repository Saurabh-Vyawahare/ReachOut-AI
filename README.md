# ReachOut-AI

AI-powered cold outreach automation that finds the right people to contact, generates personalized emails, and creates Gmail drafts — all triggered from a Google Sheet.

## The Problem

Cold outreach for job hunting is painfully manual. For every job you apply to, you need to find the hiring manager, research the team, craft a personalized email, and repeat this 3x per job across multiple Gmail accounts. At 12 jobs/day, that's 36 emails — easily 4-5 hours of repetitive work.

## The Solution

ReachOut-AI reduces that to **under 3 minutes per job**. You paste a job into a Google Sheet, the system finds the right contacts using AI-powered web search, generates personalized emails following anti-spam best practices, and saves drafts across your Gmail accounts — ready to review and send.

## How It Works

```
Google Sheet (you type a row number + "FIND")
       │
       ▼
┌─────────────────────────────────────────┐
│  1. JD Fetcher                          │
│     Fetches job description from URL    │
│     (Greenhouse, Lever, Workday, etc.)  │
│     Auto-detects industry sector        │
│                                         │
│  2. Contact Finder (Claude Web Search)  │
│     Searches LinkedIn + web for people  │
│     Applies company-size strategy       │
│     Returns top 3 ranked contacts       │
│                                         │
│  3. Email Generator (Claude AI)         │
│     Sector-specific resume matching     │
│     Anti-spam variation rotation        │
│     Different templates per role type   │
│                                         │
│  4. Gmail Drafter                       │
│     Creates drafts across 4 accounts    │
│     10/account/day cap (anti-spam)      │
│     Auto-rotates accounts               │
└─────────────────────────────────────────┘
       │
       ▼
  Gmail Drafts ready to review and send
```

## Features

**Intelligent Contact Discovery**
- AI-powered web search finds hiring managers, recruiters, and team members
- Company size detection (enterprise vs mid-size vs startup) adjusts contact strategy
- Large companies: prioritizes hiring managers over generic recruiters
- Small companies: targets founders and department heads
- Identifies name-drop candidates for personalized openers

**Smart Email Generation**
- Auto-detects job sector (Healthcare, Finance, Retail, Tech)
- Selects sector-specific experience points matched to JD requirements
- Anti-spam variation rotation: no two emails in a batch share the same subject line, transition, CTA, or resume offer
- Different templates for hiring managers vs recruiters vs staffing agencies
- Numbered points format (not bullets) to avoid spam filters

**Gmail Draft Management**
- Distributes drafts across multiple Gmail accounts
- 10 drafts/account/day cap to avoid spam flags
- Auto-rotates to next account when cap is hit
- Daily usage tracking with visual status bar

**Follow-up Automation**
- First follow-up (5-7 days): gentle bump
- Final follow-up (14 days): last note
- Only follows up with contacts who haven't replied
- Creates drafts as replies to the original email thread

**Duplicate Detection**
- Checks if a contact email was used in previous outreach
- Warns before creating duplicate drafts

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Engine | Anthropic Claude API (Sonnet/Opus) |
| Contact Search | Claude Web Search Tool |
| Email Generation | Claude with structured prompting |
| Data Layer | Google Sheets API v4 |
| Email Drafts | Gmail API (OAuth 2.0) |
| JD Parsing | BeautifulSoup + requests |
| Deployment | Google Cloud Functions (serverless) |
| Language | Python 3.12 |

## Project Structure

```
ReachOut-AI/
├── src/
│   ├── main.py              # Orchestrator — processes all triggers
│   ├── config.py             # Settings, API keys, constants
│   ├── contact_finder.py     # Claude web search for contacts
│   ├── email_generator.py    # AI email generation with variation pools
│   ├── gmail_drafter.py      # Gmail draft creation with account rotation
│   ├── jd_fetcher.py         # JD fetching from career pages
│   ├── sheets_handler.py     # Google Sheets read/write
│   └── cloud_function.py     # Serverless deployment wrapper
├── components/
│   └── apps_script.js        # Google Apps Script for sheet triggers
├── credentials/              # API credentials (gitignored)
├── data/                     # Usage logs (gitignored)
├── .env                      # API keys (gitignored)
├── .env.example              # Template for environment variables
├── setup_check.py            # Validates all credentials
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Poetry configuration
└── README.md
```

## Setup

### Prerequisites
- Python 3.12+
- Google Cloud account (free tier)
- Anthropic API account ($5 credit included for new users)
- 1-4 Gmail accounts for outreach

### Installation

```bash
git clone https://github.com/yourusername/ReachOut-AI.git
cd ReachOut-AI
poetry install --no-root
cp .env.example .env
# Fill in your API keys in .env
```

### Google Cloud Setup

1. Create a project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable **Google Sheets API** and **Gmail API**
3. Create a **Service Account** for Sheets access → download JSON to `credentials/sheets_service_account.json`
4. Create an **OAuth Client** (Desktop app) for Gmail → download JSON to `credentials/gmail_client_secret.json`
5. Share your Google Sheet with the service account email (Editor access)

### Configuration

```env
# .env
ANTHROPIC_API_KEY=your_key_here
SPREADSHEET_ID=your_google_sheet_id
GMAIL_1=first@gmail.com
GMAIL_2=second@gmail.com
GMAIL_3=third@gmail.com
GMAIL_4=fourth@gmail.com
```

### Verify Setup

```bash
poetry run python setup_check.py
```

## Usage

### Google Sheet Setup

Create a tab called **"Cold Email"** with these headers:

| Col | Header | Filled By |
|-----|--------|-----------|
| A | Row # | You |
| B | Status | You (dropdown) |
| C-E | Company, Title, Location | Auto |
| F | Sector | Auto |
| G-I | Contact 1-3 | Auto |
| J-L | Email 1-3 | You |
| M | Reply From | You |
| N-P | Gmail Used, Sent Date, Notes | Auto |

Status dropdown values: `FIND → READY → SENT → FU1 → FU2 → REPLIED → DONE`

### Workflow

```bash
# Step 1: Add a row with job reference number and set status to FIND
# Step 2: System finds contacts automatically
poetry run python src/main.py

# Step 3: Paste contact emails into the sheet, change status to READY
# Step 4: System generates emails and creates Gmail drafts
poetry run python src/main.py

# Step 5: Review drafts in Gmail, send manually, change status to SENT
# Step 6: After 5 days with no reply, change to FU1 for follow-ups
# Step 7: After 14 days, change to FU2 for final follow-up
```

### Check Daily Status

```bash
poetry run python src/main.py --status
```

## Email Generation Strategy

The system implements a structured anti-spam approach:

- **Sector Detection**: Automatically classifies jobs into Healthcare, Finance, Retail, or Tech based on JD keywords
- **Resume Matching**: Selects 2-3 experience points most relevant to the JD from a sector-specific pool
- **Variation Rotation**: Each email in a batch uses different subject lines, transition phrases, CTAs, and resume offer lines
- **Role-Based Templates**: Hiring managers get confident direct openers; recruiters get softer language with referral requests
- **Company Size Logic**: Large enterprises → skip generic recruiters; startups → contact founders directly

## Cost

| Service | Monthly Cost |
|---------|-------------|
| Anthropic Claude API | ~$8-15 (12 jobs/day) |
| Google Sheets API | Free |
| Gmail API | Free |
| Google Cloud Functions | Free (2M invocations/month) |

**Total: ~$8-15/month** for fully automated cold outreach.

## Deployment (Serverless)

Deploy to Google Cloud Functions for hands-free operation:

```bash
gcloud functions deploy reachout_ai \
    --runtime python312 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point handle_request \
    --source . \
    --timeout 120
```

Then paste `components/apps_script.js` into your Google Sheet (Extensions → Apps Script) to auto-trigger on status changes.

## Roadmap

- [x] Contact discovery via AI web search
- [x] Personalized email generation with anti-spam rotation
- [x] Gmail draft creation with multi-account rotation
- [x] Follow-up automation
- [x] Duplicate detection
- [ ] Streamlit analytics dashboard
- [ ] Email open/click tracking
- [ ] Response rate analytics by sector and company size
- [ ] A/B testing for email variations

## License

MIT
