# Railway Deployment Guide

This project is a monorepo with two deployable services:
- `backend` (FastAPI, private service)
- `frontend` (Nginx + React static assets, public service)

It also needs one managed PostgreSQL service.

## 1. Create the Railway project

1. Create a new project from your GitHub repo.
2. Add three services:
   - `backend` (source root: `backend`)
   - `frontend` (source root: `frontend`)
   - `PostgreSQL` (managed Railway database)

## 2. Backend service setup

Use the `backend/Dockerfile` in this repo.

- Container command already runs migrations then starts the API:
  - `alembic upgrade head && uvicorn ... --port ${PORT:-8000}`
- Railway settings to avoid import/startup issues:
  - Service source root must be `backend`
  - Keep Railway "Start Command" empty (so Dockerfile `CMD` is used)
  - If you must override Start Command, use:
    - `cd /app && PYTHONPATH=/app alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`
- Healthcheck path:
  - `/health`

Set backend environment variables using `backend/.env.railway.example` as template.

Minimum required:
- `APP_ENV=production`
- `DATABASE_URL=postgresql+psycopg://...` (from Railway Postgres variables)
- `JWT_SECRET_KEY=<strong secret>`
- `SECURITY_STRICT_MODE=true`
- `ARTIFACT_DOWNLOAD_MODE=signed`
- `UPLOAD_DIR=/data/uploads`
- `ARTIFACT_DIR=/data/artifacts`
- `CV_GENERATION_TRACE_DIR=/data/traces`

## 3. Add a persistent volume to backend

Attach one Railway volume to backend mounted at `/data`.

This persists:
- uploads
- artifacts
- traces

## 4. Frontend service setup

Use the `frontend/Dockerfile` in this repo.

The Nginx config is a template and reads:
- `BACKEND_HOST` (runtime env)
- `BACKEND_PORT` (runtime env)
- `PORT` (Railway runtime port, injected automatically)

Set:
- `BACKEND_HOST=${{backend.RAILWAY_PRIVATE_DOMAIN}}`
- `BACKEND_PORT=${{backend.PORT}}`
  - Replace `backend` with your exact backend service name in Railway.
  - This keeps frontend->backend internal routing aligned with the backend's actual host/port.

Healthcheck path:
- `/`

Expose/generate a public domain only for frontend.

## 5. Service visibility

- `backend`: keep private (no public domain required).
- `frontend`: public domain enabled.

`/api/*` requests from frontend are proxied internally to backend.

## 6. Verify after deployment

1. Open frontend domain.
2. Sign up and sign in.
3. Upload a ground source.
4. Generate CV/PDF.
5. Download document artifacts.

## 7. Common issues

- 502 on `/api/*`:
  - Check `BACKEND_HOST` and `BACKEND_PORT` in frontend service.
  - Ensure the service reference name in these vars matches your backend service name.
  - Ensure backend is healthy and listening on its Railway `PORT`.
- Migration/startup failures:
  - Verify `DATABASE_URL` is set.
  - Accepted forms: `postgresql+psycopg://...`, `postgresql://...`, `postgres://...` (the app normalizes to `psycopg`).
- Lost files after redeploy:
  - Confirm backend volume is mounted at `/data`.
