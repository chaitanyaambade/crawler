from __future__ import annotations

import re

from bs4 import BeautifulSoup

# Tailwind utility class pattern (e.g., "flex p-4 bg-white text-sm")
TAILWIND_RE = re.compile(
    r"\b(?:flex|grid|block|inline|hidden|"
    r"p[xytblr]?-\d|m[xytblr]?-\d|"
    r"w-\d|h-\d|"
    r"text-(?:xs|sm|base|lg|xl|\d)|"
    r"font-(?:bold|semibold|medium|light)|"
    r"bg-\w+|"
    r"rounded(?:-\w+)?|"
    r"shadow(?:-\w+)?|"
    r"border(?:-\w+)?)\b"
)


def extract_tech_stack(pages: dict[str, str]) -> dict:
    """Detect technologies used on the site by analyzing HTML signatures."""
    tech: dict[str, set[str]] = {
        "frameworks": set(),
        "cms": set(),
        "analytics": set(),
        "cdn": set(),
        "other": set(),
    }

    for _url, html in pages.items():
        soup = BeautifulSoup(html, "lxml")
        _detect_from_html(soup, html, tech)

    return {k: sorted(v) for k, v in tech.items()}


def _detect_from_html(
    soup: BeautifulSoup, raw_html: str, tech: dict[str, set[str]]
) -> None:
    """Run all detection heuristics on a single page."""
    html_lower = raw_html.lower()

    # Collect all script srcs and link hrefs for matching
    script_srcs: list[str] = []
    for script in soup.find_all("script", src=True):
        script_srcs.append(script["src"].lower())
    all_scripts_text = " ".join(script_srcs)

    link_hrefs: list[str] = []
    for link in soup.find_all("link", href=True):
        link_hrefs.append(link["href"].lower())
    all_links_text = " ".join(link_hrefs)

    # Generator meta tag
    generator = ""
    gen_meta = soup.find("meta", attrs={"name": "generator"})
    if gen_meta and gen_meta.get("content"):
        generator = gen_meta["content"].lower()

    # --- Frameworks ---

    # React
    if soup.find(attrs={"data-reactroot": True}) or "react" in all_scripts_text:
        tech["frameworks"].add("React")

    # Next.js
    if "__next_data__" in html_lower or "_next/static" in html_lower:
        tech["frameworks"].add("Next.js")

    # Vue.js
    if any(
        attr for el in soup.find_all(True)
        for attr in el.attrs if str(attr).startswith("data-v-")
    ) or "vue" in all_scripts_text:
        tech["frameworks"].add("Vue.js")

    # Nuxt.js
    if "__nuxt__" in html_lower or "__nuxt" in html_lower:
        tech["frameworks"].add("Nuxt.js")

    # Angular
    if soup.find(attrs={"ng-version": True}) or "zone.js" in all_scripts_text:
        tech["frameworks"].add("Angular")

    # Gatsby
    if soup.find(id="___gatsby"):
        tech["frameworks"].add("Gatsby")

    # Svelte
    if any(
        "svelte-" in " ".join(el.get("class", []))
        for el in soup.find_all(True, class_=True)
    ):
        tech["frameworks"].add("Svelte")

    # --- CMS ---

    if "wordpress" in generator or "wp-content" in html_lower:
        tech["cms"].add("WordPress")

    if "wix" in generator:
        tech["cms"].add("Wix")

    if "squarespace" in generator:
        tech["cms"].add("Squarespace")

    if "webflow" in generator:
        tech["cms"].add("Webflow")

    if "cdn.shopify.com" in html_lower:
        tech["cms"].add("Shopify")

    # --- Analytics ---

    if "google-analytics.com" in html_lower or "googletagmanager.com" in html_lower:
        tech["analytics"].add("Google Analytics")

    if "hotjar.com" in html_lower:
        tech["analytics"].add("Hotjar")

    if "segment.com" in html_lower or "segment.io" in html_lower:
        tech["analytics"].add("Segment")

    if "mixpanel.com" in html_lower:
        tech["analytics"].add("Mixpanel")

    # --- CDN ---

    if "cdnjs.cloudflare.com" in html_lower or "cloudflare" in html_lower:
        tech["cdn"].add("Cloudflare")

    if "cdn.jsdelivr.net" in html_lower:
        tech["cdn"].add("jsDelivr")

    if "unpkg.com" in html_lower:
        tech["cdn"].add("unpkg")

    # --- Other / CSS Frameworks / Libraries ---

    if "bootstrap.css" in all_links_text or "bootstrap.js" in all_scripts_text or "bootstrap.min" in html_lower:
        tech["other"].add("Bootstrap")

    if "jquery" in all_scripts_text:
        tech["other"].add("jQuery")

    # Tailwind detection: check if 3+ utility classes appear in a single class attr
    _detect_tailwind(soup, tech)


def _detect_tailwind(soup: BeautifulSoup, tech: dict[str, set[str]]) -> None:
    """Detect Tailwind CSS by counting utility classes in class attributes."""
    for el in soup.find_all(True, class_=True):
        class_str = " ".join(el.get("class", []))
        matches = TAILWIND_RE.findall(class_str)
        if len(matches) >= 3:
            tech["other"].add("Tailwind CSS")
            return
