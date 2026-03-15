"""
Cold Email Automation - Configuration
Dual API: Grok/xAI (contact finding) + Anthropic Claude (email generation)
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
XAI_API_KEY = os.getenv("XAI_API_KEY")                      # Grok (contact finding + web/X search)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")           # Claude (email generation)

# ─── Model Configuration ─────────────────────────────────────
CONTACT_FINDER_MODEL = "grok-4-1-fast-reasoning"              # $0.20/$0.50 per M + $5/1K searches
EMAIL_GENERATOR_MODEL = "claude-sonnet-4-6"                   # Best email quality
EMAIL_TEMPERATURE = 0.7

# ─── Google Sheets ───────────────────────────────────────────
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
UNIVERSE_TAB = "Universe"
COLD_EMAIL_TAB = "Cold Email"
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

# ─── Sheet Columns ───────────────────────────────────────────
COLD_EMAIL_COLUMNS = {
    "A": "universe_row", "B": "status", "C": "company",
    "D": "job_title", "E": "location", "F": "sector",
    "G": "contact_1", "H": "contact_2", "I": "contact_3",
    "J": "email_1", "K": "email_2", "L": "email_3",
    "M": "reply_from", "N": "gmail_used", "O": "sent_date", "P": "notes",
}

STATUS = {
    "FIND": "FIND", "READY": "READY", "SENT": "SENT",
    "FOLLOW_UP_1": "FU1", "FOLLOW_UP_2": "FU2",
    "REPLIED": "REPLIED", "DONE": "DONE", "ERROR": "ERROR",
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

MAX_EMAILS_PER_JOB = 3
FOLLOW_UP_1_DAYS = 5
FOLLOW_UP_2_DAYS = 14

SENDER_NAME = "Saurabh Vyawahare"
SENDER_PHONE = "857-230-7888"
SENDER_EMAIL = "saurabhvy.tech@gmail.com"
SENDER_LINKEDIN = "linkedin.com/in/saurabh-vyawahare"
