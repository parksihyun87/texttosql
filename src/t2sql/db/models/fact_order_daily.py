from datetime import date

from sqlalchemy import CheckConstraint, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from t2sql.db.base_class import Base


class FactOrderDaily(Base):
    __tablename__ = "fact_order_daily"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    process: Mapped[str] = mapped_column(String, primary_key=True)
    order_status: Mapped[str] = mapped_column(String, primary_key=True)
    ordered_qty: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("ordered_qty >= 0", name="ck_fact_order_daily_ordered_qty_nonneg"),
        CheckConstraint(
            "order_status IN ('출고 완료','출고 대기')",
            name="ck_fact_order_daily_order_status",
        ),
    )
