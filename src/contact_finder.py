"""
Contact Finder Module
Searches Apollo People API + Google (LinkedIn profiles)
Ranks candidates using v7.0 company size logic
Returns top 3 contacts per job
"""
import requests
import re
import logging
from typing import Optional
from config import (
    APOLLO_API_KEY, GOOGLE_CSE_API_KEY, GOOGLE_CSE_ID,
    HIRING_MANAGER_TITLES, RECRUITER_TITLES, DATA_DEPARTMENT_KEYWORDS,
    LARGE_ENTERPRISE_EMPLOYEES, MID_SIZE_EMPLOYEES,
    MAX_CONTACTS, APOLLO_RESULTS_PER_PAGE, GOOGLE_RESULTS_COUNT
)

logger = logging.getLogger(__name__)


class Contact:
    """Represents a potential outreach contact."""

    def __init__(self, name: str, title: str, company: str,
                 linkedin_url: str = "", source: str = "apollo",
                 seniority: str = "", department: str = ""):
        self.name = name
        self.title = title.strip() if title else ""
        self.company = company
        self.linkedin_url = linkedin_url
        self.source = source  # "apollo" or "google"
        self.seniority = seniority
        self.department = department
        self.score = 0  # Ranking score (higher = better)
        self.contact_type = self._classify_type()

    def _classify_type(self) -> str:
        """Classify as hiring_manager, recruiter, or team_member."""
        title_lower = self.title.lower()
        for keyword in RECRUITER_TITLES:
            if keyword in title_lower:
                return "recruiter"
        for keyword in HIRING_MANAGER_TITLES:
            if keyword in title_lower:
                return "hiring_manager"
        return "team_member"

    def __repr__(self):
        return f"{self.name} - {self.title} ({self.source}, score={self.score})"

    def display_string(self):
        """Format for sheet: 'Name - Title'"""
        return f"{self.name} - {self.title}"


def estimate_company_size(company_name: str) -> tuple[str, int]:
    """
    Use Apollo Organization Search to estimate company size.
    Returns (category, employee_count).
    """
    try:
        url = "https://api.apollo.io/api/v1/mixed_companies/search"
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "x-api-key": APOLLO_API_KEY
        }
        params = {
            "q_organization_name": company_name,
            "per_page": 1
        }
        response = requests.post(url, headers=headers, json=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        orgs = data.get("organizations", [])
        if not orgs:
            logger.warning(f"No org data found for {company_name}, defaulting to mid-size")
            return "mid_size", 5000

        org = orgs[0]
        employee_count = org.get("estimated_num_employees", 5000)

        if employee_count >= LARGE_ENTERPRISE_EMPLOYEES:
            return "large_enterprise", employee_count
        elif employee_count >= MID_SIZE_EMPLOYEES:
            return "mid_size", employee_count
        else:
            return "small", employee_count

    except Exception as e:
        logger.error(f"Company size estimation failed: {e}")
        return "mid_size", 5000


def search_apollo(company_name: str, job_title: str,
                  location: str = "") -> list[Contact]:
    """
    Search Apollo People API for contacts at the company.
    This endpoint does NOT consume credits.
    """
    contacts = []

    # Build relevant title keywords from the job title
    title_keywords = _extract_department_titles(job_title)

    try:
        url = "https://api.apollo.io/api/v1/mixed_people/search"
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "x-api-key": APOLLO_API_KEY
        }

        # Search 1: Hiring managers in the department
        params = {
            "q_organization_name": company_name,
            "person_titles": title_keywords["manager_titles"],
            "per_page": APOLLO_RESULTS_PER_PAGE,
        }
        if location:
            params["person_locations"] = [location]

        response = requests.post(url, headers=headers, json=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        for person in data.get("people", []):
            contact = _apollo_person_to_contact(person, company_name)
            if contact:
                contacts.append(contact)

        # Search 2: Recruiters who might cover this role
        params_recruiter = {
            "q_organization_name": company_name,
            "person_titles": [
                "recruiter data", "talent acquisition data",
                "recruiter analytics", "ta partner",
                "technical recruiter"
            ],
            "per_page": 5,
        }

        response2 = requests.post(url, headers=headers, json=params_recruiter, timeout=15)
        response2.raise_for_status()
        data2 = response2.json()

        for person in data2.get("people", []):
            contact = _apollo_person_to_contact(person, company_name)
            if contact:
                contacts.append(contact)

        # Search 3: Team members (potential peers)
        params_team = {
            "q_organization_name": company_name,
            "person_titles": title_keywords["peer_titles"],
            "per_page": 5,
        }
        if location:
            params_team["person_locations"] = [location]

        response3 = requests.post(url, headers=headers, json=params_team, timeout=15)
        response3.raise_for_status()
        data3 = response3.json()

        for person in data3.get("people", []):
            contact = _apollo_person_to_contact(person, company_name)
            if contact:
                contacts.append(contact)

        logger.info(f"Apollo found {len(contacts)} contacts for {company_name}")

    except Exception as e:
        logger.error(f"Apollo search failed: {e}")

    return contacts


def search_google_linkedin(company_name: str, job_title: str,
                           location: str = "") -> list[Contact]:
    """
    Search Google for LinkedIn profiles at the company.
    Uses Google Custom Search API (100 free queries/day).
    """
    contacts = []

    # Extract department keywords for search
    dept_keywords = []
    for keyword in DATA_DEPARTMENT_KEYWORDS:
        if keyword.lower() in job_title.lower():
            dept_keywords.append(keyword)
    if not dept_keywords:
        dept_keywords = ["data", "analytics"]

    # Build search queries
    queries = [
        # Query 1: Department leaders
        f'site:linkedin.com/in "{company_name}" "{dept_keywords[0]}" director OR manager OR lead',
        # Query 2: Broader team search
        f'site:linkedin.com/in "{company_name}" "{" ".join(dept_keywords)}"',
    ]

    if location:
        # Add location-specific search
        city = location.split(",")[0].strip()
        queries.append(
            f'site:linkedin.com/in "{company_name}" "{dept_keywords[0]}" "{city}"'
        )

    for query in queries:
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": GOOGLE_CSE_API_KEY,
                "cx": GOOGLE_CSE_ID,
                "q": query,
                "num": GOOGLE_RESULTS_COUNT
            }
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                contact = _google_result_to_contact(item, company_name)
                if contact:
                    contacts.append(contact)

        except Exception as e:
            logger.error(f"Google search failed for query '{query}': {e}")

    # Deduplicate by name
    seen_names = set()
    unique_contacts = []
    for c in contacts:
        name_key = c.name.lower().strip()
        if name_key not in seen_names:
            seen_names.add(name_key)
            unique_contacts.append(c)

    logger.info(f"Google/LinkedIn found {len(unique_contacts)} contacts for {company_name}")
    return unique_contacts


def rank_and_select(apollo_contacts: list[Contact],
                    google_contacts: list[Contact],
                    company_size: str,
                    job_title: str) -> list[Contact]:
    """
    Rank all contacts from both sources using v7.0 logic.
    Returns top MAX_CONTACTS (3).
    """
    all_contacts = apollo_contacts + google_contacts

    # Deduplicate across sources (prefer the one with more info)
    deduped = _deduplicate_contacts(all_contacts)

    # Score each contact
    for contact in deduped:
        contact.score = _calculate_score(contact, company_size, job_title)

    # Sort by score (highest first)
    deduped.sort(key=lambda c: c.score, reverse=True)

    # Apply company size rules from v7.0
    selected = _apply_company_size_rules(deduped, company_size)

    return selected[:MAX_CONTACTS]


def find_contacts(company_name: str, job_title: str,
                  location: str = "") -> dict:
    """
    Main entry point. Finds and ranks contacts for a job.

    Returns:
        {
            "contacts": [Contact, Contact, Contact],
            "company_size": "large_enterprise",
            "employee_count": 15000,
            "name_drop": Contact or None,
            "notes": "Found via Apollo + LinkedIn cross-reference"
        }
    """
    logger.info(f"Finding contacts for {job_title} at {company_name} ({location})")

    # Step 1: Estimate company size
    company_size, employee_count = estimate_company_size(company_name)
    logger.info(f"Company size: {company_size} ({employee_count} employees)")

    # Step 2: Search both sources
    apollo_contacts = search_apollo(company_name, job_title, location)
    google_contacts = search_google_linkedin(company_name, job_title, location)

    # Step 3: Rank and select top 3
    top_contacts = rank_and_select(
        apollo_contacts, google_contacts, company_size, job_title
    )

    # Step 4: Identify name-drop candidate (team member, not the person we email)
    name_drop = _find_name_drop(
        apollo_contacts + google_contacts, top_contacts, job_title
    )

    # Build notes
    notes_parts = []
    notes_parts.append(f"Size: {company_size} ({employee_count} emp)")
    notes_parts.append(f"Apollo: {len(apollo_contacts)} found")
    notes_parts.append(f"LinkedIn: {len(google_contacts)} found")
    if name_drop:
        notes_parts.append(f"Name-drop: {name_drop.name}")

    return {
        "contacts": top_contacts,
        "company_size": company_size,
        "employee_count": employee_count,
        "name_drop": name_drop,
        "notes": " | ".join(notes_parts)
    }


# ─── Private Helper Functions ─────────────────────────────────

def _extract_department_titles(job_title: str) -> dict:
    """
    From the job title, generate relevant search titles
    for managers and peers.
    """
    title_lower = job_title.lower()

    # Detect the department from the job title
    department = "data"
    if "analytics" in title_lower:
        department = "analytics"
    if "data science" in title_lower or "data scientist" in title_lower:
        department = "data science"
    if "machine learning" in title_lower or "ml" in title_lower:
        department = "machine learning"
    if "business intelligence" in title_lower or "bi " in title_lower:
        department = "business intelligence"

    manager_titles = [
        f"director {department}",
        f"director of {department}",
        f"senior manager {department}",
        f"head of {department}",
        f"vp {department}",
        f"manager {department}",
        f"lead {department}",
    ]

    peer_titles = [
        f"senior {department}",
        f"senior data analyst",
        f"senior data scientist",
        f"data analyst",
        f"data scientist",
        f"analytics engineer",
    ]

    return {
        "manager_titles": manager_titles,
        "peer_titles": peer_titles,
        "department": department
    }


def _apollo_person_to_contact(person: dict, company_name: str) -> Optional[Contact]:
    """Convert Apollo API person result to Contact object."""
    name = person.get("name", "")
    title = person.get("title", "")

    if not name or not title:
        return None

    return Contact(
        name=name,
        title=title,
        company=company_name,
        linkedin_url=person.get("linkedin_url", ""),
        source="apollo",
        seniority=person.get("seniority", ""),
        department=person.get("departments", [""])[0] if person.get("departments") else ""
    )


def _google_result_to_contact(item: dict, company_name: str) -> Optional[Contact]:
    """
    Parse a Google Custom Search result for a LinkedIn profile.
    Google results for LinkedIn profiles typically look like:
    Title: "John Smith - Director of Analytics - Lucid Motors | LinkedIn"
    """
    title_text = item.get("title", "")
    link = item.get("link", "")

    # Only LinkedIn profile links
    if "linkedin.com/in/" not in link:
        return None

    # Parse name and title from Google result title
    # Format: "Name - Title - Company | LinkedIn"
    # or: "Name - Title at Company | LinkedIn"
    parts = title_text.replace(" | LinkedIn", "").replace(" - LinkedIn", "")

    # Split by " - " or " at "
    segments = re.split(r'\s*[-–]\s*', parts)

    if len(segments) >= 2:
        name = segments[0].strip()
        title = segments[1].strip()
    elif " at " in parts:
        name_part, rest = parts.split(" at ", 1)
        name = name_part.strip()
        title = ""
    else:
        return None

    # Skip if name looks invalid
    if len(name) < 3 or len(name) > 50:
        return None

    return Contact(
        name=name,
        title=title,
        company=company_name,
        linkedin_url=link,
        source="google"
    )


def _deduplicate_contacts(contacts: list[Contact]) -> list[Contact]:
    """Remove duplicate contacts, preferring Apollo (more structured data)."""
    seen = {}
    for c in contacts:
        key = c.name.lower().strip()
        if key not in seen:
            seen[key] = c
        elif c.source == "apollo" and seen[key].source == "google":
            # Apollo has more structured data, prefer it
            seen[key] = c

    return list(seen.values())


def _calculate_score(contact: Contact, company_size: str,
                     job_title: str) -> int:
    """
    Score a contact based on v7.0 rules.
    Higher score = better candidate to reach out to.
    """
    score = 0
    title_lower = contact.title.lower()
    job_lower = job_title.lower()

    # 1. Contact type scoring (based on company size)
    if contact.contact_type == "hiring_manager":
        score += 100  # Always top priority
    elif contact.contact_type == "team_member":
        score += 50
    elif contact.contact_type == "recruiter":
        if company_size == "large_enterprise":
            score += 20  # Low priority for large companies
        elif company_size == "small":
            score += 70  # HR person often is the decision maker
        else:
            score += 40  # Mid-size, viable secondary

    # 2. Department relevance
    dept_match = False
    for keyword in DATA_DEPARTMENT_KEYWORDS:
        if keyword in title_lower:
            dept_match = True
            score += 30
            break

    # 3. Seniority bonus
    if any(s in title_lower for s in ["director", "vp", "vice president", "head of"]):
        score += 25
    elif any(s in title_lower for s in ["senior manager", "sr. manager"]):
        score += 20
    elif "manager" in title_lower:
        score += 15
    elif "lead" in title_lower:
        score += 10

    # 4. Title keyword overlap with job title
    job_words = set(job_lower.split())
    title_words = set(title_lower.split())
    overlap = job_words & title_words
    # Remove common words
    overlap -= {"at", "the", "and", "of", "in", "a", "an", "for", "-"}
    score += len(overlap) * 10

    # 5. For large enterprises, penalize generic recruiters
    if company_size == "large_enterprise" and contact.contact_type == "recruiter":
        if not dept_match:
            score -= 30  # Generic recruiter, probably wrong team

    # 6. Source bonus (Apollo has verified data)
    if contact.source == "apollo":
        score += 5

    return score


def _apply_company_size_rules(contacts: list[Contact],
                              company_size: str) -> list[Contact]:
    """
    Apply v7.0 company size rules to the ranked list.
    Ensures proper mix of hiring managers vs recruiters.
    """
    hiring_managers = [c for c in contacts if c.contact_type == "hiring_manager"]
    team_members = [c for c in contacts if c.contact_type == "team_member"]
    recruiters = [c for c in contacts if c.contact_type == "recruiter"]

    selected = []

    if company_size == "large_enterprise":
        # Prioritize hiring managers, skip generic recruiters
        selected.extend(hiring_managers[:2])
        if len(selected) < MAX_CONTACTS:
            # Add team members before recruiters
            selected.extend(team_members[:MAX_CONTACTS - len(selected)])
        if len(selected) < MAX_CONTACTS:
            # Only add recruiters with department match
            dept_recruiters = [r for r in recruiters if r.score > 30]
            selected.extend(dept_recruiters[:MAX_CONTACTS - len(selected)])

    elif company_size == "mid_size":
        # Mix of hiring managers and recruiters
        selected.extend(hiring_managers[:2])
        if len(selected) < MAX_CONTACTS:
            selected.extend(recruiters[:1])
        if len(selected) < MAX_CONTACTS:
            selected.extend(team_members[:MAX_CONTACTS - len(selected)])

    elif company_size == "small":
        # Founders, team leads, then anyone
        selected.extend(hiring_managers[:2])
        if len(selected) < MAX_CONTACTS:
            selected.extend(team_members[:MAX_CONTACTS - len(selected)])
        if len(selected) < MAX_CONTACTS:
            selected.extend(recruiters[:MAX_CONTACTS - len(selected)])

    else:
        # Fallback: just use score order
        selected = contacts[:MAX_CONTACTS]

    # If we still don't have enough, fill from the full ranked list
    if len(selected) < MAX_CONTACTS:
        for c in contacts:
            if c not in selected:
                selected.append(c)
            if len(selected) >= MAX_CONTACTS:
                break

    return selected


def _find_name_drop(all_contacts: list[Contact],
                    selected: list[Contact],
                    job_title: str) -> Optional[Contact]:
    """
    Find a team member NOT in the selected list
    who can be used as a name-drop in the opener.
    """
    selected_names = {c.name.lower() for c in selected}

    for contact in all_contacts:
        if contact.name.lower() not in selected_names:
            if contact.contact_type == "team_member":
                # Check if they're in a relevant department
                title_lower = contact.title.lower()
                for keyword in DATA_DEPARTMENT_KEYWORDS:
                    if keyword in title_lower:
                        return contact
    return None
