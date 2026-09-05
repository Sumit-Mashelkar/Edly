"""Create the initial Peblo TV Mini database schema.

Revision ID: 0001_initial_schema
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('editor', 'admin')", name="ck_users_role"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "shows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("synopsis", sa.Text(), nullable=False),
        sa.Column("section", sa.String(length=20), nullable=False),
        sa.Column("categories", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("section IN ('featured', 'series', 'minisodes', 'songs')", name="ck_shows_section"),
        sa.CheckConstraint("status IN ('draft', 'published')", name="ck_shows_status"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_shows_slug", "shows", ["slug"])
    op.create_index("ix_shows_section", "shows", ["section"])
    op.create_index("ix_shows_status", "shows", ["status"])

    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("show_id", sa.Integer(), sa.ForeignKey("shows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("show_id", "season_number", name="uq_seasons_show_number"),
    )

    op.create_table(
        "episodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_episode_id", sa.String(length=100), nullable=False),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column("episode_title", sa.String(length=255), nullable=False),
        sa.Column("synopsis", sa.Text()),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=5), nullable=False),
        sa.Column("content_group", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("language IN ('en', 'hi')", name="ck_episodes_language"),
        sa.CheckConstraint("status IN ('draft', 'published')", name="ck_episodes_status"),
        sa.UniqueConstraint("source_episode_id"),
        sa.UniqueConstraint("season_id", "episode_number", "language", name="uq_episodes_season_number_language"),
    )
    op.create_index("ix_episodes_content_group", "episodes", ["content_group"])
    op.create_index("ix_episodes_language", "episodes", ["language"])
    op.create_index("ix_episodes_status", "episodes", ["status"])

    op.create_table(
        "artwork",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("artwork_type", sa.String(length=20), nullable=False),
        sa.Column("storage_key", sa.String(length=500)),
        sa.Column("original_filename", sa.String(length=255)),
        sa.Column("mime_type", sa.String(length=100)),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("show_id", sa.Integer(), sa.ForeignKey("shows.id", ondelete="CASCADE")),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("artwork_type IN ('poster', 'banner', 'thumbnail')", name="ck_artwork_type"),
        sa.CheckConstraint("(show_id IS NOT NULL AND episode_id IS NULL) OR (show_id IS NULL AND episode_id IS NOT NULL)", name="ck_artwork_single_owner"),
        sa.UniqueConstraint("show_id", "artwork_type", name="uq_artwork_show_type"),
        sa.UniqueConstraint("episode_id", "artwork_type", name="uq_artwork_episode_type"),
    )

    op.create_table(
        "publish_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("shows_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("episodes_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.CheckConstraint("status IN ('success', 'failed')", name="ck_publish_runs_status"),
    )


def downgrade() -> None:
    op.drop_table("publish_runs")
    op.drop_table("artwork")
    op.drop_index("ix_episodes_status", table_name="episodes")
    op.drop_index("ix_episodes_language", table_name="episodes")
    op.drop_index("ix_episodes_content_group", table_name="episodes")
    op.drop_table("episodes")
    op.drop_table("seasons")
    op.drop_index("ix_shows_status", table_name="shows")
    op.drop_index("ix_shows_section", table_name="shows")
    op.drop_index("ix_shows_slug", table_name="shows")
    op.drop_table("shows")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
