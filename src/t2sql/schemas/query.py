from pydantic import BaseModel
from typing import Any, Dict, List

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    sql: str
    rows: List[Dict[str, Any]]
    meta: Dict[str, Any]