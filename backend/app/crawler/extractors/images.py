from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


def extract_images(pages: dict[str, str], base_url: str) -> dict:
    """Extract logo, favicon, hero images, and all notable images."""
    result: dict = {
        "logo_url": "",
        "favicon_url": "",
        "all_images": [],
    }

    seen: set[str] = set()

    for url, html in pages.items():
        soup = BeautifulSoup(html, "lxml")

        # Favicon — from homepage only
        if not result["favicon_url"]:
            result["favicon_url"] = _extract_favicon(soup, base_url)

        # Logo
        if not result["logo_url"]:
            result["logo_url"] = _extract_logo(soup, base_url)

        # All images
        for img in soup.find_all("img", src=True):
            src = _resolve_url(img["src"], base_url)
            if src and src not in seen and _is_meaningful_image(img):
                seen.add(src)
                result["all_images"].append(src)

        # CSS background images in hero sections
        for el in soup.select("[class*='hero'], [class*='banner'], header"):
            style = el.get("style", "")
            if "url(" in style:
                import re
                match = re.search(r"url\(['\"]?([^'\")\s]+)['\"]?\)", style)
                if match:
                    img_url = _resolve_url(match.group(1), base_url)
                    if img_url and img_url not in seen:
                        seen.add(img_url)
                        result["all_images"].insert(0, img_url)  # Hero at front

    # Limit
    result["all_images"] = result["all_images"][:50]
    return result


def _extract_favicon(soup: BeautifulSoup, base_url: str) -> str:
    for selector in [
        "link[rel='icon']",
        "link[rel='shortcut icon']",
        "link[rel='apple-touch-icon']",
    ]:
        tag = soup.select_one(selector)
        if tag and tag.get("href"):
            return _resolve_url(tag["href"], base_url)
    return _resolve_url("/favicon.ico", base_url)


def _extract_logo(soup: BeautifulSoup, base_url: str) -> str:
    # By common patterns
    for selector in [
        "img[class*='logo']",
        "img[id*='logo']",
        "img[alt*='logo']",
        "a[class*='logo'] img",
        "header img",
        "nav img",
        ".navbar-brand img",
    ]:
        tag = soup.select_one(selector)
        if tag and tag.get("src"):
            return _resolve_url(tag["src"], base_url)

    # SVG logo
    for selector in ["svg[class*='logo']", "a[class*='logo'] svg"]:
        tag = soup.select_one(selector)
        if tag:
            # Can't extract SVG as URL; skip
            pass

    return ""


def _resolve_url(src: str, base_url: str) -> str:
    if not src or src.startswith("data:"):
        return ""
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("http"):
        return src
    return urljoin(base_url, src)


def _is_meaningful_image(img) -> bool:
    """Filter out tiny tracking pixels, spacers, etc."""
    src = img.get("src", "")
    alt = img.get("alt", "")
    width = img.get("width", "")
    height = img.get("height", "")

    # Skip data URIs and tiny images
    if src.startswith("data:"):
        return False
    if width and height:
        try:
            if int(width) < 30 or int(height) < 30:
                return False
        except ValueError:
            pass

    # Skip tracking pixels
    if any(x in src.lower() for x in ("pixel", "tracking", "1x1", "spacer", "blank")):
        return False

    return True
