from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.artwork import Artwork
    from app.models.season import Season


class Show(TimestampMixin, Base):
    __tablename__ = "shows"
    __table_args__ = (
        CheckConstraint(
            "section IN ('featured', 'series', 'minisodes', 'songs')",
            name="ck_shows_section",
        ),
        CheckConstraint("status IN ('draft', 'published')", name="ck_shows_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    synopsis: Mapped[str] = mapped_column(String, nullable=False)
    section: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    categories: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False)

    seasons: Mapped[list["Season"]] = relationship(
        back_populates="show", cascade="all, delete-orphan"
    )
    artwork: Mapped[list["Artwork"]] = relationship(
        back_populates="show", cascade="all, delete-orphan"
    )
