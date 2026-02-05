import os
from datetime import date

from openai import OpenAI

from t2sql.services.rag.vector_search import search_schema, search_fewshots

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def llm_generate_sql(question: str) -> str:
    today = date.today()
    base_year = str(today.year)
    base_month = f"{today.month:02d}"

    # 다음 달 계산 (12월 -> 1월 처리)
    next_month = today.month + 1
    next_year = today.year
    if next_month > 12:
        next_month = 1
        next_year += 1
    next_month_str = f"{next_year}-{next_month:02d}-01"

    q = question.strip()
    rows = search_schema(q, k=8)

    schema_context = "\n".join(
        f"- ({doc_type}) {table_name}{('.' + column_name) if column_name else ''}\n {content}"
        for doc_type, table_name, column_name, content, dist in rows
        if table_name != "dim_worker"
    )

    # semantic few-shot: 질문과 유사한 예제 3개 검색
    fewshot_rows = search_fewshots(q, k=3)
    few_shots_parts = []
    for i, (fq, fsql, dist) in enumerate(fewshot_rows, 1):
        sql_with_vars = fsql.replace("{BASE_YEAR}", base_year).replace("{BASE_MONTH}", base_month)
        few_shots_parts.append(f"Example {i}:\nQ: {fq}\n{sql_with_vars}")
    few_shots = "\n\n".join(few_shots_parts)

    prompt = f"""
    너는 Postgres SQL 생성기야.
    규칙:
    - SELECT만 생성
    - 출력은 반드시 SQL 텍스트만. (``` 같은 코드블럭/설명/주석 금지)
    - 금지: 테이블 중 dim_worker를 SELECT 접근 금지
    - 위험한 쿼리(INSERT/UPDATE/DELETE/DROP/ALTER) 금지
    - 아래 스키마 컨텍스트에 있는 것만 작성(추측 금지)
    - 날짜 규칙:
    - 오늘 날짜: {base_year}-{base_month}-{today.day:02d}
    - "올해" = {base_year}년
    - "이번달"/"이번 달" = {base_year}년 {base_month}월
    - "최근"/"최근 현황"/"최근 주문" = 이번 달({base_year}년 {base_month}월)로 해석
    - 기간은 [start, end) 반열림구간 사용 (end는 다음날/다음월 1일)
    - 예: "이번달" → WHERE day >= '{base_year}-{base_month}-01' AND day < '{next_month_str}'
    - WHERE vs HAVING:
        - 집계함수(SUM/AVG/COUNT 등) 조건이면 HAVING
        - 기간/상태/상품 같은 필터는 WHERE
    - SQL은 가능한 단순하게 작성
    - 아래 조건에 해당하면 CTE(WITH) 사용:
    1) 서로 다른 집계 결과를 결합할 때(예 주문 vs 생산)
    2) 집계 결과를 다시 필터링/정렬/비율 계산할 때
    3) 같은 서브쿼리가 2번 이상 반복될 때
    - CTE 이름은 의미가 드러나게 작성 (예 orders_waiting, production_total, by_process).


    참고할 유사 예제:
    {few_shots}

    스키마 컨텍스트:
    {schema_context}

    질문: {q}
    SQL만 출력해
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    return response.choices[0].message.content.strip()
