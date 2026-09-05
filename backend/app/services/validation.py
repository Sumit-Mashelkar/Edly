from collections import defaultdict
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Artwork, Episode, Season, Show

VALID_SECTIONS = {"featured", "series", "minisodes", "songs"}
VALID_LANGUAGES = {"en", "hi"}


def _issue(
    *,
    entity: str,
    subject: str,
    message: str,
    action: str,
    show_id: Optional[int] = None,
    season_id: Optional[int] = None,
    episode_id: Optional[int] = None,
    blocker: bool = True,
) -> dict[str, Any]:
    return {
        "entity": entity,
        "subject": subject,
        "message": message,
        "action": action,
        "show_id": show_id,
        "season_id": season_id,
        "episode_id": episode_id,
        "blocker": blocker,
    }


def build_validation_report(db: Session) -> dict[str, Any]:
    shows = db.scalars(select(Show)).all()
    episodes = db.scalars(select(Episode)).all()

    issues: list[dict[str, Any]] = []
    group_map: dict[tuple[str, str], list[Episode]] = defaultdict(list)

    for episode in episodes:
        group_map[(episode.content_group, episode.language)].append(episode)

    for episode in episodes:
        if episode.status == "published":
            if episode.duration_seconds in (None, 0):
                issues.append(
                    _issue(
                        entity="episode",
                        subject=episode.episode_title or episode.content_group,
                        message="Published episode is missing a valid duration.",
                        action="Add duration_seconds for the episode before publishing.",
                        show_id=episode.season.show_id if episode.season else None,
                        season_id=episode.season_id,
                        episode_id=episode.id,
                    )
                )
            if not episode.artwork:
                issues.append(
                    _issue(
                        entity="episode",
                        subject=episode.episode_title or episode.content_group,
                        message="Published episode has no artwork attached.",
                        action="Upload a poster/banner/thumbnail for this episode.",
                        show_id=episode.season.show_id if episode.season else None,
                        season_id=episode.season_id,
                        episode_id=episode.id,
                    )
                )
            if not episode.episode_title or not episode.content_group or not episode.language:
                issues.append(
                    _issue(
                        entity="episode",
                        subject=episode.content_group or str(episode.id),
                        message="Published episode is missing required metadata.",
                        action="Fill in the episode title, language, and content_group.",
                        show_id=episode.season.show_id if episode.season else None,
                        season_id=episode.season_id,
                        episode_id=episode.id,
                    )
                )

        if episode.season and episode.season.season_number == 0:
            if episode.status == "published":
                issues.append(
                    _issue(
                        entity="season",
                        subject=f"{episode.season.show.title}: Season 0",
                        message="Season 0 is reserved for trailers and must not be treated as a normal season in the viewer.",
                        action="Keep season 0 in the CMS only for trailer content and exclude it from normal catalogue browsing.",
                        show_id=episode.season.show_id,
                        season_id=episode.season_id,
                        episode_id=episode.id,
                    )
                )

    for key, grouped in group_map.items():
        if len(grouped) > 1:
            duplicates = grouped
            for duplicate in duplicates:
                issues.append(
                    _issue(
                        entity="episode",
                        subject=duplicate.content_group,
                        message=(
                            f"Duplicate content_group/language pair for {duplicate.content_group} in "
                            f"{duplicate.language}."
                        ),
                        action="Keep only one episode per (content_group, language) combination.",
                        show_id=duplicate.season.show_id if duplicate.season else None,
                        season_id=duplicate.season_id,
                        episode_id=duplicate.id,
                    )
                )

    for show in shows:
        if not show.section or show.section not in VALID_SECTIONS:
            issues.append(
                _issue(
                    entity="show",
                    subject=show.title or show.slug,
                    message="Show is missing a valid section.",
                    action="Set a section from the accepted values: featured, series, minisodes, songs.",
                    show_id=show.id,
                )
            )
        if show.status == "published":
            if not show.section or show.section not in VALID_SECTIONS:
                issues.append(
                    _issue(
                        entity="show",
                        subject=show.title or show.slug,
                        message="Published show must have a valid section before publishing.",
                        action="Add or correct the show section value.",
                        show_id=show.id,
                    )
                )
            if not show.categories:
                issues.append(
                    _issue(
                        entity="show",
                        subject=show.title or show.slug,
                        message="Published show is missing categories.",
                        action="Add categories that match the reference list.",
                        show_id=show.id,
                    )
                )

    return {
        "valid": not any(issue["blocker"] for issue in issues),
        "issues": issues,
        "summary": {
            "total_issues": len(issues),
            "blocking_issues": sum(1 for issue in issues if issue["blocker"]),
        },
    }


def build_catalogue(db: Session) -> dict[str, Any]:
    shows = db.scalars(select(Show).where(Show.status == "published")).all()
    catalogue: list[dict[str, Any]] = []

    for show in shows:
        grouped_episodes: dict[str, list[Episode]] = defaultdict(list)
        for season in show.seasons:
            for episode in season.episodes:
                if episode.status == "published" and season.season_number != 0:
                    grouped_episodes[episode.content_group].append(episode)

        if not grouped_episodes:
            continue

        show_catalog = {
            "id": show.id,
            "title": show.title,
            "slug": show.slug,
            "synopsis": show.synopsis,
            "section": show.section,
            "categories": show.categories,
            "seasons": [],
        }

        seasons_map: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for content_group, variant_episodes in grouped_episodes.items():
            ordered = sorted(variant_episodes, key=lambda item: item.season_id)
            representative = ordered[0]
            season_number = representative.season.season_number if representative.season else 0
            seasons_map[season_number].append(
                {
                    "id": representative.id,
                    "episode_number": representative.episode_number,
                    "episode_title": representative.episode_title,
                    "synopsis": representative.synopsis,
                    "duration_seconds": representative.duration_seconds,
                    "language": representative.language,
                    "available_languages": sorted({item.language for item in ordered if item.language}),
                    "content_group": content_group,
                    "status": representative.status,
                    "artwork": {
                        artwork.artwork_type: artwork.storage_key for artwork in representative.artwork if artwork.storage_key
                    },
                }
            )

        for season_number in sorted(seasons_map):
            show_catalog["seasons"].append(
                {
                    "season_number": season_number,
                    "episodes": sorted(
                        seasons_map[season_number],
                        key=lambda item: (item["episode_number"], item["episode_title"]),
                    ),
                }
            )

        catalogue.append(show_catalog)

    return {"shows": catalogue, "generated_at": ""}
