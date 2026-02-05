from fastapi import APIRouter

from t2sql.schemas.query import GenerateQuestionsRequest, GenerateQuestionsResponse, EdgeQuestionItem
from t2sql.services.llm.llm_edge_question_generator import (
    generate_edge_questions_with_llm,
    build_full_schema_context,
)

router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("/generate", response_model=GenerateQuestionsResponse)
def generate_questions(req: GenerateQuestionsRequest):
    if req.total_questions is not None:
        total_questions = req.total_questions
    elif req.per_type is not None:
        total_questions = req.per_type * 7
    else:
        total_questions = 7

    questions = generate_edge_questions_with_llm(
        total_questions=total_questions,
        seed=req.seed,
        type_ids=req.type_ids,
    )
    items = [
        EdgeQuestionItem(
            type_id=q.type_id,
            type_name=q.type_name,
            question=q.question,
            rationale=q.rationale,
        )
        for q in questions
    ]
    schema_context = None
    if req.include_schema_context:
        schema_context = build_full_schema_context()
    return GenerateQuestionsResponse(questions=items, schema_context=schema_context)
