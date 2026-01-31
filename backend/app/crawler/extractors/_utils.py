from __future__ import annotations

from bs4 import Tag


def find_card_groups(container: Tag, min_cards: int = 3) -> list[list[Tag]]:
    """Find groups of similarly-structured sibling elements.

    Scans each element with direct children, computes a "tag signature"
    for each child (sorted list of descendant tag names), and groups
    children sharing the same signature. Returns groups with >= min_cards
    members, sorted by group size descending.
    """
    groups: list[list[Tag]] = []

    for parent in container.find_all(True):
        children = [c for c in parent.children if isinstance(c, Tag)]
        if len(children) < min_cards:
            continue

        # Group children by their structural signature
        sig_map: dict[str, list[Tag]] = {}
        for child in children:
            sig = _tag_signature(child)
            if sig:
                sig_map.setdefault(sig, []).append(child)

        for sig, members in sig_map.items():
            if len(members) >= min_cards:
                # Avoid returning duplicate groups (subsets of already-found)
                groups.append(members)

    # Deduplicate: keep the largest group per parent element
    seen_parents: set[int] = set()
    unique: list[list[Tag]] = []
    groups.sort(key=len, reverse=True)
    for group in groups:
        parent_id = id(group[0].parent)
        if parent_id not in seen_parents:
            seen_parents.add(parent_id)
            unique.append(group)

    return unique


def _tag_signature(element: Tag) -> str:
    """Compute a structural signature from an element's child tag names."""
    child_tags = []
    for child in element.descendants:
        if isinstance(child, Tag):
            child_tags.append(child.name)
    if not child_tags:
        return ""
    return ",".join(sorted(child_tags))


def extract_card_data(card: Tag) -> dict:
    """Extract name/description/image from a generic card element."""
    data: dict = {"name": "", "description": "", "image_url": ""}

    # Name: first heading (h2-h5) or strong/b
    heading = card.find(["h2", "h3", "h4", "h5"])
    if not heading:
        heading = card.find(["strong", "b"])
    if heading:
        data["name"] = heading.get_text(strip=True)[:200]

    # Description: first <p> text
    p = card.find("p")
    if p:
        data["description"] = p.get_text(strip=True)[:300]

    # Image: first <img> src
    img = card.find("img", src=True)
    if img:
        data["image_url"] = img["src"]

    return data
