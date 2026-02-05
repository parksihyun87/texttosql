import os
from openai import OpenAI
from t2sql.services.rag.vector_search import search_schema, search_fewshots
from datetime import date

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def llm_generate_sql(question: str) -> str:
    today = date.today()
    base_year = str(today.year)
    base_month = f"{today.month:02d}"

    q = question.strip()
    rows = search_schema(q, k=8)

    schema_context = "\n".join(
        f"- ({doc_type}) {table_name}{('.' + column_name) if column_name else ''}\n {content}"
        for doc_type, table_name, column_name, content, dist in rows
        if table_name != "dim_worker"
    )

    # 시맨틱 few-shot: 질문과 유사한 예제 3개 검색
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
    - 출력은 반드시 순수 SQL 텍스트만. (``` 같은 코드블록/설명/주석 절대 금지)
    - 절대 금지: 테이블 중 dim_worker의 SELECT 접근 금지
    - 날짜의 경우 연도나 월을 붙이지 않는 등 윗단위가 생략될시 당해연도나 당월처럼 현시점을 큰 시간단위로 사용
    - 위험한 키워드(INSERT/PDATE/DELETE/DROP/ALTER)는 절대 사용하지 마
    - 아래 스키마 컨텍스트에 근거해서만 작성(추측 금지)
    - 날짜 규칙:
    - 질문에 "월"만 있으면 기준연도는 현재 연도({base_year})로 해석
    - 질문에 "일"만 있고 월/연이 없으면 기준연도({base_year}), 기준월({base_month})로 해석
    - 기간은 [start, end) 반열림 구간으로 작성 (end는 다음날/다음달 1일)
    - WHERE vs HAVING:
        - 집계함수(SUM/AVG/COUNT 등)가 조건에 들어가면 HAVING
        - 기간/상태/제품 같은 행 필터는 WHERE
    - SQL은 가능한 한 단순하게 작성한다.
    - 단, 아래 조건에 해당하면 CTE(WITH)를 사용한다:
    1) 서로 다른 집계 결과를 결합할 때 (예: 주문 vs 생산)
    2) 집계 결과를 다시 필터링/정렬/비율 계산할 때
    3) 같은 서브쿼리가 2번 이상 반복될 때
    - CTE 이름은 의미가 드러나게 작성한다 (예: orders_waiting, production_total, by_process).


    참고할 유사 예제:
    {few_shots}

    스키마 컨텍스트:
    {schema_context}

    질문: {q}
    SQL만 출력해.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    return response.choices[0].message.content.strip()
