"""
JD Analyzer Agent (v2)
Fetches JD from URL, extracts key requirements, maps to Saurabh's experience.
Produces structured output used by both scouts AND the email composer.
Uses Claude Haiku for cheap, fast analysis.
"""
import re
import json
import requests
import logging
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from anthropic import Anthropic
from config import (
    ANTHROPIC_API_KEY, SCOUT_HAIKU_MODEL, SECTOR_KEYWORDS, SENDER_EXPERIENCE
)

logger = logging.getLogger(__name__)
client = Anthropic(api_key=ANTHROPIC_API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}


def analyze_jd(jd_input: str) -> dict:
    """
    Main entry: fetch JD text, then use Haiku to extract structured skill map.
    Returns: {jd_text, team, sector, company_size_hint, critical_skills: [{jd_need, saurabh_match}]}
    """
    jd_text, fetch_success, error = _get_jd_text(jd_input)

    if not fetch_success or not jd_text or len(jd_text) < 50:
        logger.warning(f"JD fetch failed or too short: {error}")
        return {
            "jd_text": jd_text or "",
            "team": "Data",
            "sector": "tech",
            "company_size_hint": "mid_size",
            "critical_skills": [],
            "fetch_success": False,
            "error": error,
        }

    sector = _detect_sector(jd_text)
    skill_map = _map_skills_with_haiku(jd_text)

    return {
        "jd_text": jd_text,
        "team": skill_map.get("team", "Data"),
        "sector": sector,
        "company_size_hint": skill_map.get("company_size_hint", "mid_size"),
        "critical_skills": skill_map.get("critical_skills", []),
        "fetch_success": True,
        "error": None,
    }


def _map_skills_with_haiku(jd_text: str) -> dict:
    """Use Haiku to extract team name, critical skills, and map to Saurabh's experience."""
    prompt = f"""Analyze this job description and return a JSON object.

JOB DESCRIPTION:
{jd_text[:3000]}

SAURABH'S EXPERIENCE:
{SENDER_EXPERIENCE}

Return ONLY valid JSON, no other text:
{{
    "team": "the specific team this role belongs to (e.g. Revenue Analytics, not just Data)",
    "company_size_hint": "large_enterprise" or "mid_size" or "small",
    "critical_skills": [
        {{
            "jd_need": "what the JD specifically asks for (1 sentence)",
            "saurabh_match": "which of Saurabh's experience points maps to this (1 sentence)"
        }}
    ]
}}

Rules:
- Extract the 2-3 MOST CRITICAL skills from the JD, not everything.
- Map each to Saurabh's actual experience, not generic claims.
- "team" should be specific: "Revenue Analytics" not "Analytics".
- If you can't determine company size, default to "mid_size"."""

    try:
        response = client.messages.create(
            model=SCOUT_HAIKU_MODEL,
            max_tokens=500,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()

        # Parse JSON
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        return {}

    except Exception as e:
        logger.error(f"Haiku skill mapping failed: {e}")
        return {}


# ─── JD Fetching (carried over from v1 jd_fetcher.py) ────────

def _get_jd_text(jd_input: str) -> tuple:
    """Fetch JD from URL or use raw text."""
    jd_input = jd_input.strip()
    if jd_input.startswith("http://") or jd_input.startswith("https://"):
        return _fetch_from_url(jd_input)
    else:
        return jd_input, True, None


def _fetch_from_url(url: str) -> tuple:
    """Route to best extraction method based on URL."""
    try:
        if "ashbyhq.com" in url:
            return _fetch_ashby_api(url)
        if "greenhouse.io" in url or "boards.greenhouse" in url:
            result = _fetch_greenhouse_api(url)
            if result[1]:
                return result

        response = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        if response.status_code != 200:
            return "", False, f"HTTP {response.status_code}"
        if "login" in response.url.lower() or "signin" in response.url.lower():
            return "", False, "Login required"

        soup = BeautifulSoup(response.text, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        jd_text = None
        if "greenhouse.io" in url or "boards.greenhouse" in url:
            jd_text = _extract_greenhouse(soup)
        elif "lever.co" in url or "jobs.lever" in url:
            jd_text = _extract_lever(soup)
        elif "myworkdayjobs.com" in url or "workday.com" in url:
            jd_text = _extract_workday(soup)

        if not jd_text or len(jd_text) < 100:
            jd_text = _extract_generic(soup)

        if jd_text and len(jd_text) > 100:
            return _clean_text(jd_text), True, None

        jd_text = _extract_json_ld(soup)
        if jd_text and len(jd_text) > 100:
            return _clean_text(jd_text), True, None

        return "", False, "Could not extract JD content"

    except requests.Timeout:
        return "", False, "Request timed out"
    except Exception as e:
        return "", False, f"Fetch error: {str(e)}"


def _fetch_ashby_api(url: str) -> tuple:
    try:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(path_parts) < 1:
            return "", False, "Could not parse Ashby URL"
        company_name = path_parts[0]
        job_id = path_parts[1] if len(path_parts) > 1 else None
        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{company_name}?includeCompensation=true"
        response = requests.get(api_url, timeout=15)
        if response.status_code != 200:
            return "", False, f"Ashby API returned {response.status_code}"
        data = response.json()
        jobs = data.get("jobs", [])
        if not jobs:
            return "", False, "No jobs found on Ashby board"
        if job_id:
            for job in jobs:
                if job_id in job.get("jobUrl", ""):
                    jd_text = job.get("descriptionPlain", "")
                    if not jd_text:
                        html_desc = job.get("descriptionHtml", "")
                        if html_desc:
                            jd_text = BeautifulSoup(html_desc, "html.parser").get_text(separator="\n")
                    if jd_text:
                        title = job.get("title", "")
                        location = job.get("location", "")
                        return _clean_text(f"Title: {title}\nLocation: {location}\n\n{jd_text}"), True, None
        for job in jobs:
            jd_text = job.get("descriptionPlain", "")
            if jd_text and len(jd_text) > 100:
                title = job.get("title", "")
                return _clean_text(f"Title: {title}\n\n{jd_text}"), True, None
        return "", False, "Could not find matching job on Ashby"
    except Exception as e:
        return "", False, f"Ashby API error: {str(e)}"


def _fetch_greenhouse_api(url: str) -> tuple:
    try:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        company_name, job_id = None, None
        for i, part in enumerate(path_parts):
            if part == "jobs" and i + 1 < len(path_parts):
                job_id = path_parts[i + 1]
                company_name = path_parts[i - 1] if i > 0 else None
        if not company_name or not job_id:
            return "", False, "Could not parse Greenhouse URL"
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{company_name}/jobs/{job_id}"
        response = requests.get(api_url, timeout=15)
        if response.status_code != 200:
            return "", False, f"Greenhouse API returned {response.status_code}"
        data = response.json()
        content = data.get("content", "")
        if content:
            jd_text = BeautifulSoup(content, "html.parser").get_text(separator="\n")
            title = data.get("title", "")
            location = data.get("location", {}).get("name", "")
            return _clean_text(f"Title: {title}\nLocation: {location}\n\n{jd_text}"), True, None
        return "", False, "No content in Greenhouse API response"
    except Exception as e:
        return "", False, f"Greenhouse API error: {str(e)}"


def _extract_greenhouse(soup):
    content = soup.find(id="content") or soup.find(class_="job-post") or soup.find("div", {"class": re.compile(r"job|posting|content")})
    return content.get_text(separator="\n") if content else None

def _extract_lever(soup):
    content = soup.find("div", {"class": "posting-page"}) or soup.find("div", {"class": re.compile(r"content|posting")})
    return content.get_text(separator="\n") if content else None

def _extract_workday(soup):
    for selector in [{"data-automation-id": "jobPostingDescription"}, {"class": re.compile(r"job.*description")}, {"id": re.compile(r"job|posting")}]:
        content = soup.find("div", selector)
        if content and len(content.get_text()) > 100:
            return content.get_text(separator="\n")
    return None

def _extract_json_ld(soup):
    scripts = soup.find_all("script", {"type": "application/ld+json"})
    for script in scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                for item in data:
                    if item.get("@type") == "JobPosting":
                        data = item
                        break
            if data.get("@type") == "JobPosting":
                parts = []
                if data.get("title"): parts.append(f"Title: {data['title']}")
                if data.get("description"):
                    desc = data["description"]
                    if "<" in desc:
                        desc = BeautifulSoup(desc, "html.parser").get_text(separator="\n")
                    parts.append(desc)
                return "\n".join(parts)
        except (json.JSONDecodeError, AttributeError):
            continue
    return None

def _extract_generic(soup):
    for selector in ["main", "article", {"class": re.compile(r"job|posting|description|content")}, {"role": "main"}]:
        element = soup.find(selector) if isinstance(selector, str) else soup.find("div", selector)
        if element:
            text = element.get_text(separator="\n")
            if len(text) > 200: return text
    body = soup.find("body")
    if body: return body.get_text(separator="\n")
    return None

def _clean_text(text: str) -> str:
    lines = text.split("\n")
    cleaned = [line.strip() for line in lines if line.strip()]
    text = "\n".join(cleaned)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text[:5000] + "\n\n[Truncated]" if len(text) > 5000 else text

def _detect_sector(jd_text: str) -> str:
    jd_lower = jd_text.lower()
    scores = {sector: sum(jd_lower.count(kw) for kw in keywords) for sector, keywords in SECTOR_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 3 else "tech"
