"""Allow incomplete show metadata for validation reporting.

Revision ID: 0002_allow_missing_show_section
Revises: 0001_initial_schema
"""
from alembic import op

revision = "0002_allow_missing_show_section"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("shows", "section", nullable=True)


def downgrade() -> None:
    op.alter_column("shows", "section", nullable=False)
