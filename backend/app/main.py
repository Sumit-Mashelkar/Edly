from typing import Any

from fastapi import FastAPI
from sqlalchemy import text

from app.api import admin_router, auth_router, catalog_router
from app.db.dependencies import get_db

app = FastAPI(title="Peblo TV Mini API")
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(catalog_router)


@app.get("/health")
def health() -> dict[str, Any]:
    database_status = "unknown"
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:
        database_status = "unavailable"
    return {
        "status": "ok",
        "database": database_status,
        "catalogue": "available",
    }
