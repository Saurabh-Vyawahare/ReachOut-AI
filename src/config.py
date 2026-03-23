"""
ReachOut-AI v2.0 — Configuration
Dual-scout standoff, quality gate, business-day reply monitor.
APIs: Grok/xAI (Scout A) + SerpAPI + Anthropic Claude (Haiku + Sonnet)
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

CREDENTIALS_DIR = BASE_DIR / "credentials"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# ─── API Keys ────────────────────────────────────────────────
XAI_API_KEY = os.getenv("XAI_API_KEY")                      # Grok (Scout A)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")           # Claude (Haiku + Sonnet)
SERPAPI_KEY = os.getenv("SERPAPI_KEY")                        # SerpAPI (Scout B)

# ─── Model Configuration ─────────────────────────────────────
SCOUT_GROK_MODEL = "grok-4-1-fast-reasoning"                  # Scout A: web + X search
SCOUT_HAIKU_MODEL = "claude-haiku-4-5-20251001"               # Scout B parser + Validator + QG + JD Analyzer
EMAIL_GENERATOR_MODEL = "claude-sonnet-4-6"                   # Email composer (quality matters)
EMAIL_TEMPERATURE = 0.7

# ─── Google Sheets ───────────────────────────────────────────
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
UNIVERSE_TAB = "Universe"
COLD_EMAIL_TAB = "Cold Email"
STANDOFF_TAB = "Standoff Tracker"                             # NEW: logs Grok vs SerpAPI wins
JD_COLUMN = "G"

# ─── Credential Files ────────────────────────────────────────
SHEETS_SERVICE_ACCOUNT = str(CREDENTIALS_DIR / "sheets_service_account.json")
GMAIL_CLIENT_SECRET = str(CREDENTIALS_DIR / "gmail_client_secret.json")

# ─── Gmail Accounts ──────────────────────────────────────────
GMAIL_ACCOUNTS = [
    {"email": os.getenv("GMAIL_1"), "credentials_file": str(CREDENTIALS_DIR / "gmail_1_token.json"), "daily_cap": 10},
    {"email": os.getenv("GMAIL_2"), "credentials_file": str(CREDENTIALS_DIR / "gmail_2_token.json"), "daily_cap": 10},
    {"email": os.getenv("GMAIL_3"), "credentials_file": str(CREDENTIALS_DIR / "gmail_3_token.json"), "daily_cap": 10},
    {"email": os.getenv("GMAIL_4"), "credentials_file": str(CREDENTIALS_DIR / "gmail_4_token.json"), "daily_cap": 10},
]

# ─── Sheet Columns (v2 expanded) ─────────────────────────────
COLD_EMAIL_COLUMNS = {
    "A": "universe_row", "B": "status", "C": "company",
    "D": "job_title", "E": "location", "F": "sector",
    "G": "contact_1", "H": "contact_2", "I": "contact_3",
    "J": "email_1", "K": "email_2", "L": "email_3",
    "M": "reply_from", "N": "gmail_used", "O": "sent_date", "P": "notes",
    "Q": "scout_winner",       # NEW: "grok" or "serpapi"
    "R": "quality_score",      # NEW: avg quality gate score
    "S": "fu1_date",           # NEW: follow-up 1 scheduled date
    "T": "fu2_date",           # NEW: follow-up 2 scheduled date
}

STATUS = {
    "FIND": "FIND", "READY": "READY", "SENT": "SENT",
    "FOLLOW_UP_1": "FU1", "FOLLOW_UP_2": "FU2",
    "REPLIED": "REPLIED", "DONE": "DONE", "ERROR": "ERROR",
    # v2 new statuses
    "PROCESSING": "PROCESSING",
    "SCOUTING": "SCOUTING",
    "COMPOSING": "COMPOSING",
    "DRAFTS_READY": "DRAFTS_READY",
}

# ─── Contact Finder Settings ─────────────────────────────────
MAX_CONTACTS = 3
HIRING_MANAGER_TITLES = [
    "director", "senior director", "vp", "vice president",
    "head of", "senior manager", "manager", "lead",
    "principal", "staff", "senior lead"
]
RECRUITER_TITLES = [
    "recruiter", "talent acquisition", "ta partner",
    "ta manager", "recruiting", "talent partner",
    "people operations", "hr business partner"
]
DATA_DEPARTMENT_KEYWORDS = [
    "data", "analytics", "data science", "machine learning",
    "ml", "ai", "artificial intelligence", "business intelligence",
    "bi", "insights", "research", "quantitative", "statistics"
]

SECTOR_KEYWORDS = {
    "healthcare": [
        "health", "medical", "pharma", "biotech", "clinical",
        "hospital", "patient", "drug", "therapeutic", "fda",
        "claims", "hipaa", "ehr", "epic", "cerner", "meddra",
        "adverse event", "safety", "regulatory"
    ],
    "finance": [
        "bank", "fintech", "insurance", "investment", "credit",
        "trading", "portfolio", "risk", "compliance", "audit",
        "payment", "transaction", "wealth", "asset", "fund",
        "mortgage", "lending", "underwriting"
    ],
    "retail": [
        "retail", "e-commerce", "ecommerce", "cpg", "merchandise",
        "store", "shopping", "consumer", "brand", "product",
        "inventory", "supply chain", "fulfillment", "marketplace",
        "wholesale", "grocery"
    ],
    "tech": [
        "software", "saas", "platform", "cloud", "api",
        "developer", "engineering", "product", "startup",
        "tech", "digital", "automation", "devops"
    ]
}

# ─── Email Settings ──────────────────────────────────────────
MAX_EMAILS_PER_JOB = 3
FOLLOW_UP_1_BIZ_DAYS = 3                                     # v2: business days, not calendar
FOLLOW_UP_2_BIZ_DAYS = 6                                     # v2: 6 biz days after send

# ─── Quality Gate ────────────────────────────────────────────
QUALITY_GATE_MIN_SCORE = 7                                    # reject below this
QUALITY_GATE_MAX_RETRIES = 2                                  # max regeneration attempts

# ─── SerpAPI Settings ────────────────────────────────────────
SERPAPI_SEARCHES_PER_COMPANY = 2                              # LinkedIn + recruiter search

# ─── Sender Info ─────────────────────────────────────────────
SENDER_NAME = "Saurabh Vyawahare"
SENDER_PHONE = "857-230-7888"
SENDER_EMAIL = "saurabhvy.tech@gmail.com"
SENDER_LINKEDIN = "linkedin.com/in/saurabh-vyawahare"

SENDER_EXPERIENCE = """
- Survival analysis, XGBoost, LightGBM, logistic regression for predictive models
- Customer segmentation using k-means clustering on 1M+ records
- Churn prediction, retention analytics, customer lifetime value modeling
- A/B testing pipelines for pricing, promotions, campaign measurement
- Multi-touch attribution for marketing channel ROI
- Recommendation engines using collaborative filtering
- ETL/SQL pipelines, Snowflake, MongoDB, data migration
- Power BI and Tableau dashboards for stakeholder reporting
- NLP, vector search, RAG systems, OpenAI API integration
- Real-time ML monitoring (drift detection, latency, accuracy)
- Healthcare claims analysis, risk scoring, MedDRA mapping, compliance
"""
