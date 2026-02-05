# Chatbot (Streamlit + SSE) 계획

## 목표
- Streamlit 기반의 간단한 챗봇 UI
- FastAPI에서 SSE로 LLM 응답 스트리밍
- 결과 메타(SQL/rows/meta)까지 표시

## 구성
1. Backend (FastAPI)
- SSE 엔드포인트: `POST /api/chat/stream`
- 이벤트 종류:
  - `delta`: 토큰 조각
  - `result`: 최종 SQL/rows/meta
  - `done`: 스트림 종료

2. Frontend (Streamlit)
- 채팅 UI + 대화 히스토리 저장
- SSE 이벤트 수신/파싱
- 최종 결과 표시 (SQL/row_count 등)

## SSE 서버 코드 (예시)
아래는 SSE 스트리밍용 FastAPI 라우터 예시 코드입니다. 구현 시 `t2sql/routers/chat.py`에 두면 됩니다.

```python
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from t2sql.db.session import get_db
from t2sql.schemas.query import QueryRequest
from t2sql.services.query.query_service import stream_nl_query

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("/stream")
def chat_stream(req: QueryRequest, db: Session = Depends(get_db)):
    def generate():
        for item in stream_nl_query(db, req.question):
            yield _sse(item["event"], item["data"])
        yield _sse("done", {})

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(generate(), media_type="text/event-stream", headers=headers)
```

## SSE 서비스 코드 (예시)
`stream_nl_query`는 LLM 토큰을 스트리밍하다가 최종 SQL/rows/meta를 내보냅니다.

```python
from sqlalchemy import text
from sqlalchemy.orm import Session
from t2sql.services.llm.llm_client import llm_generate_sql_stream
from t2sql.services.query.sql_validator import validate_and_normalize, SqlRejected

def stream_nl_query(db: Session, question: str):
    raw_parts: list[str] = []
    for delta in llm_generate_sql_stream(question):
        raw_parts.append(delta)
        yield {"event": "delta", "data": {"delta": delta}}

    raw_sql = "".join(raw_parts).strip()
    try:
        sql = validate_and_normalize(raw_sql)
    except SqlRejected as e:
        yield {"event": "result", "data": {"sql": raw_sql, "rows": [], "meta": {"ok": False, "reason": str(e)}}}
        return

    rows = db.execute(text(sql)).mappings().all()
    yield {
        "event": "result",
        "data": {"sql": sql, "rows": rows, "meta": {"ok": True, "row_count": len(rows)}},
    }
```

## Streamlit 클라이언트 (예시)
```python
import json
import streamlit as st
import requests

API_URL = "http://localhost:8000/api/chat/stream"

st.title("Text-to-SQL Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = []

question = st.chat_input("질문을 입력하세요")

if question:
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("assistant"):
        placeholder = st.empty()
        answer = ""
        with requests.post(API_URL, json={"question": question}, stream=True) as r:
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if "delta" in data:
                        answer += data["delta"]
                        placeholder.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
```

## 파일 구조 제안
- `src/t2sql/routers/chat.py` (SSE 라우터)
- `src/t2sql/services/query/query_service.py`에 `stream_nl_query`
- `src/t2sql/services/llm/llm_client.py`에 `llm_generate_sql_stream`
- `streamlit_app.py` (루트 혹은 `apps/` 폴더)

## 비고
- 현재 코드베이스는 SSE/스트리밍을 제거한 상태입니다.
- 필요 시 위 예시를 그대로 옮겨 구현하면 됩니다.
