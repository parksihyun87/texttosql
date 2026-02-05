# Text-to-SQL (RAG + pgvector)

생산/주문 데이터를 자연어로 질문하면 SQL을 생성하고 실행 결과를 반환하는 Text-to-SQL 프로젝트입니다.  
FastAPI 백엔드, PostgreSQL + pgvector, 임베딩 기반 RAG, few-shot 프롬프팅을 사용합니다.

---

## 프로젝트 개요

- 자연어 질의를 SQL로 변환하고 결과를 반환
- 스키마/컬럼 메타데이터 임베딩을 활용한 RAG
- few-shot 예제 임베딩 기반 유사도 검색
- PostgreSQL + pgvector + HNSW(ANN) 인덱스 기반 검색
- Docker Compose로 API/DB 구성
- SSE 기반 스트리밍 응답 설계

---

## 시스템 구조 요약

### 프론트 (Streamlit)
- 간단한 챗 UI
- 질문 입력 → FastAPI 호출 → 결과(응답/SQL/rows) 표시
- `src/frontend/app.py`

### 백엔드 (FastAPI)
- `/api/query`: 자연어 질문 → SQL 생성 → 실행 → 결과 반환
- `/api/questions/generate`: 엣지 질문 생성 API
- `src/t2sql/main.py`, `src/t2sql/routers/*`

### DB (PostgreSQL + pgvector)
- pgvector 확장 사용
- 스키마/컬럼/예제 SQL 임베딩 저장
- 벡터 검색(HNSW)로 RAG 수행

### Docker
- `docker-compose.yml`로 API/DB 실행
- DB: `pgvector/pgvector:pg16`
- API: `Dockerfile`로 빌드

### (옵션) SSE
- 챗봇 응답 스트리밍 설계 가능
- `docs/chatbot_plan.md` 참고

---

## SQL 생성에 사용된 기술

### 1) 자연어 임베딩
- 사용자 질문을 임베딩 모델로 벡터화
- pgvector에 저장된 스키마/메타 임베딩과 유사도 검색 수행

### 2) 스키마/컬럼/메타데이터 임베딩
- 테이블/컬럼 설명(메타데이터)을 벡터로 저장
- RAG 검색 결과를 프롬프트에 삽입하여 정확한 SQL 생성 유도

### 3) Few-shot 프롬프팅
- 유사 질문/SQL 예제를 few-shot으로 삽입
- 질문-쿼리 변환의 패턴 정합성 향상

### 4) Few-shot 벡터 검색
- few-shot 예제도 임베딩 후 pgvector로 저장
- 사용자 질문과 유사한 예제를 검색해 프롬프트에 첨부

### 5) HNSW 및 ANN
- pgvector의 HNSW 인덱스를 통해 빠른 근사 최근접 이웃(ANN) 검색
- 대용량 벡터 검색에도 실시간 성능 확보

---

## 데이터베이스 및 스키마 구조

### 테이블

- `dim_process`
  - `process` (PK)
  - `product`

- `dim_worker`  
  - `worker_id` (PK)
  - `process`
  - `worker_name`

- `fact_production_daily`
  - `day` (PK)
  - `process` (PK)
  - `produced_qty`

- `fact_order_daily`
  - `day` (PK)
  - `process` (PK)
  - `order_status` (PK: '출고 완료' | '출고 대기')
  - `ordered_qty`

- `schema_embeddings`
  - 스키마/컬럼/메타데이터 임베딩 저장

- `fewshot_embeddings`
  - few-shot 질문/SQL 임베딩 저장

---

## 주요 모듈 구성

- `src/t2sql/services/rag/vector_search.py`
  - 스키마/예제 임베딩 검색
  - `search_schema`, `search_fewshots`, `fetch_all_schema`

- `src/t2sql/services/llm/llm_client.py`
  - SQL 생성 프롬프트 + LLM 호출

- `src/t2sql/services/llm/llm_edge_question_generator.py`
  - 전체 스키마 컨텍스트 기반 엣지 질문 생성

- `src/t2sql/services/query/sql_validator.py`
  - SQL 안전성/금지 테이블 체크

---

## 폴더 구조 (간단)

- `src/t2sql/`
  - `routers/` API 라우터
  - `services/` 비즈니스 로직 (LLM, RAG, SQL 검증)
  - `db/` DB 세션/모델
  - `schemas/` Pydantic 요청/응답 모델
  - `scripts/` 임베딩/유틸 스크립트
- `src/frontend/` Streamlit UI
- `alembic/` DB 마이그레이션
- `tests/` 실험/테스트 문서
- `sql_csv/` 초기 데이터 CSV
- `docs/` 설계 문서

---

## 실행 방법 (요약)

```bash
docker compose up -d --build
```

Streamlit (로컬 실행):
```bash
streamlit run src/frontend/app.py
```

---

## 추가 문서

- 배포 관련 문서: `DEPLOY.md`

---

## 참고

- 본 프로젝트는 Text-to-SQL 정확도 향상을 위해 **스키마/메타데이터 임베딩 + few-shot 검색**을 핵심 전략으로 사용합니다.
- RAG를 통해 LLM이 임의의 테이블/컬럼을 추측하지 않도록 제약합니다.
