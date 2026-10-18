"""add widget_key and allowed_domains to tenants

Revision ID: 5a6b7c8d9e0f
Revises: 4f9a1b2c3d4e
Create Date: 2026-10-18 23:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "5a6b7c8d9e0f"
down_revision: Union[str, None] = "4f9a1b2c3d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add widget_key initially as nullable for safe existing data migration
    op.add_column(
        "tenants",
        sa.Column("widget_key", sa.String(length=64), nullable=True),
    )
    # 2. Add allowed_domains as JSONB array with default '[]'
    op.add_column(
        "tenants",
        sa.Column(
            "allowed_domains",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    # 3. Backfill any existing tenants with a unique wk_live_ key
    op.execute(
        "UPDATE tenants SET widget_key = 'wk_live_' || replace(gen_random_uuid()::text, '-', '') WHERE widget_key IS NULL"
    )
    # 4. Enforce NOT NULL and unique index on widget_key
    op.alter_column("tenants", "widget_key", nullable=False)
    op.create_index(op.f("ix_tenants_widget_key"), "tenants", ["widget_key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_tenants_widget_key"), table_name="tenants")
    op.drop_column("tenants", "allowed_domains")
    op.drop_column("tenants", "widget_key")
