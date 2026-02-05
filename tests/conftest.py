"""
Pytest 공통 설정 및 fixtures
"""
import os
import pytest
from fastapi.testclient import TestClient

# 테스트 시 환경변수 설정
os.environ.setdefault("DATABASE_URL", os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/mydb"))


@pytest.fixture(scope="session")
def api_base_url():
    """API 기본 URL (로컬 또는 Railway)"""
    return os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient fixture"""
    from t2sql.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def session_id():
    """테스트용 세션 ID"""
    import uuid
    return str(uuid.uuid4())[:8]


@pytest.fixture
def test_date():
    """테스트 기준 날짜"""
    from datetime import date
    return date.today()
