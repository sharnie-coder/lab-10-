"""add department to user

Revision ID: 75bb87588f9d
Revises: f80e3b6f9d3a
Create Date: 2026-08-11 11:05:10.385495

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "75bb87588f9d"
down_revision: Union[str, Sequence[str], None] = "f80e3b6f9d3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user",
        sa.Column("department", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user", "department")