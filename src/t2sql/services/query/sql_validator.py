import sqlglot
from sqlglot import exp

ALLOWED_TABLES = {"fact_production_daily"}
FORCE_LIMIT = 2000

class SqlRejected(Exception):
    pass

def _extract_table_names(ast: exp.Expression) -> set[str]:
    """
    AST에서 참조된 테이블 이름들을 추출.
    - schema.table 형태면 table만 or schema.table 전체를 쓸지 정책 결정 필요
    """
    names: set[str] = set()

    #from/join 등에 등장하는 exp.table 노드들을 훑음
    for t in ast.find_all(exp.Table):
        # t.name: 테이블명(예: fact_production_daily)
        # t.db: 스키마명(있으면)
        # t.catalog: 카탈로그명(있으면)
        table = t.name

        # 스키마까지 포함해서 관리하고 싶으면:
        # if t.db: table = f"{t.db}.{t.name}"
        
        names.add(table)
    
    return names


def validate_and_normalize(sql: str) -> str:
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
    
    # 테이블 화이트리스트 검사
    used_tables = _extract_table_names(ast)
    disallowed = used_tables - ALLOWED_TABLES
    if disallowed:
        raise SqlRejected(f"Disallowed tables: {sorted(disallowed)}")

    return ast.sql(dialect="postgres")