import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.seed import DEFAULT_SEED_PATH, seed_database
from app.models import Artwork, Episode, PublishRun, Season, Show, User  # noqa: F401


@pytest.fixture(scope="module")
def database_session():
    database_url = os.getenv("TEST_DATABASE_URL", os.getenv("DATABASE_URL"))
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL or DATABASE_URL to a PostgreSQL database")

    engine = create_engine(database_url)
    try:
        with engine.connect():
            pass
    except OperationalError:
        pytest.skip("PostgreSQL is not available")

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        seed_database(session, seed_path=Path(DEFAULT_SEED_PATH))
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()
