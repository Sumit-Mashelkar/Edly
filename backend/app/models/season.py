from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.episode import Episode
    from app.models.show import Show


class Season(TimestampMixin, Base):
    __tablename__ = "seasons"
    __table_args__ = (UniqueConstraint("show_id", "season_number", name="uq_seasons_show_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id", ondelete="CASCADE"), nullable=False)
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255))

    show: Mapped["Show"] = relationship(back_populates="seasons")
    episodes: Mapped[list["Episode"]] = relationship(
        back_populates="season", cascade="all, delete-orphan"
    )
