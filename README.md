# Crawler Experiment

Standalone experiment: provide a company URL, and the crawler extracts all company details — features, products, images, brand colors, social links, and more.

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB running locally (or set `MONGODB_URI` in `.env`)
- Playwright browsers installed

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
playwright install chromium

# Copy env and configure
cp .env.example .env

# Run
uvicorn app.main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5174 in your browser.

## Usage

1. Enter a client name, website URL, and optionally an industry
2. Click "Continue" to start the crawl
3. Watch the 6-step progress tracker update in real-time
4. View the extracted results: brand colors, logo, metadata, products, social links, contact info

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/crawl` | Start a crawl job (returns `job_id`) |
| `GET` | `/api/crawl/{job_id}/status` | Poll crawl progress |
| `GET` | `/api/crawl/{job_id}/result` | Get final extracted data |

## Crawl Pipeline

1. **Discover** — Fetch homepage, find internal links (/about, /products, etc.)
2. **Crawl** — Fetch all discovered pages (httpx first, Playwright fallback for JS-heavy sites)
3. **Extract** — Parse metadata, company info, products, social links
4. **Colors** — Screenshot homepage, extract dominant + palette via ColorThief + CSS parsing
5. **Images** — Extract logo, favicon, hero images, product images
6. **Complete** — Assemble and store final result in MongoDB

## Architecture

- **Backend**: FastAPI + Motor (async MongoDB) + Playwright + httpx
- **Frontend**: React 19 + TypeScript + Vite + TailwindCSS
- **Database**: MongoDB (`crawler_experiment` database, `crawl_jobs` collection)
- **Fetcher strategy**: httpx first (fast), Playwright fallback if body text < 500 chars
- **Rate limiting**: 1s delay between requests to same domain
- **Max pages**: 15 per domain
