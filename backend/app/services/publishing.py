from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PublishRun, Show
from app.services.storage import storage_service
from app.services.validation import build_catalogue, build_validation_report


def publish_catalogue(db: Session, user_id: Optional[int] = None) -> dict[str, Any]:
    validation_report = build_validation_report(db)
    if not validation_report["valid"]:
        run = PublishRun(
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            status="failed",
            error_message="Validation blocked publishing.",
            shows_count=0,
            episodes_count=0,
        )
        db.add(run)
        db.commit()
        return {
            "status": "failed",
            "message": "Publishing was blocked by validation errors.",
            "validation": validation_report,
        }

    catalogue = build_catalogue(db)
    destination = "published/catalogue.json"
    storage_service.atomic_write_json(destination, catalogue)

    published_shows = db.scalars(select(Show).where(Show.status == "published")).all()
    episode_count = sum(
        len([episode for season in show.seasons for episode in season.episodes if episode.status == "published" and season.season_number != 0])
        for show in published_shows
    )

    run = PublishRun(
        user_id=user_id,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        status="success",
        shows_count=len(published_shows),
        episodes_count=episode_count,
        error_message=None,
    )
    db.add(run)
    db.commit()
    return {
        "status": "success",
        "message": "Catalogue published successfully.",
        "destination": destination,
        "shows_count": len(published_shows),
        "episodes_count": episode_count,
    }


def get_current_catalogue() -> dict[str, Any]:
    data = storage_service.read_json("published/catalogue.json", {"shows": []})
    return data if isinstance(data, dict) else {"shows": []}


def search_catalogue(
    query: Optional[str],
    category: Optional[str],
    language: Optional[str],
    section: Optional[str],
) -> list[dict[str, Any]]:
    catalogue = get_current_catalogue()
    items: list[dict[str, Any]] = []
    q = (query or "").strip().lower()
    for show in catalogue.get("shows", []):
        show_matches = True
        if q:
            haystack = " ".join([
                show.get("title", ""),
                show.get("synopsis", ""),
                show.get("section", ""),
                *[category_name for category_name in show.get("categories", [])],
            ]).lower()
            show_matches = q in haystack
        if section and show.get("section") != section:
            show_matches = False
        if category:
            categories = show.get("categories", [])
            if category not in categories:
                show_matches = False
        if not show_matches:
            continue

        show_result = {
            "id": show.get("id"),
            "title": show.get("title"),
            "slug": show.get("slug"),
            "section": show.get("section"),
            "categories": show.get("categories", []),
            "synopsis": show.get("synopsis"),
            "seasons": [],
        }
        for season in show.get("seasons", []):
            season_result = {"season_number": season.get("season_number"), "episodes": []}
            for episode in season.get("episodes", []):
                ep_lang = episode.get("language")
                if language and ep_lang != language:
                    continue
                text = " ".join([
                    episode.get("episode_title", ""),
                    episode.get("synopsis", ""),
                    episode.get("content_group", ""),
                    *episode.get("available_languages", []),
                ]).lower()
                if q and q not in text and q not in (show.get("title", "").lower()):
                    continue
                season_result["episodes"].append(episode)
            if season_result["episodes"]:
                show_result["seasons"].append(season_result)
        if show_result["seasons"]:
            items.append(show_result)
    return items
