import os
from openai import OpenAI
from t2sql.services.rag.vector_search import search_schema

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def llm_generate_sql(question: str) -> str:
    q = question.strip()
    rows = search_schema(q, k=8)

    schema_context = "\n".join(
        f"- ({doc_type}) {table_name}{('.' + column_name) if column_name else ''}\n {content}"
        for doc_type, table_name, column_name, content, dist in rows
        if table_name != "dim_worker"
    )

    prompt = f"""
    너는 Postgres SQL 생성기야.
    규칙:
    - SELECT만 생성
    - 출력은 반드시 순수 SQL 텍스트만. (``` 같은 코드블록/설명/주석 절대 금지)
    - 절대 금지: 테이블 중 dim_worker의 SELECT 접근 금지
    - 날짜의 경우 연도나 월을 붙이지 않는 등 윗단위가 생략될시 당해연도나 당월처럼 현시점을 큰 시간단위로 사용
    - 위험한 키워드(INSERT/PDATE/DELETE/DROP/ALTER)는 절대 사용하지 마
    - 아래 스키마 컨텍스트에 근거해서만 작성(추측 금지)
    
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