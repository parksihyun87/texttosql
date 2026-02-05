from openai import OpenAI
import psycopg
import os

client = OpenAI()

EMBED_MODEL = "text-embedding-3-small"
# psycopg.connect()는 순수 postgresql:// 형식만 받음
DB_URL = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

def embed_query(q: str) -> list[float]:
    res = client.embeddings.create(model=EMBED_MODEL, input=q)
    return res.data[0].embedding

def search_schema(q: str, k: int = 8):
    qvec = embed_query(q)
    with psycopg.connect(DB_URL)  as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT doc_type, table_name, column_name, content,
                        (embedding <=> %s::vector) AS distance
                FROM schema_embeddings
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (qvec, qvec, k),
            )
            return cur.fetchall()

def fetch_all_schema():
    """Return all schema metadata rows without vector search."""
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT doc_type, table_name, column_name, content,
                       NULL AS distance
                FROM schema_embeddings
                ORDER BY table_name, column_name NULLS FIRST
                """
            )
            return cur.fetchall()

def search_fewshots(q: str, k: int = 3):
    """질문과 유사한 few-shot 예제를 검색"""
    qvec = embed_query(q)
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT question, sql_example,
                       (embedding <=> %s::vector) AS distance
                FROM fewshot_embeddings
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (qvec, qvec, k),
            )
            return cur.fetchall()
