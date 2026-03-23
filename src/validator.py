"""
Validator Agent — Neutral Standoff Judge
Compares Scout A (Grok) and Scout B (SerpAPI) outputs.
Picks the better list, logs the winner.
Can merge unique contacts from both lists.
"""
import json
import logging
from datetime import datetime
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, SCOUT_HAIKU_MODEL, MAX_CONTACTS, DATA_DIR
from contact import Contact

logger = logging.getLogger(__name__)
haiku = Anthropic(api_key=ANTHROPIC_API_KEY)

STANDOFF_LOG = DATA_DIR / "standoff_log.json"


def validate_standoff(grok_result: dict, serpapi_result: dict,
                      company: str, job_title: str) -> dict:
    """
    Compare two scout outputs and pick the best contacts.
    Returns: {contacts, winner, reason, merged, name_drop, company_size}
    """
    grok_contacts = grok_result.get("contacts", [])
    serp_contacts = serpapi_result.get("contacts", [])

    # If one scout returned nothing, the other wins by default
    if not grok_contacts and not serp_contacts:
        return _empty("Both scouts returned empty")
    if not grok_contacts:
        _log_result(company, "serpapi", "Grok returned empty")
        return _build_result(serp_contacts, "serpapi", "Grok returned empty",
                             serpapi_result.get("name_drop"), serpapi_result.get("company_size", "mid_size"))
    if not serp_contacts:
        _log_result(company, "grok", "SerpAPI returned empty")
        return _build_result(grok_contacts, "grok", "SerpAPI returned empty",
                             grok_result.get("name_drop"), grok_result.get("company_size", "mid_size"))

    # Both have contacts — let Haiku judge
    winner, reason, merged_contacts = _haiku_judge(
        grok_contacts, serp_contacts, company, job_title
    )

    # Use merged if Haiku returned them, otherwise use winner's list
    if merged_contacts:
        final_contacts = merged_contacts
    else:
        final_contacts = grok_contacts if winner == "grok" else serp_contacts

    name_drop = grok_result.get("name_drop") or serpapi_result.get("name_drop")
    company_size = grok_result.get("company_size", serpapi_result.get("company_size", "mid_size"))

    _log_result(company, winner, reason)

    return _build_result(final_contacts[:MAX_CONTACTS], winner, reason, name_drop, company_size)


def _haiku_judge(grok_contacts: list, serp_contacts: list,
                 company: str, job_title: str) -> tuple:
    """Use Haiku as neutral judge."""

    def _format_list(contacts, label):
        lines = []
        for i, c in enumerate(contacts, 1):
            url_status = "has LinkedIn URL" if c.linkedin_url else "no LinkedIn URL"
            lines.append(f"  {i}. {c.name} — {c.title} ({c.contact_type}) [{url_status}]")
        return f"{label}:\n" + "\n".join(lines)

    prompt = f"""You are a neutral judge evaluating two contact lists for cold outreach.
Company: {company}, Role: {job_title}

{_format_list(grok_contacts, "LIST A")}

{_format_list(serp_contacts, "LIST B")}

Evaluate on these criteria:
1. Are the people likely REAL and currently at {company}?
2. Do titles match the target team for a {job_title} role?
3. Is there a good mix of hiring manager + team member + recruiter?
4. Do contacts have LinkedIn URLs (stronger verification)?
5. Are any names found in BOTH lists (corroboration = very strong signal)?

Return ONLY valid JSON:
{{
    "winner": "list_a" or "list_b",
    "reason": "One sentence explaining why",
    "corroborated_names": ["names found in both lists"],
    "merge_recommended": true or false,
    "merged_indices": {{"from_a": [0, 1], "from_b": [2]}}
}}

If merge_recommended, pick the best contacts across both lists (max {MAX_CONTACTS}).
merged_indices uses 0-based indices into each list."""

    try:
        response = haiku.messages.create(
            model=SCOUT_HAIKU_MODEL,
            max_tokens=300,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start < 0 or end <= start:
            return "serpapi", "Could not parse judge response", None

        data = json.loads(text[start:end])
        winner = "grok" if data.get("winner") == "list_a" else "serpapi"
        reason = data.get("reason", "No reason given")

        merged = None
        if data.get("merge_recommended"):
            merged = []
            for idx in data.get("merged_indices", {}).get("from_a", []):
                if idx < len(grok_contacts):
                    merged.append(grok_contacts[idx])
            for idx in data.get("merged_indices", {}).get("from_b", []):
                if idx < len(serp_contacts):
                    merged.append(serp_contacts[idx])

        return winner, reason, merged

    except Exception as e:
        logger.error(f"Haiku judge failed: {e}")
        # Fallback: prefer SerpAPI (real Google results)
        return "serpapi", f"Judge failed ({e}), defaulting to SerpAPI", None


def _build_result(contacts, winner, reason, name_drop, company_size):
    return {
        "contacts": contacts,
        "winner": winner,
        "reason": reason,
        "name_drop": name_drop,
        "company_size": company_size,
    }


def _empty(reason):
    return {"contacts": [], "winner": "none", "reason": reason, "name_drop": None, "company_size": "mid_size"}


def _log_result(company: str, winner: str, reason: str):
    """Append to local standoff log for 30-day tracking."""
    try:
        log = []
        if STANDOFF_LOG.exists():
            with open(STANDOFF_LOG) as f:
                log = json.load(f)

        log.append({
            "date": datetime.now().isoformat(),
            "company": company,
            "winner": winner,
            "reason": reason,
        })

        # Keep last 30 days
        log = log[-500:]

        with open(STANDOFF_LOG, "w") as f:
            json.dump(log, f, indent=2)

    except Exception as e:
        logger.error(f"Failed to log standoff: {e}")


def get_standoff_stats() -> dict:
    """Get win counts for dashboard display."""
    try:
        if not STANDOFF_LOG.exists():
            return {"grok": 0, "serpapi": 0, "total": 0}
        with open(STANDOFF_LOG) as f:
            log = json.load(f)
        grok = sum(1 for e in log if e.get("winner") == "grok")
        serp = sum(1 for e in log if e.get("winner") == "serpapi")
        return {"grok": grok, "serpapi": serp, "total": len(log)}
    except Exception:
        return {"grok": 0, "serpapi": 0, "total": 0}
