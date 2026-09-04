"""add media archive metadata

Revision ID: 202611010008
Revises: 202611010007
Create Date: 2026-09-02 00:00:08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202611010008"
down_revision: Union[str, None] = "202611010007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("media", sa.Column("quality", sa.String(length=32), server_default="preview", nullable=False))
    op.add_column("media", sa.Column("archive_status", sa.String(length=32), server_default="remote", nullable=False))
    op.add_column("media", sa.Column("local_path", sa.String(length=1024), nullable=True))
    op.add_column("media", sa.Column("mime_type", sa.String(length=128), nullable=True))
    op.add_column("media", sa.Column("file_size", sa.BigInteger(), nullable=True))
    op.add_column("media", sa.Column("checksum_sha256", sa.String(length=64), nullable=True))
    op.add_column("media", sa.Column("duration_seconds", sa.Float(), nullable=True))
    op.add_column("media", sa.Column("archive_error", sa.String(length=1024), nullable=True))
    op.add_column("media", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_media_quality", "media", ["quality"])
    op.create_index("ix_media_archive_status", "media", ["archive_status"])


def downgrade() -> None:
    op.drop_index("ix_media_archive_status", table_name="media")
    op.drop_index("ix_media_quality", table_name="media")
    op.drop_column("media", "archived_at")
    op.drop_column("media", "archive_error")
    op.drop_column("media", "duration_seconds")
    op.drop_column("media", "checksum_sha256")
    op.drop_column("media", "file_size")
    op.drop_column("media", "mime_type")
    op.drop_column("media", "local_path")
    op.drop_column("media", "archive_status")
    op.drop_column("media", "quality")
