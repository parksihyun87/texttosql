from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from t2sql.db.base_class import Base
from datetime import date

class FactProductionDaily(Base):
    __tablename__ = "fact_production_daily"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    process: Mapped[str] = mapped_column(String, primary_key=True)
    produced_qty: Mapped[int] = mapped_column(Integer)



