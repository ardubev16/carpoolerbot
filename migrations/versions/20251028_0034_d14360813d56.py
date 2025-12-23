"""
Rename weekly poll table.

Revision ID: d14360813d56
Revises: e1d9bc73afc5
Create Date: 2025-10-28 00:34:49.894642

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d14360813d56"
down_revision: str | None = "e1d9bc73afc5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("polls", "weekly_polls")


def downgrade() -> None:
    """Downgrade schema."""
    op.rename_table("weekly_polls", "polls")
