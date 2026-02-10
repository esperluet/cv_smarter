# CV Optimizer

Containerized CV upload application with separated services:
- `frontend`: React app for CV upload and JSON rendering
- `backend`: FastAPI service for authentication, CV upload, and processing
- `postgres`: persistent relational database
- `adminer`: lightweight visual database UI
- `mailpit`: local SMTP server and mail UI

## Architecture Principles
- `KISS`: straightforward request flow and explicit dependencies
- `SOLID`: API, application, domain, and infrastructure are separated
- Small reusable functions with pragmatic abstractions
- Comments only when needed and always in English
- Document pipeline is engine-agnostic (`ingestor` + `renderer` + `artifact store`)

## Tech Stack
- Node.js `24` (Docker image: `node:24-alpine`)
- React `19.2.0`
- Python `3.13` (Docker image: `python:3.13-slim`)
- FastAPI `0.128.0`
- Docling `2.56.0`
- PostgreSQL `17`
- Adminer `5.3.0`
- Mailpit `1.27`

## Run (Docker only)
```bash
make up
```

## Stop
```bash
make down
```

## Useful Commands
```bash
make build
make ps
make logs
make migrate
make test
make db-shell
```

## Docling Packaging
Docling is packaged directly in `backend/requirements.txt`, so backend images are portable and deployable without runtime `pip install`.

After dependency changes:
```bash
docker compose build backend --no-cache
docker compose up -d backend
```

Quick verification:
```bash
docker compose exec -T backend python -c "import docling; print('docling_ok')"
```

## Service URLs
- Frontend: `http://localhost:3000`
- Backend OpenAPI: `http://localhost:8000/docs`
- Adminer: `http://localhost:8081`
- Mailpit UI: `http://localhost:8025`

## Railway Deployment
- Deployment guide: `docs/deploy-railway.md`
- Recommended topology in one Railway project:
  - Service `backend` (private)
  - Service `frontend` (public)
  - Managed `PostgreSQL`
- Backend health endpoint: `GET /health`
- Railway env templates:
  - `backend/.env.railway.example`
  - `frontend/.env.railway.example`

## Default Local DB Credentials
- Server: `postgres`
- Database: `cv_optimizer`
- User: `cv_optimizer`
- Password: `cv_optimizer`

## API Endpoint
- `POST /api/v1/cv/upload`
- Content-Type: `multipart/form-data`
- Field name: `file`
- Authentication: `Bearer <access_token>`
- Default rendered artifacts: `markdown`, `json`
- Ingestor preference via env: `DOCUMENT_INGESTOR_PREFERRED` (`fallback` or `docling`)
- PDF OCR toggle via env: `DOCUMENT_PDF_DO_OCR` (`false` by default)
- OCR auto-retry on quality failure: `DOCUMENT_OCR_AUTO_RETRY_ON_QUALITY_FAILURE` (`true` by default)
- OCR retry min text length threshold: `DOCUMENT_OCR_RETRY_MIN_TEXT_LENGTH` (`120` by default)
- `POST /api/v1/documents/process` (processing pipeline only, JSON response)
- `POST /api/v1/cv/generate` (multipart: `file` + `job_description` + optional `graph_id`) to run a config-selected LangGraph CV pipeline
- `POST /api/v1/sources` (multipart: `name` + `file`) to register reusable ground-source CV data
- `GET /api/v1/sources` to list reusable ground sources for current user
- `DELETE /api/v1/sources/{source_id}` to remove a ground source entry
- `POST /api/v1/cv/generate-from-source` (multipart: `source_id` + `job_description` + optional `graph_id`) to generate CV from stored source text
- `POST /api/v1/cv/export/pdf` (JSON: `content`, optional `format_hint`, optional `filename`) to convert CV text/markdown to PDF
- `POST /api/v1/cv/generate-from-source/pdf` (multipart: `source_id` + `job_description` + optional `graph_id`) to generate and directly download the final PDF
- Fallback ingestor is text-only (`text/plain`) and binary formats require a semantic ingestor (fail-closed policy)
- Default in `.env.example`: `DOCUMENT_INGESTOR_PREFERRED=docling`
- Providers config: `CV_GENERATION_PROVIDERS_CONFIG_PATH` (default `config/llm/providers.yml`)
- Profiles config: `CV_GENERATION_PROFILES_CONFIG_PATH` (default `config/llm/profiles.yml`)
- Graph index config: `CV_GENERATION_GRAPH_INDEX_CONFIG_PATH` (default `config/graphs/index.yml`)
- Prompt directory: `CV_GENERATION_PROMPTS_DIR` (default `prompts`)
- Trace directory: `CV_GENERATION_TRACE_DIR` (default `traces`)
- Preserve failed uploads for debugging: `PRESERVE_FAILED_UPLOADS` (`false` by default)
- Artifact download hardening: `ARTIFACT_DOWNLOAD_MODE` (`auto` by default), `ARTIFACT_DOWNLOAD_TOKEN_TTL_SECONDS` (`300` by default)
- Optional strict override: `SECURITY_STRICT_MODE` (defaults to strict outside dev-like envs)
- LLM providers are configured through LangChain-compatible kinds: `mock`, `langchain_openai`, `langchain_openai_compatible`, `langchain_anthropic`, `langchain_deepseek`
- Frontend refresh token storage mode: `VITE_REFRESH_TOKEN_STORAGE` (`local` or `session`, default `session`)

## Example JSON Response
```json
{
  "filename": "resume.txt",
  "content_type": "text/plain",
  "size_bytes": 12345,
  "storage_path": "/app/uploads/uuid_resume.txt",
  "metrics": {
    "characters": 1200,
    "words": 220,
    "non_empty_lines": 38,
    "emails_detected": 1
  },
  "artifacts": [
    {
      "format": "markdown",
      "media_type": "text/markdown",
      "storage_path": "/app/artifacts/uuid_resume_md.md"
    },
    {
      "format": "json",
      "media_type": "application/json",
      "storage_path": "/app/artifacts/uuid_resume_json.json"
    }
  ],
  "processing_report": {
    "engine_name": "fallback_text",
    "engine_version": "1",
    "warnings": []
  }
}
```
