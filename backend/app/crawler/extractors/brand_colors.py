from __future__ import annotations

import io
import re

from bs4 import BeautifulSoup


def extract_brand_colors(
    html: str,
    screenshot_bytes: bytes | None = None,
) -> dict:
    """Extract brand colors and fonts from screenshot (ColorThief) + CSS."""
    result: dict = {
        "dominant_color": "",
        "palette": [],
        "fonts": [],
    }

    # Method 1: Screenshot-based extraction via ColorThief
    if screenshot_bytes:
        try:
            from colorthief import ColorThief
            from PIL import Image

            img = Image.open(io.BytesIO(screenshot_bytes))
            # Save to a temporary buffer for ColorThief
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)

            ct = ColorThief(buf)
            dominant = ct.get_color(quality=5)
            result["dominant_color"] = _rgb_to_hex(dominant)

            palette = ct.get_palette(color_count=6, quality=5)
            result["palette"] = [_rgb_to_hex(c) for c in palette]
        except Exception:
            pass  # Fall through to CSS extraction

    # Font extraction
    result["fonts"] = _extract_fonts(html)

    # Method 2: CSS hex extraction from inline styles and style tags
    css_colors = _extract_css_colors(html)

    # Merge: prefer screenshot dominant, supplement palette with CSS colors
    if not result["dominant_color"] and css_colors:
        result["dominant_color"] = css_colors[0]
    if not result["palette"]:
        result["palette"] = css_colors[:6]
    else:
        # Add unique CSS colors to palette
        existing = set(result["palette"])
        for c in css_colors:
            if c not in existing and len(result["palette"]) < 8:
                result["palette"].append(c)
                existing.add(c)

    return result


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb).upper()


def _extract_css_colors(html: str) -> list[str]:
    """Extract hex colors from CSS in style tags and inline styles."""
    soup = BeautifulSoup(html, "lxml")
    colors: list[str] = []
    seen: set[str] = set()

    # From <style> tags
    for style in soup.find_all("style"):
        text = style.string or ""
        colors.extend(_find_hex_colors(text, seen))

    # From inline styles on key elements (headers, buttons, navs)
    for el in soup.select("header, nav, button, a, h1, h2, .btn, [class*='brand']"):
        style = el.get("style", "")
        if style:
            colors.extend(_find_hex_colors(style, seen))

    # Filter out black, white, and near-gray (not brand colors)
    return [c for c in colors if not _is_neutral(c)]


def _find_hex_colors(text: str, seen: set[str]) -> list[str]:
    matches = re.findall(r"#([0-9a-fA-F]{3,8})\b", text)
    results: list[str] = []
    for m in matches:
        if len(m) == 3:
            hex_color = "#" + "".join(c * 2 for c in m).upper()
        elif len(m) == 6:
            hex_color = "#" + m.upper()
        else:
            continue
        if hex_color not in seen:
            seen.add(hex_color)
            results.append(hex_color)
    return results


def _is_neutral(hex_color: str) -> bool:
    """Check if a color is too close to black, white, or gray."""
    hex_str = hex_color.lstrip("#")
    r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
    # Near white
    if r > 240 and g > 240 and b > 240:
        return True
    # Near black
    if r < 15 and g < 15 and b < 15:
        return True
    # Gray (low saturation)
    max_c, min_c = max(r, g, b), min(r, g, b)
    if max_c - min_c < 15 and max_c > 30:
        return True
    return False


# Generic CSS font families to exclude
_GENERIC_FONTS = {
    "serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui",
    "ui-serif", "ui-sans-serif", "ui-monospace", "ui-rounded",
    "inherit", "initial", "unset", "none", "auto",
    "-apple-system", "blinkmacsystemfont", "segoe ui",
}


def _extract_fonts(html: str) -> list[str]:
    """Extract brand fonts from Google Fonts links, CSS font-family, and @font-face."""
    soup = BeautifulSoup(html, "lxml")
    fonts: list[str] = []
    seen: set[str] = set()

    def _add(name: str) -> None:
        cleaned = name.strip().strip("'\"").strip()
        if not cleaned or cleaned.lower() in _GENERIC_FONTS:
            return
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            fonts.append(cleaned)

    # 1. Google Fonts links: <link href="fonts.googleapis.com/css?family=Roboto+Mono|Open+Sans">
    for link in soup.find_all("link", href=True):
        href = link["href"]
        if "fonts.googleapis.com" in href or "fonts.gstatic.com" in href:
            # Parse family= parameter
            family_match = re.search(r"family=([^&\"]+)", href)
            if family_match:
                families_str = family_match.group(1)
                # Families are separated by | and variants by : or @
                for family in families_str.split("|"):
                    # Strip weight/variant info: "Roboto:400,700" → "Roboto"
                    name = family.split(":")[0].split("@")[0].replace("+", " ").strip()
                    _add(name)

    # 2. Adobe Fonts / Typekit
    for link in soup.find_all("link", href=True):
        if "use.typekit.net" in link["href"]:
            _add("Adobe Fonts (Typekit)")  # Can't resolve exact names without JS

    # 3. CSS font-family in <style> tags and inline styles
    css_text = ""
    for style in soup.find_all("style"):
        css_text += (style.string or "") + "\n"
    # Also check inline styles on body, h1-h3, p
    for el in soup.select("body, h1, h2, h3, p, [class*='heading'], [class*='title']"):
        inline = el.get("style", "")
        if inline:
            css_text += inline + "\n"

    # Parse font-family declarations
    for match in re.finditer(r"font-family\s*:\s*([^;}]+)", css_text, re.IGNORECASE):
        families = match.group(1)
        for family in families.split(","):
            _add(family)

    # 4. @font-face src declarations — extract family name
    for match in re.finditer(
        r"@font-face\s*\{[^}]*font-family\s*:\s*['\"]?([^'\";}]+)",
        css_text,
        re.IGNORECASE,
    ):
        _add(match.group(1))

    return fonts[:10]
