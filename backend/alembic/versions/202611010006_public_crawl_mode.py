"""add public crawl mode and note completeness

Revision ID: 202611010006
Revises: 202611010005
Create Date: 2026-09-01 00:00:06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202611010006"
down_revision: Union[str, None] = "202611010005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("crawl_jobs", sa.Column("crawl_mode", sa.String(length=32), server_default="auto", nullable=False))
    op.create_index("ix_crawl_jobs_crawl_mode", "crawl_jobs", ["crawl_mode"])
    op.add_column("notes", sa.Column("completeness", sa.String(length=32), server_default="card", nullable=False))
    op.create_index("ix_notes_completeness", "notes", ["completeness"])


def downgrade() -> None:
    op.drop_index("ix_notes_completeness", table_name="notes")
    op.drop_column("notes", "completeness")
    op.drop_index("ix_crawl_jobs_crawl_mode", table_name="crawl_jobs")
    op.drop_column("crawl_jobs", "crawl_mode")
