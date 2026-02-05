from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[4] / ".env"
load_dotenv(env_path)

import os
from openai import OpenAI
import psycopg

EMBED_MODEL = "text-embedding-3-small"
DB_URL = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def embed_text(text: str) -> list[float]:
    res = client.embeddings.create(model=EMBED_MODEL, input=text)
    return res.data[0].embedding

# Few-shot 예제들 (질문만 임베딩, SQL은 그대로 저장)
FEWSHOTS = [
    {
        "question": "fact_production_daily에서 3월 5일~7일 생산량 합계는?",
        "sql": """SELECT SUM(produced_qty) AS total_produced
FROM fact_production_daily
WHERE day >= DATE '{BASE_YEAR}-03-05'
  AND day < DATE '{BASE_YEAR}-03-08';"""
    },
    {
        "question": "1월 전체 생산량 합계는?",
        "sql": """SELECT SUM(produced_qty) AS total_produced
FROM fact_production_daily
WHERE day >= DATE '{BASE_YEAR}-01-01'
  AND day < DATE '{BASE_YEAR}-02-01';"""
    },
    {
        "question": "15일 생산량 합계는?",
        "sql": """SELECT SUM(produced_qty) AS total_produced
FROM fact_production_daily
WHERE day = DATE '{BASE_YEAR}-{BASE_MONTH}-15';"""
    },
    {
        "question": "3월에 공정 C 생산량 총합은?",
        "sql": """SELECT SUM(produced_qty) AS total_produced
FROM fact_production_daily
WHERE process = 'C'
  AND day >= DATE '{BASE_YEAR}-03-01'
  AND day < DATE '{BASE_YEAR}-04-01';"""
    },
    {
        "question": "3월에 공정별 생산합계가 10 이상인 공정은?",
        "sql": """SELECT process, SUM(produced_qty) AS total_produced
FROM fact_production_daily
WHERE day >= DATE '{BASE_YEAR}-03-01'
  AND day < DATE '{BASE_YEAR}-04-01'
GROUP BY process
HAVING SUM(produced_qty) >= 10
ORDER BY total_produced DESC;"""
    },
    {
        "question": "일별 공정 기록에서 공정 종류는 몇 개인가?",
        "sql": """SELECT COUNT(DISTINCT process) AS process_count
FROM fact_production_daily;"""
    },
    {
        "question": "fact_production_daily와 dim_process로 product '물건2'의 생산량 총합을 구해줘",
        "sql": """SELECT dp.product, SUM(fp.produced_qty) AS total_produced
FROM fact_production_daily AS fp
JOIN dim_process AS dp ON fp.process = dp.process
WHERE dp.product = '물건2'
GROUP BY dp.product;"""
    },
    {
        "question": "1월에 '출고 대기' 주문량 합계는?",
        "sql": """SELECT SUM(ordered_qty) AS total_ordered_waiting
FROM fact_order_daily
WHERE order_status = '출고 대기'
  AND day >= DATE '{BASE_YEAR}-01-01'
  AND day < DATE '{BASE_YEAR}-02-01';"""
    },
    {
        "question": "1월 '출고 대기' 주문량 대비 1월 생산량 달성률(%)은?",
        "sql": """WITH o AS (
  SELECT SUM(ordered_qty) AS ordered_waiting
  FROM fact_order_daily
  WHERE order_status = '출고 대기'
    AND day >= DATE '{BASE_YEAR}-01-01'
    AND day < DATE '{BASE_YEAR}-02-01'
),
p AS (
  SELECT SUM(produced_qty) AS produced_total
  FROM fact_production_daily
  WHERE day >= DATE '{BASE_YEAR}-01-01'
    AND day < DATE '{BASE_YEAR}-02-01'
)
SELECT
  o.ordered_waiting,
  p.produced_total,
  CASE
    WHEN o.ordered_waiting = 0 THEN 0
    ELSE ROUND((p.produced_total * 100.0) / o.ordered_waiting, 2)
  END AS achievement_pct
FROM o, p;"""
    },
    {
        "question": "1월 공정별로 '출고 대기' 주문량 대비 생산량 달성률(%)을 보여줘",
        "sql": """WITH o AS (
  SELECT process, SUM(ordered_qty) AS ordered_waiting
  FROM fact_order_daily
  WHERE order_status = '출고 대기'
    AND day >= DATE '{BASE_YEAR}-01-01'
    AND day < DATE '{BASE_YEAR}-02-01'
  GROUP BY process
),
p AS (
  SELECT process, SUM(produced_qty) AS produced_total
  FROM fact_production_daily
  WHERE day >= DATE '{BASE_YEAR}-01-01'
    AND day < DATE '{BASE_YEAR}-02-01'
  GROUP BY process
)
SELECT
  o.process,
  o.ordered_waiting,
  COALESCE(p.produced_total, 0) AS produced_total,
  CASE
    WHEN o.ordered_waiting = 0 THEN 0
    ELSE ROUND((COALESCE(p.produced_total, 0) * 100.0) / o.ordered_waiting, 2)
  END AS achievement_pct
FROM o
LEFT JOIN p ON p.process = o.process
ORDER BY achievement_pct DESC;"""
    },
]

def main():
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            # 기존 데이터 삭제
            cur.execute("TRUNCATE fewshot_embeddings;")

            for fs in FEWSHOTS:
                emb = embed_text(fs["question"])
                cur.execute(
                    """
                    INSERT INTO fewshot_embeddings (question, sql_example, embedding)
                    VALUES (%s, %s, %s::vector)
                    """,
                    (fs["question"], fs["sql"], emb),
                )
                print(f"Inserted: {fs['question'][:40]}...")
            conn.commit()
    print(f"\nTotal {len(FEWSHOTS)} fewshots embedded.")

if __name__ == "__main__":
    main()
