from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup, Tag

from app.crawler.extractors._utils import extract_card_data, find_card_groups

RATING_RE = re.compile(r"(\d(?:\.\d)?)\s*/\s*5")
ATTRIBUTION_RE = re.compile(r"^(.+?)\s*[,\-\|]\s*(.+)$")

# Reject quotes that are just dates: "8 August 2025", "19 November 2024", etc.
_DATE_ONLY_RE = re.compile(
    r"^\d{1,2}\s+"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{4}$",
    re.IGNORECASE,
)
# Also catch short date variants: "2024-03-19", "03/19/2024", etc.
_DATE_ISO_RE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$")
_DATE_SLASH_RE = re.compile(r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$")


def extract_testimonials(pages: dict[str, str]) -> list[dict]:
    """Extract testimonials/reviews from all pages."""
    testimonials: list[dict] = []

    for url, html in pages.items():
        soup = BeautifulSoup(html, "lxml")

        # Strategy 1: JSON-LD Review / AggregateRating
        testimonials.extend(_extract_jsonld_reviews(soup))

        # Strategy 2: <blockquote> elements
        testimonials.extend(_extract_blockquotes(soup))

        # Strategy 3: Testimonial sections with card detection
        for container in soup.select(
            "[class*='testimonial'], [class*='review'], [class*='quote'], "
            "[id*='testimonial'], [id*='review']"
        ):
            testimonials.extend(_extract_card_testimonials(container))

    # Deduplicate by quote text (first 50 chars)
    seen: set[str] = set()
    unique: list[dict] = []
    for t in testimonials:
        key = t["quote"][:50].strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(t)

    return unique[:20]


def _extract_jsonld_reviews(soup: BeautifulSoup) -> list[dict]:
    """Parse JSON-LD @type: Review."""
    reviews: list[dict] = []
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

            if item_type == "Review":
                body = item.get("reviewBody", "") or item.get("description", "")
                if not body:
                    continue

                author = item.get("author", {})
                author_name = ""
                if isinstance(author, dict):
                    author_name = author.get("name", "")
                elif isinstance(author, str):
                    author_name = author

                rating = None
                review_rating = item.get("reviewRating", {})
                if isinstance(review_rating, dict):
                    try:
                        rating = float(review_rating.get("ratingValue", 0))
                    except (ValueError, TypeError):
                        pass

                reviews.append({
                    "quote": body[:500],
                    "author_name": author_name,
                    "author_company": "",
                    "author_role": "",
                    "rating": rating if rating else None,
                })

    return reviews


def _extract_blockquotes(soup: BeautifulSoup) -> list[dict]:
    """Extract <blockquote> elements with attribution."""
    testimonials: list[dict] = []

    for bq in soup.find_all("blockquote"):
        quote = ""
        # Get quote text from <p> inside blockquote, or direct text
        p = bq.find("p")
        if p:
            quote = p.get_text(strip=True)
        else:
            quote = bq.get_text(strip=True)

        if not quote or len(quote) < 10:
            continue

        # Attribution from <cite> or <figcaption>
        author_name = ""
        author_company = ""
        author_role = ""

        cite = bq.find("cite") or bq.find_next_sibling("cite")
        if not cite:
            fig = bq.find_parent("figure")
            if fig:
                cite = fig.find("figcaption")

        if cite:
            attr_text = cite.get_text(strip=True)
            author_name, author_company, author_role = _parse_attribution(attr_text)

        testimonials.append({
            "quote": quote[:500],
            "author_name": author_name,
            "author_company": author_company,
            "author_role": author_role,
            "rating": None,
        })

    return testimonials


def _extract_card_testimonials(container: Tag) -> list[dict]:
    """Extract testimonial cards using repeated structure detection."""
    testimonials: list[dict] = []

    card_groups = find_card_groups(container, min_cards=2)

    for group in card_groups[:2]:
        for card in group:
            testimonial = _parse_testimonial_card(card)
            if testimonial:
                testimonials.append(testimonial)

    return testimonials


def _parse_testimonial_card(card: Tag) -> dict | None:
    """Parse a single testimonial card."""
    # Quote: longest <p> or blockquote text
    quote = ""
    bq = card.find("blockquote")
    if bq:
        quote = bq.get_text(strip=True)
    else:
        paragraphs = card.find_all("p")
        if paragraphs:
            # Pick the longest paragraph as the quote
            texts = [(p.get_text(strip=True), len(p.get_text(strip=True))) for p in paragraphs]
            texts.sort(key=lambda x: x[1], reverse=True)
            quote = texts[0][0]

    if not quote or len(quote) < 10:
        return None

    # Reject date-only quotes
    if _is_date_string(quote.strip()):
        return None

    # Author name: heading or strong/b
    author_name = ""
    heading = card.find(["h4", "h5", "h6", "strong", "b"])
    if heading:
        author_name = heading.get_text(strip=True)

    # Rating: star icons or text pattern
    rating = _detect_rating(card)

    # Attribution parsing for company/role
    author_company = ""
    author_role = ""
    for span in card.find_all(["span", "p", "cite"]):
        text = span.get_text(strip=True)
        if text and text != quote and text != author_name and len(text) < 100:
            name, company, role = _parse_attribution(text)
            if company:
                author_company = company
            if role:
                author_role = role
            if name and not author_name:
                author_name = name
            break

    return {
        "quote": quote[:500],
        "author_name": author_name,
        "author_company": author_company,
        "author_role": author_role,
        "rating": rating,
    }


def _detect_rating(card: Tag) -> float | None:
    """Detect star rating from icons or text."""
    # Count star icons
    stars = card.select(".fa-star, [class*='star-filled'], [class*='star-active']")
    if stars:
        return float(len(stars))

    # itemprop ratingValue
    rating_el = card.select_one("[itemprop='ratingValue']")
    if rating_el:
        try:
            return float(rating_el.get_text(strip=True))
        except ValueError:
            pass

    # Text pattern "X/5"
    text = card.get_text()
    match = RATING_RE.search(text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass

    return None


def _parse_attribution(text: str) -> tuple[str, str, str]:
    """Parse 'Name, Company' or 'Name - Role at Company'."""
    name = text
    company = ""
    role = ""

    # Try "Name - Role at Company" or "Name, Role at Company"
    match = ATTRIBUTION_RE.match(text)
    if match:
        name = match.group(1).strip()
        rest = match.group(2).strip()

        if " at " in rest.lower():
            parts = rest.split(" at ", 1) if " at " in rest else rest.split(" At ", 1)
            role = parts[0].strip()
            company = parts[1].strip() if len(parts) > 1 else ""
        else:
            company = rest

    return name, company, role


def _is_date_string(text: str) -> bool:
    """Check if text is just a date (not a real testimonial quote)."""
    return bool(
        _DATE_ONLY_RE.match(text)
        or _DATE_ISO_RE.match(text)
        or _DATE_SLASH_RE.match(text)
    )
