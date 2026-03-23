"""
Scout B — SerpAPI + Claude Haiku
Google search returns real LinkedIn results (no hallucination).
Haiku parses the search snippets to extract contacts.
"""
import json
import logging
import requests
from anthropic import Anthropic
from config import SERPAPI_KEY, ANTHROPIC_API_KEY, SCOUT_HAIKU_MODEL, MAX_CONTACTS, SERPAPI_SEARCHES_PER_COMPANY
from contact import Contact

logger = logging.getLogger(__name__)
haiku = Anthropic(api_key=ANTHROPIC_API_KEY)


def scout_serpapi(company: str, job_title: str, location: str, team: str = "Data") -> dict:
    """
    Run Google search via SerpAPI, then parse results with Haiku.
    Returns: {contacts: [Contact], company_size, name_drop, notes, source: "serpapi"}
    """
    if not SERPAPI_KEY:
        logger.error("SERPAPI_KEY not set — Scout B disabled")
        return _empty("SERPAPI_KEY not configured")

    # Run 2 targeted searches — location baked into query, not API param
    location_str = f' "{location}"' if location and location.lower() != "remote" else ""
    queries = [
        f'"{company}" "{team}" "Director" OR "VP" OR "Head of"{location_str} site:linkedin.com/in',
        f'"{company}" "recruiter" OR "talent acquisition" "data" OR "analytics" site:linkedin.com/in',
    ]

    all_results = []
    for q in queries[:SERPAPI_SEARCHES_PER_COMPANY]:
        results = _search_google(q, location)
        all_results.extend(results)

    if not all_results:
        logger.warning(f"SerpAPI returned 0 results for {company}")
        return _empty("No LinkedIn results found")

    # Parse with Haiku
    contacts = _parse_with_haiku(all_results, company, job_title, team, location)

    return {
        "contacts": contacts[:MAX_CONTACTS],
        "company_size": "mid_size",  # SerpAPI doesn't tell us this
        "name_drop": contacts[MAX_CONTACTS] if len(contacts) > MAX_CONTACTS else None,
        "notes": f"SerpAPI: {len(contacts)} found from {len(all_results)} search results",
        "source": "serpapi",
    }


def _search_google(query: str, location: str = "") -> list:
    """Call SerpAPI and return organic results."""
    try:
        params = {
            "engine": "google",
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": 10,
        }
        # Don't pass location param — causes 400 on free tier
        # Instead, bake location into the query string if needed

        response = requests.get("https://serpapi.com/search", params=params, timeout=15)

        if response.status_code != 200:
            error_detail = ""
            try:
                error_detail = response.json().get("error", response.text[:200])
            except Exception:
                error_detail = response.text[:200]
            logger.error(f"SerpAPI HTTP {response.status_code}: {error_detail}")
            return []

        data = response.json()
        results = []
        for r in data.get("organic_results", []):
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "link": r.get("link", ""),
            })
        return results

    except Exception as e:
        logger.error(f"SerpAPI search failed: {e}")
        return []


def _parse_with_haiku(results: list, company: str, job_title: str, team: str, location: str) -> list:
    """Use Haiku to extract contacts from search result snippets."""
    results_text = "\n\n".join([
        f"Title: {r['title']}\nSnippet: {r['snippet']}\nURL: {r['link']}"
        for r in results[:15]
    ])

    prompt = f"""Extract real people from these LinkedIn search results for {company}.

TARGET: People on the {team} team at {company}, relevant to a {job_title} role.
LOCATION PREFERENCE: {location or 'any'}

SEARCH RESULTS:
{results_text}

For each person found, extract:
- Full name (from the LinkedIn title/snippet)
- Current job title at {company}
- LinkedIn URL
- Type: "hiring_manager", "recruiter", or "team_member"

RULES:
- Only extract people who CURRENTLY work at {company} (based on the snippet).
- If the snippet says they left or work elsewhere, skip them.
- LinkedIn URLs must contain "linkedin.com/in/" to be valid.
- Return up to 5 contacts, prioritize hiring managers and team leads.

Return ONLY valid JSON:
{{
    "contacts": [
        {{"name": "Full Name", "title": "Job Title", "linkedin_url": "https://linkedin.com/in/...", "type": "hiring_manager"}}
    ]
}}"""

    try:
        response = haiku.messages.create(
            model=SCOUT_HAIKU_MODEL,
            max_tokens=500,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            return []

        data = json.loads(text[start:end])
        contacts = []
        for c in data.get("contacts", []):
            contact = Contact(
                name=c.get("name", ""),
                title=c.get("title", ""),
                company=company,
                linkedin_url=c.get("linkedin_url", ""),
                source="serpapi",
            )
            ptype = c.get("type", "")
            if ptype in ["hiring_manager", "recruiter", "team_member"]:
                contact.contact_type = ptype
            contacts.append(contact)

        return contacts

    except Exception as e:
        logger.error(f"Haiku parse failed: {e}")
        return []


def _empty(error: str) -> dict:
    return {"contacts": [], "company_size": "mid_size", "name_drop": None, "notes": f"SerpAPI failed: {error}", "source": "serpapi"}
