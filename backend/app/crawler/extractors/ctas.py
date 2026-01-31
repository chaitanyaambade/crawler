from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

_CTA_CLASS_RE = re.compile(
    r"cta|btn|button|primary|hero-btn|action",
    re.IGNORECASE,
)

_HERO_RE = re.compile(r"hero|banner|jumbotron|masthead|above-fold", re.IGNORECASE)
_HEADER_RE = re.compile(r"header|navbar|nav-bar|topbar|top-bar", re.IGNORECASE)
_FOOTER_RE = re.compile(r"footer|bottom-bar", re.IGNORECASE)

_SKIP_TEXTS = {
    "", "×", "x", "close", "menu", "toggle", "search",
    "submit", "cancel", "back", "previous", "next",
}


def extract_ctas(pages: dict[str, str]) -> list[dict]:
    """Extract primary call-to-action buttons and their context."""
    ctas: list[dict] = []

    for url, html in pages.items():
        soup = BeautifulSoup(html, "lxml")

        # Find CTA-like elements
        for el in soup.find_all(["a", "button"]):
            if not _is_cta_element(el):
                continue

            text = el.get_text(strip=True)
            if not text or text.lower() in _SKIP_TEXTS or len(text) > 80:
                continue

            href = el.get("href", "") if el.name == "a" else ""
            location = _detect_location(el)

            ctas.append({
                "text": text,
                "url": href,
                "location": location,
            })

    # Deduplicate by text, prioritize hero/header CTAs
    seen: set[str] = set()
    unique: list[dict] = []

    # Sort: hero first, then header, then body, then footer
    priority = {"hero": 0, "header": 1, "body": 2, "footer": 3}
    ctas.sort(key=lambda c: priority.get(c["location"], 2))

    for cta in ctas:
        key = cta["text"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(cta)

    return unique[:15]


def _is_cta_element(el: Tag) -> bool:
    """Check if an element looks like a CTA button."""
    # Check class names
    classes = " ".join(el.get("class", []))
    if _CTA_CLASS_RE.search(classes):
        return True

    # Check role="button"
    if el.get("role") == "button":
        return True

    # For <a> tags, check if styled as a button (common pattern)
    if el.name == "a" and el.get("href"):
        # Links with button-like classes
        if any(c in classes.lower() for c in ("btn", "button", "cta")):
            return True
        # Links in hero/header areas with short text
        text = el.get_text(strip=True)
        if text and len(text) < 30:
            parent_classes = _get_ancestor_classes(el, levels=3)
            if _HERO_RE.search(parent_classes) or _HEADER_RE.search(parent_classes):
                return True

    return False


def _detect_location(el: Tag) -> str:
    """Determine where on the page this CTA is located."""
    ancestor_classes = _get_ancestor_classes(el, levels=5)

    if _HERO_RE.search(ancestor_classes):
        return "hero"
    if _HEADER_RE.search(ancestor_classes):
        return "header"
    if _FOOTER_RE.search(ancestor_classes):
        return "footer"
    return "body"


def _get_ancestor_classes(el: Tag, levels: int = 3) -> str:
    """Get concatenated class names of ancestors up to N levels."""
    parts: list[str] = []
    current = el.parent
    for _ in range(levels):
        if not current or not isinstance(current, Tag):
            break
        cls = current.get("class", [])
        if cls:
            parts.extend(cls)
        el_id = current.get("id", "")
        if el_id:
            parts.append(el_id)
        # Also check tag name
        if current.name in ("header", "footer", "nav"):
            parts.append(current.name)
        current = current.parent
    return " ".join(parts)
