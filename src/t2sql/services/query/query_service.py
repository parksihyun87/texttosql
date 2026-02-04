from sqlalchemy.orm import Session
from sqlalchemy import text
from t2sql.services.llm.llm_client import llm_generate_sql
from t2sql.services.query.sql_validator import validate_and_normalize, SqlRejected

def run_nl_query(db:Session, question: str) -> dict:
    raw_sql = llm_generate_sql(question)
    try:
        sql = validate_and_normalize(raw_sql)
    except SqlRejected as e:
        return {"sql":raw_sql, "rows": [], "meta": {"ok": False, "reason": str(e)}}
    rows = db.execute(text(sql)).mappings().all()
    return {"sql":sql, "rows": rows, "meta": {"ok": True}}
    