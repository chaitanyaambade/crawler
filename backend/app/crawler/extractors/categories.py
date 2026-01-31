"""Smart product-category extraction.

Instead of maintaining hardcoded skip-lists for every possible website,
this module uses a **scoring system** to decide whether a navigation link
is likely a product/service category.  Every candidate gets positive and
negative signals; only candidates whose score exceeds a threshold are kept.
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring helpers – patterns, not exhaustive lists
# ---------------------------------------------------------------------------

# URL patterns that positively suggest a product/category listing page
_CATEGORY_URL_RE = re.compile(
    r"/(?:collections?|categories?|catalog|shop|department|browse)"
    r"|/c/[0-9]|/b/[0-9]|/pl/|/clp/",
    re.IGNORECASE,
)

# URL patterns that suggest a utility / non-category page
_UTILITY_URL_RE = re.compile(
    r"/(?:account|login|sign[-_]?in|register|cart|checkout|bag|wishlist"
    r"|help|faq|support|contact|privacy|terms|policy|legal|sitemap"
    r"|careers|jobs|press|media|investors|accessibility|newsletter"
    r"|orders?|returns?|shipping|tracking|gift[-_]?cards?|size[-_]?guide"
    r"|store[-_]?(?:locator|finder)|find[-_]?(?:a[-_]?)?store"
    r"|blog|article|post|news|about(?:[-_]us)?"
    r"|pages/(?!collections))",
    re.IGNORECASE,
)

# Name patterns that suggest utility / non-category
_UTILITY_NAME_RE = re.compile(
    r"^(?:home|log\s*in|sign\s*(?:in|up)|register|cart|bag|checkout"
    r"|account|my\s+account|help|faq|support|contact(?:\s+us)?"
    r"|privacy|terms|search|wishlist|menu|close|skip"
    r"|more|see\s+all|view\s+all|show\s+all|all\s+categories"
    r"|download\s+app|get\s+the\s+app)$",
    re.IGNORECASE,
)

# Segments in URL paths that are structural wrappers, not category names
_WRAPPER_SEGMENTS = frozenset({
    "products", "product", "shop", "store", "collections", "collection",
    "category", "categories", "catalog", "department", "departments",
    "pages", "page", "p", "c", "b", "s", "t", "w",
    "cp", "lp", "dp", "pl", "clp", "item", "detail",
})

# Two-letter country / locale codes
_LOCALE_RE = re.compile(r"^[a-z]{2}(?:[-_][a-z]{2,4})?$", re.IGNORECASE)

# Segments that are clearly technical / non-content
_TECHNICAL_RE = re.compile(
    r"^(?:cdn|assets?|static|media|images?|img|js|css|api|v[0-9]|dist"
    r"|_next|__next|_nuxt|wp-content|wp-includes|wp-admin|wp-json"
    r"|node_modules|\.well-known)$",
    re.IGNORECASE,
)


def _score_candidate(name: str, url: str, has_subcategories: bool) -> float:
    """Score a nav item – positive means likely category, negative means utility.

    The scoring uses patterns rather than site-specific keywords so it
    generalises across any website.
    """
    score = 0.0
    lower_name = name.strip().lower()
    path = urlparse(url).path.lower() if url else ""

    # --- Negative signals ---------------------------------------------------

    # Utility name pattern
    if _UTILITY_NAME_RE.match(lower_name):
        score -= 5.0

    # Utility URL pattern
    if path and _UTILITY_URL_RE.search(path):
        score -= 5.0

    # Very long names are rarely categories (e.g. "What could have caused this?")
    if len(lower_name) > 60:
        score -= 2.0

    # Names with sentence-like patterns (contains verbs / questions)
    if re.search(r"\b(?:how|what|why|when|where|can|does|do|is|are|we|our|your|my)\b", lower_name):
        score -= 1.5

    # Links to external domains or anchors
    if url and (url.startswith("mailto:") or url.startswith("tel:") or url.startswith("#")):
        score -= 5.0

    # Empty URL or javascript:void
    if not url or "javascript:" in url.lower():
        score -= 2.0

    # Technical / CDN URLs
    if path:
        for seg in path.strip("/").split("/")[:2]:
            if _TECHNICAL_RE.match(seg):
                score -= 5.0
                break

    # --- Positive signals ---------------------------------------------------

    # Category-like URL pattern (/collections/, /c/123, /shop/men etc.)
    if path and _CATEGORY_URL_RE.search(path):
        score += 3.0

    # Has subcategories → strong signal it's a category
    if has_subcategories:
        score += 2.5

    # Short, punchy name (1-4 words) typical of categories
    word_count = len(lower_name.split())
    if 1 <= word_count <= 3:
        score += 1.0
    elif word_count == 4:
        score += 0.5

    # Name is Title Case or ALL CAPS (typical for categories)
    if name == name.title() or (name == name.upper() and len(name) > 1):
        score += 0.5

    # URL path depth 1-3 (shallow = category, deep = product detail)
    path_depth = len([s for s in path.strip("/").split("/") if s])
    if 1 <= path_depth <= 3:
        score += 0.5

    return score


_SCORE_THRESHOLD = 0.0  # must be net-positive to be kept


def extract_categories(pages: dict[str, str]) -> list[dict]:
    """Extract product categories from a website using multiple strategies."""
    candidates: list[dict] = []

    homepage_url = list(pages.keys())[0] if pages else ""
    homepage_html = pages.get(homepage_url, "")

    if homepage_html:
        soup = BeautifulSoup(homepage_html, "lxml")
        # Strategy 1: Nav menus (including mega-menus)
        candidates.extend(_extract_nav_categories(soup, homepage_url))
        # Strategy 2: JSON-LD
        candidates.extend(_extract_jsonld_categories(soup))
        # Strategy 3: Footer category links
        candidates.extend(_extract_footer_categories(soup, homepage_url))

    # Strategy 4: URL path clustering with subcategories
    candidates.extend(_extract_url_path_categories(pages))

    # Score, filter, and deduplicate
    seen: set[str] = set()
    results: list[dict] = []

    for cat in candidates:
        key = cat["name"].strip().lower()
        if not key or len(key) <= 1 or key in seen:
            continue

        has_subs = bool(cat.get("subcategories"))
        score = _score_candidate(cat["name"], cat.get("url", ""), has_subs)

        if score <= _SCORE_THRESHOLD:
            continue

        seen.add(key)

        # Score and filter subcategories too
        if cat.get("subcategories"):
            sub_seen: set[str] = set()
            filtered_subs: list[dict] = []
            for sub in cat["subcategories"]:
                sub_key = sub["name"].strip().lower()
                if not sub_key or sub_key in sub_seen or sub_key == key:
                    continue
                sub_score = _score_candidate(sub["name"], sub.get("url", ""), False)
                if sub_score > _SCORE_THRESHOLD:
                    sub_seen.add(sub_key)
                    filtered_subs.append(sub)
            cat["subcategories"] = filtered_subs

        results.append(cat)

    return results[:30]


# ---------------------------------------------------------------------------
# Strategy 1: Navigation menus (nav, mega-menus, header)
# ---------------------------------------------------------------------------

def _extract_nav_categories(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Parse <nav>, mega-menus, and header elements for categories."""
    categories: list[dict] = []

    for nav in soup.find_all("nav"):
        cats = _parse_nav_container(nav, base_url)
        if cats:
            categories.extend(cats)

    if not categories:
        header = soup.find("header")
        if header:
            categories.extend(_parse_nav_container(header, base_url))

    if not categories:
        for div in soup.find_all("div", class_=re.compile(
            r"mega[-_]?menu|nav[-_]?menu|main[-_]?nav|primary[-_]?nav|"
            r"site[-_]?nav|header[-_]?nav|desktop[-_]?nav",
            re.IGNORECASE,
        )):
            cats = _parse_nav_container(div, base_url)
            if cats:
                categories.extend(cats)
                break

    return categories


def _parse_nav_container(container: Tag, base_url: str) -> list[dict]:
    """Parse a nav-like container for category items."""
    categories: list[dict] = []

    top_ul = container.find("ul")
    if top_ul:
        for li in top_ul.find_all("li", recursive=False):
            cat = _parse_nav_item(li, base_url)
            if cat:
                categories.append(cat)

    if not categories:
        links = container.find_all("a", recursive=False)
        if not links:
            for child in container.children:
                if isinstance(child, Tag):
                    links = child.find_all("a", recursive=False)
                    if links:
                        break

        for link in links:
            name = link.get_text(strip=True)[:200]
            if not name or len(name) <= 1:
                continue
            href = link.get("href", "")
            url = urljoin(base_url, href) if href else ""
            categories.append({"name": name, "url": url, "subcategories": []})

    return categories


def _parse_nav_item(li: Tag, base_url: str) -> dict | None:
    """Convert a <li> (with optional nested <ul> or mega-menu div) to a category."""
    link = li.find("a")
    if not link:
        return None

    name = link.get_text(strip=True)[:200]
    if not name or len(name) <= 1:
        return None

    href = link.get("href", "")
    url = urljoin(base_url, href) if href else ""

    subcategories: list[dict] = []

    # Nested <ul>
    nested_ul = li.find("ul")
    if nested_ul:
        for sub_li in nested_ul.find_all("li", recursive=False):
            sub = _parse_nav_item(sub_li, base_url)
            if sub:
                subcategories.append(sub)

    # Mega-menu div panels
    if not subcategories:
        mega_div = li.find("div", class_=re.compile(
            r"dropdown|submenu|mega|panel|flyout|popup", re.IGNORECASE
        ))
        if mega_div:
            for sub_link in mega_div.find_all("a"):
                sub_name = sub_link.get_text(strip=True)[:200]
                if not sub_name or sub_name.lower() == name.lower():
                    continue
                sub_href = sub_link.get("href", "")
                sub_url = urljoin(base_url, sub_href) if sub_href else ""
                subcategories.append({
                    "name": sub_name,
                    "url": sub_url,
                    "subcategories": [],
                })

    return {"name": name, "url": url, "subcategories": subcategories}


# ---------------------------------------------------------------------------
# Strategy 2: JSON-LD SiteNavigationElement / ItemList
# ---------------------------------------------------------------------------

def _extract_jsonld_categories(soup: BeautifulSoup) -> list[dict]:
    """Parse JSON-LD for SiteNavigationElement or ItemList schemas."""
    categories: list[dict] = []

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

            if schema_type == "SiteNavigationElement":
                name = item.get("name", "")
                url = item.get("url", "")
                if name:
                    categories.append({"name": name, "url": url, "subcategories": []})

            elif schema_type == "ItemList":
                for elem in item.get("itemListElement", []):
                    if not isinstance(elem, dict):
                        continue
                    name = elem.get("name", "")
                    url = ""
                    item_ref = elem.get("item")
                    if isinstance(item_ref, dict):
                        url = item_ref.get("url", "")
                    elif isinstance(item_ref, str):
                        url = item_ref
                    if not url:
                        url = elem.get("url", "")
                    if name:
                        categories.append({"name": name, "url": url, "subcategories": []})

    return categories


# ---------------------------------------------------------------------------
# Strategy 3: Footer category links
# ---------------------------------------------------------------------------

def _extract_footer_categories(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Extract category links from footer sections with category-like headings."""
    categories: list[dict] = []
    footer = soup.find("footer")
    if not footer:
        return categories

    category_headings = re.compile(
        r"^(shop|products?|categories|departments?|browse|our\s+brands?"
        r"|collections?|explore|what\s+we\s+(?:do|offer)|services?)$",
        re.IGNORECASE,
    )

    for heading in footer.find_all(re.compile(r"^h[2-6]$")):
        heading_text = heading.get_text(strip=True)
        if not category_headings.match(heading_text):
            continue

        sibling = heading.find_next_sibling()
        if not sibling or not isinstance(sibling, Tag):
            continue

        for link in sibling.find_all("a"):
            name = link.get_text(strip=True)[:200]
            if not name:
                continue
            href = link.get("href", "")
            url = urljoin(base_url, href) if href else ""
            categories.append({"name": name, "url": url, "subcategories": []})

    return categories


# ---------------------------------------------------------------------------
# Strategy 4: URL path clustering with subcategories
# ---------------------------------------------------------------------------

def _extract_url_path_categories(pages: dict[str, str]) -> list[dict]:
    """Cluster internal links by path segments to infer categories."""
    if not pages:
        return []

    base_url = list(pages.keys())[0]
    base_domain = urlparse(base_url).netloc

    all_links: set[str] = set()
    for page_url, html in pages.items():
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            href = urljoin(page_url, a["href"].strip())
            parsed = urlparse(href)
            if parsed.netloc == base_domain:
                clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
                all_links.add(clean)

    top_counter: Counter[str] = Counter()
    top_url: dict[str, str] = {}
    sub_groups: dict[str, Counter[str]] = defaultdict(Counter)
    sub_url: dict[str, dict[str, str]] = defaultdict(dict)

    for link in all_links:
        segments = _meaningful_segments(urlparse(link).path)
        if not segments:
            continue

        top = segments[0]
        top_counter[top] += 1
        if top not in top_url:
            top_url[top] = link

        if len(segments) > 1:
            sub = segments[1]
            sub_groups[top][sub] += 1
            if sub not in sub_url[top]:
                sub_url[top][sub] = link

    categories: list[dict] = []
    for segment, count in top_counter.most_common(25):
        if count < 3:
            continue

        name = segment.replace("-", " ").replace("_", " ").title()
        if not name or len(name) <= 1:
            continue

        subcategories: list[dict] = []
        for sub_seg, sub_count in sub_groups[segment].most_common(15):
            if sub_count < 2:
                continue
            sub_name = sub_seg.replace("-", " ").replace("_", " ").title()
            if sub_name and len(sub_name) > 1:
                subcategories.append({
                    "name": sub_name,
                    "url": sub_url[segment].get(sub_seg, ""),
                    "subcategories": [],
                })

        categories.append({
            "name": name,
            "url": top_url[segment],
            "subcategories": subcategories,
        })

    return categories


def _meaningful_segments(path: str) -> list[str]:
    """Extract meaningful path segments, skipping wrappers, locales, and IDs."""
    raw = [s for s in path.strip("/").split("/") if s]
    segments: list[str] = []

    for seg in raw:
        lower = seg.lower()

        # Skip wrapper segments (structural, not content)
        if lower in _WRAPPER_SEGMENTS:
            continue

        # Skip technical paths
        if _TECHNICAL_RE.match(lower):
            continue

        # Skip very short segments (likely locale codes: /en/, /fr/, /in/)
        if len(lower) <= 2:
            continue

        # Skip locale patterns like "en-us", "fr-fr"
        if _LOCALE_RE.match(lower) and len(lower) <= 5:
            continue

        # Skip numeric IDs and hex hashes
        if re.match(r"^[0-9]+$|^[0-9a-f]{8,}$", lower):
            continue

        segments.append(lower)

    return segments
