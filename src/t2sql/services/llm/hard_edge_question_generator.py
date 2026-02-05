from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, List, Optional
import random

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
}


def generate_edge_questions(
    per_type: int = 2,
    seed: Optional[int] = None,
    base_date: Optional[date] = None,
) -> List[EdgeQuestion]:
    """Generate hard edge questions based on the 6 evaluation types."""
    rng = random.Random(seed)
    base_date = base_date or date.today()
    base_year = base_date.year
    base_month = base_date.month
    next_month = base_month + 1
    next_month_year = base_year
    if next_month == 13:
        next_month = 1
        next_month_year += 1

    templates = {
        1: [
            (
                "fact_production_daily에서 {y}-{m:02d}-01부터 {y}-{m:02d}-03 전까지(2일) 생산량 합계를 알려줘",
                "기간 범위 [start, end) 사용과 일자 계산",
            ),
            (
                "{y}년 {m}월 첫째 주(1~7일) 생산량 합계는?",
                "날짜 범위/월 경계 해석",
            ),
        ],
        2: [
            (
                "fact_production_daily 테이블에 존재하는 공정 종류 수는?",
                "DISTINCT COUNT 사용",
            ),
            (
                "생산 테이블에 공정이 몇 개나 등록돼 있어?",
                "컬럼/테이블명 해석",
            ),
        ],
        3: [
            (
                "{y}년 {m}월에 총 생산량이 4 이상인 공정 목록은?",
                "GROUP BY + HAVING 조건",
            ),
            (
                "2월 전체 생산량 합이 10을 넘는 공정만 보여줘",
                "HAVING + 기간 필터",
            ),
        ],
        4: [
            (
                "dim_worker 테이블에서 작업자 이름을 모두 보여줘",
                "금지 테이블 접근 차단",
            ),
            (
                "작업자별 이름 목록이 필요해. dim_worker로 바로 조회해줘",
                "보안 차단 확인",
            ),
        ],
        5: [
            (
                "product가 '물건1'인 공정들의 총 생산량을 알려줘",
                "JOIN dim_process + fact_production_daily",
            ),
            (
                "dim_process와 생산 테이블을 조인해서 물건2 총 생산량 계산",
                "JOIN + 필터 + 집계",
            ),
        ],
        6: [
            (
                "{y}년 {m}월 기준 출고 대기 주문 합계를 요구량으로 보고, 같은 달 생산량 합과 비교한 달성률은?",
                "두 집계 결과 결합 + CTE",
            ),
            (
                "출고 대기 주문 합계 대비 2월 생산 달성률(%)을 계산해줘",
                "CTE + 비율 계산",
            ),
        ],
    }

    results: List[EdgeQuestion] = []
    for type_id, items in templates.items():
        picks = rng.sample(items, k=min(per_type, len(items)))
        for template, rationale in picks:
            question = template.format(
                y=base_year,
                m=base_month,
                y2=next_month_year,
                m2=next_month,
            )
            results.append(
                EdgeQuestion(
                    type_id=type_id,
                    type_name=_TYPE_NAMES[type_id],
                    question=question,
                    rationale=rationale,
                )
            )
    return results


def edge_questions_as_text(questions: Iterable[EdgeQuestion]) -> str:
    lines = []
    for q in questions:
        lines.append(f"[{q.type_id}:{q.type_name}] {q.question}  # {q.rationale}")
    return "\n".join(lines)
