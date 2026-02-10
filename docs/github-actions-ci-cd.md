# GitHub Actions CI/CD Setup

This project now includes CI/CD workflows under `.github/workflows/`.

## Workflows

- `ci.yml`
  - `backend-tests`: backend test suite (`pytest -q`) using `backend/requirements-ci.txt`
  - `frontend-build`: deterministic frontend build with `npm ci && npm run build`
  - `docker-build`: builds backend/frontend Docker images only when Docker-relevant files change
- `dependency-review.yml`
  - Reviews dependency diffs on pull requests and fails on high severity alerts
- `codeql.yml`
  - Static analysis for Python + JavaScript/TypeScript on PRs, `main`, and weekly schedule
- `deploy-railway.yml`
  - Deploys backend + frontend to Railway after successful `CI` on `main`
  - Supports manual trigger via `workflow_dispatch`

## Branch Protection (Required)

Configure branch protection (or rulesets) for `main` with:

- Require pull request before merge
- Require at least one approval
- Require branches to be up to date before merging
- Require merge queue
- Require status checks:
  - `backend-tests`
  - `frontend-build`
  - `docker-build`
  - `dependency-review`

`CodeQL` checks are recommended, but can be non-blocking if you want faster merge velocity at first.

## Railway CD Secrets

Add the following repository secrets:

- `RAILWAY_TOKEN`
- `RAILWAY_PROJECT_ID`
- `RAILWAY_ENVIRONMENT_NAME` (example: `production`)
- `RAILWAY_BACKEND_SERVICE_ID`
- `RAILWAY_FRONTEND_SERVICE_ID`

If one of these is missing, deployment is skipped and the workflow reports `deploy-not-configured`.

## Railway Service Settings

To avoid duplicate deployments:

- Disable Railway GitHub Auto Deploy for backend/frontend services
- Let `deploy-railway.yml` own production deployments from `main`

## Local/CI Dependency Parity

- Frontend uses `package-lock.json` and `npm ci` (local CI and Docker image build)
- Backend CI uses `backend/requirements-ci.txt` to avoid heavyweight optional runtime dependencies that are not needed for automated tests
