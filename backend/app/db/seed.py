import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import DEV_PASSWORD
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Artwork, Episode, Season, Show, User


VALID_ARTWORK_TYPES = {"poster", "banner", "thumbnail"}
DEVELOPMENT_USERS = (
    ("editor@example.com", "editor"),
    ("admin@example.com", "admin"),
)
DEFAULT_SEED_PATH = Path(__file__).resolve().parents[3] / "seed" / "seed_shows.json"


def load_seed_records(path: Path = DEFAULT_SEED_PATH) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as seed_file:
        records = json.load(seed_file)
    if not isinstance(records, list):
        raise ValueError("Seed data must be a JSON array")
    return records


def _get_or_create_show(session: Session, record: dict[str, Any], status: str) -> Show:
    show = session.scalar(select(Show).where(Show.slug == record["slug"]))
    if show is None:
        show = Show(
            title=record["show_title"],
            slug=record["slug"],
            synopsis=record["synopsis"],
            section=record["section"],
            categories=record["categories"],
            status=status,
        )
        session.add(show)
        session.flush()
    else:
        show.title = record["show_title"]
        show.synopsis = record["synopsis"]
        show.section = record["section"]
        show.categories = record["categories"]
        show.status = status
    return show


def _get_or_create_season(session: Session, show: Show, season_number: int) -> Season:
    season = session.scalar(
        select(Season).where(Season.show_id == show.id, Season.season_number == season_number)
    )
    if season is None:
        season = Season(show_id=show.id, season_number=season_number)
        session.add(season)
        session.flush()
    return season


def _upsert_episode(session: Session, season: Season, record: dict[str, Any]) -> Episode:
    episode = session.scalar(
        select(Episode).where(Episode.source_episode_id == record["episode_id"])
    )
    values = {
        "source_episode_id": record["episode_id"],
        "season_id": season.id,
        "episode_number": record["episode_number"],
        "episode_title": record["episode_title"],
        "synopsis": record.get("synopsis"),
        "duration_seconds": record["duration_seconds"],
        "language": record["language"],
        "content_group": record["content_group"],
        "status": record["status"],
    }
    if episode is None:
        episode = Episode(**values)
        session.add(episode)
        session.flush()
    else:
        for key, value in values.items():
            setattr(episode, key, value)
    return episode


def _upsert_artwork(session: Session, episode: Episode, artwork_type: str) -> None:
    artwork = session.scalar(
        select(Artwork).where(
            Artwork.episode_id == episode.id,
            Artwork.artwork_type == artwork_type,
        )
    )
    if artwork is None:
        session.add(Artwork(episode_id=episode.id, artwork_type=artwork_type))


def seed_users(session: Session, password: str = DEV_PASSWORD) -> None:
    for email, role in DEVELOPMENT_USERS:
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            session.add(User(email=email, password_hash=hash_password(password), role=role))
        else:
            user.role = role


def seed_database(
    session: Session,
    records: Optional[Iterable[dict[str, Any]]] = None,
    seed_path: Path = DEFAULT_SEED_PATH,
) -> dict[str, int]:
    records = list(records) if records is not None else load_seed_records(seed_path)
    status_by_slug: dict[str, str] = {}
    for record in records:
        if record["status"] == "published":
            status_by_slug[record["slug"]] = "published"
        else:
            status_by_slug.setdefault(record["slug"], "draft")

    for record in records:
        show = _get_or_create_show(session, record, status_by_slug[record["slug"]])
        season = _get_or_create_season(session, show, record["season_number"])
        episode = _upsert_episode(session, season, record)
        for artwork_type in record.get("artwork_available", []):
            if artwork_type in VALID_ARTWORK_TYPES:
                _upsert_artwork(session, episode, artwork_type)

    seed_users(session)
    session.commit()
    return {
        "shows": len(status_by_slug),
        "seasons": session.query(Season).count(),
        "episodes": session.query(Episode).count(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Peblo TV Mini seed data")
    parser.add_argument("--seed-path", type=Path, default=DEFAULT_SEED_PATH)
    args = parser.parse_args()
    with SessionLocal() as session:
        counts = seed_database(session, seed_path=args.seed_path)
    print(json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
