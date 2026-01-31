from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

_PRESS_URL_PATTERNS = re.compile(
    r"/press|/news|/media|/in-the-press|/coverage|/press-releases",
    re.IGNORECASE,
)

_SECTION_HEADINGS = re.compile(
    r"press|in\s+the\s+(?:news|press|media)|media\s+(?:coverage|mentions)|"
    r"as\s+(?:seen|featured)\s+(?:in|on)|news(?:room)?|coverage",
    re.IGNORECASE,
)

_NEWS_DOMAINS = {
    "techcrunch.com", "forbes.com", "bbc.com", "bbc.co.uk",
    "reuters.com", "bloomberg.com", "cnbc.com", "wired.com",
    "theverge.com", "mashable.com", "venturebeat.com",
    "businessinsider.com", "inc.com", "entrepreneur.com",
    "fastcompany.com", "zdnet.com", "cnet.com", "engadget.com",
    "nytimes.com", "wsj.com", "theguardian.com", "huffpost.com",
    "producthunt.com", "thenextweb.com", "arstechnica.com",
}

_DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4}|"
    r"\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)


def extract_media_mentions(pages: dict[str, str]) -> list[dict]:
    """Extract press/news/media references."""
    mentions: list[dict] = []

    for url, html in pages.items():
        soup = BeautifulSoup(html, "lxml")
        url_lower = url.lower()

        # Strategy 1: JSON-LD NewsArticle / Article
        mentions.extend(_extract_jsonld_articles(soup))

        # Strategy 2: Dedicated press/news pages
        if _PRESS_URL_PATTERNS.search(url_lower):
            mentions.extend(_extract_from_press_page(soup, url))

        # Strategy 3: Press sections on any page
        for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
            text = heading.get_text(strip=True)
            if not _SECTION_HEADINGS.search(text):
                continue
            section = heading.find_parent(["section", "div"])
            if section:
                mentions.extend(_extract_links_from_section(section))

        # Strategy 4: Links to known news domains
        mentions.extend(_extract_news_domain_links(soup))

    # Deduplicate by title or URL
    seen: set[str] = set()
    unique: list[dict] = []
    for m in mentions:
        key = (m.get("title", "")[:50] or m.get("url", "")).strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(m)

    return unique[:20]


def _extract_jsonld_articles(soup: BeautifulSoup) -> list[dict]:
    """Parse JSON-LD NewsArticle / Article schemas."""
    mentions: list[dict] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type", "")
            if isinstance(item_type, list):
                item_type = item_type[0] if item_type else ""
            if item_type not in ("NewsArticle", "Article"):
                continue

            title = item.get("headline", "") or item.get("name", "")
            if not title:
                continue

            publisher = item.get("publisher", {})
            source = ""
            if isinstance(publisher, dict):
                source = publisher.get("name", "")

            mentions.append({
                "title": title[:200],
                "source": source,
                "url": item.get("url", ""),
                "date": item.get("datePublished", ""),
            })

    return mentions


def _extract_from_press_page(soup: BeautifulSoup, page_url: str) -> list[dict]:
    """Extract mentions from dedicated press/news pages."""
    mentions: list[dict] = []

    for article in soup.find_all(["article", "li", "div"]):
        heading = article.find(["h2", "h3", "h4", "h5"])
        if not heading:
            continue

        title = heading.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        link = ""
        a_tag = heading.find("a", href=True) or article.find("a", href=True)
        if a_tag:
            link = a_tag.get("href", "")

        # Try to find a date
        date = ""
        text = article.get_text()
        date_match = _DATE_RE.search(text)
        if date_match:
            date = date_match.group(0)

        # Source: from external domain
        source = ""
        if link:
            parsed = urlparse(link)
            if parsed.hostname:
                host = parsed.hostname.lstrip("www.")
                if host in _NEWS_DOMAINS:
                    source = host.split(".")[0].capitalize()

        mentions.append({
            "title": title[:200],
            "source": source,
            "url": link,
            "date": date,
        })

    return mentions


def _extract_links_from_section(section: Tag) -> list[dict]:
    """Extract media mention links from a section."""
    mentions: list[dict] = []

    for a in section.find_all("a", href=True):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if not text or len(text) < 5:
            continue

        parsed = urlparse(href)
        source = ""
        if parsed.hostname:
            host = parsed.hostname.lstrip("www.")
            if host in _NEWS_DOMAINS:
                source = host.split(".")[0].capitalize()

        if source or len(text) > 10:
            mentions.append({
                "title": text[:200],
                "source": source,
                "url": href,
                "date": "",
            })

    return mentions


def _extract_news_domain_links(soup: BeautifulSoup) -> list[dict]:
    """Find links to known news domains anywhere on the page."""
    mentions: list[dict] = []

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        parsed = urlparse(href)
        if not parsed.hostname:
            continue

        host = parsed.hostname.lstrip("www.")
        if host not in _NEWS_DOMAINS:
            continue

        text = a.get_text(strip=True)
        if not text or len(text) < 5:
            # Try alt text from child image
            img = a.find("img", alt=True)
            if img:
                text = img.get("alt", "").strip()
            if not text or len(text) < 3:
                continue

        source = host.split(".")[0].capitalize()
        mentions.append({
            "title": text[:200],
            "source": source,
            "url": href,
            "date": "",
        })

    return mentions
