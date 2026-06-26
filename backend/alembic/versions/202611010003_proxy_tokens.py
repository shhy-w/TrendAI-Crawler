"""proxy tokens

Revision ID: 202611010003
Revises: 202611010002
Create Date: 2026-11-01 00:00:03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202611010003"
down_revision: Union[str, None] = "202611010002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "guest_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("proxy_id", sa.Integer(), nullable=True),
        sa.Column("guest_token", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["proxy_id"], ["proxies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guest_tokens_proxy_id", "guest_tokens", ["proxy_id"])
    op.create_index("ix_guest_tokens_status", "guest_tokens", ["status"])

    op.create_table(
        "query_id_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("operation_name", sa.String(length=128), nullable=False),
        sa.Column("query_id", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("operation_name", name="uq_query_id_cache_operation_name"),
    )


def downgrade() -> None:
    op.drop_table("query_id_cache")
    op.drop_index("ix_guest_tokens_status", table_name="guest_tokens")
    op.drop_index("ix_guest_tokens_proxy_id", table_name="guest_tokens")
    op.drop_table("guest_tokens")
