"""per-platform streaming settings

Revision ID: 003_streaming_settings
Revises: 002_church_playlist_settings
Create Date: 2026-05-12 00:00:00.000000

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "003_streaming_settings"
down_revision: Union[str, Sequence[str], None] = "002_church_playlist_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "streaming_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("church_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("playlist_mode", sa.String(length=20), nullable=False, server_default="shared"),
        sa.Column(
            "playlist_name_template",
            sa.Text(),
            nullable=False,
            server_default="{church_name} Worship",
        ),
        sa.Column(
            "playlist_description_template",
            sa.Text(),
            nullable=False,
            server_default="Worship set for {date}",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["church_id"], ["church.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("church_id", "platform", name="uq_streaming_settings_church_platform"),
    )
    op.create_index(
        op.f("ix_streaming_settings_church_id"),
        "streaming_settings",
        ["church_id"],
        unique=False,
    )

    # Backfill: one streaming_settings row per existing streaming_connection,
    # copying the platform-agnostic template values from church.
    bind = op.get_bind()
    existing = bind.execute(
        sa.text(
            """
            SELECT sc.church_id, sc.platform,
                   c.playlist_mode, c.playlist_name_template, c.playlist_description_template
            FROM streaming_connection sc
            JOIN church c ON c.id = sc.church_id
            """
        )
    ).fetchall()
    if existing:
        bind.execute(
            sa.text(
                """
                INSERT INTO streaming_settings (
                    id, church_id, platform,
                    playlist_mode, playlist_name_template, playlist_description_template
                ) VALUES (
                    :id, :church_id, :platform,
                    :playlist_mode, :playlist_name_template, :playlist_description_template
                )
                """
            ),
            [
                {
                    "id": uuid.uuid4(),
                    "church_id": row.church_id,
                    "platform": row.platform,
                    "playlist_mode": row.playlist_mode,
                    "playlist_name_template": row.playlist_name_template,
                    "playlist_description_template": row.playlist_description_template,
                }
                for row in existing
            ],
        )

    op.drop_column("church", "playlist_description_template")
    op.drop_column("church", "playlist_name_template")
    op.drop_column("church", "playlist_mode")


def downgrade() -> None:
    op.add_column(
        "church",
        sa.Column("playlist_mode", sa.String(20), nullable=False, server_default="shared"),
    )
    op.add_column(
        "church",
        sa.Column(
            "playlist_name_template",
            sa.Text(),
            nullable=False,
            server_default="{church_name} Worship",
        ),
    )
    op.add_column(
        "church",
        sa.Column(
            "playlist_description_template",
            sa.Text(),
            nullable=False,
            server_default="Worship set for {date}",
        ),
    )
    op.drop_index(op.f("ix_streaming_settings_church_id"), table_name="streaming_settings")
    op.drop_table("streaming_settings")
