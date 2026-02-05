from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from t2sql.db.session import get_db
from t2sql.schemas.query import QueryRequest, QueryResponse
from t2sql.services.query.query_service import run_nl_query
from sqlalchemy import text, inspect

router = APIRouter(prefix="/query", tags=["query"])

# 허용된 테이블 목록
ALLOWED_TABLES = {
    "fact_production_daily",
    "fact_order_daily",
    "dim_process",
    "dim_worker",
}


@router.post("", response_model=QueryResponse)
def query(req: QueryRequest, db: Session = Depends(get_db)):
    result = run_nl_query(db, req.question, role=req.role)
    result["meta"]["row_count"] = len(result.get("rows", []))
    return result


@router.get("/tables")
def list_tables():
    """허용된 테이블 목록 반환"""
    return {"tables": list(ALLOWED_TABLES)}


@router.get("/table/{table_name}/schema")
def get_table_schema(table_name: str, db: Session = Depends(get_db)):
    """테이블 스키마(컬럼 정보) 반환"""
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    inspector = inspect(db.bind)
    columns = inspector.get_columns(table_name)
    return {
        "table_name": table_name,
        "columns": [{"name": col["name"], "type": str(col["type"])} for col in columns]
    }


@router.get("/table/{table_name}/data")
def get_table_data(table_name: str, limit: int = 100, db: Session = Depends(get_db)):
    """테이블 데이터 반환 (최대 limit개)"""
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    result = db.execute(text(f"SELECT * FROM {table_name} LIMIT :limit"), {"limit": limit})
    columns = result.keys()
    rows = [dict(zip(columns, row)) for row in result.fetchall()]

    return {
        "table_name": table_name,
        "columns": list(columns),
        "rows": rows,
        "row_count": len(rows)
    }