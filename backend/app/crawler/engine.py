from __future__ import annotations

import asyncio
import logging
import time

from app.config import settings
from app.crawler.extractors.brand_colors import extract_brand_colors
from app.crawler.extractors.brand_voice import analyze_brand_voice
from app.crawler.extractors.business_type import detect_business_type
from app.crawler.extractors.case_studies import extract_case_studies
from app.crawler.extractors.client_logos import extract_client_logos
from app.crawler.extractors.ctas import extract_ctas
from app.crawler.extractors.industry import extract_industry
from app.crawler.extractors.lead_magnets import extract_lead_magnets
from app.crawler.extractors.media_mentions import extract_media_mentions
from app.crawler.extractors.categories import extract_categories
from app.crawler.extractors.company_info import extract_company_info
from app.crawler.extractors.images import extract_images
from app.crawler.extractors.metadata import extract_metadata
from app.crawler.extractors.pricing import extract_pricing
from app.crawler.extractors.products import extract_products
from app.crawler.extractors.socials import extract_social_links
from app.crawler.extractors.team import extract_team
from app.crawler.extractors.tech_stack import extract_tech_stack
from app.crawler.extractors.testimonials import extract_testimonials
from app.crawler.fetcher import FetchResult, fetch_page
from app.crawler.page_discovery import discover_links, discover_links_recursive
from app.models import CrawlResult, StepStatus
from app.storage import save_result, update_step

logger = logging.getLogger(__name__)


async def run_crawl(job_id: str, url: str, client_name: str) -> None:
    """Main crawl orchestrator. Runs as a background task."""
    start = time.time()
    pages: dict[str, FetchResult] = {}

    try:
        # Step 1: Discover pages
        await update_step(job_id, "discovering", StepStatus.in_progress)
        homepage = await fetch_page(url)
        pages[url] = homepage
        internal_links = discover_links(homepage.html, url)
        await update_step(
            job_id,
            "discovering",
            StepStatus.complete,
            f"found {len(internal_links) + 1} pages",
        )

        # Step 2: Crawl discovered pages (level 0)
        await update_step(job_id, "crawling", StepStatus.in_progress, "0/{} pages".format(len(internal_links)))
        for i, link in enumerate(internal_links):
            try:
                result = await fetch_page(link)
                pages[link] = result
            except Exception as exc:
                logger.warning("Failed to fetch %s: %s", link, exc)
            await update_step(
                job_id,
                "crawling",
                StepStatus.in_progress,
                f"{i + 1}/{len(internal_links)} pages",
            )
            await asyncio.sleep(settings.request_delay)

        # 2-level discovery: find new links from all fetched pages
        all_html_so_far = {u: fr.html for u, fr in pages.items()}
        level1_links = discover_links_recursive(all_html_so_far, url)

        if level1_links:
            total = len(internal_links) + len(level1_links)
            for i, link in enumerate(level1_links):
                try:
                    result = await fetch_page(link)
                    pages[link] = result
                except Exception as exc:
                    logger.warning("Failed to fetch %s: %s", link, exc)
                await update_step(
                    job_id,
                    "crawling",
                    StepStatus.in_progress,
                    f"{len(internal_links) + i + 1}/{total} pages",
                )
                await asyncio.sleep(settings.request_delay)

        await update_step(
            job_id,
            "crawling",
            StepStatus.complete,
            f"{len(pages)} pages fetched",
        )

        # Collect all HTML for extraction
        all_html = {u: fr.html for u, fr in pages.items()}

        # Step 3: Extract text & metadata
        await update_step(job_id, "extracting", StepStatus.in_progress)
        meta = extract_metadata(homepage.html, url)
        company = extract_company_info(all_html)
        tech_stack = extract_tech_stack(all_html)
        business_type = detect_business_type(all_html, tech_stack)

        # Extract product categories (most useful for e-commerce sites,
        # but run always — returns empty list when no categories found)
        categories = extract_categories(all_html)

        products = extract_products(all_html)
        socials = extract_social_links(all_html)
        pricing = extract_pricing(all_html)
        team = extract_team(all_html)
        testimonials = extract_testimonials(all_html)
        brand_voice = analyze_brand_voice(all_html)
        client_logos = extract_client_logos(
            all_html,
            company_name=company.get("name", client_name),
            site_url=url,
        )
        case_studies = extract_case_studies(all_html)
        media_mentions = extract_media_mentions(all_html)
        ctas = extract_ctas(all_html)
        lead_magnets = extract_lead_magnets(all_html)
        industry_info = extract_industry(all_html)
        await update_step(job_id, "extracting", StepStatus.complete)

        # Step 4: Brand colors
        await update_step(job_id, "colors", StepStatus.in_progress)
        screenshot_result = await fetch_page(url, take_screenshot=True)
        colors = extract_brand_colors(
            homepage.html, screenshot_result.screenshot_bytes
        )
        await update_step(job_id, "colors", StepStatus.complete)

        # Step 5: Images
        await update_step(job_id, "images", StepStatus.in_progress)
        img_data = extract_images(all_html, url)
        await update_step(job_id, "images", StepStatus.complete)

        # Step 6: Assemble result
        await update_step(job_id, "complete", StepStatus.in_progress)
        elapsed = round(time.time() - start, 1)

        result = CrawlResult(
            company_name=company.get("name", client_name),
            tagline=meta.get("tagline", ""),
            about=company.get("about", ""),
            brand={
                "dominant_color": colors.get("dominant_color", ""),
                "palette": colors.get("palette", []),
                "fonts": colors.get("fonts", []),
                "logo_url": img_data.get("logo_url", ""),
                "favicon_url": img_data.get("favicon_url", ""),
                "og_image": meta.get("og_image", ""),
            },
            metadata={
                "title": meta.get("title", ""),
                "description": meta.get("description", ""),
                "keywords": meta.get("keywords", []),
                "structured_data": meta.get("structured_data", {}),
            },
            social_links=socials,
            products=products.get("products", []),
            categories=categories,
            features=products.get("features", []),
            images=img_data.get("all_images", []),
            contact=company.get("contact", {}),
            pages_crawled=list(pages.keys()),
            crawl_duration_seconds=elapsed,
            pricing=pricing,
            team=team,
            testimonials=testimonials,
            tech_stack=tech_stack,
            brand_voice=brand_voice,
            business_type=business_type,
            founded_year=company.get("founded_year", ""),
            employee_count=company.get("employee_count", ""),
            headquarters=company.get("headquarters", ""),
            client_logos=client_logos,
            case_studies=case_studies,
            media_mentions=media_mentions,
            ctas=ctas,
            lead_magnets=lead_magnets,
            industry=industry_info,
        )

        await save_result(job_id, result.model_dump())
        await update_step(job_id, "complete", StepStatus.complete)

    except Exception as exc:
        logger.exception("Crawl failed for job %s: %s", job_id, exc)
        await update_step(job_id, "complete", StepStatus.failed, str(exc))
