from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

_SECTION_HEADINGS = re.compile(
    r"trusted\s+by|our\s+clients|our\s+partners|as\s+seen\s+in|featured\s+in|"
    r"brands\s+we\s+work\s+with|our\s+customers|they\s+trust\s+us|"
    r"companies\s+that\s+trust|partnered\s+with|working\s+with",
    re.IGNORECASE,
)

# Elements that are clearly navigation/header/footer — not client logo sections
_SKIP_ANCESTORS = re.compile(r"header|navbar|nav-bar|footer|menu|sidebar", re.IGNORECASE)


def extract_client_logos(
    pages: dict[str, str],
    company_name: str = "",
    site_url: str = "",
) -> list[dict]:
    """Extract client/partner logos from 'Trusted by' style sections."""
    logos: list[dict] = []

    # Build a set of terms to reject (the company's own name/domain)
    reject_terms: set[str] = set()
    if company_name:
        reject_terms.add(company_name.strip().lower())
    if site_url:
        parsed = urlparse(site_url)
        if parsed.hostname:
            # e.g. "axgen" from "axgen.co"
            domain_name = parsed.hostname.lstrip("www.").split(".")[0].lower()
            reject_terms.add(domain_name)

    for url, html in pages.items():
        soup = BeautifulSoup(html, "lxml")

        # Strategy 1: Find headings that match trust/partner patterns
        for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p"]):
            text = heading.get_text(strip=True)
            if not _SECTION_HEADINGS.search(text):
                continue

            section = heading.find_parent(["section", "div"])
            if section and not _in_nav_or_footer(section):
                logos.extend(_extract_logos_from_container(section, reject_terms))

        # Strategy 2: Sections with trust-related class/id names
        # Use more specific selectors to avoid matching generic "client" in navbars
        for container in soup.select(
            "[class*='client-logo'], [class*='client_logo'], "
            "[class*='partner-logo'], [class*='partner_logo'], "
            "[class*='trust-logo'], [class*='logo-strip'], "
            "[class*='logo-grid'], [class*='logo-bar'], [class*='logo-wall'], "
            "[id*='client-logo'], [id*='partner-logo'], [id*='trust']"
        ):
            if not _in_nav_or_footer(container):
                logos.extend(_extract_logos_from_container(container, reject_terms))

    # Deduplicate by name
    seen: set[str] = set()
    unique: list[dict] = []
    for logo in logos:
        key = logo["name"].strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(logo)

    return unique[:30]


def _extract_logos_from_container(
    container: Tag, reject_terms: set[str]
) -> list[dict]:
    """Extract logo images from a container element."""
    logos: list[dict] = []

    for img in container.find_all("img", src=True):
        alt = (img.get("alt") or "").strip()
        src = (img.get("src") or "").strip()

        if not alt or len(alt) < 2:
            continue

        alt_lower = alt.lower()

        # Skip generic decorative alt texts
        if alt_lower in ("logo", "image", "icon", "decoration", "background"):
            continue

        # Skip the company's own logo
        if any(term in alt_lower for term in reject_terms if term):
            continue

        logos.append({"name": alt, "logo_url": src})

    return logos


def _in_nav_or_footer(el: Tag) -> bool:
    """Check if element is inside a nav, header, or footer."""
    for parent in el.parents:
        if not isinstance(parent, Tag):
            continue
        if parent.name in ("header", "footer", "nav"):
            return True
        classes = " ".join(parent.get("class", []))
        el_id = parent.get("id", "") or ""
        if _SKIP_ANCESTORS.search(classes) or _SKIP_ANCESTORS.search(el_id):
            return True
    return False
