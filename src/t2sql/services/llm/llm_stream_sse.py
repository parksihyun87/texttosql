import os
from typing import Dict, List, Optional, AsyncGenerator

from openai import OpenAI

client = OpenAI(api_key = os.environ.get("OPEN_API_KEY"))

MODEL = "gpt-4o-mini"

def _build_messages(user_msg: str, history: List[dict], system: Optional[str]) -> List[Dict]:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(history)
    msgs.append({"role":"user", "content": user_msg})
    return msgs

def llm_answer_once(user_msg: str, history: List[dict], system: Optional[str] = None) -> str:
    messages = _build_messages(user_msg, history, system)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temparature=0.2,
    )
    return resp.choices[0].message.content or""

async def llm_answer_stream(
    user_msg: str,
    history: List[dict],
    system: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    SSE에 흘릴 delta text를 yield.
    openai SDK stream 동작은 버전에 따라 인터페이스 다를 수 있음
    """
    messages = _build_messages(user_msg, history, system)

    stream = client.chat.completions.create(
        model=MODEL,
        messages= messages,
        temperature=0.2,
        stream=True
    )

    for event in stream:
        #event.choices[0].delta.content 형태(sdk나 모델에 따라 차이)
        delta = getattr(event.choices[0].delta, "content", None)
        if delta:
            yield delta

