import sqlglot
from sqlglot import exp

# role별 허용 테이블
ALLOWED_TABLES_BY_ROLE = {
    "user": {"fact_production_daily", "fact_order_daily", "dim_process"},
    "admin": {"fact_production_daily", "fact_order_daily", "dim_process", "dim_worker"},
}
FORCE_LIMIT = 2000

class SqlRejected(Exception):
    pass

def _extract_cte_names(ast: exp.Expression) -> set[str]:
    """WITH 절에서 정의된 CTE 이름들을 추출"""
    cte_names: set[str] = set()
    for cte in ast.find_all(exp.CTE):
        if cte.alias:
            cte_names.add(cte.alias)
    return cte_names


def _extract_table_names(ast: exp.Expression) -> set[str]:
    """
    AST에서 참조된 실제 테이블 이름들을 추출.
    CTE 별칭은 제외함.
    """
    names: set[str] = set()
    cte_names = _extract_cte_names(ast)

    # from/join 등에 등장하는 exp.Table 노드들을 훑음
    for t in ast.find_all(exp.Table):
        table = t.name
        # CTE 별칭은 실제 테이블이 아니므로 제외
        if table not in cte_names:
            names.add(table)

    return names


def validate_and_normalize(sql: str, role: str = "user") -> str:
    try:
        ast = sqlglot.parse_one(sql, read="postgres")
    except Exception as e:
        raise SqlRejected(f"SQL parse failed: {e}")

    # SELECT 또는 with(최종이 select인 경우) 허용
    if isinstance(ast, exp.With):
        if not isinstance(ast.this , exp.Select):
            raise SqlRejected("Only SELECT queries are allowed.")
        select_node = ast.this
    elif isinstance(ast, exp.Select):
        select_node = ast
    else:
        raise SqlRejected("Only SELECT queries are allowed.")

    # role에 따른 테이블 화이트리스트 검사
    allowed_tables = ALLOWED_TABLES_BY_ROLE.get(role, ALLOWED_TABLES_BY_ROLE["user"])
    used_tables = _extract_table_names(ast)
    disallowed = used_tables - allowed_tables
    if disallowed:
        raise SqlRejected(f"Disallowed tables: {sorted(disallowed)}")

    return ast.sql(dialect="postgres")