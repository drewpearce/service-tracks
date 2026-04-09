"""church playlist settings

Revision ID: 002_church_playlist_settings
Revises: d3fa24a0a7ea
Create Date: 2026-04-07 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_church_playlist_settings"
down_revision: Union[str, Sequence[str], None] = "d3fa24a0a7ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add playlist settings columns to church table."""
    op.add_column("church", sa.Column("playlist_mode", sa.String(20), nullable=False, server_default="shared"))
    op.add_column(
        "church",
        sa.Column("playlist_name_template", sa.Text(), nullable=False, server_default=r"{church_name} Worship"),
    )  # noqa: E501
    op.add_column(
        "church",
        sa.Column("playlist_description_template", sa.Text(), nullable=False, server_default=r"Worship set for {date}"),
    )  # noqa: E501


def downgrade() -> None:
    """Remove playlist settings columns from church table."""
    op.drop_column("church", "playlist_description_template")
    op.drop_column("church", "playlist_name_template")
    op.drop_column("church", "playlist_mode")
