from __future__ import annotations

from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings
from app.models import CrawlJob, StepInfo, StepStatus

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def get_db() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(settings.mongodb_uri)
        _db = _client[settings.mongodb_database]
    return _db


async def close_db() -> None:
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None


async def create_job(job: CrawlJob) -> str:
    db = await get_db()
    await db.crawl_jobs.insert_one(job.model_dump())
    return job.job_id


async def get_job(job_id: str) -> dict | None:
    db = await get_db()
    return await db.crawl_jobs.find_one({"job_id": job_id}, {"_id": 0})


async def update_step(
    job_id: str,
    step_name: str,
    status: StepStatus,
    detail: str = "",
) -> None:
    db = await get_db()
    now = datetime.now(timezone.utc)
    update: dict = {
        f"steps.{step_name}.status": status.value,
        f"steps.{step_name}.detail": detail,
    }
    if status == StepStatus.in_progress:
        update[f"steps.{step_name}.started_at"] = now
        update["status"] = step_name
    elif status in (StepStatus.complete, StepStatus.failed):
        update[f"steps.{step_name}.finished_at"] = now

    await db.crawl_jobs.update_one({"job_id": job_id}, {"$set": update})


async def save_result(job_id: str, result: dict) -> None:
    db = await get_db()
    await db.crawl_jobs.update_one(
        {"job_id": job_id},
        {"$set": {"result": result, "status": "complete"}},
    )
