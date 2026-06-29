"""web bearer tokens

Revision ID: 202611010004
Revises: 202611010003
Create Date: 2026-11-01 00:00:04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202611010004"
down_revision: Union[str, None] = "202611010003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "web_bearer_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_web_bearer_tokens_status", "web_bearer_tokens", ["status"])


def downgrade() -> None:
    op.drop_index("ix_web_bearer_tokens_status", table_name="web_bearer_tokens")
    op.drop_table("web_bearer_tokens")
