from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup


def extract_company_info(pages: dict[str, str]) -> dict:
    """Extract about text, company name, contact info, and org metadata from all pages."""
    result: dict = {
        "name": "",
        "about": "",
        "contact": {"emails": [], "phones": [], "addresses": []},
        "founded_year": "",
        "employee_count": "",
        "headquarters": "",
    }

    for url, html in pages.items():
        soup = BeautifulSoup(html, "lxml")
        url_lower = url.lower()

        # Company name from structured data or OG site_name
        if not result["name"]:
            og_site = soup.find("meta", property="og:site_name")
            if og_site and og_site.get("content"):
                result["name"] = og_site["content"]

        # About text -- prefer /about pages
        if any(p in url_lower for p in ("/about", "/about-us", "/about_us")):
            about_text = _extract_about(soup)
            if about_text and len(about_text) > len(result["about"]):
                result["about"] = about_text

        # Collect all emails and phones
        _extract_all_emails(soup, result["contact"])
        _extract_all_phones(soup, result["contact"])
        _extract_addresses(soup, result["contact"])

        # Org metadata from JSON-LD
        _extract_org_jsonld(soup, result)

    # Fallback: extract about from homepage if no /about page
    if not result["about"]:
        homepage_urls = [u for u in pages if u.rstrip("/").count("/") <= 3]
        if homepage_urls:
            soup = BeautifulSoup(pages[homepage_urls[0]], "lxml")
            result["about"] = _extract_about(soup)

    return result


def _extract_about(soup: BeautifulSoup) -> str:
    """Extract the longest meaningful paragraph as the about text."""
    for selector in [
        "section[id*='about']", "div[id*='about']",
        "section[class*='about']", "div[class*='about']",
        "main", "article",
    ]:
        section = soup.select_one(selector)
        if section:
            paragraphs = section.find_all("p")
            texts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50]
            if texts:
                return " ".join(texts[:3])

    all_p = soup.find_all("p")
    texts = [(p.get_text(strip=True), len(p.get_text(strip=True))) for p in all_p]
    texts.sort(key=lambda x: x[1], reverse=True)
    if texts and texts[0][1] > 50:
        return texts[0][0]

    return ""


def _extract_all_emails(soup: BeautifulSoup, contact: dict) -> None:
    """Collect every unique email from the page."""
    emails = contact["emails"]
    seen = set(emails)

    # mailto links
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0].strip().lower()
            if "@" in email and email not in seen:
                seen.add(email)
                emails.append(email)

    # Regex fallback across full page text
    text = soup.get_text()
    for match in re.finditer(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}", text):
        email = match.group(0).lower()
        if email not in seen:
            seen.add(email)
            emails.append(email)


def _extract_all_phones(soup: BeautifulSoup, contact: dict) -> None:
    """Collect every unique phone number from the page."""
    phones = contact["phones"]
    # Normalize to digits-only for deduplication (handles +91-8433808080 vs 8433808080)
    seen_normalized: set[str] = {_normalize_phone(p) for p in phones}

    def _add_phone(raw: str) -> None:
        # Strip trailing punctuation
        cleaned = raw.rstrip(".,;:!?")
        if not cleaned:
            return
        norm = _normalize_phone(cleaned)
        # Skip if we already have a number whose digits are a suffix/prefix match
        if norm in seen_normalized:
            return
        # Also check if this number's core digits overlap with an existing one
        for existing in list(seen_normalized):
            if existing.endswith(norm) or norm.endswith(existing):
                return
        seen_normalized.add(norm)
        phones.append(cleaned)

    # tel: links
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("tel:"):
            phone = href.replace("tel:", "").strip()
            if phone:
                _add_phone(phone)

    # Regex fallback
    text = soup.get_text()
    for match in re.finditer(r"[\+]?[(]?[0-9]{1,4}[)]?[-\s./0-9]{7,15}", text):
        phone = match.group(0).strip()
        if len(phone) >= 10:
            _add_phone(phone)


def _normalize_phone(phone: str) -> str:
    """Strip a phone number to digits only for dedup comparison."""
    return re.sub(r"[^0-9]", "", phone)


def _extract_addresses(soup: BeautifulSoup, contact: dict) -> None:
    """Extract physical addresses."""
    addresses = contact["addresses"]
    for addr in soup.find_all("address"):
        text = addr.get_text(strip=True)
        if text and len(text) > 10 and text not in addresses:
            addresses.append(text)
    for el in soup.select("[itemprop='address']"):
        text = el.get_text(strip=True)
        if text and text not in addresses:
            addresses.append(text)


def _extract_org_jsonld(soup: BeautifulSoup, result: dict) -> None:
    """Parse JSON-LD Organization schema for founding date, employees, HQ."""
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

            if item_type not in ("Organization", "Corporation", "LocalBusiness"):
                continue

            if not result["founded_year"] and item.get("foundingDate"):
                result["founded_year"] = str(item["foundingDate"])[:4]

            if not result["employee_count"]:
                employees = item.get("numberOfEmployees")
                if isinstance(employees, dict):
                    result["employee_count"] = str(employees.get("value", ""))
                elif employees:
                    result["employee_count"] = str(employees)

            if not result["headquarters"]:
                address = item.get("address")
                if isinstance(address, dict):
                    parts = [
                        address.get("streetAddress", ""),
                        address.get("addressLocality", ""),
                        address.get("addressRegion", ""),
                        address.get("addressCountry", ""),
                    ]
                    hq = ", ".join(p for p in parts if p)
                    if hq:
                        result["headquarters"] = hq
                elif isinstance(address, str) and address:
                    result["headquarters"] = address
