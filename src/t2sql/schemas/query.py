from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class QueryRequest(BaseModel):
    question: str
    role: str = "user"  # "user" 또는 "admin"

class QueryResponse(BaseModel):
    sql: str
    rows: List[Dict[str, Any]]
    meta: Dict[str, Any]


class EdgeQuestionItem(BaseModel):
    type_id: int
    type_name: str
    question: str
    rationale: str


class GenerateQuestionsRequest(BaseModel):
    per_type: Optional[int] = None
    total_questions: Optional[int] = None
    seed: Optional[int] = None
    include_schema_context: bool = False


class GenerateQuestionsResponse(BaseModel):
    questions: List[EdgeQuestionItem]
    schema_context: Optional[str] = None
