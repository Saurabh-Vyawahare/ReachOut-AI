"""
Scout A — Grok/xAI with Web + X Search
Uses Grok 4.1 Fast for contact discovery. ~2K tokens per search.
"""
import json
import logging
from openai import OpenAI
from config import XAI_API_KEY, SCOUT_GROK_MODEL, MAX_CONTACTS
from contact import Contact

logger = logging.getLogger(__name__)

client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1") if XAI_API_KEY else None


def scout_grok(company: str, job_title: str, location: str, team: str = "Data") -> dict:
    """
    Run Grok web + X search to find contacts.
    Returns: {contacts: [Contact], company_size, name_drop, notes, source: "grok"}
    """
    if not client:
        logger.error("XAI_API_KEY not set — Scout A (Grok) disabled")
        return _empty("XAI_API_KEY not configured")

    location_str = f" in {location}" if location else ""

    prompt = f"""Find real people to contact for cold outreach about this job.

COMPANY: {company}
JOB TITLE: {job_title}
TEAM: {team}
LOCATION: {location if location else "Not specified"}

Search strategy:
1. Estimate company size: "large_enterprise" (10K+), "mid_size" (1K-10K), "small" (<1K)
2. Search LinkedIn for HEAD of the {team} team at {company}{location_str}
3. Search for SENIOR MEMBERS of the {team} team
4. Search for a RECRUITER covering data/analytics roles
5. Check X/Twitter for anyone at {company} posting about hiring data roles

CRITICAL: Only return VERIFIED people. Never fabricate names. Return fewer rather than unverified.

Return ONLY valid JSON:
{{
    "company_size": "mid_size",
    "employee_count": 5000,
    "contacts": [
        {{"name": "Full Name", "title": "Current Title", "linkedin_url": "url_if_found", "type": "hiring_manager"}}
    ],
    "name_drop": {{"name": "Full Name", "title": "Title"}} or null
}}"""

    try:
        response = client.responses.create(
            model=SCOUT_GROK_MODEL,
            tools=[{"type": "web_search"}, {"type": "x_search"}],
            input=prompt
        )

        full_text = response.output_text if hasattr(response, 'output_text') else ""
        if not full_text:
            for item in response.output:
                if hasattr(item, "content"):
                    for block in item.content:
                        if hasattr(block, "text"):
                            full_text += block.text

        return _parse(full_text, company)

    except Exception as e:
        logger.error(f"Grok scout failed: {e}")
        return _empty(str(e))


def _parse(text: str, company: str) -> dict:
    try:
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            return _empty("No JSON in response")

        data = json.loads(text[start:end])
        contacts = []
        for c in data.get("contacts", []):
            contact = Contact(
                name=c.get("name", ""), title=c.get("title", ""),
                company=company, linkedin_url=c.get("linkedin_url", ""),
                source="grok"
            )
            ptype = c.get("type", "")
            if ptype in ["hiring_manager", "recruiter", "team_member"]:
                contact.contact_type = ptype
            contacts.append(contact)

        name_drop = None
        nd = data.get("name_drop")
        if nd and nd.get("name"):
            name_drop = Contact(name=nd["name"], title=nd.get("title", ""), company=company, source="grok")

        company_size = data.get("company_size", "mid_size")
        return {
            "contacts": contacts[:MAX_CONTACTS],
            "company_size": company_size,
            "name_drop": name_drop,
            "notes": f"Grok: {len(contacts)} found (size: {company_size})",
            "source": "grok",
        }
    except Exception as e:
        logger.error(f"Grok parse error: {e}")
        return _empty(str(e))


def _empty(error: str) -> dict:
    return {"contacts": [], "company_size": "mid_size", "name_drop": None, "notes": f"Grok failed: {error}", "source": "grok"}
