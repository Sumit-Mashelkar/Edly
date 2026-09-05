import mimetypes
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import admin_router, auth_router, catalog_router
from app.db.dependencies import get_db
from app.services.storage import storage_service

app = FastAPI(title="Peblo TV Mini API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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


@app.get("/media/{storage_key:path}")
def media(storage_key: str) -> Response:
    if ".." in storage_key.split("/"):
        raise HTTPException(status_code=400, detail="Invalid media path.")
    content = storage_service.read_bytes(storage_key)
    if content is None:
        raise HTTPException(status_code=404, detail="Media file not found.")
    media_type = mimetypes.guess_type(storage_key)[0] or "application/octet-stream"
    return Response(content=content, media_type=media_type)
