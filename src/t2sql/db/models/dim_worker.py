from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from t2sql.db.base_class import Base

class DimWorker(Base):
    __tablename__ = "dim_worker"

    worker_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    process: Mapped[str] = mapped_column(String, nullable=False)  # FK 없음
    worker_name: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("process", "worker_name", name="uq_dim_worker_process_name"),
    )
