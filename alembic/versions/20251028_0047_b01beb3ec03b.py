"""
Rename users table.

Revision ID: b01beb3ec03b
Revises: d14360813d56
Create Date: 2025-10-28 00:47:03.890537

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b01beb3ec03b"
down_revision: str | None = "d14360813d56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("users", "telegram_users")


def downgrade() -> None:
    """Downgrade schema."""
    op.rename_table("telegram_users", "users")
