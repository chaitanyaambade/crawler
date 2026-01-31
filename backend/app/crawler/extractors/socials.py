from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

SOCIAL_DOMAINS = {
    "instagram.com": "instagram",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "linkedin.com": "linkedin",
    "facebook.com": "facebook",
    "fb.com": "facebook",
    "youtube.com": "youtube",
    "github.com": "github",
    "tiktok.com": "tiktok",
    "pinterest.com": "pinterest",
    "medium.com": "medium",
    "discord.gg": "discord",
    "discord.com": "discord",
    "slack.com": "slack",
    "t.me": "telegram",
    "telegram.me": "telegram",
}

ALL_KEYS = {
    "instagram", "twitter", "linkedin", "facebook", "youtube", "github",
    "tiktok", "pinterest", "medium", "discord", "slack", "telegram",
}


def extract_social_links(pages: dict[str, str]) -> dict:
    """Extract social media links from all crawled pages, footer-first."""
    socials: dict[str, str] = {k: "" for k in ALL_KEYS}

    for _url, html in pages.items():
        soup = BeautifulSoup(html, "lxml")

        # Search footer first (most reliable location)
        footer = soup.find("footer")
        if footer:
            _scan_links(footer, socials)

        # Then scan full page for anything still missing
        if not all(socials.values()):
            _scan_links(soup, socials)

        # Early exit if all found
        if all(socials.values()):
            break

    return socials


def _scan_links(container: Tag, socials: dict[str, str]) -> None:
    """Scan all <a> links in a container and populate social dict."""
    for a in container.find_all("a", href=True):
        href: str = a["href"].strip()
        if not href.startswith("http"):
            continue

        parsed = urlparse(href)
        domain = parsed.netloc.lower().lstrip("www.")

        for social_domain, key in SOCIAL_DOMAINS.items():
            if domain == social_domain or domain.endswith("." + social_domain):
                if not socials[key]:
                    socials[key] = href
                break
