"""
Cold Email Automation - Configuration
All settings, API keys, and constants live here.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── API Keys ────────────────────────────────────────────────
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
GOOGLE_CSE_API_KEY = os.getenv("GOOGLE_CSE_API_KEY")       # Google Custom Search
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")                 # Custom Search Engine ID
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")                # For email generation

# ─── Google Sheets ───────────────────────────────────────────
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")                # Your Job Applications Sheet ID
UNIVERSE_TAB = "Universe"                                    # Main job tracking tab
COLD_EMAIL_TAB = "Cold Email"                               # Cold outreach tab
JD_COLUMN = "G"                                             # Column in Universe tab for JD link/text

# ─── Gmail Accounts (Priority Order) ─────────────────────────
# The system rotates through these, 10 drafts max per account
GMAIL_ACCOUNTS = [
    {
        "email": os.getenv("GMAIL_1"),
        "credentials_file": "credentials/gmail_1_token.json",
        "daily_cap": 10
    },
    {
        "email": os.getenv("GMAIL_2"),
        "credentials_file": "credentials/gmail_2_token.json",
        "daily_cap": 10
    },
    {
        "email": os.getenv("GMAIL_3"),
        "credentials_file": "credentials/gmail_3_token.json",
        "daily_cap": 10
    },
    {
        "email": os.getenv("GMAIL_4"),
        "credentials_file": "credentials/gmail_4_token.json",
        "daily_cap": 10
    },
]

# ─── Cold Email Sheet Column Mapping ─────────────────────────
# Cold Email tab structure
COLD_EMAIL_COLUMNS = {
    "A": "universe_row",      # Row number from Universe tab
    "B": "status",            # FIND / READY / SENT / FU1 / FU2 / REPLIED / DONE
    "C": "company",           # Auto-filled from Universe
    "D": "job_title",         # Auto-filled from Universe
    "E": "location",          # Auto-filled from Universe
    "F": "sector",            # Auto-detected: Tech / Healthcare / Finance / Retail
    "G": "contact_1",         # "Name - Title" (auto from contact finder)
    "H": "contact_2",         # "Name - Title"
    "I": "contact_3",         # "Name - Title"
    "J": "email_1",           # You paste from Apollo
    "K": "email_2",           # You paste from Apollo
    "L": "email_3",           # You paste from Apollo
    "M": "reply_from",        # "1" or "2" or "1,3" etc
    "N": "gmail_used",        # Which Gmail account got drafts
    "O": "sent_date",         # Date emails were sent
    "P": "notes",             # System log
}

# ─── Status Values ────────────────────────────────────────────
STATUS = {
    "FIND": "FIND",           # Trigger: find contacts
    "READY": "READY",         # Contacts found, emails pasted, generate drafts
    "SENT": "SENT",           # Emails sent manually
    "FOLLOW_UP_1": "FU1",    # 5-7 days, first follow-up
    "FOLLOW_UP_2": "FU2",    # 14 days, final follow-up
    "REPLIED": "REPLIED",     # Someone replied, stop
    "DONE": "DONE",           # Completed
    "ERROR": "ERROR",         # Something went wrong
}

# ─── Contact Finder Settings ─────────────────────────────────
MAX_CONTACTS = 3                    # Top 3 contacts per job
APOLLO_RESULTS_PER_PAGE = 10       # Results from Apollo search
GOOGLE_RESULTS_COUNT = 10          # Results from Google LinkedIn search

# ─── Company Size Thresholds ─────────────────────────────────
LARGE_ENTERPRISE_EMPLOYEES = 10000
MID_SIZE_EMPLOYEES = 1000

# ─── Hiring Manager Title Keywords (Priority 1) ──────────────
HIRING_MANAGER_TITLES = [
    "director", "senior director", "vp", "vice president",
    "head of", "senior manager", "manager", "lead",
    "principal", "staff", "senior lead"
]

# ─── Recruiter Title Keywords (Priority 3-4) ─────────────────
RECRUITER_TITLES = [
    "recruiter", "talent acquisition", "ta partner",
    "ta manager", "recruiting", "talent partner",
    "people operations", "hr business partner"
]

# ─── Department Keywords (for matching) ───────────────────────
DATA_DEPARTMENT_KEYWORDS = [
    "data", "analytics", "data science", "machine learning",
    "ml", "ai", "artificial intelligence", "business intelligence",
    "bi", "insights", "research", "quantitative", "statistics"
]

# ─── Sector Detection Keywords ────────────────────────────────
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

# ─── Email Generation Settings ────────────────────────────────
AI_MODEL = "gpt-4o"                 # OpenAI model for email generation
AI_TEMPERATURE = 0.7                # Slight creativity for variation
MAX_EMAILS_PER_JOB = 3             # 3 contacts = 3 emails

# ─── Follow-up Timing ────────────────────────────────────────
FOLLOW_UP_1_DAYS = 5               # Days after SENT for first follow-up
FOLLOW_UP_2_DAYS = 14              # Days after SENT for final follow-up

# ─── Saurabh's Contact Info ──────────────────────────────────
SENDER_NAME = "Saurabh Vyawahare"
SENDER_PHONE = "857-230-7888"
SENDER_EMAIL = "saurabhvy.tech@gmail.com"
SENDER_LINKEDIN = "linkedin.com/in/saurabh-vyawahare"
