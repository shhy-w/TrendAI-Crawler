"""add account protection controls

Revision ID: 202611010007
Revises: 202611010006
Create Date: 2026-09-01 00:00:07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202611010007"
down_revision: Union[str, None] = "202611010006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("crawler_sessions", sa.Column("protection_enabled", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("crawler_sessions", sa.Column("daily_request_limit", sa.Integer(), server_default="60", nullable=False))
    op.add_column("crawler_sessions", sa.Column("daily_request_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("crawler_sessions", sa.Column("daily_request_date", sa.Date(), nullable=True))
    op.add_column("crawler_sessions", sa.Column("cooldown_seconds", sa.Integer(), server_default="30", nullable=False))
    op.add_column("crawler_sessions", sa.Column("failure_threshold", sa.Integer(), server_default="2", nullable=False))
    op.add_column("crawler_sessions", sa.Column("lockout_minutes", sa.Integer(), server_default="360", nullable=False))
    op.add_column("crawler_sessions", sa.Column("consecutive_failures", sa.Integer(), server_default="0", nullable=False))
    op.add_column("crawler_sessions", sa.Column("last_request_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("crawler_sessions", sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("crawler_sessions", "blocked_until")
    op.drop_column("crawler_sessions", "last_request_at")
    op.drop_column("crawler_sessions", "consecutive_failures")
    op.drop_column("crawler_sessions", "lockout_minutes")
    op.drop_column("crawler_sessions", "failure_threshold")
    op.drop_column("crawler_sessions", "cooldown_seconds")
    op.drop_column("crawler_sessions", "daily_request_date")
    op.drop_column("crawler_sessions", "daily_request_count")
    op.drop_column("crawler_sessions", "daily_request_limit")
    op.drop_column("crawler_sessions", "protection_enabled")
