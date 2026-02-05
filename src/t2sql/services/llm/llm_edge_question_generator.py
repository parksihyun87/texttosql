from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Iterable, List, Optional

from openai import OpenAI

from t2sql.services.rag.vector_search import fetch_all_schema

client = OpenAI()


@dataclass(frozen=True)
class EdgeQuestion:
    type_id: int
    type_name: str
    question: str
    rationale: str


_TYPE_NAMES = {
    1: "date_range",
    2: "simple_count",
    3: "having_agg",
    4: "disallowed_table",
    5: "join_product",
    6: "cte_ratio",
    7: "creative_schema",
}


def build_full_schema_context() -> str:
    rows = fetch_all_schema()
    return "\n".join(
        f"- ({doc_type}) {table_name}{('.' + column_name) if column_name else ''}\n {content}"
        for doc_type, table_name, column_name, content, dist in rows
    )


def _parse_questions_json(raw: str) -> List[dict]:
    raw = raw.strip()
    if not raw:
        raise ValueError("Empty LLM response")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise
        data = json.loads(raw[start : end + 1])

    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of questions")
    return data


def generate_edge_questions_with_llm(
    total_questions: int = 7,
    seed: Optional[int] = None,
    base_date: Optional[date] = None,
) -> List[EdgeQuestion]:
    base_date = base_date or date.today()
    base_year = base_date.year
    base_month = base_date.month

    schema_context = build_full_schema_context()

    prompt = f"""
너는 Text-to-SQL 평가를 위한 "엣지 질문" 생성기다.

[스키마 컨텍스트]
{schema_context}

[유형 정의]
1) date_range: 날짜 범위/월 경계/하루만 입력 시 날짜 해석 질문
2) simple_count: COUNT/DISTINCT 같은 단순 집계 질문
3) having_agg: GROUP BY + HAVING 필요 질문
4) disallowed_table: 금지 테이블(dim_worker)을 요구하는 질문 (의도적으로 위반)
5) join_product: dim_process(또는 관련 테이블) 조인이 필요한 질문 (product 조건 포함)
6) cte_ratio: 주문 vs 생산 같은 서로 다른 집계 결과 결합/비율 계산 질문 (CTE 필요)
7) creative_schema: 스키마 컨텍스트에 있는 테이블/컬럼만 사용해 창의적이고 복합적인 질문

[기준 날짜]
- 기준년도: {base_year}
- 기준월: {base_month:02d}
- 질문에 "올해/이번달"만 있으면 위 기준으로 해석

[요구사항]
- 총 {total_questions}개 생성
- 7개 유형이 최대한 골고루 포함되도록 구성
- 서로 다른 표현/조건/기간/숫자 변형
- 스키마 컨텍스트에 없는 테이블/컬럼/값은 사용하지 말 것
- 출력은 JSON 배열만. 각 원소 형식:
  {{
    "type_id": 1~7,
    "question": "...",
    "rationale": "왜 이 유형에 해당하는지 한 줄 설명"
  }}
- seed 값이 있으면 참고: {seed}

JSON만 출력해.
""".strip()

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    data = _parse_questions_json(resp.choices[0].message.content)
    results: List[EdgeQuestion] = []
    for item in data:
        type_id = int(item["type_id"])
        type_name = _TYPE_NAMES.get(type_id, "unknown")
        results.append(
            EdgeQuestion(
                type_id=type_id,
                type_name=type_name,
                question=item["question"].strip(),
                rationale=item["rationale"].strip(),
            )
        )
    return results


def edge_questions_as_text(questions: Iterable[EdgeQuestion]) -> str:
    lines = []
    for q in questions:
        lines.append(f"[{q.type_id}:{q.type_name}] {q.question}  # {q.rationale}")
    return "\n".join(lines)
