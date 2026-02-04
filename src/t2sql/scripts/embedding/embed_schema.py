from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트의 .env 로드
env_path = Path(__file__).resolve().parents[4] / ".env"
load_dotenv(env_path)

import os
from datetime import datetime
from openai import OpenAI
import psycopg

EMBED_MODEL =  "text-embedding-3-small"
DB_URL = os.environ["DATABASE_URL"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY)

def embed_test(text: str) -> list[float]:
    res = client.embeddings.create(
        model = EMBED_MODEL,
        input = text,
    )
    return res.data[0].embedding

DOCS = [
    {
    "doc_type": "table",
    "table_name": "fact_production_daily",
    "column_name": None,
    "content": """[TABLE] fact_production_daily
    설명: 일자/공정별 생산 실적(단위: 개)
    컬럼:
    - day DATE: 생산 집계 날짜
    - process TEXT: 공정 코드 'A'~'I'
    - produced_qty INT: 생산 수량(0 이상)
    힌트: 생산 총합=SUM(produced_qty), 공정별=GROUP BY process""",
    },
    {
    "doc_type": "table",
    "table_name": "fact_order_daily",
    "column_name": None,
    "content": """[TABLE] fact_order_daily
    설명: 일자/공정/출고상태별 주문 수량(단위: 개)
    컬럼:
    - day DATE
    - process TEXT: 'A'~'I'
    - ordered_qty INT (0 이상)
    - order_status TEXT enum: '출고 대기'|'출고 완료'
    값 정의:
    - '출고 대기'=미출고 수요(backlog)=앞으로 채워야 할 물량
    - '출고 완료'=이행 완료(fulfilled)=이미 처리된 물량
    계산:
    pending_qty = SUM(ordered_qty) WHERE order_status='출고 대기'
    need_more_qty = GREATEST(pending_qty - produced_qty, 0)""",
    },
    {
    "doc_type": "table",
    "table_name": "dim_process",
    "column_name": None,
    "content": """[TABLE] dim_process
    설명: 공정-제품 매핑 테이블 (공정 A~I가 어떤 제품을 생산하는지)
    컬럼:
    - process TEXT (PK): 공정 코드 'A'~'I'
    - product TEXT: 제품명 ('물건1', '물건2', '물건3')
    힌트: A,B,C는 물건1 / D,E,F는 물건2 / G,H,I는 물건3 생산""",
    },
    {
    "doc_type": "table",
    "table_name": "dim_worker",
    "column_name": None,
    "content": """[TABLE] dim_worker
    설명: 공정별 작업자 목록(사전 테이블)
    컬럼:
    - worker_id SERIAL (PK): 작업자 ID
    - process TEXT: 공정 코드 'A'~'I'
    - worker_name TEXT: 작업자 이름
    제약:
    - UNIQUE(process, worker_name)
    힌트:
    - 공정별 작업자 수: SELECT process, COUNT(*) FROM dim_worker GROUP BY process
    - 전체 작업자 수: SELECT COUNT(*) FROM dim_worker""",
    },
]

def main():
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            for d in DOCS:
                emb = embed_test(d["content"])
                cur.execute(
                    """
                    INSERT INTO schema_embeddings
                    (doc_type, table_name, column_name, content, embedding, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        d["doc_type"],
                        d["table_name"],
                        d["column_name"],
                        d["content"],
                        emb,
                        datetime.utcnow(),
                    ),
                )
            conn.commit()
if __name__ == "__main__":
    main()
