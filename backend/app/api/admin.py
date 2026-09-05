from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.auth import require_admin, require_editor
from app.db.dependencies import get_db
from app.models import Artwork, Episode, PublishRun, Season, Show
from app.services.artwork import validate_artwork_upload
from app.services.publishing import publish_catalogue
from app.services.storage import storage_service
from app.services.validation import build_validation_report

router = APIRouter(prefix="/admin", tags=["admin"])

VALID_SECTIONS = {"featured", "series", "minisodes", "songs"}
VALID_LANGUAGES = {"en", "hi"}
VALID_STATUSES = {"draft", "published"}
VALID_ARTWORK_TYPES = {"poster", "banner", "thumbnail"}

class ShowPayload(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    synopsis: str = ""
    section: str
    categories: list[str] = Field(default_factory=list)
    status: str = "draft"

class SeasonPayload(BaseModel):
    season_number: int = Field(ge=0)
    title: Optional[str] = Field(default=None, max_length=255)

class EpisodePayload(BaseModel):
    source_episode_id: str = Field(min_length=1, max_length=100)
    episode_number: int = Field(ge=1)
    episode_title: str = Field(min_length=1, max_length=255)
    synopsis: Optional[str] = None
    duration_seconds: int = Field(ge=0)
    language: str
    content_group: str = Field(min_length=1, max_length=255)
    status: str = "draft"

def _validate_common(payload: Any) -> None:
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail="Status must be draft or published.")

def _serialize_artwork(artwork: Artwork) -> dict[str, Any]:
    return {
        "id": artwork.id,
        "artwork_type": artwork.artwork_type,
        "storage_key": artwork.storage_key,
        "original_filename": artwork.original_filename,
        "mime_type": artwork.mime_type,
        "width": artwork.width,
        "height": artwork.height,
        "size_bytes": artwork.size_bytes,
    }

def _serialize_episode(episode: Episode) -> dict[str, Any]:
    return {
        "id": episode.id,
        "source_episode_id": episode.source_episode_id,
        "season_id": episode.season_id,
        "episode_number": episode.episode_number,
        "episode_title": episode.episode_title,
        "synopsis": episode.synopsis,
        "duration_seconds": episode.duration_seconds,
        "language": episode.language,
        "content_group": episode.content_group,
        "status": episode.status,
        "artwork": [_serialize_artwork(item) for item in episode.artwork],
    }

def _serialize_season(season: Season) -> dict[str, Any]:
    return {
        "id": season.id,
        "show_id": season.show_id,
        "season_number": season.season_number,
        "title": season.title,
        "episodes": [_serialize_episode(item) for item in season.episodes],
    }

def _serialize_show(show: Show, include_children: bool = True) -> dict[str, Any]:
    result = {
        "id": show.id,
        "title": show.title,
        "slug": show.slug,
        "synopsis": show.synopsis,
        "section": show.section,
        "categories": show.categories,
        "status": show.status,
        "artwork": [_serialize_artwork(item) for item in show.artwork],
    }
    if include_children:
        result["seasons"] = [_serialize_season(item) for item in show.seasons]
    return result

def _get_show(db: Session, show_id: int) -> Show:
    show = db.scalar(
        select(Show)
        .options(
            selectinload(Show.seasons).selectinload(Season.episodes).selectinload(Episode.artwork),
            selectinload(Show.artwork),
        )
        .where(Show.id == show_id)
    )
    if show is None:
        raise HTTPException(status_code=404, detail="Show not found.")
    return show

def _get_season(db: Session, season_id: int) -> Season:
    season = db.scalar(
        select(Season).options(selectinload(Season.episodes).selectinload(Episode.artwork)).where(Season.id == season_id)
    )
    if season is None:
        raise HTTPException(status_code=404, detail="Season not found.")
    return season

def _get_episode(db: Session, episode_id: int) -> Episode:
    episode = db.scalar(select(Episode).options(selectinload(Episode.artwork)).where(Episode.id == episode_id))
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found.")
    return episode

def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        detail = "That value conflicts with existing content. Check the slug, source episode ID, or episode number/language."
        if "section" in str(error.orig):
            detail = "Choose a valid section: featured, series, minisodes, or songs."
        raise HTTPException(status_code=409, detail=detail)

@router.get("/validation-report")
def validation_report(db: Session = Depends(get_db), _: Any = Depends(require_editor)) -> dict[str, Any]:
    return build_validation_report(db)

@router.post("/catalog/publish")
def publish_catalog(db: Session = Depends(get_db), user: Any = Depends(require_admin)) -> dict[str, Any]:
    return publish_catalogue(db, user_id=user.id)

@router.get("/publish-runs")
def publish_runs(
    db: Session = Depends(get_db),
    _: Any = Depends(require_editor),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    total = db.query(PublishRun).count()
    rows = (
        db.query(PublishRun)
        .order_by(PublishRun.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [
            {
                "id": row.id,
                "started_at": row.started_at.isoformat(),
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "status": row.status,
                "shows_count": row.shows_count,
                "episodes_count": row.episodes_count,
                "error_message": row.error_message,
            }
            for row in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }

@router.post("/artwork/upload")
def upload_artwork(
    file: UploadFile = File(...),
    artwork_type: str = Query(...),
    show_id: Optional[int] = Query(default=None),
    episode_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    _: Any = Depends(require_editor),
) -> dict[str, Any]:
    if artwork_type not in VALID_ARTWORK_TYPES:
        raise HTTPException(status_code=422, detail="Artwork type must be poster, banner, or thumbnail.")
    if (show_id is None) == (episode_id is None):
        raise HTTPException(status_code=422, detail="Choose exactly one show or episode for this artwork.")
    if show_id is not None and db.get(Show, show_id) is None:
        raise HTTPException(status_code=404, detail="Show not found.")
    if episode_id is not None and db.get(Episode, episode_id) is None:
        raise HTTPException(status_code=404, detail="Episode not found.")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Please select an image file before uploading.")

    content = file.file.read()
    is_valid, message = validate_artwork_upload(content, file.filename, artwork_type)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    from PIL import Image

    with Image.open(__import__("io").BytesIO(content)) as image:
        width, height = image.size
    suffix = Path(file.filename).suffix.lower()
    storage_key = f"uploads/{'shows' if show_id else 'episodes'}/{show_id or episode_id}/{artwork_type}-{uuid4().hex}{suffix}"
    storage_service.put_bytes(storage_key, content)
    query = select(Artwork).where(Artwork.artwork_type == artwork_type)
    query = query.where(Artwork.show_id == show_id) if show_id is not None else query.where(Artwork.episode_id == episode_id)
    artwork = db.scalar(query)
    if artwork is None:
        artwork = Artwork(artwork_type=artwork_type, show_id=show_id, episode_id=episode_id)
        db.add(artwork)
    artwork.storage_key = storage_key
    artwork.original_filename = file.filename
    artwork.mime_type = file.content_type
    artwork.width = width
    artwork.height = height
    artwork.size_bytes = len(content)
    _commit(db)
    return {"status": "uploaded", "artwork": _serialize_artwork(artwork)}

@router.get("/shows")
def list_shows(
    db: Session = Depends(get_db),
    _: Any = Depends(require_editor),
    q: Optional[str] = Query(default=None),
    section: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    language: Optional[str] = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    query = select(Show).options(selectinload(Show.artwork)).order_by(Show.title)
    if q:
        search = f"%{q.strip()}%"
        query = query.where(or_(Show.title.ilike(search), Show.slug.ilike(search), Show.synopsis.ilike(search)))
    if section:
        query = query.where(Show.section == section)
    if status:
        query = query.where(Show.status == status)
    if language:
        query = query.join(Show.seasons).join(Season.episodes).where(Episode.language == language).distinct()
    rows = db.scalars(query).all()
    total = len(rows)
    start = (page - 1) * page_size
    return {"items": [_serialize_show(row, False) for row in rows[start : start + page_size]], "page": page, "page_size": page_size, "total": total}

@router.get("/shows/{show_id}")
def show_detail(show_id: int, db: Session = Depends(get_db), _: Any = Depends(require_editor)) -> dict[str, Any]:
    return _serialize_show(_get_show(db, show_id))

@router.post("/shows")
def create_show(payload: ShowPayload, db: Session = Depends(get_db), _: Any = Depends(require_editor)) -> dict[str, Any]:
    if payload.section not in VALID_SECTIONS:
        raise HTTPException(status_code=422, detail="Choose a valid section: featured, series, minisodes, or songs.")
    _validate_common(payload)
    show = Show(**payload.model_dump())
    db.add(show)
    _commit(db)
    return _serialize_show(_get_show(db, show.id))

@router.patch("/shows/{show_id}")
def update_show(show_id: int, payload: ShowPayload, db: Session = Depends(get_db), _: Any = Depends(require_editor)) -> dict[str, Any]:
    if payload.section not in VALID_SECTIONS:
        raise HTTPException(status_code=422, detail="Choose a valid section: featured, series, minisodes, or songs.")
    _validate_common(payload)
    show = _get_show(db, show_id)
    for key, value in payload.model_dump().items():
        setattr(show, key, value)
    _commit(db)
    return _serialize_show(_get_show(db, show_id))

@router.delete("/shows/{show_id}")
def delete_show(show_id: int, db: Session = Depends(get_db), _: Any = Depends(require_editor)) -> dict[str, str]:
    show = _get_show(db, show_id)
    db.delete(show)
    _commit(db)
    return {"message": "Show deleted."}

@router.post("/shows/{show_id}/seasons")
def create_season(show_id: int, payload: SeasonPayload, db: Session = Depends(get_db), _: Any = Depends(require_editor)) -> dict[str, Any]:
    _get_show(db, show_id)
    season = Season(show_id=show_id, **payload.model_dump())
    db.add(season)
    _commit(db)
    return _serialize_season(_get_season(db, season.id))

@router.patch("/seasons/{season_id}")
def update_season(season_id: int, payload: SeasonPayload, db: Session = Depends(get_db), _: Any = Depends(require_editor)) -> dict[str, Any]:
    season = _get_season(db, season_id)
    for key, value in payload.model_dump().items():
        setattr(season, key, value)
    _commit(db)
    return _serialize_season(_get_season(db, season_id))

@router.delete("/seasons/{season_id}")
def delete_season(season_id: int, db: Session = Depends(get_db), _: Any = Depends(require_editor)) -> dict[str, str]:
    season = _get_season(db, season_id)
    db.delete(season)
    _commit(db)
    return {"message": "Season deleted."}

@router.post("/seasons/{season_id}/episodes")
def create_episode(season_id: int, payload: EpisodePayload, db: Session = Depends(get_db), _: Any = Depends(require_editor)) -> dict[str, Any]:
    _get_season(db, season_id)
    if payload.language not in VALID_LANGUAGES:
        raise HTTPException(status_code=422, detail="Language must be en or hi.")
    _validate_common(payload)
    episode = Episode(season_id=season_id, **payload.model_dump())
    db.add(episode)
    _commit(db)
    return _serialize_episode(_get_episode(db, episode.id))

@router.patch("/episodes/{episode_id}")
def update_episode(episode_id: int, payload: EpisodePayload, db: Session = Depends(get_db), _: Any = Depends(require_editor)) -> dict[str, Any]:
    episode = _get_episode(db, episode_id)
    if payload.language not in VALID_LANGUAGES:
        raise HTTPException(status_code=422, detail="Language must be en or hi.")
    _validate_common(payload)
    for key, value in payload.model_dump().items():
        setattr(episode, key, value)
    _commit(db)
    return _serialize_episode(_get_episode(db, episode_id))

@router.delete("/episodes/{episode_id}")
def delete_episode(episode_id: int, db: Session = Depends(get_db), _: Any = Depends(require_editor)) -> dict[str, str]:
    episode = _get_episode(db, episode_id)
    db.delete(episode)
    _commit(db)
    return {"message": "Episode deleted."}

