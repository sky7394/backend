"""add otp codes

Revision ID: 9a1c2d3e4f5b
Revises: 4c9bdf2e71a8
Create Date: 2026-08-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "9a1c2d3e4f5b"
down_revision: str | Sequence[str] | None = "4c9bdf2e71a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "otp_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("mobile", sa.String(length=20), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_otp_codes_mobile"),
        "otp_codes",
        ["mobile"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_otp_codes_mobile"), table_name="otp_codes")
    op.drop_table("otp_codes")
