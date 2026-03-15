"""
JD Fetcher Module (v2 - Robust)
Fetches job descriptions from URLs using platform-specific APIs where possible.
Ashby, Greenhouse → use their public JSON APIs (no HTML parsing needed).
Lever, generic → HTML parsing with BeautifulSoup.
Workday → JS-rendered, attempt HTML but warn if fails.
"""
import re
import json
import requests
import logging
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from config import SECTOR_KEYWORDS

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}


def fetch_jd(jd_input: str) -> dict:
    """
    Main entry point. Takes either a URL or raw JD text.
    """
    jd_input = jd_input.strip()

    if jd_input.startswith("http://") or jd_input.startswith("https://"):
        jd_text, success, error = _fetch_from_url(jd_input)
        if success:
            sector = detect_sector(jd_text)
            return {"jd_text": jd_text, "sector": sector, "source": "url",
                    "fetch_success": True, "error": None}
        else:
            return {"jd_text": "", "sector": "tech", "source": "url",
                    "fetch_success": False, "error": error}
    else:
        sector = detect_sector(jd_input)
        return {"jd_text": jd_input, "sector": sector, "source": "raw_text",
                "fetch_success": True, "error": None}


def _fetch_from_url(url: str) -> tuple[str, bool, str]:
    """Route to the best extraction method based on URL."""
    try:
        # ─── ASHBY: Use public JSON API (no HTML needed) ────────
        if "ashbyhq.com" in url:
            return _fetch_ashby_api(url)

        # ─── GREENHOUSE: Use JSON API if possible ────────────────
        if "greenhouse.io" in url or "boards.greenhouse" in url:
            result = _fetch_greenhouse_api(url)
            if result[1]:  # success
                return result
            # Fall through to HTML if API fails

        # ─── HTML-based fetching for everything else ─────────────
        response = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)

        if response.status_code != 200:
            return "", False, f"HTTP {response.status_code}"

        if "login" in response.url.lower() or "signin" in response.url.lower():
            return "", False, "Login required"

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "application/json" not in content_type:
            return "", False, f"Not HTML: {content_type}"

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove noise
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        jd_text = None

        # Platform-specific extractors
        if "greenhouse.io" in url or "boards.greenhouse" in url:
            jd_text = _extract_greenhouse(soup)
        elif "lever.co" in url or "jobs.lever" in url:
            jd_text = _extract_lever(soup)
        elif "myworkdayjobs.com" in url or "workday.com" in url or ".wd1." in url or ".wd5." in url:
            jd_text = _extract_workday(soup)
        elif "avature.net" in url:
            jd_text = _extract_avature(soup)
        elif "adp.com" in url or "workforcenow" in url:
            jd_text = _extract_adp(soup)

        # Generic fallback
        if not jd_text or len(jd_text) < 100:
            jd_text = _extract_generic(soup)

        if jd_text and len(jd_text) > 100:
            return _clean_text(jd_text), True, None
        else:
            # Last resort: check if page has JSON-LD structured data
            jd_text = _extract_json_ld(soup)
            if jd_text and len(jd_text) > 100:
                return _clean_text(jd_text), True, None
            return "", False, "Could not extract JD content (page may be JS-rendered)"

    except requests.Timeout:
        return "", False, "Request timed out"
    except Exception as e:
        return "", False, f"Fetch error: {str(e)}"


# ─── API-BASED EXTRACTORS (most reliable) ─────────────────────

def _fetch_ashby_api(url: str) -> tuple[str, bool, str]:
    """
    Fetch JD from Ashby's free public API.
    URL format: jobs.ashbyhq.com/{company}/{job-id}
    API: GET https://api.ashbyhq.com/posting-api/job-board/{company}
    """
    try:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]

        if len(path_parts) < 1:
            return "", False, "Could not parse Ashby URL"

        company_name = path_parts[0]
        job_id = path_parts[1] if len(path_parts) > 1 else None

        # Fetch all jobs for this company
        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{company_name}?includeCompensation=true"
        response = requests.get(api_url, timeout=15)

        if response.status_code != 200:
            return "", False, f"Ashby API returned {response.status_code}"

        data = response.json()
        jobs = data.get("jobs", [])

        if not jobs:
            return "", False, "No jobs found on Ashby board"

        # Find the specific job by ID in URL
        if job_id:
            for job in jobs:
                job_url = job.get("jobUrl", "")
                if job_id in job_url:
                    jd_text = job.get("descriptionPlain", "")
                    if not jd_text:
                        # Fall back to HTML description
                        html_desc = job.get("descriptionHtml", "")
                        if html_desc:
                            soup = BeautifulSoup(html_desc, "html.parser")
                            jd_text = soup.get_text(separator="\n")

                    if jd_text:
                        # Prepend title and location for context
                        title = job.get("title", "")
                        location = job.get("location", "")
                        department = job.get("department", "")
                        prefix = f"Title: {title}\nLocation: {location}\nDepartment: {department}\n\n"
                        return _clean_text(prefix + jd_text), True, None

        # If no specific match, try first job (or return all titles)
        if jobs:
            # Try matching by title similarity
            for job in jobs:
                jd_text = job.get("descriptionPlain", "")
                if jd_text and len(jd_text) > 100:
                    title = job.get("title", "")
                    location = job.get("location", "")
                    prefix = f"Title: {title}\nLocation: {location}\n\n"
                    return _clean_text(prefix + jd_text), True, None

        return "", False, "Could not find matching job on Ashby"

    except Exception as e:
        return "", False, f"Ashby API error: {str(e)}"


def _fetch_greenhouse_api(url: str) -> tuple[str, bool, str]:
    """
    Fetch JD from Greenhouse's embed API.
    URL format: boards.greenhouse.io/company/jobs/12345
    or: job-boards.greenhouse.io/company/jobs/12345
    API: GET https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{id}
    """
    try:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]

        # Find company and job ID
        company_name = None
        job_id = None

        for i, part in enumerate(path_parts):
            if part == "jobs" and i + 1 < len(path_parts):
                job_id = path_parts[i + 1]
                company_name = path_parts[i - 1] if i > 0 else None
            elif part == "job" and i + 1 < len(path_parts):
                job_id = path_parts[i + 1]
                company_name = path_parts[0] if path_parts else None

        # Also try embed format: /embed/job/12345
        if not job_id:
            for i, part in enumerate(path_parts):
                if part.isdigit() and len(part) > 5:
                    job_id = part
                    break

        if not company_name or not job_id:
            return "", False, "Could not parse Greenhouse URL"

        api_url = f"https://boards-api.greenhouse.io/v1/boards/{company_name}/jobs/{job_id}"
        response = requests.get(api_url, timeout=15)

        if response.status_code != 200:
            return "", False, f"Greenhouse API returned {response.status_code}"

        data = response.json()
        content = data.get("content", "")

        if content:
            soup = BeautifulSoup(content, "html.parser")
            jd_text = soup.get_text(separator="\n")
            title = data.get("title", "")
            location = data.get("location", {}).get("name", "")
            prefix = f"Title: {title}\nLocation: {location}\n\n"
            return _clean_text(prefix + jd_text), True, None

        return "", False, "No content in Greenhouse API response"

    except Exception as e:
        return "", False, f"Greenhouse API error: {str(e)}"


# ─── HTML-BASED EXTRACTORS (fallback) ─────────────────────────

def _extract_greenhouse(soup: BeautifulSoup) -> str:
    content = soup.find(id="content")
    if not content:
        content = soup.find(class_="job-post")
    if not content:
        content = soup.find("div", {"class": re.compile(r"job|posting|content")})
    return content.get_text(separator="\n") if content else None


def _extract_lever(soup: BeautifulSoup) -> str:
    content = soup.find("div", {"class": "posting-page"})
    if not content:
        content = soup.find("div", {"class": re.compile(r"content|posting")})
    return content.get_text(separator="\n") if content else None


def _extract_workday(soup: BeautifulSoup) -> str:
    """Workday pages are JS-rendered. Try multiple selectors."""
    for selector in [
        {"data-automation-id": "jobPostingDescription"},
        {"class": re.compile(r"job.*description|posting.*description")},
        {"class": re.compile(r"css-")},  # Workday uses CSS module classes
        {"id": re.compile(r"job|posting")},
    ]:
        content = soup.find("div", selector)
        if content and len(content.get_text()) > 100:
            return content.get_text(separator="\n")
    return None


def _extract_avature(soup: BeautifulSoup) -> str:
    """Avature (used by companies like Ally)."""
    for selector in [
        {"class": re.compile(r"job-detail|job-description|posting")},
        {"id": re.compile(r"job|posting|description")},
        "article", "main"
    ]:
        if isinstance(selector, str):
            content = soup.find(selector)
        else:
            content = soup.find("div", selector)
        if content and len(content.get_text()) > 100:
            return content.get_text(separator="\n")
    return None


def _extract_adp(soup: BeautifulSoup) -> str:
    """ADP/WorkforceNow (used by companies like REVOLVE)."""
    for selector in [
        {"class": re.compile(r"job|posting|description|details")},
        {"id": re.compile(r"job|posting|requisition")},
        "main", "article"
    ]:
        if isinstance(selector, str):
            content = soup.find(selector)
        else:
            content = soup.find("div", selector)
        if content and len(content.get_text()) > 100:
            return content.get_text(separator="\n")
    return None


def _extract_json_ld(soup: BeautifulSoup) -> str:
    """
    Extract from JSON-LD structured data (schema.org/JobPosting).
    Many career sites embed this even when the visible content is JS-rendered.
    """
    scripts = soup.find_all("script", {"type": "application/ld+json"})
    for script in scripts:
        try:
            data = json.loads(script.string)
            # Handle both single object and array
            if isinstance(data, list):
                for item in data:
                    if item.get("@type") == "JobPosting":
                        data = item
                        break
            if data.get("@type") == "JobPosting":
                parts = []
                if data.get("title"):
                    parts.append(f"Title: {data['title']}")
                if data.get("jobLocation"):
                    loc = data["jobLocation"]
                    if isinstance(loc, dict):
                        address = loc.get("address", {})
                        parts.append(f"Location: {address.get('addressLocality', '')} {address.get('addressRegion', '')}")
                if data.get("description"):
                    desc = data["description"]
                    # Description might be HTML
                    if "<" in desc:
                        desc_soup = BeautifulSoup(desc, "html.parser")
                        desc = desc_soup.get_text(separator="\n")
                    parts.append(f"\n{desc}")
                return "\n".join(parts)
        except (json.JSONDecodeError, AttributeError):
            continue
    return None


def _extract_generic(soup: BeautifulSoup) -> str:
    """Generic extraction. Tries multiple strategies."""
    # Strategy 1: Common containers
    for selector in [
        "main", "article",
        {"class": re.compile(r"job|posting|description|content|details|requisition")},
        {"id": re.compile(r"job|posting|description|content|requisition")},
        {"role": "main"},
    ]:
        if isinstance(selector, str):
            element = soup.find(selector)
        else:
            element = soup.find("div", selector)
        if element:
            text = element.get_text(separator="\n")
            if len(text) > 200:
                return text

    # Strategy 2: Find the largest text block in the page
    body = soup.find("body")
    if body:
        divs = body.find_all("div")
        largest = ""
        for div in divs:
            text = div.get_text(separator="\n")
            if len(text) > len(largest) and len(text) > 200:
                largest = text
        if largest:
            return largest

    # Strategy 3: Just get body text
    if body:
        return body.get_text(separator="\n")

    return None


def _clean_text(text: str) -> str:
    lines = text.split("\n")
    cleaned = [line.strip() for line in lines if line.strip()]
    text = "\n".join(cleaned)
    text = re.sub(r'\n{3,}', '\n\n', text)
    if len(text) > 5000:
        text = text[:5000] + "\n\n[Truncated]"
    return text


def detect_sector(jd_text: str) -> str:
    jd_lower = jd_text.lower()
    scores = {}
    for sector, keywords in SECTOR_KEYWORDS.items():
        score = sum(jd_lower.count(kw) for kw in keywords)
        scores[sector] = score
    best_sector = max(scores, key=scores.get)
    return best_sector if scores[best_sector] >= 3 else "tech"
