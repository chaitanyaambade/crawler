from __future__ import annotations

import json

from bs4 import BeautifulSoup, Tag

from app.crawler.extractors._utils import extract_card_data, find_card_groups

TEAM_PATH_KEYWORDS = ("/team", "/our-team", "/people", "/leadership", "/staff")
ROLE_KEYWORDS = {
    "ceo", "cto", "cfo", "coo", "vp", "director", "manager", "lead",
    "engineer", "designer", "developer", "founder", "co-founder",
    "president", "head of", "chief", "partner", "analyst", "consultant",
    "officer", "architect", "scientist", "coordinator", "specialist",
}


def extract_team(pages: dict[str, str]) -> list[dict]:
    """Extract team members from team pages or about pages."""
    members: list[dict] = []

    for url, html in pages.items():
        url_lower = url.lower()
        soup = BeautifulSoup(html, "lxml")

        is_team_page = any(p in url_lower for p in TEAM_PATH_KEYWORDS)
        is_about_page = any(p in url_lower for p in ("/about", "/about-us"))

        if not is_team_page and not is_about_page:
            continue

        # Strategy 1: JSON-LD Person
        members.extend(_extract_jsonld_team(soup))

        # Strategy 2: Team sections + card detection
        containers: list[Tag] = []
        if is_team_page:
            containers.append(soup)
        else:
            containers.extend(
                soup.select(
                    "[id*='team'], [class*='team'], "
                    "[id*='leadership'], [class*='leadership'], "
                    "[id*='people'], [class*='people']"
                )
            )

        for container in containers:
            members.extend(_extract_card_team(container))

    # Deduplicate by name
    seen: set[str] = set()
    unique: list[dict] = []
    for member in members:
        key = member["name"].strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(member)

    return unique[:30]


def _extract_jsonld_team(soup: BeautifulSoup) -> list[dict]:
    """Parse JSON-LD @type: Person."""
    members: list[dict] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type", "")
            if isinstance(item_type, list):
                item_type = item_type[0] if item_type else ""
            if item_type != "Person":
                continue

            name = item.get("name", "")
            if not name:
                continue

            linkedin = ""
            same_as = item.get("sameAs", [])
            if isinstance(same_as, str):
                same_as = [same_as]
            for link in same_as:
                if "linkedin.com" in str(link):
                    linkedin = str(link)
                    break

            members.append({
                "name": name,
                "role": item.get("jobTitle", ""),
                "photo_url": item.get("image", "") if isinstance(item.get("image"), str) else "",
                "linkedin_url": linkedin,
            })

    return members


def _extract_card_team(container: Tag) -> list[dict]:
    """Extract team member cards using repeated structure detection."""
    members: list[dict] = []

    card_groups = find_card_groups(container, min_cards=2)

    for group in card_groups[:3]:
        for card in group:
            member = _parse_team_card(card)
            if member:
                members.append(member)

    # Fallback: class-based card detection
    if not members:
        for card in container.select(
            "[class*='team-member'], [class*='team-card'], "
            "[class*='member'], [class*='person'], [class*='staff']"
        ):
            member = _parse_team_card(card)
            if member:
                members.append(member)

    return members


def _parse_team_card(card: Tag) -> dict | None:
    """Parse a single team member card."""
    # Name: heading or strong
    heading = card.find(["h2", "h3", "h4", "h5"])
    if not heading:
        heading = card.find(["strong", "b"])
    if not heading:
        return None

    name = heading.get_text(strip=True)
    if not name or len(name) > 100 or len(name) < 2:
        return None

    # Role: short <p> text, or element with role-like keywords
    role = ""
    for p in card.find_all("p"):
        text = p.get_text(strip=True)
        if text and len(text) < 80 and _looks_like_role(text):
            role = text
            break
    # Also check <span> elements
    if not role:
        for span in card.find_all("span"):
            text = span.get_text(strip=True)
            if text and len(text) < 80 and _looks_like_role(text):
                role = text
                break

    # Photo
    photo_url = ""
    img = card.find("img", src=True)
    if img:
        photo_url = img["src"]

    # LinkedIn
    linkedin_url = ""
    for a in card.find_all("a", href=True):
        if "linkedin.com" in a["href"]:
            linkedin_url = a["href"]
            break

    return {
        "name": name,
        "role": role,
        "photo_url": photo_url,
        "linkedin_url": linkedin_url,
    }


def _looks_like_role(text: str) -> bool:
    """Heuristic: does this short text look like a job title?"""
    text_lower = text.lower()
    return any(kw in text_lower for kw in ROLE_KEYWORDS)
