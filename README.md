# Target Triage

Ranks small-business leads by how good an acquisition target they are, and explains every score. Built as an add-on for SaaSquatch-style lead tools: run it before spending enrichment credits so you only enrich the top of the list.

## Run locally (Python 3.9+)
```bash
cd target-triage
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000, click **Load sample data**, or upload your own CSV.

## CSV columns
`name, city, industry, year_founded, employees, est_revenue, review_count, rating, website, owner_operated, locations`
Only `name` is required. Revenue accepts `$9.2M`, `850k` or plain numbers.

## How scoring works (max 100, see `app/scoring.py`)
Revenue in $5-25M range 25 | Years in business 20 | Owner-operated 20 | Review strength 15 | Single location 10 | Weak web presence 10.
Tier A >= 70, B >= 50, C below. Every score ships with plain-English reasons, shown when you click a row.

## Architecture
- **Backend:** FastAPI (Python), single process
- **Storage:** SQLite (`leads.db`), keyed on normalized name + city, which also deduplicates
- **Frontend:** one static HTML file, vanilla JS, no build step
- **Hosting (production idea):** Render or Fly.io container; swap SQLite for Postgres (Neon/RDS); static file could move to Vercel or S3+CloudFront

## Next steps
Pull leads directly from OpenStreetMap/Google Places, add an LLM-written outreach note per target, calibrate weights against closed-deal data, and push tiers to a CRM.
