from __future__ import annotations

import re

from bs4 import BeautifulSoup


# Business types matching INPUT_SPEC.md Block 1.5
BUSINESS_TYPES = ("ecommerce", "saas", "services", "local_business", "app")


def detect_business_type(
    pages: dict[str, str],
    tech_stack: dict | None = None,
) -> str:
    """Classify the website into a business type.

    Uses a scoring system across multiple signals:
    - Tech stack (Shopify/WooCommerce → ecommerce)
    - Page URL patterns (/pricing with /mo → saas)
    - CTA button text (Add to cart → ecommerce, Book → services)
    - JSON-LD schema types
    - App store links
    - Physical location signals (address, Google Maps → local)

    Returns one of: "ecommerce", "saas", "services", "local_business", "app", ""
    """
    scores: dict[str, float] = {t: 0.0 for t in BUSINESS_TYPES}

    tech_stack = tech_stack or {}
    cms_list = [c.lower() for c in tech_stack.get("cms", [])]

    # --- Tech stack signals ---
    if any(p in cms_list for p in ("shopify", "woocommerce", "magento", "bigcommerce", "prestashop")):
        scores["ecommerce"] += 3.0

    if any(p in cms_list for p in ("wordpress",)):
        # WordPress alone is weak signal — could be blog, services, etc.
        scores["services"] += 0.5

    # --- Page-level analysis ---
    for url, html in pages.items():
        url_lower = url.lower()
        soup = BeautifulSoup(html, "lxml")
        page_text = soup.get_text(" ", strip=True).lower()

        # Ecommerce signals
        _score_ecommerce(soup, page_text, url_lower, scores)

        # SaaS signals
        _score_saas(soup, page_text, url_lower, scores)

        # Services signals
        _score_services(soup, page_text, url_lower, scores)

        # Local business signals
        _score_local(soup, page_text, url_lower, scores)

        # App signals
        _score_app(soup, page_text, scores)

    # Pick the highest score, require minimum threshold
    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    if scores[best] >= 1.5:
        return best
    return ""


def _score_ecommerce(
    soup: BeautifulSoup, text: str, url: str, scores: dict[str, float]
) -> None:
    """Score ecommerce signals."""
    # Cart/checkout pages
    if any(p in url for p in ("/cart", "/checkout", "/shop", "/store", "/collections")):
        scores["ecommerce"] += 1.5

    # Product pages with add-to-cart
    for btn in soup.find_all(["button", "a", "input"]):
        btn_text = btn.get_text(strip=True).lower()
        if any(kw in btn_text for kw in ("add to cart", "buy now", "add to bag", "shop now")):
            scores["ecommerce"] += 1.5
            return  # One strong signal is enough

    # Cart icon, product schema
    if any(kw in text for kw in ("add to cart", "shopping cart", "your cart", "buy now")):
        scores["ecommerce"] += 1.0

    # Currency with product patterns
    if re.search(r"[₹\$\€\£]\s*\d+.*(?:add|buy|cart|order)", text):
        scores["ecommerce"] += 0.5


def _score_saas(
    soup: BeautifulSoup, text: str, url: str, scores: dict[str, float]
) -> None:
    """Score SaaS/software signals."""
    # Pricing page with subscription terms
    if "/pricing" in url or "/plans" in url:
        if any(kw in text for kw in ("/mo", "/month", "/year", "per month", "per year",
                                      "annual", "monthly", "billed yearly", "free trial")):
            scores["saas"] += 2.5
        else:
            scores["saas"] += 1.0

    # Signup/trial CTAs
    for btn in soup.find_all(["button", "a"]):
        btn_text = btn.get_text(strip=True).lower()
        if any(kw in btn_text for kw in ("start free trial", "sign up free", "get started free",
                                          "start trial", "try for free", "create account")):
            scores["saas"] += 1.5
            return

    # SaaS keywords in body
    saas_keywords = ("free trial", "sign up", "subscription", "saas", "software as a service",
                     "cloud-based", "dashboard", "api", "integrate", "workspace")
    hits = sum(1 for kw in saas_keywords if kw in text)
    scores["saas"] += min(hits * 0.3, 1.5)


def _score_services(
    soup: BeautifulSoup, text: str, url: str, scores: dict[str, float]
) -> None:
    """Score services/lead-gen signals."""
    # Booking/consultation CTAs
    for btn in soup.find_all(["button", "a"]):
        btn_text = btn.get_text(strip=True).lower()
        if any(kw in btn_text for kw in ("book a consultation", "schedule a call", "book now",
                                          "get a quote", "request a quote", "contact us",
                                          "book appointment", "schedule appointment",
                                          "free consultation", "get in touch")):
            scores["services"] += 1.5
            return

    # Services-related pages
    if any(p in url for p in ("/services", "/our-services", "/solutions", "/consultation")):
        scores["services"] += 1.0

    # Service keywords
    service_keywords = ("consultation", "appointment", "booking", "our services",
                        "we offer", "our expertise", "years of experience", "certified",
                        "licensed", "professional services")
    hits = sum(1 for kw in service_keywords if kw in text)
    scores["services"] += min(hits * 0.3, 1.5)


def _score_local(
    soup: BeautifulSoup, text: str, url: str, scores: dict[str, float]
) -> None:
    """Score local business signals."""
    # Physical address / Google Maps
    if soup.find("address"):
        scores["local_business"] += 0.5

    if soup.find("iframe", src=lambda s: s and "google.com/maps" in s):
        scores["local_business"] += 1.5

    # Local business JSON-LD
    import json
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            schema_type = item.get("@type", "")
            if isinstance(schema_type, list):
                schema_type = schema_type[0] if schema_type else ""
            if schema_type in ("LocalBusiness", "Restaurant", "Store", "MedicalBusiness",
                               "HealthAndBeautyBusiness", "FoodEstablishment",
                               "LodgingBusiness", "SportsActivityLocation"):
                scores["local_business"] += 2.0
                return

    # Visit-us, directions, store hours
    local_keywords = ("visit us", "store hours", "opening hours", "get directions",
                      "find us", "walk-in", "our location", "come visit", "our store")
    hits = sum(1 for kw in local_keywords if kw in text)
    scores["local_business"] += min(hits * 0.5, 1.5)


def _score_app(
    soup: BeautifulSoup, text: str, scores: dict[str, float]
) -> None:
    """Score mobile/web app signals."""
    # App store links
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if "apps.apple.com" in href or "itunes.apple.com" in href:
            scores["app"] += 2.0
        elif "play.google.com/store" in href:
            scores["app"] += 2.0

    # App store badges
    for img in soup.find_all("img", alt=True):
        alt = img["alt"].lower()
        if any(kw in alt for kw in ("app store", "google play", "download on",
                                     "get it on")):
            scores["app"] += 1.0

    # App-related keywords
    app_keywords = ("download the app", "get the app", "available on app store",
                    "available on google play", "mobile app", "install the app")
    hits = sum(1 for kw in app_keywords if kw in text)
    scores["app"] += min(hits * 0.5, 1.5)
