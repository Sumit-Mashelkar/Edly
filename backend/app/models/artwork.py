from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.episode import Episode
    from app.models.show import Show


class Artwork(TimestampMixin, Base):
    __tablename__ = "artwork"
    __table_args__ = (
        CheckConstraint(
            "artwork_type IN ('poster', 'banner', 'thumbnail')",
            name="ck_artwork_type",
        ),
        CheckConstraint(
            "(show_id IS NOT NULL AND episode_id IS NULL) OR "
            "(show_id IS NULL AND episode_id IS NOT NULL)",
            name="ck_artwork_single_owner",
        ),
        UniqueConstraint("show_id", "artwork_type", name="uq_artwork_show_type"),
        UniqueConstraint("episode_id", "artwork_type", name="uq_artwork_episode_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    artwork_type: Mapped[str] = mapped_column(String(20), nullable=False)
    storage_key: Mapped[Optional[str]] = mapped_column(String(500))
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    show_id: Mapped[Optional[int]] = mapped_column(ForeignKey("shows.id", ondelete="CASCADE"))
    episode_id: Mapped[Optional[int]] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"))

    show: Mapped[Optional["Show"]] = relationship(back_populates="artwork")
    episode: Mapped[Optional["Episode"]] = relationship(back_populates="artwork")
