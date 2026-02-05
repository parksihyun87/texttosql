"""
Text-to-SQL Streamlit Frontend
통합 챗봇 인터페이스
"""
import os
import json
from pathlib import Path
import base64
import requests
import streamlit as st

# API 서버 URL (환경변수 또는 기본값)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def unified_chat_api(session_id: str, message: str, role: str = "user") -> dict:
    """통합 챗봇 API 호출"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat/unified",
            json={"session_id": session_id, "message": message, "role": role},
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def check_health() -> bool:
    """API 서버 상태 확인"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def generate_creative_questions() -> list:
    """창의적 질문(type_id=7) 생성 API 호출"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/questions/generate",
            json={"total_questions": 3, "type_ids": [7]},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return [q["question"] for q in data.get("questions", [])]
    except requests.exceptions.RequestException:
        return []


def extract_tables_from_sql(sql: str) -> list:
    """SQL에서 테이블명 추출"""
    import re
    if not sql:
        return []
    # FROM, JOIN 절에서 테이블명 추출
    pattern = r'\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    matches = re.findall(pattern, sql, re.IGNORECASE)
    # 중복 제거 및 소문자 변환
    return list(dict.fromkeys([m.lower() for m in matches]))


def get_table_schema(table_name: str) -> dict:
    """테이블 스키마 조회"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/query/table/{table_name}/schema",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {}


def get_table_data(table_name: str, limit: int = 100) -> dict:
    """테이블 데이터 조회"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/query/table/{table_name}/data",
            params={"limit": limit},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {}


# Streamlit 앱 설정
BASE_DIR = Path(__file__).resolve().parent
ASKING_DOG = BASE_DIR / "img" / "asking_dog_2.png"

def _image_as_data_uri(path: Path) -> str:
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/png;base64,{b64}"
st.set_page_config(
    page_title="Text-to-SQL",
    page_icon=str(ASKING_DOG),
    layout="wide"
)

dog_uri = _image_as_data_uri(ASKING_DOG)

# 상단 헤더: 제목 + 세션/API 정보
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.markdown(
        f"""
        <div style="display:flex; align-items:flex-end; gap:6px;">
          <img src="{dog_uri}" style="height:72px; width:auto; display:block; margin:0;" />
          <div style="display:flex; align-items:baseline; gap:10px;">
            <span style="font-size:36px; font-weight:700; line-height:1;">SQL 물어보개</span>
            <span style="font-size:14px; color:#6b7280; line-height:1;">생산/주문 데이터에 대해 자연어로 질문하세요</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# 세션 상태 초기화 (사이드바보다 먼저)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = os.urandom(8).hex()
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None
if "generating_creative" not in st.session_state:
    st.session_state.generating_creative = False
if "creative_questions" not in st.session_state:
    st.session_state.creative_questions = []
if "expanded_tables" not in st.session_state:
    st.session_state.expanded_tables = set()

# 상단 오른쪽에 세션/API 정보 표시
with header_col2:
    st.markdown(
        f"""
        <div style="text-align:right; font-size:11px; color:#9ca3af; padding-top:8px;">
            세션: {st.session_state.session_id[:8]}...<br/>
            API: {API_BASE_URL.replace('https://', '').replace('http://', '')[:25]}...
        </div>
        """,
        unsafe_allow_html=True,
    )

# 사이드바
with st.sidebar:
    st.header("설정")

    # API 상태 표시
    if check_health():
        st.success("✅ API 서버 연결됨")
    else:
        st.error("❌ API 서버 연결 실패")
        st.info(f"API URL: {API_BASE_URL}")

    st.divider()

    # 권한 모드
    user_role = st.selectbox(
        "권한",
        ["user", "admin"],
        help="admin: 모든 테이블 접근 가능\nuser: 제한된 테이블만 접근"
    )

    st.divider()

    # 세션 관리
    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.session_state.session_id = os.urandom(8).hex()
        st.rerun()

    st.divider()
    st.markdown("**예시 질문 (유형별):**")

    # 6가지 평가 유형별 예시 질문 + rationale
    from datetime import date
    base_date = date.today()
    y, m = base_date.year, base_date.month

    edge_questions = [
        {
            "type": "1️⃣ 날짜범위",
            "question": f"{y}년 {m}월 첫째 주(1~7일) 생산량 합계는?",
            "hint": "날짜 범위/월 경계 해석 테스트"
        },
        {
            "type": "2️⃣ 단순집계",
            "question": "fact_production_daily 테이블에 존재하는 공정 종류 수는?",
            "hint": "DISTINCT COUNT 사용 테스트"
        },
        {
            "type": "3️⃣ HAVING",
            "question": f"{y}년 {m}월에 총 생산량이 4 이상인 공정 목록은?",
            "hint": "GROUP BY + HAVING 조건 테스트"
        },
        {
            "type": "4️⃣ 금지테이블",
            "question": "dim_worker 테이블에서 작업자 이름을 모두 보여줘",
            "hint": "금지 테이블 접근 차단 테스트"
        },
        {
            "type": "5️⃣ JOIN",
            "question": "product가 '물건1'인 공정들의 총 생산량을 알려줘",
            "hint": "JOIN dim_process + fact_production_daily 테스트"
        },
        {
            "type": "6️⃣ CTE비율",
            "question": f"{y}년 {m}월 출고 대기 주문 합계 대비 생산량 달성률(%)은?",
            "hint": "두 집계 결과 결합 + CTE 테스트"
        },
    ]

    for i, eq in enumerate(edge_questions):
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            if st.button(f"{eq['type']}", key=f"edge_{i}", use_container_width=True):
                st.session_state.pending_question = eq["question"]
                st.rerun()
        with col2:
            st.markdown(f"<span title='{eq['hint']}' style='cursor:help; font-size:16px;'>❓</span>", unsafe_allow_html=True)

    st.divider()
    st.markdown("**7️⃣ 창의적 질문:**")
    if st.button("🎲 AI가 생성한 질문 받기", key="gen_creative", use_container_width=True, help="스키마 기반 창의적 질문을 LLM이 생성합니다"):
        st.session_state.generating_creative = True
        st.rerun()

    st.divider()
    st.markdown("**8️⃣ 쉬운 자연어:**")
    st.caption("초보자용 간단한 질문")

    easy_questions = [
        {"question": "공정 목록 보여줘", "hint": "dim_process 조회"},
        {"question": "주문 현황 알려줘", "hint": "fact_order_daily 조회"},
        {"question": "이번 달 생산 데이터 보여줘", "hint": "fact_production_daily 조회"},
    ]

    for i, eq in enumerate(easy_questions):
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            if st.button(eq["question"], key=f"easy_{i}", use_container_width=True):
                st.session_state.pending_question = eq["question"]
                st.rerun()
        with col2:
            st.markdown(f"<span title='{eq['hint']}' style='cursor:help; font-size:16px;'>💡</span>", unsafe_allow_html=True)

    st.divider()
    st.markdown("**📚 스키마 및 테이블:**")

    # 테이블 메타데이터 정의
    table_metadata = {
        "fact_production_daily": {
            "description": "일자/공정별 생산 실적",
            "columns": [
                ("day", "DATE", "생산 집계 날짜"),
                ("process", "TEXT", "공정 코드 (A~I)"),
                ("produced_qty", "INT", "생산 수량"),
            ]
        },
        "fact_order_daily": {
            "description": "일자/공정/출고상태별 주문 수량",
            "columns": [
                ("day", "DATE", "주문 날짜"),
                ("process", "TEXT", "공정 코드 (A~I)"),
                ("order_status", "TEXT", "'출고 대기' | '출고 완료'"),
                ("ordered_qty", "INT", "주문 수량"),
            ]
        },
        "dim_process": {
            "description": "공정-제품 매핑 테이블",
            "columns": [
                ("process", "TEXT", "공정 코드 (A~I)"),
                ("product", "TEXT", "제품명 (물건1~3)"),
            ]
        },
        "dim_worker": {
            "description": "공정별 작업자 목록 (접근 제한)",
            "columns": [
                ("worker_id", "INT", "작업자 ID"),
                ("process", "TEXT", "공정 코드"),
                ("worker_name", "TEXT", "작업자 이름"),
            ]
        },
    }

    for tbl_name, meta in table_metadata.items():
        with st.expander(f"📋 {tbl_name}"):
            st.caption(meta["description"])
            for col_name, col_type, col_desc in meta["columns"]:
                st.markdown(f"- `{col_name}` ({col_type}): {col_desc}")

            # 자세히 보기 토글
            schema_key = f"schema_{tbl_name}"
            is_open = schema_key in st.session_state.expanded_tables
            btn_text = "접기" if is_open else "🔎 자세히 보기"

            if st.button(btn_text, key=f"btn_schema_{tbl_name}"):
                if is_open:
                    st.session_state.expanded_tables.discard(schema_key)
                else:
                    st.session_state.expanded_tables.add(schema_key)
                st.rerun()

            if is_open:
                data = get_table_data(tbl_name)
                if data.get("rows"):
                    st.dataframe(data["rows"], use_container_width=True, height=200)
                else:
                    st.info("데이터가 없습니다.")

# 창의적 질문 생성 처리
if st.session_state.generating_creative:
    with st.spinner("창의적 질문 생성 중..."):
        st.session_state.creative_questions = generate_creative_questions()
    st.session_state.generating_creative = False
    st.rerun()

# 생성된 창의적 질문 사이드바에 표시
if st.session_state.creative_questions:
    with st.sidebar:
        st.markdown("**생성된 질문:**")
        for i, q in enumerate(st.session_state.creative_questions):
            if st.button(f"🎲 {q[:30]}..." if len(q) > 30 else f"🎲 {q}", key=f"creative_{i}", use_container_width=True):
                st.session_state.pending_question = q
                st.rerun()

# 이전 메시지 표시
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # SQL 결과가 있으면 표시
        if message.get("sql"):
            with st.expander("📝 생성된 SQL"):
                st.code(message["sql"], language="sql")
        if message.get("data"):
            with st.expander(f"📊 결과 ({len(message['data'])}행)"):
                st.dataframe(message["data"], use_container_width=True)

        # 사용된 테이블 확인
        used_tables = message.get("used_tables", [])
        if used_tables:
            with st.expander("🔍 데이터 확인 (사용된 테이블)"):
                for tbl in used_tables:
                    schema = get_table_schema(tbl)
                    if schema:
                        cols = schema.get("columns", [])
                        col_names = [c["name"] for c in cols]
                        st.markdown(f"**{tbl}** - 컬럼: `{', '.join(col_names)}`")

                        table_key = f"hist_{tbl}_{idx}"
                        is_expanded = table_key in st.session_state.expanded_tables
                        btn_label = f"📋 {tbl} 접기" if is_expanded else f"📋 {tbl} 전체 보기"

                        if st.button(btn_label, key=f"btn_{table_key}"):
                            if is_expanded:
                                st.session_state.expanded_tables.discard(table_key)
                            else:
                                st.session_state.expanded_tables.add(table_key)
                            st.rerun()

                        if is_expanded:
                            data = get_table_data(tbl)
                            if data.get("rows"):
                                st.dataframe(data["rows"], use_container_width=True)
                            else:
                                st.info("데이터가 없습니다.")

# pending_question 처리 (예시 질문 클릭 시)
prompt = None
if st.session_state.pending_question:
    prompt = st.session_state.pending_question
    st.session_state.pending_question = None

# 사용자 입력 - 항상 표시 (조건 없이)
user_input = st.chat_input("질문을 입력하세요...")
if not prompt:
    prompt = user_input

if prompt:
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 응답 생성
    with st.chat_message("assistant"):
        with st.spinner("처리 중..."):
            result = unified_chat_api(
                st.session_state.session_id,
                prompt,
                role=user_role
            )

        if "error" in result:
            response_text = f"오류가 발생했습니다: {result['error']}"
            st.error(response_text)
            st.session_state.messages.append({
                "role": "assistant",
                "content": response_text
            })
        else:
            intent = result.get("intent", "")
            answer = result.get("answer")
            sql = result.get("sql")
            rows = result.get("rows", [])
            meta = result.get("meta", {})

            if intent == "data_query":
                # SQL 질의 결과
                if meta.get("ok"):
                    response_text = f"쿼리가 성공적으로 실행되었습니다. ({meta.get('row_count', 0)}행)"
                    st.success(response_text)
                else:
                    response_text = f"쿼리 실행 실패: {meta.get('reason', '알 수 없는 오류')}"
                    st.warning(response_text)

                # SQL 표시
                if sql:
                    with st.expander("📝 생성된 SQL", expanded=True):
                        st.code(sql, language="sql")

                # 결과 테이블 표시
                if rows:
                    with st.expander(f"📊 결과 ({len(rows)}행)", expanded=True):
                        st.dataframe(rows, use_container_width=True)

                # 사용된 테이블 데이터 확인
                used_tables = extract_tables_from_sql(sql)
                if used_tables:
                    with st.expander("🔍 데이터 확인 (사용된 테이블)"):
                        for tbl in used_tables:
                            schema = get_table_schema(tbl)
                            if schema:
                                cols = schema.get("columns", [])
                                col_names = [c["name"] for c in cols]
                                st.markdown(f"**{tbl}** - 컬럼: `{', '.join(col_names)}`")

                                table_key = f"new_{tbl}_{len(st.session_state.messages)}"
                                is_expanded = table_key in st.session_state.expanded_tables
                                btn_label = f"📋 {tbl} 접기" if is_expanded else f"📋 {tbl} 전체 보기"

                                if st.button(btn_label, key=f"btn_{table_key}"):
                                    if is_expanded:
                                        st.session_state.expanded_tables.discard(table_key)
                                    else:
                                        st.session_state.expanded_tables.add(table_key)
                                    st.rerun()

                                if is_expanded:
                                    data = get_table_data(tbl)
                                    if data.get("rows"):
                                        st.dataframe(data["rows"], use_container_width=True)
                                    else:
                                        st.info("데이터가 없습니다.")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_text,
                    "sql": sql,
                    "data": rows,
                    "used_tables": used_tables
                })
            else:
                # greeting 또는 off_topic
                st.markdown(answer)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })

