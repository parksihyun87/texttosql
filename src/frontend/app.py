"""
Text-to-SQL Streamlit Frontend
통합 챗봇 인터페이스
"""
import os
import json
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


# Streamlit 앱 설정
st.set_page_config(
    page_title="Text-to-SQL",
    page_icon="💬",
    layout="wide"
)

st.title("💬 데이터 챗봇")
st.caption("생산/주문 데이터에 대해 자연어로 질문하세요")

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
    st.markdown("**예시 질문:**")
    st.markdown("- 이번 달 총 생산량은?")
    st.markdown("- 최근 주문 현황 알려줘")
    st.markdown("- 공정별 생산량 비교해줘")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = os.urandom(8).hex()

# 이전 메시지 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # SQL 결과가 있으면 표시
        if message.get("sql"):
            with st.expander("📝 생성된 SQL"):
                st.code(message["sql"], language="sql")
        if message.get("data"):
            with st.expander(f"📊 결과 ({len(message['data'])}행)"):
                st.dataframe(message["data"], use_container_width=True)

# 사용자 입력
if prompt := st.chat_input("질문을 입력하세요..."):
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

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_text,
                    "sql": sql,
                    "data": rows
                })
            else:
                # greeting 또는 off_topic
                st.markdown(answer)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })

# 하단 정보
st.divider()
st.caption(f"세션 ID: {st.session_state.session_id} | API: {API_BASE_URL}")
