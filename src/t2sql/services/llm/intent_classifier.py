"""
사용자 의도 분류기
- greeting: 인사
- data_query: 데이터/테이블 관련 질문
- off_topic: 주제 외 질문
"""
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """당신은 사용자 의도를 분류하는 분류기입니다.
사용자 메시지를 읽고 다음 중 하나로 분류하세요:

1. greeting - 인사, 안부 (예: 안녕, 하이, 반가워, 뭐해)
2. data_query - 데이터, 테이블, 생산, 주문, 수량 등에 대한 질문 (예: 이번 달 생산량은?, 주문 현황 알려줘)
3. off_topic - 위에 해당하지 않는 모든 것 (예: 날씨 어때?, 맛집 추천해줘, 코드 짜줘)

반드시 greeting, data_query, off_topic 중 하나만 출력하세요. 다른 말은 하지 마세요."""


def classify_intent(message: str) -> str:
    """
    사용자 메시지의 의도를 분류
    Returns: "greeting" | "data_query" | "off_topic"
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ],
            max_tokens=20,
            temperature=0
        )
        intent = response.choices[0].message.content.strip().lower()

        # 유효한 의도인지 확인
        if intent in ("greeting", "data_query", "off_topic"):
            return intent
        return "off_topic"
    except Exception:
        return "data_query"  # 실패 시 기본값


# 하드코딩된 응답
RESPONSES = {
    "greeting": "안녕하세요! 저는 생산/주문 데이터에 대한 질문에 답변하는 챗봇입니다. 궁금한 점을 질문해 주세요.",
    "off_topic": "죄송합니다. 저는 생산 및 주문 데이터에 관한 질문만 답변할 수 있습니다. 예: '이번 달 생산량은?', '최근 주문 현황 알려줘'"
}
