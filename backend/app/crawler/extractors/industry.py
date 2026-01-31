from __future__ import annotations

import re

from bs4 import BeautifulSoup

_INDUSTRY_KEYWORDS: dict[str, list[str]] = {
    "healthcare": [
        "health", "medical", "patient", "clinical", "hospital", "pharmacy",
        "telemedicine", "diagnosis", "treatment", "wellness", "therapeutic",
        "healthcare", "hipaa", "ehr", "emr",
    ],
    "fintech": [
        "fintech", "banking", "payment", "lending", "insurance", "trading",
        "investment", "financial", "mortgage", "crypto", "blockchain",
        "wallet", "neobank", "transactions",
    ],
    "edtech": [
        "education", "learning", "student", "teacher", "course", "curriculum",
        "classroom", "edtech", "tutoring", "university", "school",
        "e-learning", "training", "lms",
    ],
    "ecommerce": [
        "shop", "store", "cart", "checkout", "product", "buy", "purchase",
        "ecommerce", "e-commerce", "retail", "marketplace", "shipping",
        "catalog", "inventory",
    ],
    "saas": [
        "saas", "platform", "software", "dashboard", "api", "integration",
        "workflow", "automation", "subscription", "cloud", "deploy",
        "analytics", "crm", "erp",
    ],
    "real_estate": [
        "real estate", "property", "listing", "rent", "lease", "mortgage",
        "apartment", "housing", "broker", "realty", "homes for sale",
        "commercial property",
    ],
    "food": [
        "restaurant", "food", "recipe", "meal", "delivery", "catering",
        "menu", "cuisine", "dining", "chef", "ingredients", "grocery",
    ],
    "fashion": [
        "fashion", "clothing", "apparel", "wear", "style", "designer",
        "collection", "outfit", "boutique", "garment", "textile",
    ],
    "fitness": [
        "fitness", "gym", "workout", "exercise", "training", "wellness",
        "nutrition", "yoga", "crossfit", "personal trainer", "health club",
    ],
    "travel": [
        "travel", "hotel", "booking", "flight", "vacation", "tourism",
        "destination", "resort", "itinerary", "accommodation", "airfare",
    ],
    "legal": [
        "legal", "law firm", "attorney", "lawyer", "litigation", "contract",
        "compliance", "court", "paralegal", "counsel", "arbitration",
    ],
    "construction": [
        "construction", "building", "contractor", "architect", "renovation",
        "engineering", "infrastructure", "concrete", "blueprint", "permit",
    ],
    "automotive": [
        "automotive", "vehicle", "car", "auto", "dealership", "motor",
        "electric vehicle", "fleet", "mechanic", "parts", "tire",
    ],
    "marketing": [
        "marketing", "advertising", "seo", "social media", "campaign",
        "branding", "content marketing", "email marketing", "ppc", "agency",
    ],
    "cybersecurity": [
        "security", "cybersecurity", "threat", "vulnerability", "firewall",
        "encryption", "penetration testing", "soc", "siem", "compliance",
    ],
    "hr_tech": [
        "hr", "human resources", "recruitment", "hiring", "talent",
        "payroll", "onboarding", "applicant", "employee engagement",
    ],
    "logistics": [
        "logistics", "supply chain", "shipping", "freight", "warehouse",
        "tracking", "fulfillment", "fleet management", "last mile",
    ],
    "media": [
        "media", "publishing", "news", "content", "streaming", "podcast",
        "video", "entertainment", "broadcast", "journalism",
    ],
    "agriculture": [
        "agriculture", "farming", "crop", "harvest", "livestock",
        "agritech", "precision farming", "fertilizer", "irrigation",
    ],
}

# Pre-compile patterns for efficiency
_INDUSTRY_PATTERNS: dict[str, re.Pattern] = {
    industry: re.compile(
        r"\b(?:" + "|".join(re.escape(kw) for kw in keywords) + r")\b",
        re.IGNORECASE,
    )
    for industry, keywords in _INDUSTRY_KEYWORDS.items()
}


def extract_industry(pages: dict[str, str]) -> dict:
    """Classify the website's industry/vertical based on page content."""
    scores: dict[str, float] = {industry: 0.0 for industry in _INDUSTRY_KEYWORDS}

    for url, html in pages.items():
        soup = BeautifulSoup(html, "lxml")

        # Weight different content sources
        # Meta description (high weight)
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            content = meta_desc.get("content", "")
            if content:
                _score_text(content, scores, weight=3.0)

        # Meta keywords
        meta_kw = soup.find("meta", attrs={"name": "keywords"})
        if meta_kw:
            content = meta_kw.get("content", "")
            if content:
                _score_text(content, scores, weight=2.0)

        # Page title
        title = soup.find("title")
        if title:
            _score_text(title.get_text(), scores, weight=2.0)

        # Headings (h1, h2)
        for h in soup.find_all(["h1", "h2"]):
            _score_text(h.get_text(), scores, weight=1.5)

        # Body text (sampled, lower weight)
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 20:
                _score_text(text, scores, weight=0.5)

    # Sort by score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top = ranked[0] if ranked else ("", 0.0)
    second = ranked[1] if len(ranked) > 1 else ("", 0.0)

    # Calculate confidence (0-1 range)
    total_score = sum(s for _, s in ranked)
    confidence = 0.0
    if total_score > 0 and top[1] > 0:
        confidence = round(min(top[1] / max(total_score * 0.3, 1), 1.0), 2)

    primary = top[0] if top[1] > 0 else ""
    secondary = second[0] if second[1] > 0 and second[1] >= top[1] * 0.3 else ""

    return {
        "primary": primary,
        "secondary": secondary,
        "confidence": confidence,
    }


def _score_text(text: str, scores: dict[str, float], weight: float = 1.0) -> None:
    """Score text against all industry patterns."""
    for industry, pattern in _INDUSTRY_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            scores[industry] += len(matches) * weight
