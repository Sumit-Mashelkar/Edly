from sqlalchemy import func, select

from app.db.base import Base
from app.models import Episode, Season, Show


def test_database_schema_is_initialized(database_session):
    assert {"users", "shows", "seasons", "episodes", "artwork", "publish_runs"} <= set(
        Base.metadata.tables
    )


def test_seed_creates_expected_show_count(database_session):
    assert database_session.scalar(select(func.count()).select_from(Show)) == 8


def test_seed_preserves_language_variants_as_rows(database_session):
    rows = database_session.scalars(
        select(Episode).where(Episode.content_group == "motis-many-lives-s01e01")
    ).all()
    assert len(rows) == 2
    assert {episode.language for episode in rows} == {"en", "hi"}


def test_seed_preserves_content_group(database_session):
    episode = database_session.scalar(
        select(Episode).where(Episode.source_episode_id == "ep_0001")
    )
    assert episode is not None
    assert episode.content_group == "motis-many-lives-s01e01"


def test_seed_preserves_season_zero(database_session):
    season_zero = database_session.scalar(select(Season).where(Season.season_number == 0))
    assert season_zero is not None
    assert database_session.scalar(
        select(func.count()).select_from(Episode).where(Episode.season_id == season_zero.id)
    ) == 2


def test_seed_is_idempotent(database_session):
    before = {
        "shows": database_session.scalar(select(func.count()).select_from(Show)),
        "episodes": database_session.scalar(select(func.count()).select_from(Episode)),
    }
    from app.db.seed import seed_database

    seed_database(database_session)
    after = {
        "shows": database_session.scalar(select(func.count()).select_from(Show)),
        "episodes": database_session.scalar(select(func.count()).select_from(Episode)),
    }
    assert after == before == {"shows": 8, "episodes": 95}
