from app.api.v1.routes.account import router as account_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.cv import router as cv_router
from app.api.v1.routes.cv_generation import router as cv_generation_router
from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.sources import router as sources_router

__all__ = [
    "account_router",
    "auth_router",
    "cv_generation_router",
    "cv_router",
    "documents_router",
    "sources_router",
]
