"""
Contact model shared across scouts and validators.
"""
from config import HIRING_MANAGER_TITLES, RECRUITER_TITLES


class Contact:
    """Represents a potential outreach contact."""

    def __init__(self, name: str, title: str, company: str,
                 linkedin_url: str = "", source: str = "unknown",
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

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "company": self.company,
            "linkedin_url": self.linkedin_url,
            "source": self.source,
            "contact_type": self.contact_type,
        }
