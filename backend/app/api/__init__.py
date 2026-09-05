from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.catalog import router as catalog_router

__all__ = ["auth_router", "admin_router", "catalog_router"]
