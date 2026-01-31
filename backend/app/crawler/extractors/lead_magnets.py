from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

_LEAD_KEYWORDS = {
    "free_trial": re.compile(r"free\s+trial|start\s+free|try\s+(?:it\s+)?free|get\s+started\s+free", re.IGNORECASE),
    "demo": re.compile(r"(?:request|book|schedule|get)\s+(?:a\s+)?demo|live\s+demo", re.IGNORECASE),
    "ebook": re.compile(r"e-?book|whitepaper|white\s+paper|download\s+(?:our|the|free)|free\s+(?:guide|report|pdf)", re.IGNORECASE),
    "newsletter": re.compile(r"newsletter|subscribe|sign\s*up\s+(?:for|to)\s+(?:our|the)|stay\s+updated|join\s+our\s+(?:list|mailing)", re.IGNORECASE),
    "webinar": re.compile(r"webinar|live\s+(?:event|session|class|workshop)|register\s+(?:for|now)", re.IGNORECASE),
}

_OFFER_HEADING_RE = re.compile(
    r"free|download|get\s+(?:your|our|the)|grab|claim|unlock|access",
    re.IGNORECASE,
)


def extract_lead_magnets(pages: dict[str, str]) -> list[dict]:
    """Extract lead magnets, offers, and signup forms."""
    magnets: list[dict] = []

    for url, html in pages.items():
        soup = BeautifulSoup(html, "lxml")

        # Strategy 1: Forms with email inputs
        magnets.extend(_extract_signup_forms(soup, url))

        # Strategy 2: CTA sections with lead magnet keywords
        magnets.extend(_extract_offer_sections(soup, url))

        # Strategy 3: Popup/modal content
        for modal in soup.select(
            "[class*='modal'], [class*='popup'], [class*='overlay'], "
            "[id*='modal'], [id*='popup']"
        ):
            magnets.extend(_extract_signup_forms(modal, url))
            magnets.extend(_extract_offer_sections(modal, url))

    # Deduplicate by title
    seen: set[str] = set()
    unique: list[dict] = []
    for m in magnets:
        key = (m.get("title", "") or m.get("type", ""))[:50].strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(m)

    return unique[:15]


def _extract_signup_forms(container: Tag, page_url: str) -> list[dict]:
    """Detect forms with email inputs as lead magnets."""
    magnets: list[dict] = []

    forms = container.find_all("form") if container.name != "form" else [container]

    for form in forms:
        email_input = form.find("input", attrs={"type": "email"})
        if not email_input:
            # Also check name/placeholder for email hints
            for inp in form.find_all("input"):
                name = (inp.get("name") or "").lower()
                placeholder = (inp.get("placeholder") or "").lower()
                if "email" in name or "email" in placeholder:
                    email_input = inp
                    break

        if not email_input:
            continue

        # Determine type from surrounding text
        form_text = form.get_text(" ", strip=True)
        magnet_type = _classify_type(form_text)

        # Title: heading near the form
        title = ""
        heading = form.find(["h1", "h2", "h3", "h4", "h5"])
        if not heading:
            parent = form.parent
            if parent:
                heading = parent.find(["h1", "h2", "h3", "h4", "h5"])
        if heading:
            title = heading.get_text(strip=True)[:200]

        # Description: first <p> in or near form
        description = ""
        p = form.find("p")
        if not p and form.parent:
            p = form.parent.find("p")
        if p:
            description = p.get_text(strip=True)[:300]

        # URL from form action
        action = form.get("action", "") or page_url

        magnets.append({
            "type": magnet_type,
            "title": title,
            "description": description,
            "url": action,
        })

    return magnets


def _extract_offer_sections(container: Tag, page_url: str) -> list[dict]:
    """Extract offer/download sections based on keyword matching."""
    magnets: list[dict] = []

    for heading in container.find_all(["h1", "h2", "h3", "h4", "h5"]):
        text = heading.get_text(strip=True)
        if not _OFFER_HEADING_RE.search(text):
            continue

        section = heading.find_parent(["section", "div"])
        if not section:
            continue

        section_text = section.get_text(" ", strip=True)
        magnet_type = _classify_type(section_text)
        if magnet_type == "newsletter":
            # Only include if there's actually a form
            if not section.find("form") and not section.find("input"):
                continue

        description = ""
        p = section.find("p")
        if p:
            description = p.get_text(strip=True)[:300]

        link = ""
        a = section.find("a", href=True)
        if a:
            link = a.get("href", "")

        magnets.append({
            "type": magnet_type,
            "title": text[:200],
            "description": description,
            "url": link or page_url,
        })

    return magnets


def _classify_type(text: str) -> str:
    """Classify the lead magnet type from surrounding text."""
    for magnet_type, pattern in _LEAD_KEYWORDS.items():
        if pattern.search(text):
            return magnet_type
    return "newsletter"
