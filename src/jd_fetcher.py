"""
JD Fetcher Module
Fetches job descriptions from URLs (Greenhouse, Lever, Workday, etc.)
Falls back to treating the content as raw JD text if URL fetch fails.
"""
import re
import requests
import logging
from bs4 import BeautifulSoup
from config import SECTOR_KEYWORDS

logger = logging.getLogger(__name__)


def fetch_jd(jd_input: str) -> dict:
    """
    Main entry point. Takes either a URL or raw JD text.

    Returns:
        {
            "jd_text": str,        # The full JD text
            "sector": str,         # Detected sector
            "source": str,         # "url" or "raw_text"
            "fetch_success": bool, # Whether URL fetch worked
            "error": str or None
        }
    """
    jd_input = jd_input.strip()

    # Check if it's a URL
    if jd_input.startswith("http://") or jd_input.startswith("https://"):
        jd_text, success, error = _fetch_from_url(jd_input)
        if success:
            sector = detect_sector(jd_text)
            return {
                "jd_text": jd_text,
                "sector": sector,
                "source": "url",
                "fetch_success": True,
                "error": None
            }
        else:
            return {
                "jd_text": "",
                "sector": "tech",  # default
                "source": "url",
                "fetch_success": False,
                "error": error
            }
    else:
        # Treat as raw JD text
        sector = detect_sector(jd_input)
        return {
            "jd_text": jd_input,
            "sector": sector,
            "source": "raw_text",
            "fetch_success": True,
            "error": None
        }


def _fetch_from_url(url: str) -> tuple[str, bool, str]:
    """
    Fetch JD from a URL. Handles Greenhouse, Lever, Workday,
    and generic career pages.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=20,
                                allow_redirects=True)

        # Check for login walls / redirects
        if response.status_code != 200:
            return "", False, f"HTTP {response.status_code}"

        if "login" in response.url.lower() or "signin" in response.url.lower():
            return "", False, "Login required"

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            return "", False, f"Not HTML: {content_type}"

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Try platform-specific extractors first
        jd_text = None

        # Greenhouse
        if "greenhouse.io" in url or "boards.greenhouse" in url:
            jd_text = _extract_greenhouse(soup)

        # Lever
        elif "lever.co" in url or "jobs.lever" in url:
            jd_text = _extract_lever(soup)

        # Workday
        elif "myworkdayjobs.com" in url or "workday.com" in url:
            jd_text = _extract_workday(soup)

        # Ashby
        elif "ashbyhq.com" in url:
            jd_text = _extract_ashby(soup)

        # Generic fallback
        if not jd_text:
            jd_text = _extract_generic(soup)

        if jd_text and len(jd_text) > 100:
            return _clean_text(jd_text), True, None
        else:
            return "", False, "Could not extract JD content"

    except requests.Timeout:
        return "", False, "Request timed out"
    except Exception as e:
        return "", False, f"Fetch error: {str(e)}"


def _extract_greenhouse(soup: BeautifulSoup) -> str:
    """Extract JD from Greenhouse job pages."""
    # Greenhouse uses #content or .job-post
    content = soup.find(id="content")
    if not content:
        content = soup.find(class_="job-post")
    if not content:
        content = soup.find("div", {"class": re.compile(r"job|posting|content")})
    return content.get_text(separator="\n") if content else None


def _extract_lever(soup: BeautifulSoup) -> str:
    """Extract JD from Lever job pages."""
    content = soup.find("div", {"class": "posting-page"})
    if not content:
        content = soup.find("div", {"class": re.compile(r"content|posting")})
    return content.get_text(separator="\n") if content else None


def _extract_workday(soup: BeautifulSoup) -> str:
    """Extract JD from Workday job pages."""
    # Workday pages are often JS-rendered, might not work perfectly
    content = soup.find("div", {"data-automation-id": "jobPostingDescription"})
    if not content:
        content = soup.find("div", {"class": re.compile(r"job|description|posting")})
    return content.get_text(separator="\n") if content else None


def _extract_ashby(soup: BeautifulSoup) -> str:
    """Extract JD from Ashby job pages."""
    content = soup.find("div", {"class": re.compile(r"ashby-job-posting")})
    if not content:
        content = soup.find("main")
    return content.get_text(separator="\n") if content else None


def _extract_generic(soup: BeautifulSoup) -> str:
    """
    Generic JD extraction. Looks for the largest text block
    that contains job-related keywords.
    """
    # Try common containers
    for selector in [
        "main", "article",
        {"class": re.compile(r"job|posting|description|content|details")},
        {"id": re.compile(r"job|posting|description|content")},
    ]:
        if isinstance(selector, str):
            element = soup.find(selector)
        else:
            element = soup.find("div", selector)
        if element:
            text = element.get_text(separator="\n")
            if len(text) > 200:
                return text

    # Last resort: get the body text
    body = soup.find("body")
    return body.get_text(separator="\n") if body else None


def _clean_text(text: str) -> str:
    """Clean extracted text."""
    # Remove excessive whitespace
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        line = line.strip()
        if line:
            cleaned.append(line)
    text = "\n".join(cleaned)

    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Truncate if too long (keep first 5000 chars for AI processing)
    if len(text) > 5000:
        text = text[:5000] + "\n\n[Truncated]"

    return text


def detect_sector(jd_text: str) -> str:
    """
    Detect the sector/industry from JD text.
    Returns: "healthcare", "finance", "retail", or "tech" (default)
    """
    jd_lower = jd_text.lower()
    scores = {}

    for sector, keywords in SECTOR_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            count = jd_lower.count(keyword)
            score += count
        scores[sector] = score

    # Get the highest scoring sector
    best_sector = max(scores, key=scores.get)

    # If no strong signal, default to tech
    if scores[best_sector] < 3:
        return "tech"

    return best_sector
