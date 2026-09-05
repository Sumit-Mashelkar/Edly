"""Allow duplicate episode variants for validation reporting.

Revision ID: 0003_allow_validation_duplicates
Revises: 0002_allow_missing_show_section
"""
from alembic import op

revision = "0003_allow_validation_duplicates"
down_revision = "0002_allow_missing_show_section"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_episodes_season_number_language", "episodes", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_episodes_season_number_language",
        "episodes",
        ["season_id", "episode_number", "language"],
    )
