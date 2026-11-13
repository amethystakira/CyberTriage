# API / Integration Contract

The current backend exposes the FastAPI application from `backend/app/main.py`.

- Base URL during development: `http://127.0.0.1:8000`
- Health check: `GET /api/health`
- Cases: `GET /api/cases`, `POST /api/cases`, `PATCH /api/cases/{case_id}`
- Dashboard counts: `GET /api/dashboard/counts`
- Evidence: `GET /api/evidence`

Interactive API documentation is available at `/docs`.

When adding detection endpoints, agree request/response schemas with the detection-engine
owner first. Suggested response fields: `summary`, `risk_score`, `severity`, `indicators`,
and `timeline`. Do not silently change existing response keys used by the frontend.
