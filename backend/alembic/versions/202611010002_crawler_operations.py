"""crawler operations

Revision ID: 202611010002
Revises: 202611010001
Create Date: 2026-11-01 00:00:02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202611010002"
down_revision: Union[str, None] = "202611010001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("crawl_jobs", sa.Column("failure_type", sa.String(length=64), nullable=True))
    op.add_column("crawl_jobs", sa.Column("debug_path", sa.String(length=1024), nullable=True))
    op.create_index("ix_crawl_jobs_failure_type", "crawl_jobs", ["failure_type"])

    op.create_table(
        "proxies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("proxy_url", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_proxies_name"),
    )
    op.create_index("ix_proxies_status", "proxies", ["status"])

    op.create_table(
        "crawl_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cache_key", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cache_key", name="uq_crawl_cache_cache_key"),
    )
    op.create_index("ix_crawl_cache_expires_at", "crawl_cache", ["expires_at"])

    op.create_table(
        "crawl_failures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("keyword", sa.String(length=128), nullable=True),
        sa.Column("failure_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("debug_path", sa.String(length=1024), nullable=True),
        sa.Column("proxy_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["crawl_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["proxy_id"], ["proxies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crawl_failures_failure_type", "crawl_failures", ["failure_type"])


def downgrade() -> None:
    op.drop_index("ix_crawl_failures_failure_type", table_name="crawl_failures")
    op.drop_table("crawl_failures")
    op.drop_index("ix_crawl_cache_expires_at", table_name="crawl_cache")
    op.drop_table("crawl_cache")
    op.drop_index("ix_proxies_status", table_name="proxies")
    op.drop_table("proxies")
    op.drop_index("ix_crawl_jobs_failure_type", table_name="crawl_jobs")
    op.drop_column("crawl_jobs", "debug_path")
    op.drop_column("crawl_jobs", "failure_type")
