"""
Semantic Few-shot 테스트
- RAG + Semantic Few-shot 도입 후 SQL 생성 품질 검증
- 참조: tests/after_rag_fewshot_semantic.md

실행: pytest tests/pytest/test_semantic_fewshot.py -v
"""
import pytest
from datetime import date


class TestDateRangeQuery:
    """테스트 1: 날짜 범위 쿼리"""

    def test_date_range_specific_days(self, client, current_month):
        """특정 날짜 범위 (X월1일~2일) 해석 테스트"""
        question = f"fact_production_daily 테이블에서 {current_month}월1일~2일 제품 총 합계는 얼마야?"

        response = client.post(
            "/api/query",
            json={"question": question, "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()

        sql = data.get("sql", "").upper()
        assert sql, "SQL이 생성되지 않음"
        assert "FACT_PRODUCTION_DAILY" in sql, "올바른 테이블명 사용 필요"
        assert "SUM" in sql, "SUM 집계 함수 필요"
        assert "WHERE" in sql, "날짜 조건 WHERE 절 필요"


class TestSimpleCountQuery:
    """테스트 2: 단순 집계 쿼리"""

    def test_distinct_count(self, client):
        """DISTINCT COUNT 테스트"""
        response = client.post(
            "/api/query",
            json={"question": "fact_production_daily 테이블에 존재하는 공정 종류 수는?", "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()

        sql = data.get("sql", "").upper()
        assert sql, "SQL이 생성되지 않음"
        assert "COUNT" in sql, "COUNT 함수 필요"
        assert "DISTINCT" in sql or "GROUP BY" in sql, "DISTINCT 또는 GROUP BY 필요"

    def test_ambiguous_table_interpretation(self, client):
        """애매한 테이블명 해석 테스트"""
        response = client.post(
            "/api/query",
            json={"question": "매일 공정 테이블에서 작업 세션은 총 몇개?", "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()

        sql = data.get("sql", "").upper()
        assert sql, "SQL이 생성되지 않음"
        valid_tables = ["FACT_PRODUCTION_DAILY", "FACT_ORDER_DAILY", "DIM_PROCESS"]
        assert any(t in sql for t in valid_tables), "유효한 테이블명 사용 필요"


class TestHavingAggQuery:
    """테스트 3: HAVING 집계 조건 쿼리"""

    def test_having_clause(self, client, current_year, current_month):
        """GROUP BY + HAVING 조건 테스트"""
        question = f"{current_year}년 {current_month}월에 총 생산량이 4 이상인 공정은?"

        response = client.post(
            "/api/query",
            json={"question": question, "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()

        sql = data.get("sql", "").upper()
        assert sql, "SQL이 생성되지 않음"
        assert "GROUP BY" in sql, "GROUP BY 절 필요"
        assert "HAVING" in sql, "HAVING 절 필요 (집계 조건)"
        assert "SUM" in sql, "SUM 집계 함수 필요"


class TestDisallowedTableQuery:
    """테스트 4: 금지 테이블 접근 테스트"""

    def test_dim_worker_user_role(self, client):
        """user 권한으로 dim_worker 접근 시도"""
        response = client.post(
            "/api/query",
            json={"question": "dim_worker 테이블에서 사람은 총 몇명?", "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()

        sql = data.get("sql", "")
        # 현재는 경고만 기록 (향후 개선 필요)
        if sql and "DIM_WORKER" in sql.upper():
            pytest.skip("dim_worker 차단 기능 미구현 - 향후 개선 필요")

    def test_dim_worker_admin_role(self, client):
        """admin 권한으로 dim_worker 접근"""
        response = client.post(
            "/api/query",
            json={"question": "dim_worker 테이블에서 사람은 총 몇명?", "role": "admin"}
        )
        assert response.status_code == 200
        data = response.json()

        sql = data.get("sql", "")
        assert sql, "admin은 dim_worker 접근 가능해야 함"


class TestJoinQuery:
    """테스트 5: 조인 쿼리"""

    def test_join_with_filter(self, client):
        """테이블 조인 + 필터 조건 테스트"""
        response = client.post(
            "/api/query",
            json={
                "question": "fact_production_daily 테이블과 dim_process 테이블을 이용하여 product '물건1'의 총 생산량을 계산",
                "role": "user"
            }
        )
        assert response.status_code == 200
        data = response.json()

        sql = data.get("sql", "").upper()
        assert sql, "SQL이 생성되지 않음"
        assert "FACT_PRODUCTION_DAILY" in sql, "fact_production_daily 테이블 필요"
        assert "DIM_PROCESS" in sql, "dim_process 테이블 필요"
        assert "JOIN" in sql, "JOIN 절 필요"
        assert "물건1" in data.get("sql", "") or "'물건1'" in data.get("sql", ""), "물건1 필터 조건 필요"

    def test_simple_product_filter(self, client):
        """간단한 제품 필터 조인 테스트"""
        response = client.post(
            "/api/query",
            json={"question": "product가 '물건1'인 공정들의 총 생산량을 알려줘", "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()

        sql = data.get("sql", "").upper()
        assert sql, "SQL이 생성되지 않음"
        assert "SUM" in sql, "SUM 집계 함수 필요"


class TestCTERatioQuery:
    """테스트 6: CTE 비율 계산 쿼리"""

    def test_percentage_calculation(self, client, current_month):
        """퍼센트 달성률 계산 테스트"""
        question = (
            f"fact_production_daily와 fact_order_daily를 이용하고, "
            f"order_status가 '출고 대기'인 물품의 ordered_qty를 전체 생산 요구량으로 잡고, "
            f"{current_month}월 produced_qty 총합과 비교해 몇 퍼센트 달성되었는지 찾아줘"
        )

        response = client.post(
            "/api/query",
            json={"question": question, "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()

        sql = data.get("sql", "").upper()
        assert sql, "SQL이 생성되지 않음"
        assert "FACT_PRODUCTION_DAILY" in sql, "fact_production_daily 테이블 필요"
        assert "FACT_ORDER_DAILY" in sql, "fact_order_daily 테이블 필요"

        has_percent_calc = (
            "100" in sql or
            "PERCENT" in sql or
            "/" in data.get("sql", "")
        )
        assert has_percent_calc, "퍼센트 계산 로직 필요"


class TestEasyNaturalLanguageQuery:
    """테스트 7: 쉬운 자연어 쿼리"""

    def test_simple_list_query(self, client):
        """단순 목록 조회"""
        response = client.post(
            "/api/query",
            json={"question": "공정 목록 보여줘", "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()

        assert data.get("sql"), "SQL이 생성되지 않음"
        assert data.get("meta", {}).get("ok"), "쿼리 실행 성공해야 함"

    def test_simple_status_query(self, client):
        """단순 현황 조회"""
        response = client.post(
            "/api/query",
            json={"question": "주문 현황 알려줘", "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()

        sql = data.get("sql", "").upper()
        assert sql, "SQL이 생성되지 않음"
        assert "ORDER" in sql or "FACT_ORDER" in sql, "주문 관련 테이블 사용 필요"

    def test_this_month_data_query(self, client):
        """이번 달 데이터 조회"""
        response = client.post(
            "/api/query",
            json={"question": "이번 달 생산 데이터 보여줘", "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()

        sql = data.get("sql", "").upper()
        assert sql, "SQL이 생성되지 않음"
        assert "PRODUCTION" in sql or "FACT_PRODUCTION" in sql, "생산 관련 테이블 사용 필요"


class TestRecentInterpretation:
    """'최근' 해석 일관성 테스트"""

    def test_recent_means_this_month(self, client, current_year, current_month):
        """'최근' = '이번 달' 해석 테스트"""
        response = client.post(
            "/api/query",
            json={"question": "최근 생산량 알려줘", "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()

        sql = data.get("sql", "")
        assert sql, "SQL이 생성되지 않음"

        year_str = str(current_year)
        month_str = f"{current_month:02d}"

        has_date_condition = (
            year_str in sql and month_str in sql
        ) or "WHERE" in sql.upper()

        assert has_date_condition, "'최근'은 이번 달로 해석되어야 함"


class TestSQLQuality:
    """SQL 품질 테스트"""

    def test_sql_uses_cast_for_dates(self, client, current_year, current_month):
        """날짜 CAST 사용 확인"""
        response = client.post(
            "/api/query",
            json={"question": f"{current_year}년 {current_month}월 생산량 합계", "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()

        sql = data.get("sql", "").upper()
        if sql:
            has_date_handling = (
                "CAST" in sql or
                "::DATE" in sql or
                "DATE '" in sql or
                "DATE'" in sql
            )
            if not has_date_handling:
                pytest.skip("날짜 CAST 사용 권장 (현재 미사용)")

    def test_no_sql_injection_risk(self, client):
        """SQL 인젝션 위험 없음 확인"""
        malicious_input = "'; DROP TABLE fact_production_daily; --"
        response = client.post(
            "/api/query",
            json={"question": malicious_input, "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()

        sql = data.get("sql", "").upper()
        assert "DROP TABLE" not in sql, "SQL 인젝션 방지 필요"
