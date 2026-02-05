from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, List
import json
import asyncio
from sqlalchemy.orm import Session

from t2sql.services.llm.llm_stream_sse import llm_answer_stream, llm_answer_once
from t2sql.services.llm.intent_classifier import classify_intent, RESPONSES
from t2sql.services.query.query_service import run_nl_query
from t2sql.db.session import get_db

router = APIRouter(prefix="/chat", tags=["chat"])

# 데모용 메모리(임시)
_CHAT_MEMORY: Dict[str, List[dict]] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str
    system: Optional[str] = None
    role: str = "user"  # user 또는 admin

@router.post("")
def chat_once(req: ChatRequest):
    history = _CHAT_MEMORY.get(req.session_id, [])
    answer = llm_answer_once(req.message, history=history, system=req.system)

    # 메모리 새롭게
    history = history + [
        {"role": "user", "content":req.message},
        {"role": "assistant", "content":answer},
    ]
    _CHAT_MEMORY[req.session_id] = history

    return {"session_id": req.session_id, "answer": answer}

@router.post("/stream")
def chat_stream(req: ChatRequest):
    history = _CHAT_MEMORY.get(req.session_id, [])

    async def event_gen():
        # (선택) 시작 이벤트
        yield _sse({"event": "start","session_id": req.session_id})

        acc = []
        try:
            async for chunk in llm_answer_stream(req.message, history=history, system = req.system):
                acc.append(chunk)
                yield _sse({"event":"delta", "text": chunk})

                # 너무 빡빡하면 살짝 양보(서버 과부하 방지용)
                await asyncio.sleep(0)

            final_text = "".join(acc)

            # 메모리 업데이트(스트림 끝나고 한번에 저장)
            new_history = history + [
                {"role": "user", "content": req.message},
                {"role": "assistant", "content": final_text},
            ]
            _CHAT_MEMORY[req.session_id] = new_history

            yield _sse({"event": "done"})
        except Exception as e:
            yield _sse({"event": "error", "message": str(e)})

    return StreamingResponse(event_gen(), media_type="text/event-stream")

def _sse(obj: dict) -> str:
    # SSE 규격: data: ... \n\n
    return f"data:{json.dumps(obj,ensure_ascii=False)}\n\n"


# ============ 통합 챗봇 엔드포인트 ============

@router.post("/unified")
def unified_chat(req: ChatRequest, db: Session = Depends(get_db)):
    """
    통합 챗봇: 의도 분류 후 적절한 응답
    - greeting: 인사 응답
    - data_query: SQL 생성 + 실행
    - off_topic: 주제 외 안내
    """
    intent = classify_intent(req.message)
    history = _CHAT_MEMORY.get(req.session_id, [])

    if intent == "greeting":
        answer = RESPONSES["greeting"]
    elif intent == "off_topic":
        answer = RESPONSES["off_topic"]
    else:  # data_query
        result = run_nl_query(db, req.message, role=req.role)
        meta = result.get("meta", {})
        sql = result.get("sql", "")
        rows = result.get("rows", [])

        return {
            "session_id": req.session_id,
            "intent": intent,
            "answer": None,
            "sql": sql,
            "rows": [dict(r) for r in rows],
            "meta": {**meta, "row_count": len(rows)}
        }

    # greeting/off_topic은 메모리에 저장
    new_history = history + [
        {"role": "user", "content": req.message},
        {"role": "assistant", "content": answer},
    ]
    _CHAT_MEMORY[req.session_id] = new_history

    return {
        "session_id": req.session_id,
        "intent": intent,
        "answer": answer,
        "sql": None,
        "rows": [],
        "meta": {}
    }

