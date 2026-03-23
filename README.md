# ReachOut-AI v2.0

Multi-agent cold email automation with dual-scout standoff, quality gates, and business-day follow-ups.

## Project Structure

```
ReachOut-AI/
│
├── src/                          # Python backend — all AI agents
│   ├── config.py                 # Settings, API keys, model config
│   ├── contact.py                # Contact model (shared)
│   ├── jd_analyzer.py            # JD fetcher + Haiku skill mapper
│   ├── scout_grok.py             # Scout A: Grok web + X search
│   ├── scout_serpapi.py          # Scout B: SerpAPI + Haiku parser
│   ├── validator.py              # Standoff judge + 30-day tracker
│   ├── email_generator.py        # Sonnet email composer
│   ├── quality_gate.py           # Haiku email scorer (1-10)
│   ├── gmail_drafter.py          # Round-robin Gmail drafts
│   ├── reply_monitor.py          # Business day follow-up logic
│   ├── sheets_handler.py         # Google Sheets read/write
│   ├── auth.py                   # Supabase JWT verification
│   ├── main.py                   # CLI orchestrator
│   └── reauth_gmail.py           # Gmail token re-authorization
│
├── frontend/                     # React dashboard
│   ├── src/
│   │   ├── components/           # Sidebar, WorkflowCanvas, etc.
│   │   ├── views/                # Landing, Auth, Dashboard, Pipeline, Chat
│   │   ├── data/                 # API client, Supabase client, mock data
│   │   ├── App.jsx               # Main app with routing
│   │   ├── main.jsx              # Entry point
│   │   └── index.css             # Tailwind + theme
│   ├── public/                   # Static assets
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── credentials/                  # Google service account + Gmail tokens
│   ├── sheets_service_account.json
│   ├── gmail_client_secret.json
│   ├── gmail_1_token.json
│   ├── gmail_2_token.json
│   ├── gmail_3_token.json
│   └── gmail_4_token.json
│
├── data/                         # Runtime data (logs, usage tracking)
│   ├── automation_v2.log
│   ├── gmail_usage.json
│   ├── gmail_rotation.json
│   └── standoff_log.json
│
├── components/                   # Google Apps Script
│   └── apps_script_v2.js
│
├── server.py                     # FastAPI backend server
├── setup_check.py                # Verify all credentials
├── requirements.txt              # Python dependencies
├── .env                          # Your API keys (not committed)
├── .env.example                  # Template for .env
├── .gitignore
├── Dockerfile                    # Railway deployment
├── railway.toml                  # Railway config
└── Procfile                      # Railway process file
```

## Quick Start

### 1. Backend setup
```bash
pip install -r requirements.txt
cp .env.example .env              # Fill in your API keys
python setup_check.py             # Verify everything
```

### 2. Run the pipeline (CLI)
```bash
cd src
python main.py                    # Process all FIND/READY rows
python main.py --status           # Gmail health + standoff stats
python main.py --monitor          # Check replies + trigger follow-ups
```

### 3. Frontend setup
```bash
cd frontend
npm install
npm run dev                       # Starts on http://localhost:5173
```

### 4. API server (connects frontend to backend)
```bash
python server.py                  # Starts on http://localhost:8000
```

### 5. Gmail re-authorization (if tokens expire)
```bash
cd src
python reauth_gmail.py            # One account at a time, no mixups
```

## Architecture

```
JD URL → JD Analyzer (Haiku) → Scout A (Grok) ──┐
                                Scout B (SerpAPI) ─┤→ Validator (Haiku)
                                                    → Email Composer (Sonnet)
                                                    → Quality Gate (Haiku)
                                                    → Gmail Dispatcher
                                                    → Reply Monitor
```

## Costs

| Agent | Model | Cost/company |
|-------|-------|-------------|
| JD Analyzer | Haiku | ~$0.003 |
| Scout A | Grok 4.1 Fast | ~$0.004 |
| Scout B | SerpAPI + Haiku | ~$0.007 |
| Validator | Haiku | ~$0.002 |
| Composer | Sonnet 4.6 | ~$0.015 |
| Quality Gate | Haiku | ~$0.003 |
| **Total** | | **~$0.03** |
