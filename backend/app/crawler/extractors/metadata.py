from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup


def extract_metadata(html: str, url: str) -> dict:
    """Extract title, description, keywords, JSON-LD, OG tags from HTML."""
    soup = BeautifulSoup(html, "lxml")
    result: dict = {}

    # Title
    og_title = soup.find("meta", property="og:title")
    title_tag = soup.find("title")
    result["title"] = (
        og_title["content"] if og_title and og_title.get("content")
        else (title_tag.get_text(strip=True) if title_tag else "")
    )

    # Description
    og_desc = soup.find("meta", property="og:description")
    meta_desc = soup.find("meta", attrs={"name": "description"})
    result["description"] = (
        og_desc["content"] if og_desc and og_desc.get("content")
        else (meta_desc["content"] if meta_desc and meta_desc.get("content") else "")
    )

    # Tagline — often the second part of a "Brand | Tagline" title, or the h1 subtitle
    result["tagline"] = _extract_tagline(soup, result["title"])

    # Keywords
    meta_kw = soup.find("meta", attrs={"name": "keywords"})
    if meta_kw and meta_kw.get("content"):
        result["keywords"] = [k.strip() for k in meta_kw["content"].split(",") if k.strip()]
    else:
        result["keywords"] = []

    # OG image
    og_img = soup.find("meta", property="og:image")
    result["og_image"] = og_img["content"] if og_img and og_img.get("content") else ""

    # JSON-LD structured data
    result["structured_data"] = _extract_jsonld(soup)

    return result


def _extract_tagline(soup: BeautifulSoup, title: str) -> str:
    # Try "Brand | Tagline" or "Brand - Tagline" in title
    for sep in [" | ", " - ", " — ", " – "]:
        if sep in title:
            parts = title.split(sep, 1)
            if len(parts[1]) > 5:
                return parts[1].strip()

    # Try first h1's adjacent p or subtitle element
    h1 = soup.find("h1")
    if h1:
        sibling = h1.find_next_sibling(["p", "h2", "span"])
        if sibling:
            text = sibling.get_text(strip=True)
            if 10 < len(text) < 200:
                return text

    return ""


def _extract_jsonld(soup: BeautifulSoup) -> dict:
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                # Return the first Organization/WebSite item if found
                for item in data:
                    if isinstance(item, dict) and item.get("@type") in (
                        "Organization", "WebSite", "LocalBusiness", "Corporation"
                    ):
                        return item
                return data[0] if data else {}
            return data
        except (json.JSONDecodeError, TypeError):
            continue
    return {}
