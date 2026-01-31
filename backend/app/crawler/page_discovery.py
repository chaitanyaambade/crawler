from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.config import settings

# Pages most likely to contain useful company info, ordered by priority
PRIORITY_PATHS = [
    "/about", "/about-us", "/about_us",
    "/products", "/services", "/features",
    "/pricing",
    "/team", "/our-team",
    "/contact", "/contact-us",
    "/blog",
    "/careers",
    "/faq",
]


def discover_links(html: str, base_url: str) -> list[str]:
    """Extract internal links from HTML, prioritised by likely usefulness."""
    parsed_base = urlparse(base_url)
    domain = parsed_base.netloc
    soup = BeautifulSoup(html, "lxml")

    seen: set[str] = set()
    links: list[str] = []

    for tag in soup.find_all("a", href=True):
        href: str = tag["href"].strip()
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue

        full = urljoin(base_url, href)
        parsed = urlparse(full)

        # Same domain only
        if parsed.netloc != domain:
            continue

        # Normalise: strip query/fragment, ensure trailing slash consistency
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        if clean in seen or clean == base_url.rstrip("/"):
            continue

        # Skip non-HTML resources
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in (
            ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".css", ".js",
            ".zip", ".mp4", ".mp3", ".webp", ".ico",
        )):
            continue

        seen.add(clean)
        links.append(clean)

    # Sort: priority paths first, then alphabetical
    return _prioritise(links, base_url)


def _prioritise(links: list[str], base_url: str) -> list[str]:
    base_path = urlparse(base_url).path.rstrip("/")

    def sort_key(url: str) -> tuple[int, str]:
        path = urlparse(url).path.rstrip("/")
        rel = path[len(base_path):] if path.startswith(base_path) else path
        rel_lower = rel.lower()
        for i, p in enumerate(PRIORITY_PATHS):
            if rel_lower == p or rel_lower.startswith(p + "/"):
                return (i, url)
        return (len(PRIORITY_PATHS), url)

    sorted_links = sorted(links, key=sort_key)
    return sorted_links[: settings.max_pages - 1]  # -1 for homepage


def discover_links_recursive(
    pages_html: dict[str, str], base_url: str
) -> list[str]:
    """2-level discovery: find links from all already-fetched pages.

    Takes HTML of pages fetched so far (homepage + level-0 pages),
    runs discover_links() on each to find level-1 links, then deduplicates
    and prioritises, capping at max_pages.
    """
    all_known = set(pages_html.keys())
    all_known.add(base_url.rstrip("/"))

    new_links: list[str] = []
    for page_url, html in pages_html.items():
        found = discover_links(html, base_url)
        for link in found:
            clean = link.rstrip("/")
            if clean not in all_known and link not in new_links:
                all_known.add(clean)
                new_links.append(link)

    # Cap to remaining budget
    remaining = max(0, settings.max_pages - len(pages_html))
    return _prioritise(new_links, base_url)[:remaining]
