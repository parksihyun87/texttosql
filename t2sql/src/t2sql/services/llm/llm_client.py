from openai import OpenAI

client = OpenAI()

def llm_generate_sql(question: str)-> str:
    q = question.strip()

    prompt = f"""
    너는 Postgres SQL 생성기야.
    규칙:
    - SELECT만 생성
    - 테이블: fact_production_daily(day, process, produced_qty)만 사용
    - 위험한 키워드(INSERT/UPDATE/DELETE/DROP/ALTER)는 절대 사용하지 마
    질문: {q}
    SQL만 출력해.
    """

        response = client.responses.create(
            model = "gpt-5-2",
            input = prompt,
        )

        return response.output_text.strip()