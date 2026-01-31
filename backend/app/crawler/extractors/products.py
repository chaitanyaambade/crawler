from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup, Tag

from app.crawler.extractors._utils import extract_card_data, find_card_groups

# Price pattern: ₹500, $29.99, €10, £15, ¥1000, Free, etc.
_PRICE_RE = re.compile(
    r"[₹\$\€\£\¥]\s*\d[\d,]*(?:\.\d{1,2})?",
)

# Pattern to detect date-like strings: "8 August 2025", "19 June 2024", etc.
_DATE_RE = re.compile(
    r"^\d{1,2}\s+"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{4}$",
    re.IGNORECASE,
)

# Sections that contain testimonials/reviews — skip these for product extraction
_TESTIMONIAL_SELECTORS = (
    "[class*='testimonial']", "[class*='review']", "[class*='quote']",
    "[id*='testimonial']", "[id*='review']", "[id*='quote']",
)

# Headings that are marketing copy, not products/services
_MARKETING_HEADING_RE = re.compile(
    r"\b(?:why|how|what|when|ready|tired|stop|start|imagine|discover"
    r"|introducing|welcome|join|meet|built|designed|trusted|powered"
    r"|don.?t|didn.?t|can.?t|won.?t|isn.?t|aren.?t|shouldn.?t|couldn.?t|wouldn.?t"
    r"|you.?re|we.?re|they.?re|it.?s|that.?s|let.?s|here.?s"
    r"|too\s+\w+|wasting|struggling|frustrated|worried"
    r"|founders?|agencies|marketers?)\b"
    r"|[.!?]$",  # ends with sentence punctuation
    re.IGNORECASE,
)

# Sections that are clearly not product listings (by class/id)
_NON_PRODUCT_SECTION_RE = re.compile(
    r"hero|banner|cta|call.to.action|newsletter|subscribe|footer"
    r"|testimonial|review|faq|pricing|team|partner|client|logo"
    r"|stat|counter|metric|number|social|cookie|modal|popup",
    re.IGNORECASE,
)


def _score_product(name: str, description: str, price: str, image_url: str) -> float:
    """Score whether a candidate is a real product/service vs marketing copy."""
    score = 0.0
    lower_name = name.strip().lower()

    # --- Negative signals (marketing copy / non-product) ---

    # Marketing headline patterns (questions, emotional words, contractions, sentence endings)
    if _MARKETING_HEADING_RE.search(name.strip()):
        score -= 3.0

    # Very short name with no description (likely a section heading)
    if len(lower_name.split()) <= 2 and not description:
        score -= 1.0

    # Very long name (likely a sentence, not a product name)
    if len(lower_name) > 80:
        score -= 2.0

    # All caps short phrases are often section headers ("OUR MISSION", "WHY US")
    if name == name.upper() and len(name.split()) <= 3 and not price:
        score -= 1.5

    # Description looks like a date (testimonial artifact)
    if description and _DATE_RE.match(description.strip()):
        score -= 3.0

    # Name + description together sound like a problem statement, not a product
    combined = (lower_name + " " + description.lower()).strip()
    if re.search(r"\b(?:you have to|you need to|you spend|you waste|charge|lakh|expensive"
                 r"|problem|pain|struggle|frustrat|interrupt|distract"
                 r"|headache|nightmare|broken|failing|losing)\b", combined):
        score -= 3.0

    # --- Positive signals (real product/service) ---

    # Has a real price → strong product signal (ignore tiny amounts like ₹1 which are artifacts)
    if price:
        digits = re.sub(r"[^\d.]", "", price)
        try:
            amount = float(digits) if digits else 0
        except ValueError:
            amount = 0
        if amount >= 5:
            score += 3.0
        elif amount > 0:
            score += 0.5  # suspicious tiny price, weak signal

    # Has an image → likely a real listing
    if image_url:
        score += 1.0

    # Has a substantive description (not just 1-2 words)
    if description and len(description.split()) >= 5:
        score += 1.5
    elif description:
        score += 0.5

    # Name length in sweet spot for product names (3-8 words)
    word_count = len(lower_name.split())
    if 2 <= word_count <= 8:
        score += 1.0

    # Name is Title Case (product names tend to be)
    if name == name.title():
        score += 0.5

    # Contains product-like keywords
    if re.search(r"\b(?:plan|pro|premium|basic|starter|enterprise|lite|plus|edition"
                 r"|pack|bundle|kit|service|solution|platform|tool|suite|system"
                 r"|agent|software|app)\b", lower_name, re.IGNORECASE):
        score += 1.5

    return score


_PRODUCT_SCORE_THRESHOLD = 0.0


def extract_products(pages: dict[str, str]) -> dict:
    """Extract products/services and features using 3 strategies."""
    products: list[dict] = []
    features: list[str] = []

    # Identify product-related pages and homepage
    product_pages: list[tuple[str, str]] = []
    homepage_html: str = ""
    for url, html in pages.items():
        url_lower = url.lower()
        if any(p in url_lower for p in ("/product", "/service", "/solution", "/feature")):
            product_pages.append((url, html))
        if url.rstrip("/").count("/") <= 3 and not homepage_html:
            homepage_html = html

    # Process product pages, fallback to homepage
    pages_to_scan = product_pages if product_pages else [("homepage", homepage_html)] if homepage_html else []

    for page_url, html in pages_to_scan:
        soup = BeautifulSoup(html, "lxml")
        url_category = _category_from_url(page_url)

        # Strategy 1: JSON-LD structured data (highest confidence)
        products.extend(_extract_jsonld_products(soup))

        # Strategy 2: Heading hierarchy in main content
        products.extend(_extract_heading_products(soup, url_category))
        features.extend(_extract_feature_list(soup))

        # Strategy 3: Repeated structure detection (works without class names)
        products.extend(_extract_card_products(soup, url_category))

    # Score, filter, and deduplicate
    seen_names: set[str] = set()
    unique_products = []
    for p in products:
        name = p["name"].strip().lower()
        if not name or name in seen_names:
            continue
        score = _score_product(
            p["name"], p.get("description", ""),
            p.get("price", ""), p.get("image_url", ""),
        )
        if score <= _PRODUCT_SCORE_THRESHOLD:
            continue
        seen_names.add(name)
        unique_products.append(p)

    seen_features: set[str] = set()
    unique_features = []
    for f in features:
        if f not in seen_features:
            seen_features.add(f)
            unique_features.append(f)

    return {
        "products": unique_products[:20],
        "features": unique_features[:20],
    }


def _extract_jsonld_products(soup: BeautifulSoup) -> list[dict]:
    """Strategy 1: Parse JSON-LD Product/Service/Offer/SoftwareApplication."""
    products: list[dict] = []
    target_types = {"Product", "Service", "Offer", "SoftwareApplication", "IndividualProduct"}

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            _collect_jsonld_item(item, target_types, products)

    return products


def _collect_jsonld_item(item: dict, target_types: set, products: list[dict]) -> None:
    """Recursively collect product items from JSON-LD."""
    item_type = item.get("@type", "")
    if isinstance(item_type, list):
        item_type = item_type[0] if item_type else ""

    if item_type in target_types:
        name = item.get("name", "")
        if name:
            # Extract price from offers
            price = ""
            offers = item.get("offers")
            if isinstance(offers, dict):
                raw_price = offers.get("price", "")
                currency = offers.get("priceCurrency", "")
                if raw_price:
                    price = f"{currency} {raw_price}".strip() if currency else str(raw_price)
            elif isinstance(offers, list) and offers:
                first = offers[0]
                if isinstance(first, dict):
                    raw_price = first.get("price", "")
                    currency = first.get("priceCurrency", "")
                    if raw_price:
                        price = f"{currency} {raw_price}".strip() if currency else str(raw_price)

            # Extract category
            category = ""
            cat = item.get("category")
            if isinstance(cat, str):
                category = cat
            elif isinstance(cat, list) and cat:
                category = str(cat[0])

            products.append({
                "name": name,
                "description": item.get("description", "")[:300],
                "image_url": item.get("image", "") if isinstance(item.get("image"), str) else "",
                "price": price,
                "category": category,
            })

    # Check nested offers/hasOfferCatalog
    for key in ("offers", "hasOfferCatalog", "itemListElement"):
        nested = item.get(key)
        if isinstance(nested, list):
            for sub in nested:
                if isinstance(sub, dict):
                    _collect_jsonld_item(sub, target_types, products)
        elif isinstance(nested, dict):
            _collect_jsonld_item(nested, target_types, products)


def _extract_heading_products(soup: BeautifulSoup, url_category: str = "") -> list[dict]:
    """Strategy 2: Walk h2/h3 in main content areas with adjacent descriptions."""
    products: list[dict] = []

    # Try to get category from breadcrumbs
    breadcrumb_cat = _category_from_breadcrumbs(soup) or url_category

    # Only look in main content areas, skip nav/footer/header
    for container_sel in ["main", "article", "section"]:
        for container in soup.find_all(container_sel):
            if container.find_parent(["nav", "footer", "header"]):
                continue

            # Skip sections that are clearly non-product (hero, CTA, FAQ, etc.)
            container_classes = " ".join(container.get("class", [])).lower()
            container_id = (container.get("id") or "").lower()
            if _NON_PRODUCT_SECTION_RE.search(container_classes + " " + container_id):
                continue

            for heading in container.find_all(["h2", "h3"]):
                name = heading.get_text(strip=True)
                if not name or len(name) > 200 or len(name) < 3:
                    continue

                desc = ""
                next_sib = heading.find_next_sibling()
                if next_sib and next_sib.name == "p":
                    desc = next_sib.get_text(strip=True)[:300]

                img_url = ""
                parent = heading.parent
                if parent:
                    img = parent.find("img", src=True)
                    if img:
                        img_url = img["src"]

                # Extract price from nearby text
                price = ""
                if parent:
                    parent_text = parent.get_text(" ", strip=True)
                    price_match = _PRICE_RE.search(parent_text)
                    if price_match:
                        price = price_match.group(0).strip()

                products.append({
                    "name": name,
                    "description": desc,
                    "image_url": img_url,
                    "price": price,
                    "category": breadcrumb_cat,
                })

    return products[:15]


def _extract_card_products(soup: BeautifulSoup, url_category: str = "") -> list[dict]:
    """Strategy 3: Repeated structure detection using _utils."""
    products: list[dict] = []

    breadcrumb_cat = _category_from_breadcrumbs(soup) or url_category

    main = soup.find("main") or soup.find("body") or soup
    card_groups = find_card_groups(main, min_cards=3)

    for group in card_groups[:3]:
        if group and _is_inside_testimonial_section(group[0]):
            continue

        group_products: list[dict] = []
        for card in group:
            data = extract_card_data(card)
            if data["name"] and not _looks_like_testimonial_card(data):
                # Extract price from card text
                card_text = card.get_text(" ", strip=True)
                price_match = _PRICE_RE.search(card_text)
                data["price"] = price_match.group(0).strip() if price_match else ""
                data["category"] = breadcrumb_cat
                group_products.append(data)

        if group_products:
            products.extend(group_products)

    return products


def _is_inside_testimonial_section(element: Tag) -> bool:
    """Check if an element is nested inside a testimonial/review container."""
    for parent in element.parents:
        if not isinstance(parent, Tag):
            continue
        parent_classes = " ".join(parent.get("class", [])).lower()
        parent_id = (parent.get("id") or "").lower()
        for keyword in ("testimonial", "review", "quote", "feedback", "customer-say"):
            if keyword in parent_classes or keyword in parent_id:
                return True
    return False


def _looks_like_testimonial_card(data: dict) -> bool:
    """Heuristic: reject cards that look like testimonials, not products.

    Testimonial cards typically have a person's name as the "name" field
    and a date or short quote as the "description". Real product cards
    usually have longer descriptions or no date-like text.
    """
    name = data.get("name", "")
    desc = data.get("description", "")

    # If description is a date like "8 August 2025", it's a testimonial card
    if _DATE_RE.match(desc.strip()):
        return True

    return False


def _extract_feature_list(soup: BeautifulSoup) -> list[str]:
    """Extract feature bullet points or headings."""
    features: list[str] = []

    # Look for feature sections by class/id
    for section in soup.select(
        "[class*='feature'], [class*='benefit'], [class*='advantage'], "
        "[id*='feature'], [id*='benefit']"
    ):
        for heading in section.find_all(["h2", "h3", "h4"]):
            text = heading.get_text(strip=True)
            if 3 < len(text) < 150:
                features.append(text)

    # List items in feature-like sections
    for ul in soup.select(
        "[class*='feature'] ul, [class*='benefit'] ul, "
        "[id*='feature'] ul"
    ):
        for li in ul.find_all("li"):
            text = li.get_text(strip=True)
            if 3 < len(text) < 200:
                features.append(text)

    return features


def _category_from_url(url: str) -> str:
    """Infer product category from URL path segments.

    E.g. /products/cricket-gear/bat → "cricket gear"
         /shop/electronics           → "electronics"
    """
    from urllib.parse import urlparse

    path = urlparse(url).path.strip("/").lower()
    segments = path.split("/")

    # Skip the first segment if it's a generic prefix
    skip = {"products", "product", "services", "service", "shop", "store",
            "collections", "collection", "category", "categories", "catalog"}
    meaningful = [s for s in segments if s and s not in skip]

    if meaningful:
        # Take the first meaningful segment, clean hyphens/underscores
        return meaningful[0].replace("-", " ").replace("_", " ").title()
    return ""


def _category_from_breadcrumbs(soup: BeautifulSoup) -> str:
    """Extract category from breadcrumb navigation."""
    for selector in [
        "nav[aria-label*='breadcrumb']",
        "[class*='breadcrumb']",
        "[id*='breadcrumb']",
        "ol.breadcrumb",
    ]:
        bc = soup.select_one(selector)
        if not bc:
            continue
        items = bc.find_all("li")
        # Breadcrumb typically: Home > Category > Subcategory > Product
        # We want the second-to-last item (category) if there are 3+
        if len(items) >= 3:
            cat_text = items[-2].get_text(strip=True)
            if cat_text and len(cat_text) < 80:
                return cat_text
        elif len(items) == 2:
            cat_text = items[0].get_text(strip=True)
            if cat_text.lower() not in ("home", "shop", "store") and len(cat_text) < 80:
                return cat_text
    return ""
