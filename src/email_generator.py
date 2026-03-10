"""
Email Generator Module
Uses OpenAI API to generate cold emails following v7.0 outreach logic.
Handles variation rotation, sector-specific resume points, and
different templates for hiring managers vs recruiters.
"""
import json
import random
import logging
from openai import OpenAI
from config import (
    OPENAI_API_KEY, AI_MODEL, AI_TEMPERATURE,
    SENDER_NAME, SENDER_PHONE, SENDER_EMAIL
)

logger = logging.getLogger(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

# ─── Variation Pools (v7.0 Anti-Spam) ─────────────────────────

SUBJECT_LINES = {
    "standard": [
        "{job_title} at {company}",
        "{job_title} role at {company}",
        "{job_title} position at {company}",
    ],
    "conversational": [
        "Quick note about the {job_title} role",
        "Reaching out about {job_title}",
        "Interest in the {job_title} position",
    ],
    "team_focused": [
        "{job_title} opening on your team",
        "{job_title} role on the {department} team",
    ]
}

TRANSITION_LINES = [
    "Here's why I'd be a strong fit:",
    "A few reasons I think I'd be a good match:",
    "Here's what makes me a fit for this role:",
    "This is what I've been working on:",
    "Here's what I bring to the table:",
    "A quick look at my relevant experience:",
]

CTA_HIRING_MANAGER = [
    "Would love the opportunity to interview for this role.",
    "I'd welcome the chance to interview.",
    "Would be great to interview and discuss further.",
    "I'd appreciate the opportunity to interview.",
    "Would love to interview if you think there's a fit.",
]

CTA_RECRUITER = [
    "Would love to interview for this role, or if you could point me to the hiring manager, I'd appreciate it.",
    "I'd welcome the chance to interview. If there's a better contact for this role, happy to reach out to them as well.",
    "Would be great to interview, or if you could connect me with the hiring manager, that would be helpful.",
    "I'd appreciate the opportunity to interview. If there's someone else I should reach out to, please let me know.",
]

RESUME_OFFER = [
    "Happy to send my resume if you'd like to review my background in more detail.",
    "I can share my resume if that would be helpful.",
    "Please let me know if you'd like me to send over my resume.",
    "I'd be glad to provide my resume if you'd like to take a closer look.",
    "If it would be helpful, I can send my resume for your review.",
]

# ─── Follow-up Templates ──────────────────────────────────────

FOLLOW_UP_1_TEMPLATE = """Hi {first_name},

Just bumping this up. I know things get buried. Still interested in the {job_title} role.

Would love to chat if you have a few minutes.

Thanks,
Saurabh"""

FOLLOW_UP_2_TEMPLATE = """Hi {first_name},

Last note from me. Totally understand if timing isn't right.

If anything changes, I'm at {email}.

Thanks,
Saurabh"""


# ─── Sector-Specific Resume Points ────────────────────────────

RESUME_POINTS = {
    "healthcare": [
        "I built a claims risk scoring model using logistic regression to flag high-cost cases before they escalated, improving identification accuracy for case review",
        "I standardized multi-source healthcare and claims data using ETL workflows in SQL, improving data interoperability across systems",
        "I built an NLP pipeline to extract and standardize adverse event data with MedDRA mapping, streamlining case review workflows",
        "I created Power BI dashboards for compliance KPIs and stakeholder reporting, giving leadership real-time visibility into key metrics",
        "I built a risk-stratification pipeline using survival analysis and XGBoost to predict patient outcomes and flag high-risk cases",
        "I built Python and SQL pipelines with automated validation to ensure data quality and governance alignment",
    ],
    "finance": [
        "I built a risk-profiling model using LightGBM on transaction behavior to identify high-risk customers for early intervention",
        "I consolidated transaction and payment data from multiple sources using ETL pipelines, improving data quality for financial reporting",
        "I built audit-ready logging systems that captured model inputs and outputs for regulatory traceability",
        "I created Power BI dashboards tracking repayment rates and spending KPIs, enabling faster business decisions",
        "I built segmentation models using clustering on 1M+ records to identify high-value cohorts and improve targeting",
        "I built Python and SQL pipelines with automated validation to ensure data quality and governance alignment",
    ],
    "retail": [
        "I built a recommendation engine using collaborative filtering on purchase and browsing behavior, delivering personalized product suggestions",
        "I designed a multi-touch attribution model to measure marketing channel ROI across digital and offline campaigns",
        "I built an A/B testing pipeline for promotional pricing strategies, validating discount timing and conversion impact",
        "I built churn prediction models to identify at-risk customers, enabling targeted retention campaigns",
        "I built segmentation models using clustering on 1M+ transaction records to identify high-value cohorts and improve targeting",
        "I created interactive dashboards delivering real-time insights to stakeholders for weekly decision-making",
    ],
    "tech": [
        "I built an ensemble prediction model using LightGBM on product usage telemetry to measure feature impact and improve prioritization",
        "I built an automated migration pipeline to consolidate 10M+ CRM records into Snowflake, reducing analytics query time significantly",
        "I built a real-time ML monitoring system that tracks model drift, latency, and accuracy, alerting teams before predictions degrade",
        "I built a RAG-based document assistant using NLP, vector search, and OpenAI APIs to enable instant retrieval from hundreds of documents",
        "I built segmentation models using clustering on 1M+ records to identify high-value cohorts and improve targeting",
        "I created Power BI dashboards delivering real-time insights to stakeholders for weekly decision-making",
    ]
}


class VariationTracker:
    """
    Tracks which variations have been used within a batch.
    Ensures no two emails in the same batch use the same variation.
    """

    def __init__(self):
        self.used_subjects = []
        self.used_transitions = []
        self.used_ctas = []
        self.used_resume_offers = []

    def get_subject(self, job_title: str, company: str,
                    department: str = "Data") -> str:
        """Get a unique subject line for this batch."""
        all_subjects = []
        for pool in SUBJECT_LINES.values():
            for template in pool:
                formatted = template.format(
                    job_title=job_title,
                    company=company,
                    department=department
                )
                if formatted not in self.used_subjects:
                    all_subjects.append(formatted)

        if not all_subjects:
            # All used, reset
            self.used_subjects = []
            return self.get_subject(job_title, company, department)

        choice = random.choice(all_subjects)
        self.used_subjects.append(choice)
        return choice

    def get_transition(self) -> str:
        available = [t for t in TRANSITION_LINES if t not in self.used_transitions]
        if not available:
            self.used_transitions = []
            available = TRANSITION_LINES
        choice = random.choice(available)
        self.used_transitions.append(choice)
        return choice

    def get_cta(self, contact_type: str) -> str:
        pool = CTA_RECRUITER if contact_type == "recruiter" else CTA_HIRING_MANAGER
        available = [c for c in pool if c not in self.used_ctas]
        if not available:
            self.used_ctas = []
            available = pool
        choice = random.choice(available)
        self.used_ctas.append(choice)
        return choice

    def get_resume_offer(self) -> str:
        available = [r for r in RESUME_OFFER if r not in self.used_resume_offers]
        if not available:
            self.used_resume_offers = []
            available = RESUME_OFFER
        choice = random.choice(available)
        self.used_resume_offers.append(choice)
        return choice


def generate_emails(contacts: list, jd_text: str, company: str,
                    job_title: str, location: str, sector: str,
                    company_size: str, name_drop=None) -> list[dict]:
    """
    Generate personalized cold emails for each contact.

    Returns list of:
    {
        "contact_name": str,
        "contact_email": str,  # empty, filled later by user
        "contact_type": str,
        "subject": str,
        "body": str
    }
    """
    tracker = VariationTracker()
    emails = []

    for i, contact in enumerate(contacts):
        # Get unique variations for this email
        subject = tracker.get_subject(job_title, company)
        transition = tracker.get_transition()
        cta = tracker.get_cta(contact.contact_type)
        resume_offer = tracker.get_resume_offer()

        # Select resume points most relevant to JD
        points = _select_resume_points(jd_text, sector)

        # Build the email using AI
        email_body = _generate_single_email(
            contact=contact,
            jd_text=jd_text,
            company=company,
            job_title=job_title,
            location=location,
            sector=sector,
            company_size=company_size,
            name_drop=name_drop if i == 0 else None,  # Name-drop only in first email
            transition=transition,
            cta=cta,
            resume_offer=resume_offer,
            points=points
        )

        emails.append({
            "contact_name": contact.name,
            "contact_title": contact.title,
            "contact_type": contact.contact_type,
            "subject": subject,
            "body": email_body
        })

    return emails


def generate_follow_up(contact_name: str, job_title: str,
                       follow_up_number: int) -> dict:
    """Generate a follow-up email."""
    first_name = contact_name.split()[0] if contact_name else "there"

    if follow_up_number == 1:
        body = FOLLOW_UP_1_TEMPLATE.format(
            first_name=first_name,
            job_title=job_title
        )
        subject = f"Re: {job_title}"
    else:
        body = FOLLOW_UP_2_TEMPLATE.format(
            first_name=first_name,
            email=SENDER_EMAIL
        )
        subject = f"Re: {job_title}"

    return {
        "subject": subject,
        "body": body
    }


def _select_resume_points(jd_text: str, sector: str) -> list[str]:
    """
    Select the 2-3 most relevant resume points based on JD keywords.
    Uses the sector-specific resume points pool.
    """
    points_pool = RESUME_POINTS.get(sector, RESUME_POINTS["tech"])
    jd_lower = jd_text.lower()

    # Score each point by keyword overlap with JD
    scored = []
    for point in points_pool:
        point_lower = point.lower()
        # Count meaningful keyword matches
        keywords = [
            "claims", "risk", "etl", "sql", "python", "power bi",
            "dashboard", "nlp", "ml", "model", "pipeline", "snowflake",
            "segmentation", "churn", "prediction", "recommendation",
            "a/b test", "attribution", "compliance", "audit",
            "healthcare", "financial", "transaction", "monitoring",
            "rag", "openai", "vector", "drift", "lightgbm", "xgboost",
            "migration", "crm", "clustering", "survival analysis"
        ]
        score = sum(1 for kw in keywords if kw in point_lower and kw in jd_lower)
        scored.append((point, score))

    # Sort by score, pick top 3
    scored.sort(key=lambda x: x[1], reverse=True)

    # Always return 2-3 points
    selected = [p[0] for p in scored[:3]]

    # If less than 2, pad with highest-scored remaining
    if len(selected) < 2:
        for p in scored:
            if p[0] not in selected:
                selected.append(p[0])
            if len(selected) >= 2:
                break

    return selected


def _generate_single_email(contact, jd_text: str, company: str,
                           job_title: str, location: str, sector: str,
                           company_size: str, name_drop,
                           transition: str, cta: str,
                           resume_offer: str, points: list[str]) -> str:
    """
    Use OpenAI to generate a single personalized email.
    The AI handles the opener and genuine reason.
    We provide the structural elements (transition, CTA, points, etc.)
    """
    first_name = contact.name.split()[0] if contact.name else "there"

    # Build the numbered points string
    points_text = ""
    for i, point in enumerate(points, 1):
        points_text += f"{i}. {point}\n"

    # Determine opener type
    if contact.contact_type == "recruiter":
        opener_instruction = (
            "Use a RECRUITER opener with soft/uncertain language. "
            "Do NOT definitively say someone's team is hiring. "
            "Use phrases like 'could be under' or 'might be related to'."
        )
        if name_drop:
            opener_instruction += (
                f" You can reference {name_drop.name} ({name_drop.title}) "
                f"on the team with uncertain language like 'I saw there's a "
                f"{job_title} opening that could be under {name_drop.name}'s team.'"
            )
    elif name_drop:
        opener_instruction = (
            f"Use a NAME-DROP opener. Reference {name_drop.name} "
            f"({name_drop.title}) on the team. Use safe language like "
            f"'I noticed {name_drop.name} on the [team] team and saw "
            f"there's a {job_title} opening that could be on your team.' "
            f"NEVER say they referred you."
        )
    else:
        opener_instruction = (
            "Use a DIRECT/CONFIDENT opener. Something like "
            "'I'm a data scientist who builds [relevant thing from JD]. "
            f"Saw you're hiring for {job_title} and wanted to reach out.'"
        )

    system_prompt = f"""You are writing a cold outreach email for Saurabh Vyawahare, a Data Scientist with 4+ years of experience.

CRITICAL RULES:
- NO "I hope this finds you well"
- NO percentages or metrics
- NO company names in numbered points
- NO dashes anywhere in the message (looks AI-generated). Use commas and periods only.
- NO bullet points. Use numbered format (1. 2. 3.) which are already provided.
- Keep it concise and confident, not needy.
- The email should sound like a confident professional who KNOWS they're a fit.

STRUCTURE (follow exactly):
1. "Hi {first_name}," (greeting)
2. Opener (1-2 sentences based on instructions below)
3. Genuine reason (1 sentence about why this company/role specifically)
4. Transition line (provided, use exactly)
5. Numbered points (provided, use exactly as given)
6. CTA (provided, use exactly)
7. Resume offer (provided, use exactly)
8. Sign-off: "Thanks,\\nSaurabh Vyawahare\\n857-230-7888"

OUTPUT FORMAT:
Return ONLY the email body. No subject line. No explanations. Just the email text.
"""

    user_prompt = f"""Generate the cold email with these elements:

RECIPIENT: {contact.name}, {contact.title} at {company}
RECIPIENT TYPE: {contact.contact_type}
JOB TITLE: {job_title}
COMPANY: {company}
LOCATION: {location}
SECTOR: {sector}
COMPANY SIZE: {company_size}

OPENER INSTRUCTION: {opener_instruction}

TRANSITION LINE (use exactly): {transition}

NUMBERED POINTS (use exactly as written):
{points_text}

CTA (use exactly): {cta}

RESUME OFFER (use exactly): {resume_offer}

JD SUMMARY (for genuine reason):
{jd_text[:1500]}

Generate the email now. Return ONLY the email body text.
"""

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            temperature=AI_TEMPERATURE,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=800
        )

        email_body = response.choices[0].message.content.strip()

        # Post-processing: enforce rules
        email_body = _enforce_rules(email_body)

        return email_body

    except Exception as e:
        logger.error(f"Email generation failed: {e}")
        # Fallback: build email manually without AI
        return _build_fallback_email(
            first_name, contact.contact_type, job_title, company,
            name_drop, transition, points_text, cta, resume_offer
        )


def _enforce_rules(email_body: str) -> str:
    """Post-processing to enforce v7.0 rules."""
    # Remove any dashes that snuck in
    email_body = email_body.replace(" — ", ", ")
    email_body = email_body.replace(" – ", ", ")
    email_body = email_body.replace("—", ",")
    email_body = email_body.replace("–", ",")

    # Ensure sign-off is correct
    if "Saurabh Vyawahare" not in email_body:
        email_body += f"\n\nThanks,\nSaurabh Vyawahare\n857-230-7888"

    return email_body


def _build_fallback_email(first_name, contact_type, job_title, company,
                          name_drop, transition, points_text, cta,
                          resume_offer) -> str:
    """Fallback email if AI generation fails."""
    if name_drop and contact_type != "recruiter":
        opener = (
            f"I noticed {name_drop.name} on the team and saw there's a "
            f"{job_title} opening that could be on your team."
        )
    elif contact_type == "recruiter":
        opener = (
            f"I saw there's a {job_title} opening at {company}. "
            f"The focus on data and analytics is exactly what I've been doing."
        )
    else:
        opener = (
            f"I'm a data scientist with 4+ years of experience building "
            f"production ML systems. Saw the {job_title} role at {company} "
            f"and wanted to reach out."
        )

    genuine = f"The work your team is doing at {company} is exactly the kind of problem I want to solve."

    email = f"""Hi {first_name},

{opener}

{genuine}

{transition}

{points_text}
{cta}

{resume_offer}

Thanks,
Saurabh Vyawahare
857-230-7888"""

    return email
