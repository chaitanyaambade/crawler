from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup, Tag

from app.crawler.extractors._utils import extract_card_data, find_card_groups

PRICE_RE = re.compile(
    r"[\$\€\£]\s*\d[\d,]*(?:\.\d{1,2})?|free|contact\s*(?:us|sales)?|custom",
    re.IGNORECASE,
)
BILLING_RE = re.compile(r"/\s*(mo(?:nth)?|yr|year|annual|week)", re.IGNORECASE)
HIGHLIGHT_KEYWORDS = {"popular", "recommended", "best", "pro"}


def extract_pricing(pages: dict[str, str]) -> list[dict]:
    """Extract pricing plans from pricing pages or pricing sections."""
    plans: list[dict] = []

    for url, html in pages.items():
        url_lower = url.lower()
        soup = BeautifulSoup(html, "lxml")

        is_pricing_page = any(
            p in url_lower for p in ("/pricing", "/plans", "/packages")
        )

        # Find pricing sections on any page
        pricing_containers: list[Tag] = []
        if is_pricing_page:
            pricing_containers.append(soup)
        else:
            pricing_containers.extend(
                soup.select(
                    "[id*='pricing'], [class*='pricing'], "
                    "[id*='plans'], [class*='plans'], "
                    "[id*='packages'], [class*='packages']"
                )
            )

        for container in pricing_containers:
            # Strategy 1: JSON-LD Offer
            plans.extend(_extract_jsonld_pricing(container))

            # Strategy 2: Card detection
            plans.extend(_extract_card_pricing(container))

    # Deduplicate by plan name
    seen: set[str] = set()
    unique: list[dict] = []
    for plan in plans:
        key = plan["name"].strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(plan)

    return unique[:10]


def _extract_jsonld_pricing(container: Tag) -> list[dict]:
    """Extract pricing from JSON-LD Offer schema."""
    plans: list[dict] = []
    for script in container.find_all("script", type="application/ld+json"):
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
            if item_type == "Offer":
                name = item.get("name", "")
                price = item.get("price", "")
                if name:
                    plans.append({
                        "name": name,
                        "price": str(price),
                        "billing_period": item.get("priceCurrency", ""),
                        "features": [],
                        "is_highlighted": False,
                    })
    return plans


def _extract_card_pricing(container: Tag) -> list[dict]:
    """Extract pricing cards using repeated structure detection."""
    plans: list[dict] = []

    card_groups = find_card_groups(container, min_cards=2)

    for group in card_groups[:2]:
        for card in group:
            plan = _parse_pricing_card(card)
            if plan:
                plans.append(plan)

    # Fallback: look for elements with pricing class names
    if not plans:
        for card in container.select(
            "[class*='plan'], [class*='pricing-card'], [class*='price-card'], "
            "[class*='tier'], [class*='package']"
        ):
            plan = _parse_pricing_card(card)
            if plan:
                plans.append(plan)

    return plans


def _parse_pricing_card(card: Tag) -> dict | None:
    """Parse a single pricing card element."""
    # Name from heading
    heading = card.find(["h2", "h3", "h4", "h5"])
    if not heading:
        heading = card.find(["strong", "b"])
    if not heading:
        return None

    name = heading.get_text(strip=True)
    if not name or len(name) > 100:
        return None

    card_text = card.get_text(" ", strip=True)

    # Price
    price = ""
    price_match = PRICE_RE.search(card_text)
    if price_match:
        price = price_match.group(0).strip()

    # Billing period
    billing_period = ""
    billing_match = BILLING_RE.search(card_text)
    if billing_match:
        period = billing_match.group(1).lower()
        if period.startswith("mo"):
            billing_period = "monthly"
        elif period in ("yr", "year", "annual"):
            billing_period = "yearly"
        elif period == "week":
            billing_period = "weekly"

    # Features from <ul> items
    features: list[str] = []
    for ul in card.find_all("ul"):
        for li in ul.find_all("li"):
            text = li.get_text(strip=True)
            if 2 < len(text) < 200:
                features.append(text)

    # Highlighted / popular flag
    card_classes = " ".join(card.get("class", [])).lower()
    is_highlighted = any(kw in card_classes for kw in HIGHLIGHT_KEYWORDS)

    return {
        "name": name,
        "price": price,
        "billing_period": billing_period,
        "features": features[:15],
        "is_highlighted": is_highlighted,
    }
