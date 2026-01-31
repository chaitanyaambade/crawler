from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

_stealth = Stealth()

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    url: str
    html: str
    status: int
    used_playwright: bool = False
    screenshot_bytes: bytes | None = None


async def fetch_page(
    url: str,
    take_screenshot: bool = False,
) -> FetchResult:
    """Fetch a page. Try httpx first; fall back to Playwright if body is thin."""
    # Try httpx (fast)
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=15.0
        ) as client:
            resp = await client.get(url, headers=_headers())
            html = resp.text
            body_text = BeautifulSoup(html, "lxml").get_text(strip=True)
            if len(body_text) >= settings.min_body_length and not take_screenshot:
                return FetchResult(url=url, html=html, status=resp.status_code)
    except Exception as exc:
        logger.debug("httpx failed for %s: %s", url, exc)
        html = ""

    # Playwright fallback (handles JS-rendered pages)
    return await _fetch_with_playwright(url, take_screenshot)


async def _fetch_with_playwright(
    url: str, take_screenshot: bool
) -> FetchResult:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await _stealth.apply_stealth_async(page)

            # Try networkidle first; fall back to domcontentloaded on timeout
            try:
                await page.goto(url, wait_until="networkidle", timeout=settings.playwright_timeout)
            except Exception:
                logger.debug("networkidle timed out for %s, retrying with domcontentloaded", url)
                await page.goto(url, wait_until="domcontentloaded", timeout=settings.playwright_timeout)

            html = await page.content()
            screenshot = None
            if take_screenshot:
                screenshot = await page.screenshot(full_page=False, type="png")
            return FetchResult(
                url=url,
                html=html,
                status=200,
                used_playwright=True,
                screenshot_bytes=screenshot,
            )
        finally:
            await browser.close()


def _headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AxgenCrawler/1.0; +https://axgen.dev)"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
