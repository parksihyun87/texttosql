from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, List
import json
import asyncio

from t2sql.services.llm.llm_stream_sse import llm_answer_stream, llm_answer_once

router = APIRouter(prefix="/chat", tags =["chat"])

# 데모용 메모리(임시)
_CHAT_MEMORY: Dict[str,List[dict]] = {}

class ChatRequest(BaseModel):
    session_id: str
    message: str
    system: Optional[str] = None

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

def _sse(obj: dict) ->str:
    # SSE 규격: data: ... \n\n
    return f"data:{json.dumps(obj,ensure_ascii=False)}\n\n"

