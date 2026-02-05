# Text-to-SQL RAG + Semantic Few-shot + CTE 프롬프팅 테스트 결과

## 테스트 환경
- 벡터 검색(RAG): pgvector + OpenAI text-embedding-3-small
- Semantic Few-shot: 질문과 유사한 예제 3개 동적 검색
- **CTE 프롬프팅 추가**: 복잡한 쿼리에서 의미있는 CTE 이름 사용
- LLM: gpt-4o-mini
- 테스트 일시: 2026-02-05

---

## CTE 프롬프팅 규칙

```
- SQL은 가능한 한 단순하게 작성한다.
- 단, 아래 조건에 해당하면 CTE(WITH)를 사용한다:
  1) 서로 다른 집계 결과를 결합할 때 (예: 주문 vs 생산)
  2) 집계 결과를 다시 필터링/정렬/비율 계산할 때
  3) 같은 서브쿼리가 2번 이상 반복될 때
- CTE 이름은 의미가 드러나게 작성한다 (예: orders_waiting, production_total, by_process).
```

---

## 테스트 케이스별 결과

### 테스트 1: 날짜 범위 쿼리

**질문**: `fact_production_daily 테이블에서 2월1일~2일 제품 총 합계는 얼마야?`

**생성된 SQL**:
```sql
SELECT SUM(produced_qty) AS total_produced
FROM fact_production_daily
WHERE day >= CAST('2026-02-01' AS DATE)
  AND day < CAST('2026-02-03' AS DATE)
```

**결과**: `total_produced = 36`

| 항목 | 평가 |
|------|------|
| CTE 사용 | ➡️ 불필요 (단순 쿼리) |
| 날짜 범위 | ✅ 2월1~2일 정확 |
| SQL 실행 | ✅ 성공 |

**정확도**: ✅ **완전 정확**

---

### 테스트 2: 애매한 테이블명 쿼리

**질문**: `매일 공정 테이블에서 작업 세션은 총 몇개?`

**생성된 SQL**:
```sql
SELECT COUNT(DISTINCT process) AS session_count
FROM fact_production_daily
```

**결과**: `session_count = 9`

| 항목 | 평가 |
|------|------|
| CTE 사용 | ➡️ 불필요 (단순 쿼리) |
| 논리 해석 | ✅ 합리적 |
| SQL 실행 | ✅ 성공 |

**정확도**: ✅ **완전 정확**

---

### 테스트 3: HAVING 집계 조건 쿼리

**질문**: `2월에 생산합계가 4이상인 공정은?`

**생성된 SQL**:
```sql
SELECT process, SUM(produced_qty) AS total_produced
FROM fact_production_daily
WHERE day >= CAST('2026-02-01' AS DATE)
  AND day < CAST('2026-03-01' AS DATE)
GROUP BY process
HAVING SUM(produced_qty) >= 4
```

**결과**: 6개 공정 (B, E, I, C, H, F)

| 항목 | 평가 |
|------|------|
| CTE 사용 | ➡️ 불필요 (단순 집계) |
| HAVING 절 | ✅ 정확 |
| SQL 실행 | ✅ 성공 |

**정확도**: ✅ **완전 정확**

---

### 테스트 4: 테이블 접근 금지 (dim_worker)

**질문**: `dim_worker 테이블에서 사람은 총 몇명?`

**생성된 SQL**:
```sql
SELECT COUNT(*) AS total_people
FROM dim_worker
```

**결과**: `{"ok": false, "reason": "Disallowed tables: ['dim_worker']"}`

| 항목 | 평가 |
|------|------|
| dim_worker 접근 | ✅ **차단됨** |
| 에러 메시지 | ✅ `Disallowed tables: ['dim_worker']` |

**정확도**: ✅ **보안 목표 달성** - 화이트리스트 검증으로 차단

---

### 테스트 5: 조인 쿼리 (물건1 생산량)

**질문**: `fact_production_daily 테이블과 dim_process 테이블을 이용하여 product '물건1'의 총 생산량을 계산`

**생성된 SQL**:
```sql
SELECT dp.product, SUM(fp.produced_qty) AS total_produced
FROM fact_production_daily AS fp
JOIN dim_process AS dp ON fp.process = dp.process
WHERE dp.product = '물건1'
GROUP BY dp.product
```

**결과**: `product = '물건1', total_produced = 18`

| 항목 | 평가 |
|------|------|
| CTE 사용 | ➡️ 불필요 (단순 조인) |
| 조인/필터 | ✅ 완벽 |
| SQL 실행 | ✅ 성공 |

**정확도**: ✅ **완전 정확**

---

### 테스트 6: 복합 계산 (퍼센트 달성률) ⭐ CTE 개선

**질문**: `fact_production_daily와 fact_order_daily를 이용하고, order_status가 '출고 대기'인 물품의 ordered_qty를 전체 생산 요구량으로 잡고, 2월 produced_qty 총합과 비교해 몇 퍼센트 달성되었는지 찾아줘`

**생성된 SQL** (CTE 이름 개선):
```sql
WITH orders_waiting AS (
  SELECT SUM(ordered_qty) AS total_ordered
  FROM fact_order_daily
  WHERE order_status = '출고 대기'
    AND day >= CAST('2026-02-01' AS DATE)
    AND day < CAST('2026-03-01' AS DATE)
),
production_total AS (
  SELECT SUM(produced_qty) AS total_produced
  FROM fact_production_daily
  WHERE day >= CAST('2026-02-01' AS DATE)
    AND day < CAST('2026-03-01' AS DATE)
)
SELECT
  COALESCE(pt.total_produced, 0) AS total_produced,
  ot.total_ordered,
  CASE
    WHEN ot.total_ordered = 0 THEN 0
    ELSE ROUND((COALESCE(pt.total_produced, 0) * 100.0) / ot.total_ordered, 2)
  END AS achievement_pct
FROM orders_waiting AS ot
CROSS JOIN production_total AS pt
```

**결과**: `total_produced = 54, total_ordered = 222, achievement_pct = 24.32`

| 항목 | 이전 (Semantic) | CTE 프롬프팅 후 |
|------|-----------------|-----------------|
| CTE 이름 | `o`, `p` | `orders_waiting`, `production_total` |
| 별칭 | `o`, `p` | `ot`, `pt` |
| 가독성 | 보통 | ✅ **향상** |

| 항목 | 평가 |
|------|------|
| CTE 사용 | ✅ 적절 (서로 다른 집계 결합) |
| CTE 이름 | ✅ **의미있는 이름** (`orders_waiting`, `production_total`) |
| 퍼센트 계산 | ✅ 정확 |
| SQL 실행 | ✅ 성공 |

**정확도**: ✅ **완전 정확** + 가독성 향상

---

## 종합 평가

### CTE 프롬프팅 효과

| 테스트 | CTE 필요 | CTE 사용 | CTE 이름 |
|--------|----------|----------|----------|
| 1. 날짜 범위 | ❌ | ❌ | - |
| 2. 애매한 테이블 | ❌ | ❌ | - |
| 3. HAVING 조건 | ❌ | ❌ | - |
| 4. dim_worker | ❌ | ❌ | - |
| 5. 조인 쿼리 | ❌ | ❌ | - |
| 6. 퍼센트 계산 | ✅ | ✅ | ✅ `orders_waiting`, `production_total` |

### CTE 이름 비교 (테스트 6)

| 버전 | CTE 이름 | 가독성 |
|------|----------|--------|
| Semantic Few-shot | `o`, `p` | 🟡 약어 |
| **CTE 프롬프팅** | `orders_waiting`, `production_total` | ✅ **의미 명확** |

### 테스트 결과 요약

| 테스트 | 결과 | 변화 |
|--------|------|------|
| 1. 날짜 범위 | ✅ 완전 정확 | ➡️ 동일 |
| 2. 애매한 테이블 | ✅ 완전 정확 | ➡️ 동일 |
| 3. HAVING 조건 | ✅ 완전 정확 | ➡️ 동일 |
| 4. dim_worker 차단 | 🟡 차단 실패 | ➡️ 동일 |
| 5. 조인 쿼리 | ✅ 완전 정확 | ➡️ 동일 |
| 6. 퍼센트 계산 | ✅ 완전 정확 | ⬆️ CTE 이름 개선 |

---

## 결론

- **단순 쿼리**: CTE 없이 간결하게 생성 (프롬프트 규칙 준수)
- **복합 쿼리**: CTE 사용 + 의미있는 이름 (`orders_waiting`, `production_total`)
- **가독성 향상**: 사람이 SQL을 읽고 이해하기 쉬워짐

### CTE 프롬프팅의 장점

1. **필요할 때만 CTE 사용**: 불필요한 복잡성 방지
2. **의미있는 이름**: `o`, `p` → `orders_waiting`, `production_total`
3. **유지보수 용이**: SQL 의도가 명확해짐
