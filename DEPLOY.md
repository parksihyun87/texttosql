# Railway 배포 가이드

## 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    Railway Project                       │
├─────────────────┬─────────────────┬─────────────────────┤
│   PostgreSQL    │    FastAPI      │     Streamlit       │
│   (pgvector)    │    (Backend)    │     (Frontend)      │
│   :5432         │    :PORT        │     :PORT           │
└─────────────────┴─────────────────┴─────────────────────┘
```

## 배포 단계

### 1. Railway 계정 생성 & 프로젝트 생성

1. [railway.app](https://railway.app)에서 계정 생성
2. 새 프로젝트 생성 (Empty Project)

### 2. PostgreSQL + pgvector 배포

Railway는 기본 PostgreSQL은 제공하지만, pgvector 확장이 필요합니다.

**옵션 A: Railway PostgreSQL 사용 (pgvector 수동 설치)**
1. 프로젝트에서 "+ New" → "Database" → "PostgreSQL" 선택
2. 생성된 DB에서 `CREATE EXTENSION IF NOT EXISTS vector;` 실행

**옵션 B: Docker 이미지로 직접 배포**
1. "+ New" → "Docker Image"
2. 이미지: `pgvector/pgvector:pg16`
3. 환경 변수 설정:
   ```
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=<secure-password>
   POSTGRES_DB=mydb
   ```

### 3. FastAPI 백엔드 배포

1. "+ New" → "GitHub Repo" → 이 저장소 선택
2. 설정:
   - Root Directory: `/` (기본값)
   - Dockerfile: `Dockerfile`
3. 환경 변수 설정:
   ```
   DATABASE_URL=postgresql+psycopg://<user>:<password>@<db-host>:5432/<db-name>
   OPENAI_API_KEY=sk-xxx...
   ```

   > PostgreSQL 서비스의 "Variables" 탭에서 연결 정보 복사 가능

4. "Deploy" 클릭

### 4. Streamlit 프론트엔드 배포

1. "+ New" → "GitHub Repo" → 같은 저장소 다시 선택
2. 설정:
   - Dockerfile: `Dockerfile.streamlit`
3. 환경 변수 설정:
   ```
   API_BASE_URL=https://<fastapi-service-domain>.railway.app
   ```

   > FastAPI 서비스의 "Settings" → "Networking" → "Public Domain"에서 URL 확인

4. "Deploy" 클릭

### 5. 도메인 설정

각 서비스에서:
1. "Settings" → "Networking" → "Generate Domain" 클릭
2. 커스텀 도메인도 설정 가능

## 환경 변수 요약

| 서비스 | 변수 | 값 |
|--------|------|-----|
| PostgreSQL | POSTGRES_USER | postgres |
| PostgreSQL | POSTGRES_PASSWORD | (자동생성 또는 직접설정) |
| PostgreSQL | POSTGRES_DB | mydb |
| FastAPI | DATABASE_URL | postgresql+psycopg://... |
| FastAPI | OPENAI_API_KEY | sk-... |
| Streamlit | API_BASE_URL | https://fastapi-xxx.railway.app |

## 로컬 테스트 (docker-compose)

```bash
# 전체 스택 실행
docker-compose up --build

# 접속
# - FastAPI: http://localhost:8000
# - Streamlit: http://localhost:8501
# - PostgreSQL: localhost:5433
```

## 마이그레이션 실행 (최초 1회)

Railway에서 FastAPI 서비스 배포 후:

```bash
# Railway CLI 설치
npm install -g @railway/cli

# 로그인
railway login

# 프로젝트 연결
railway link

# 마이그레이션 실행
railway run alembic upgrade head
```

## 데이터 초기화

임베딩 데이터 등 초기 데이터가 필요한 경우:

```bash
# Railway CLI로 스크립트 실행
railway run python -m t2sql.scripts.init_embeddings
```

## 비용

Railway 요금:
- Hobby Plan: $5/월 (5$ 크레딧 포함)
- 리소스 사용량에 따라 과금
- PostgreSQL: 약 $0.000231/시간 (512MB RAM 기준)

## 트러블슈팅

### pgvector 확장 오류
```sql
-- PostgreSQL에서 실행
CREATE EXTENSION IF NOT EXISTS vector;
```

### 연결 오류
- DATABASE_URL 형식 확인: `postgresql+psycopg://user:pass@host:5432/dbname`
- Railway 내부 네트워크는 `<service-name>.railway.internal` 사용

### 스트리밍 응답 타임아웃
Railway의 기본 요청 타임아웃은 100초. 필요시 설정에서 조정.
