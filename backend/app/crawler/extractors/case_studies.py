from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

_CASE_STUDY_URL_PATTERNS = re.compile(
    r"/case[-_]?stud(?:y|ies)|/success[-_]?stor(?:y|ies)|/customers?/",
    re.IGNORECASE,
)

_SECTION_HEADINGS = re.compile(
    r"case\s+stud(?:y|ies)|success\s+stor(?:y|ies)|customer\s+stories",
    re.IGNORECASE,
)

_METRIC_RE = re.compile(
    r"\d+[%xX]|\d+\s*(?:percent|times|increase|decrease|reduction|growth|improvement|faster|more)",
    re.IGNORECASE,
)


def extract_case_studies(pages: dict[str, str]) -> list[dict]:
    """Extract case study summaries from case study pages and homepage sections."""
    studies: list[dict] = []

    for url, html in pages.items():
        soup = BeautifulSoup(html, "lxml")
        url_lower = url.lower()

        # Strategy 1: Dedicated case study pages
        if _CASE_STUDY_URL_PATTERNS.search(url_lower):
            study = _extract_from_page(soup, url)
            if study:
                studies.append(study)

        # Strategy 2: Case study sections on other pages (e.g., homepage)
        for heading in soup.find_all(["h1", "h2", "h3"]):
            text = heading.get_text(strip=True)
            if not _SECTION_HEADINGS.search(text):
                continue
            section = heading.find_parent(["section", "div"])
            if section:
                studies.extend(_extract_cards_from_section(section, url))

    # Deduplicate by title
    seen: set[str] = set()
    unique: list[dict] = []
    for s in studies:
        key = s["title"][:60].strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(s)

    return unique[:20]


def _extract_from_page(soup: BeautifulSoup, url: str) -> dict | None:
    """Extract a single case study from a dedicated page."""
    title_tag = soup.find("h1")
    if not title_tag:
        return None

    title = title_tag.get_text(strip=True)
    if not title:
        return None

    # Summary: first substantial paragraph
    summary = ""
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) > 50:
            summary = text[:300]
            break

    # Client name: look for "Client:", "Company:", or meta
    client_name = ""
    for el in soup.find_all(["dt", "strong", "b", "span"]):
        el_text = el.get_text(strip=True).lower()
        if el_text in ("client", "client:", "company", "company:", "customer", "customer:"):
            sibling = el.find_next(["dd", "span", "p"])
            if sibling:
                client_name = sibling.get_text(strip=True)[:100]
                break

    # Metrics: look for percentage/number results
    metrics = _extract_metrics(soup)

    return {
        "title": title[:200],
        "summary": summary,
        "client_name": client_name,
        "url": url,
        "metrics": metrics,
    }


def _extract_cards_from_section(section: Tag, base_url: str) -> list[dict]:
    """Extract case study cards from a section."""
    studies: list[dict] = []

    for card in section.find_all(["article", "div", "a"], recursive=True):
        heading = card.find(["h3", "h4", "h5"])
        if not heading:
            continue

        title = heading.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        summary = ""
        p = card.find("p")
        if p:
            summary = p.get_text(strip=True)[:300]

        link = ""
        a_tag = card.find("a", href=True) if card.name != "a" else card
        if a_tag and a_tag.get("href"):
            link = a_tag["href"]

        studies.append({
            "title": title[:200],
            "summary": summary,
            "client_name": "",
            "url": link,
            "metrics": [],
        })

    return studies


def _extract_metrics(soup: BeautifulSoup) -> list[str]:
    """Extract result metrics (percentages, multipliers, etc.)."""
    metrics: list[str] = []

    # Look in elements that commonly hold metrics
    for el in soup.find_all(["li", "div", "span", "p", "h2", "h3"]):
        text = el.get_text(strip=True)
        if _METRIC_RE.search(text) and len(text) < 150:
            metrics.append(text)
            if len(metrics) >= 5:
                break

    return metrics
