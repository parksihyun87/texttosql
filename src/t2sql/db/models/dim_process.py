from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from t2sql.db.base_class import Base

class DimProcess(Base):
    __tablename__ = "dim_process"

    process: Mapped[str] = mapped_column(String, primary_key=True)
    product: Mapped[str] = mapped_column(String, nullable=False)  