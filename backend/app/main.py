from fastapi import FastAPI

from app.api.v1.routes.account import router as account_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.cv import router as cv_router
from app.api.v1.routes.cv_generation import router as cv_generation_router
from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.sources import router as sources_router


def create_app() -> FastAPI:
    app = FastAPI(title="CV Optimizer API", version="1.0.0")
    app.include_router(cv_router, prefix="/api/v1")
    app.include_router(cv_generation_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(sources_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(account_router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
