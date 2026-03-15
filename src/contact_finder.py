"""
Contact Finder Module (v4 - Grok/xAI with Web + X Search)
Uses Grok 4.1 Fast with web search AND X/Twitter search.
Better at finding real people. $0.20/$0.50 per M tokens + $5/1K search calls.
Uses OpenAI SDK with xAI base URL (fully compatible).
"""
import json
import logging
from openai import OpenAI
from config import (
    XAI_API_KEY, CONTACT_FINDER_MODEL, MAX_CONTACTS,
    HIRING_MANAGER_TITLES, RECRUITER_TITLES
)

logger = logging.getLogger(__name__)

# Grok uses OpenAI-compatible API with different base URL
client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1"
)


class Contact:
    """Represents a potential outreach contact."""

    def __init__(self, name: str, title: str, company: str,
                 linkedin_url: str = "", source: str = "grok_search",
                 seniority: str = "", department: str = ""):
        self.name = name
        self.title = title.strip() if title else ""
        self.company = company
        self.linkedin_url = linkedin_url
        self.source = source
        self.seniority = seniority
        self.department = department
        self.score = 0
        self.contact_type = self._classify_type()

    def _classify_type(self) -> str:
        title_lower = self.title.lower()
        for keyword in RECRUITER_TITLES:
            if keyword in title_lower:
                return "recruiter"
        for keyword in HIRING_MANAGER_TITLES:
            if keyword in title_lower:
                return "hiring_manager"
        return "team_member"

    def __repr__(self):
        return f"{self.name} - {self.title} ({self.source})"

    def display_string(self):
        return self.name


def find_contacts(company_name: str, job_title: str,
                  location: str = "") -> dict:
    """
    Uses Grok with web search + X search to find contacts.
    X search catches people posting about new roles, promotions, hiring.
    """
    logger.info(f"Finding contacts for {job_title} at {company_name} ({location})")

    location_str = f" in {location}" if location else ""

    prompt = f"""Find real people to contact for cold outreach about this specific job opening.

COMPANY: {company_name}
JOB TITLE: {job_title}
JOB LOCATION: {location if location else "Not specified"}

Your search must be PRECISE. Here's what matters:

1. COMPANY SIZE: Estimate employees at {company_name}. Return "large_enterprise" (10K+), "mid_size" (1K-10K), or "small" (under 1K).

2. CONTACTS: Find 4-5 REAL people at {company_name}. Search strategy:

   STEP A: Figure out which TEAM this role belongs to from the job title "{job_title}".
   For example: "Data Scientist, Revenue Analytics" → Revenue Analytics team.
   "Analyst, Commercial Analytics" → Commercial Analytics team.
   "Senior Data Scientist" → Data Science team.

   STEP B: Search LinkedIn for the HEAD of that specific team at {company_name}.
   Search: "{company_name}" + "Director" or "VP" or "Head of" + [team name from Step A]
   {"Also search with location: " + location if location else ""}

   STEP C: Search for SENIOR MEMBERS of that same team.
   Search: "{company_name}" + "Senior" + [relevant title keywords]
   {"Prioritize people located in or near: " + location if location else ""}

   STEP D: Search for a RECRUITER who covers this specific department.
   Search: "{company_name}" + "recruiter" or "talent acquisition" + "data" or "analytics"

   STEP E: Check X/Twitter for anyone at {company_name} posting about hiring for data/analytics roles.

3. NAME-DROP: One additional team member (not in contact list) who works on the same team.

PRIORITY ORDER:
- People on the EXACT team this role is for (e.g., Revenue Analytics, not just any analytics)
- People at the SAME LOCATION as the job ({location if location else "any"})
- The hiring manager of that team > senior team members > department recruiters

For EACH person: full name, exact current job title, LinkedIn URL if found, type (hiring_manager/recruiter/team_member).

CRITICAL:
- ONLY return people you VERIFIED through search results. NEVER fabricate names.
- Verify they CURRENTLY work at {company_name} (not a past role).
- {"People in " + location + " are strongly preferred over those in other locations." if location else ""}
- Return fewer contacts rather than unverified ones.
- For large enterprises: prioritize hiring managers, skip generic company-wide recruiters.
- For small companies: target founders and department heads.

Return ONLY valid JSON, no other text:
{{
    "company_size": "mid_size",
    "employee_count": 5000,
    "contacts": [
        {{"name": "Full Name", "title": "Current Job Title", "linkedin_url": "url_if_found", "type": "hiring_manager"}}
    ],
    "name_drop": {{"name": "Full Name", "title": "Job Title"}}
}}

If no name_drop found, set to null."""

    try:
        response = client.responses.create(
            model=CONTACT_FINDER_MODEL,
            tools=[
                {"type": "web_search"},
                {"type": "x_search"}
            ],
            input=prompt
        )

        # Extract text from response
        full_text = response.output_text if hasattr(response, 'output_text') else ""

        if not full_text:
            for item in response.output:
                if hasattr(item, "content"):
                    for block in item.content:
                        if hasattr(block, "text"):
                            full_text += block.text

        result = _parse_response(full_text, company_name)

        if result:
            logger.info(
                f"Found {len(result['contacts'])} contacts for {company_name} "
                f"(size: {result['company_size']})"
            )
            return result
        else:
            logger.warning(f"Could not parse response for {company_name}")
            return _empty_result(company_name)

    except Exception as e:
        logger.error(f"Grok contact search failed: {e}")
        return _empty_result(company_name)


def _parse_response(text: str, company_name: str) -> dict:
    try:
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            return None

        data = json.loads(text[start:end])

        contacts = []
        for c in data.get("contacts", []):
            contact = Contact(
                name=c.get("name", ""),
                title=c.get("title", ""),
                company=company_name,
                linkedin_url=c.get("linkedin_url", ""),
            )
            provided_type = c.get("type", "")
            if provided_type in ["hiring_manager", "recruiter", "team_member"]:
                contact.contact_type = provided_type
            contacts.append(contact)

        company_size = data.get("company_size", "mid_size")
        selected = _apply_company_size_rules(contacts, company_size)

        name_drop = None
        nd_data = data.get("name_drop")
        if nd_data and nd_data.get("name"):
            name_drop = Contact(name=nd_data["name"], title=nd_data.get("title", ""), company=company_name)

        employee_count = data.get("employee_count", 0)
        notes = f"Size: {company_size} ({employee_count} emp) | Found: {len(contacts)} | Selected: {len(selected)} | Source: Grok web+X search"
        if name_drop:
            notes += f" | Name-drop: {name_drop.name}"

        return {
            "contacts": selected[:MAX_CONTACTS],
            "company_size": company_size,
            "employee_count": employee_count,
            "name_drop": name_drop,
            "notes": notes
        }
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"Parse error: {e}")
        return None


def _apply_company_size_rules(contacts, company_size):
    hiring_managers = [c for c in contacts if c.contact_type == "hiring_manager"]
    team_members = [c for c in contacts if c.contact_type == "team_member"]
    recruiters = [c for c in contacts if c.contact_type == "recruiter"]
    selected = []

    if company_size == "large_enterprise":
        selected.extend(hiring_managers[:2])
        if len(selected) < MAX_CONTACTS:
            selected.extend(team_members[:MAX_CONTACTS - len(selected)])
        if len(selected) < MAX_CONTACTS:
            selected.extend(recruiters[:MAX_CONTACTS - len(selected)])
    elif company_size == "mid_size":
        selected.extend(hiring_managers[:2])
        if len(selected) < MAX_CONTACTS:
            selected.extend(recruiters[:1])
        if len(selected) < MAX_CONTACTS:
            selected.extend(team_members[:MAX_CONTACTS - len(selected)])
    elif company_size == "small":
        selected.extend(hiring_managers[:2])
        if len(selected) < MAX_CONTACTS:
            selected.extend(team_members[:MAX_CONTACTS - len(selected)])
        if len(selected) < MAX_CONTACTS:
            selected.extend(recruiters[:MAX_CONTACTS - len(selected)])
    else:
        selected = contacts[:MAX_CONTACTS]

    if len(selected) < MAX_CONTACTS:
        for c in contacts:
            if c not in selected:
                selected.append(c)
            if len(selected) >= MAX_CONTACTS:
                break
    return selected


def _empty_result(company_name):
    return {
        "contacts": [],
        "company_size": "mid_size",
        "employee_count": 0,
        "name_drop": None,
        "notes": f"Search failed for {company_name}. Try again or add contacts manually."
    }
