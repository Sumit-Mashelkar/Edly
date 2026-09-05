from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.auth import require_admin, require_editor
from app.db.dependencies import get_db
from app.models import Show
from app.services.artwork import validate_artwork_upload
from app.services.publishing import publish_catalogue
from app.services.storage import storage_service
from app.services.validation import build_validation_report

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/validation-report")
def validation_report(
    db: Session = Depends(get_db),
    _: Any = Depends(require_editor),
) -> dict[str, Any]:
    return build_validation_report(db)


@router.post("/catalog/publish")
def publish_catalog(
    db: Session = Depends(get_db),
    user: Any = Depends(require_admin),
) -> dict[str, Any]:
    return publish_catalogue(db, user_id=user.id)


@router.post("/artwork/upload")
def upload_artwork(
    file: UploadFile = File(...),
    artwork_type: str = Query(..., description="poster | banner | thumbnail"),
    db: Session = Depends(get_db),
    _: Any = Depends(require_editor),
) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Please select an image file before uploading.")

    content = file.file.read()
    is_valid, message = validate_artwork_upload(content, file.filename, artwork_type)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    destination = f"uploads/{artwork_type}/{file.filename}"
    storage_service.put_bytes(destination, content)

    return {
        "status": "uploaded",
        "artwork_type": artwork_type,
        "filename": file.filename,
        "storage_key": destination,
    }


@router.get("/shows")
def list_shows(
    db: Session = Depends(get_db),
    _: Any = Depends(require_editor),
) -> list[dict[str, Any]]:
    rows = db.query(Show).order_by(Show.title).all()
    return [
        {
            "id": show.id,
            "title": show.title,
            "slug": show.slug,
            "section": show.section,
            "status": show.status,
            "categories": show.categories,
        }
        for show in rows
    ]

