"""create availabilities table

Revision ID: ab4e6e8d7b90
Revises: 6c7323aa2bb7
Create Date: 2026-07-26 21:37:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab4e6e8d7b90'
down_revision: str | None = '6c7323aa2bb7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'availabilities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Time(timezone=False), nullable=False),
        sa.Column('end_time', sa.Time(timezone=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('day_of_week >= 0 AND day_of_week <= 6', name='ck_availability_day_of_week'),
        sa.CheckConstraint('start_time < end_time', name='ck_availability_time_range'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_availabilities_day_of_week', 'availabilities', ['day_of_week'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_availabilities_day_of_week', table_name='availabilities')
    op.drop_table('availabilities')
