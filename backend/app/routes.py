from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from app.crawler.engine import run_crawl
from app.models import CrawlJob, CrawlRequest
from app.storage import create_job, get_job

router = APIRouter(prefix="/api")


@router.post("/crawl")
async def start_crawl(req: CrawlRequest):
    job = CrawlJob(
        url=str(req.url),
        client_name=req.client_name,
        industry=req.industry,
    )
    await create_job(job)
    asyncio.create_task(run_crawl(job.job_id, str(req.url), req.client_name))
    return {"job_id": job.job_id}


@router.get("/crawl/{job_id}/status")
async def crawl_status(job_id: str):
    doc = await get_job(job_id)
    if not doc:
        raise HTTPException(404, "Job not found")
    return {
        "job_id": doc["job_id"],
        "status": doc["status"],
        "steps": doc["steps"],
    }


@router.get("/crawl/{job_id}/result")
async def crawl_result(job_id: str):
    doc = await get_job(job_id)
    if not doc:
        raise HTTPException(404, "Job not found")
    if doc["status"] != "complete":
        raise HTTPException(202, "Crawl still in progress")
    return doc["result"]
