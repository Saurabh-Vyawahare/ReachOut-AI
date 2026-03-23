"""
Quality Gate Agent
Scores each email 1-10 using Haiku. Rejects below threshold with specific feedback.
"""
import json
import logging
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, SCOUT_HAIKU_MODEL, QUALITY_GATE_MIN_SCORE

logger = logging.getLogger(__name__)
haiku = Anthropic(api_key=ANTHROPIC_API_KEY)


def score_email(email_body: str, contact_name: str, contact_type: str,
                job_title: str, company: str, jd_text: str) -> dict:
    """
    Score an email 1-10. Returns {score, passed, feedback}.
    """
    prompt = f"""Score this cold outreach email on a scale of 1-10.

CONTEXT: Email to {contact_name} ({contact_type}) about {job_title} at {company}.

EMAIL:
{email_body}

JD SUMMARY (first 500 chars):
{jd_text[:500]}

Score on these criteria:
1. JD SPECIFICITY (0-3): Does the opener reference something specific from this JD? Not generic.
2. SPAM RISK (0-2): Any "I hope this finds you well", percentages, or company names in bullet points?
3. STRUCTURE (0-2): Numbered points (not bullets)? Proper greeting and sign-off?
4. TONE (0-2): Confident but not desperate? Natural, not template-y?
5. RELEVANCE (0-1): Are the numbered points actually about what the JD asks for?

Return ONLY valid JSON:
{{
    "score": 8,
    "breakdown": {{"jd_specificity": 2, "spam_risk": 2, "structure": 2, "tone": 1, "relevance": 1}},
    "feedback": "One sentence on what to improve, or empty if score >= 7"
}}"""

    try:
        response = haiku.messages.create(
            model=SCOUT_HAIKU_MODEL,
            max_tokens=200,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start < 0 or end <= start:
            return {"score": 7, "passed": True, "feedback": "Could not parse QG response"}

        data = json.loads(text[start:end])
        score = int(data.get("score", 7))
        score = max(1, min(10, score))  # clamp

        return {
            "score": score,
            "passed": score >= QUALITY_GATE_MIN_SCORE,
            "feedback": data.get("feedback", ""),
            "breakdown": data.get("breakdown", {}),
        }

    except Exception as e:
        logger.error(f"Quality gate failed: {e}")
        return {"score": 7, "passed": True, "feedback": f"QG error: {e}"}


def score_batch(emails: list, job_title: str, company: str, jd_text: str) -> list:
    """Score a batch of emails. Returns list of {email_data, score_result}."""
    results = []
    for email_data in emails:
        score_result = score_email(
            email_body=email_data["body"],
            contact_name=email_data["contact_name"],
            contact_type=email_data["contact_type"],
            job_title=job_title,
            company=company,
            jd_text=jd_text,
        )
        results.append({
            **email_data,
            "score": score_result["score"],
            "passed": score_result["passed"],
            "feedback": score_result["feedback"],
        })
        logger.info(
            f"QG: {email_data['contact_name']} → {score_result['score']}/10 "
            f"({'PASS' if score_result['passed'] else 'REJECT: ' + score_result['feedback']})"
        )
    return results
