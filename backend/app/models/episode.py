from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.artwork import Artwork
    from app.models.season import Season


class Episode(TimestampMixin, Base):
    __tablename__ = "episodes"
    __table_args__ = (
        UniqueConstraint(
            "season_id", "episode_number", "language", name="uq_episodes_season_number_language"
        ),
        CheckConstraint("language IN ('en', 'hi')", name="ck_episodes_language"),
        CheckConstraint("status IN ('draft', 'published')", name="ck_episodes_status"),
        Index("ix_episodes_content_group", "content_group"),
        Index("ix_episodes_language", "language"),
        Index("ix_episodes_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_episode_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    episode_title: Mapped[str] = mapped_column(String(255), nullable=False)
    synopsis: Mapped[Optional[str]] = mapped_column(String)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str] = mapped_column(String(5), nullable=False)
    content_group: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    season: Mapped["Season"] = relationship(back_populates="episodes")
    artwork: Mapped[list["Artwork"]] = relationship(
        back_populates="episode", cascade="all, delete-orphan"
    )
