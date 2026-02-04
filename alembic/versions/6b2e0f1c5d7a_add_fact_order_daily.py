"""add fact_order_daily

Revision ID: 6b2e0f1c5d7a
Revises: 05cc62626ad2
Create Date: 2026-02-04 15:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b2e0f1c5d7a"
down_revision: Union[str, Sequence[str], None] = "05cc62626ad2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("fact_order_daily"):
        op.create_table(
            "fact_order_daily",
            sa.Column("day", sa.Date(), nullable=False),
            sa.Column("process", sa.String(), nullable=False),
            sa.Column("order_status", sa.String(), nullable=False),
            sa.Column("ordered_qty", sa.Integer(), nullable=False),
            sa.CheckConstraint(
                "ordered_qty >= 0",
                name="ck_fact_order_daily_ordered_qty_nonneg",
            ),
            sa.CheckConstraint(
                "order_status IN ('출고 완료','출고 대기')",
                name="ck_fact_order_daily_order_status",
            ),
            sa.PrimaryKeyConstraint(
                "day",
                "process",
                "order_status",
                name="pk_fact_order_daily",
            ),
        )

    op.execute(
        """
        INSERT INTO fact_order_daily (day, process, ordered_qty, order_status) VALUES
        -- 2026-02-01
        ('2026-02-01','A', 2,'출고 완료'), ('2026-02-01','A', 8,'출고 대기'),
        ('2026-02-01','B', 1,'출고 완료'), ('2026-02-01','B', 7,'출고 대기'),
        ('2026-02-01','C', 3,'출고 완료'), ('2026-02-01','C', 9,'출고 대기'),
        ('2026-02-01','D', 0,'출고 완료'), ('2026-02-01','D', 6,'출고 대기'),
        ('2026-02-01','E', 2,'출고 완료'), ('2026-02-01','E', 8,'출고 대기'),
        ('2026-02-01','F', 1,'출고 완료'), ('2026-02-01','F', 7,'출고 대기'),
        ('2026-02-01','G', 0,'출고 완료'), ('2026-02-01','G', 5,'출고 대기'),
        ('2026-02-01','H', 2,'출고 완료'), ('2026-02-01','H', 8,'출고 대기'),
        ('2026-02-01','I', 1,'출고 완료'), ('2026-02-01','I', 7,'출고 대기'),

        -- 2026-02-02
        ('2026-02-02','A', 1,'출고 완료'), ('2026-02-02','A', 9,'출고 대기'),
        ('2026-02-02','B', 2,'출고 완료'), ('2026-02-02','B', 8,'출고 대기'),
        ('2026-02-02','C', 1,'출고 완료'), ('2026-02-02','C',10,'출고 대기'),
        ('2026-02-02','D', 0,'출고 완료'), ('2026-02-02','D', 7,'출고 대기'),
        ('2026-02-02','E', 2,'출고 완료'), ('2026-02-02','E', 9,'출고 대기'),
        ('2026-02-02','F', 1,'출고 완료'), ('2026-02-02','F', 8,'출고 대기'),
        ('2026-02-02','G', 1,'출고 완료'), ('2026-02-02','G', 6,'출고 대기'),
        ('2026-02-02','H', 0,'출고 완료'), ('2026-02-02','H', 9,'출고 대기'),
        ('2026-02-02','I', 2,'출고 완료'), ('2026-02-02','I', 8,'출고 대기'),

        -- 2026-02-03
        ('2026-02-03','A', 0,'출고 완료'), ('2026-02-03','A',10,'출고 대기'),
        ('2026-02-03','B', 1,'출고 완료'), ('2026-02-03','B', 9,'출고 대기'),
        ('2026-02-03','C', 2,'출고 완료'), ('2026-02-03','C',11,'출고 대기'),
        ('2026-02-03','D', 1,'출고 완료'), ('2026-02-03','D', 8,'출고 대기'),
        ('2026-02-03','E', 0,'출고 완료'), ('2026-02-03','E',10,'출고 대기'),
        ('2026-02-03','F', 2,'출고 완료'), ('2026-02-03','F', 9,'출고 대기'),
        ('2026-02-03','G', 0,'출고 완료'), ('2026-02-03','G', 7,'출고 대기'),
        ('2026-02-03','H', 1,'출고 완료'), ('2026-02-03','H',10,'출고 대기'),
        ('2026-02-03','I', 0,'출고 완료'), ('2026-02-03','I', 9,'출고 대기')
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("fact_order_daily")
