import type { CrawlRequest, CrawlResult, CrawlStatus } from "../types";

const BASE = "/api";

export async function startCrawl(
  req: CrawlRequest
): Promise<{ job_id: string }> {
  const res = await fetch(`${BASE}/crawl`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`Failed to start crawl: ${res.statusText}`);
  return res.json();
}

export async function getCrawlStatus(jobId: string): Promise<CrawlStatus> {
  const res = await fetch(`${BASE}/crawl/${jobId}/status`);
  if (!res.ok) throw new Error(`Failed to get status: ${res.statusText}`);
  return res.json();
}

export async function getCrawlResult(
  jobId: string
): Promise<CrawlResult | null> {
  const res = await fetch(`${BASE}/crawl/${jobId}/result`);
  if (res.status === 202) return null; // Still in progress
  if (!res.ok) throw new Error(`Failed to get result: ${res.statusText}`);
  return res.json();
}
