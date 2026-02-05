from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from t2sql.db.session import get_db
from t2sql.schemas.query import QueryRequest, QueryResponse
from t2sql.services.query.query_service import run_nl_query
from sqlalchemy import text

router = APIRouter(prefix="/query", tags=["query"])

@router.post("", response_model=QueryResponse)
def query(req: QueryRequest, db: Session = Depends(get_db)):
    result = run_nl_query(db, req.question, role=req.role)
    result["meta"]["row_count"] = len(result.get("rows", []))
    return result