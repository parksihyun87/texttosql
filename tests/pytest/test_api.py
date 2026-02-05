"""
API 엔드포인트 테스트
- Health check
- Query endpoints
- Table endpoints
- Chat endpoints

실행: pytest tests/pytest/test_api.py -v
"""
import pytest


class TestHealthCheck:
    """API 상태 확인 테스트"""

    def test_health_endpoint(self, client):
        """GET /api/health - 서버 상태 확인"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True


class TestTableEndpoints:
    """테이블 관련 엔드포인트 테스트"""

    def test_list_tables(self, client):
        """GET /api/query/tables - 허용된 테이블 목록"""
        response = client.get("/api/query/tables")
        assert response.status_code == 200
        data = response.json()
        assert "tables" in data
        assert isinstance(data["tables"], list)
        # 필수 테이블 존재 확인
        expected_tables = {"fact_production_daily", "fact_order_daily", "dim_process", "dim_worker"}
        assert expected_tables.issubset(set(data["tables"]))

    @pytest.mark.parametrize("table_name", [
        "fact_production_daily",
        "fact_order_daily",
        "dim_process",
        "dim_worker",
    ])
    def test_get_table_schema(self, client, table_name):
        """GET /api/query/table/{table_name}/schema - 테이블 스키마"""
        response = client.get(f"/api/query/table/{table_name}/schema")
        assert response.status_code == 200
        data = response.json()
        assert data["table_name"] == table_name
        assert "columns" in data
        assert len(data["columns"]) > 0
        # 컬럼 정보 구조 확인
        for col in data["columns"]:
            assert "name" in col
            assert "type" in col

    def test_get_table_schema_not_found(self, client):
        """존재하지 않는 테이블 스키마 요청"""
        response = client.get("/api/query/table/nonexistent_table/schema")
        assert response.status_code == 404

    @pytest.mark.parametrize("table_name", [
        "fact_production_daily",
        "fact_order_daily",
        "dim_process",
    ])
    def test_get_table_data(self, client, table_name):
        """GET /api/query/table/{table_name}/data - 테이블 데이터"""
        response = client.get(f"/api/query/table/{table_name}/data", params={"limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert data["table_name"] == table_name
        assert "columns" in data
        assert "rows" in data
        assert "row_count" in data
        assert data["row_count"] <= 10

    def test_get_table_data_not_found(self, client):
        """존재하지 않는 테이블 데이터 요청"""
        response = client.get("/api/query/table/nonexistent_table/data")
        assert response.status_code == 404


class TestQueryEndpoint:
    """쿼리 엔드포인트 테스트"""

    def test_simple_query(self, client):
        """POST /api/query - 단순 쿼리"""
        response = client.post(
            "/api/query",
            json={"question": "공정 목록 보여줘", "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "sql" in data
        assert "rows" in data
        assert "meta" in data

    def test_query_with_admin_role(self, client):
        """POST /api/query - admin 권한 쿼리"""
        response = client.post(
            "/api/query",
            json={"question": "dim_worker 테이블 전체 보여줘", "role": "admin"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "sql" in data


class TestChatEndpoint:
    """채팅 엔드포인트 테스트"""

    def test_unified_chat_greeting(self, client, session_id):
        """POST /chat/unified - 인사 의도"""
        response = client.post(
            "/chat/unified",
            json={"session_id": session_id, "message": "안녕하세요", "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "greeting"
        assert data["answer"] is not None

    def test_unified_chat_data_query(self, client, session_id):
        """POST /chat/unified - 데이터 쿼리 의도"""
        response = client.post(
            "/chat/unified",
            json={"session_id": session_id, "message": "이번 달 생산량 알려줘", "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "data_query"
        assert data["sql"] is not None

    def test_unified_chat_off_topic(self, client, session_id):
        """POST /chat/unified - 주제 외 의도"""
        response = client.post(
            "/chat/unified",
            json={"session_id": session_id, "message": "오늘 날씨 어때?", "role": "user"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "off_topic"
        assert data["answer"] is not None


class TestQuestionGenerateEndpoint:
    """질문 생성 엔드포인트 테스트"""

    @pytest.mark.slow
    def test_generate_creative_questions(self, client):
        """POST /api/questions/generate - 창의적 질문 생성 (type_id=7)"""
        response = client.post(
            "/api/questions/generate",
            json={"total_questions": 2, "type_ids": [7]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert len(data["questions"]) >= 1
        for q in data["questions"]:
            assert q["type_id"] == 7
            assert q["type_name"] == "creative_schema"
            assert "question" in q
            assert "rationale" in q

    @pytest.mark.slow
    def test_generate_ambiguous_questions(self, client):
        """POST /api/questions/generate - 모호한 질문 생성 (type_id=8)"""
        response = client.post(
            "/api/questions/generate",
            json={"total_questions": 2, "type_ids": [8]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        for q in data["questions"]:
            assert q["type_id"] == 8
            assert q["type_name"] == "ambiguous_edge"
