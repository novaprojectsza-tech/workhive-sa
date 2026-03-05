# WorkHive SA — Full Stack

Python/FastAPI backend + HTML frontend for South Africa's job aggregator.

## Quick Start

```bash
cd workhive-sa

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000

API docs at http://localhost:8000/docs

## Project Structure

```
workhive-sa/
├── app/
│   ├── main.py                    # FastAPI app entry point
│   ├── models/
│   │   ├── models.py              # SQLAlchemy models (Job, JobAlert, FetchLog)
│   │   ├── database.py            # DB engine + sessions
│   │   └── schemas.py             # Pydantic response schemas
│   ├── routers/
│   │   ├── auth.py                # Register, login, logout + application tracker
│   │   ├── jobs.py                # Job listing, search, categories, stats
│   │   ├── sources.py             # Fetch logs + source health
│   │   └── alerts.py             # Job alert subscriptions
│   └── services/
│       ├── base.py                # Base scraper class + deduplication
│       ├── fetcher_adzuna.py      # Adzuna API (SA jobs, pre-configured)
│       ├── fetcher_reed.py        # Reed API (optional, set REED_API_KEY)
│       ├── fetcher_rss.py         # Free RSS feeds (Careers24, Jobmail...)
│       └── scheduler.py           # Orchestrator + job expiry
├── static/
│   └── index.html                 # Full frontend
├── .env                           # API keys
└── requirements.txt
```

## API Endpoints

| Method | Endpoint                        | Description                  |
|--------|---------------------------------|------------------------------|
| GET    | /api/v1/jobs                    | List/search jobs             |
| GET    | /api/v1/jobs/{id}               | Job detail                   |
| GET    | /api/v1/jobs/categories         | Category counts              |
| GET    | /api/v1/jobs/stats              | Total/remote/tech counts     |
| POST   | /api/v1/jobs/refresh            | Trigger manual scrape        |
| POST   | /api/v1/auth/register           | Register user                |
| POST   | /api/v1/auth/login              | Login                        |
| POST   | /api/v1/auth/logout             | Logout                       |
| GET    | /api/v1/auth/me                 | Current user                 |
| GET    | /api/v1/applications            | My tracked applications      |
| POST   | /api/v1/applications            | Add application to tracker   |
| PATCH  | /api/v1/applications/{id}       | Update status/notes          |
| DELETE | /api/v1/applications/{id}       | Remove application           |
| GET    | /api/v1/sources/health          | Last scrape per source       |
| POST   | /api/v1/alerts                  | Subscribe to job alerts      |

## Deploy Free on Render

1. Push this folder to GitHub
2. render.com → New Web Service → connect repo
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add env vars from .env in Render's dashboard

## AdSense

In `static/index.html`, replace `ca-pub-XXXXXXXXXXXXXXXX` with your publisher ID
and uncomment the `<ins>` tags.

## Add yourself as admin

After registering, update the DB:
```sql
UPDATE users SET role='admin' WHERE email='your@email.com';
```
