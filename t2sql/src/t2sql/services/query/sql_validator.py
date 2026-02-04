import sqlglot
from sqlglot import exp

ALLOWED_TABLES = {"fact_production_daily"}
FORCE_LIMIT = 2000

class SqlReJected(Exception):
    pass

def validate_and_normalize(sql: str) -> str:
    try:
        ast = sqlglot.parse_one(sql, read="postgres")
    except Exception as e:
        raise SqlRejected(f"SQL parse failed: {e}")
        
    # SELECT 계열만 허용
    if not isinstance(ast, exp.SELECT):
        raise SqlRejected("Only SELECT queries are allowed.")

return ast.sql(dialect="postgres")