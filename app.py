import streamlit as st
import pandas as pd
from datetime import datetime
import time
import json
import os

# Google Sheets & Groq API (Secrets에서 로드)
# import gspread
# from google.oauth2.service_account import Credentials
# from groq import Groq

# [핵심] 사주 엔진 로드
try:
    import saju_engine
except ImportError:
    st.error("🚨 'saju_engine.py' 파일이 없거나 로드할 수 없습니다. 같은 폴더에 위치해 있는지 확인해주세요.")
    st.stop()

# ==========================================
# 1. 설정 및 초기화 (Configuration)
# ==========================================

st.set_page_config(
    page_title="신령 (Sinryeong)",
    page_icon="🔮",
    layout="centered", # 모바일 친화적 중앙 정렬
    initial_sidebar_state="collapsed"
)

# CSS Injection for Mobile-First & Card UI
st.markdown("""
<style>
    /* 전체 배경 및 폰트 */
    .stApp {
        background-color: #f0f2f6;
        font-family: 'Noto Sans KR', sans-serif;
    }
    /* 카드 UI 스타일 */
    .css-1r6slb0, .css-12oz5g7 { 
        background-color: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #ffffff;
        border-radius: 10px 10px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e0f7fa;
        color: #006064;
        font-weight: bold;
    }
    /* 채팅 메시지 스타일 */
    .stChatMessage {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    /* 버튼 스타일 */
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        background-color: #00838f;
        color: white;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Session State 초기화
if 'step' not in st.session_state: st.session_state.step = 0 # 0:입력, 1:결과, 2:채팅
if 'chat_count' not in st.session_state: st.session_state.chat_count = 0
if 'messages' not in st.session_state: st.session_state.messages = []
if 'report_data' not in st.session_state: st.session_state.report_data = None
if 'user_lang' not in st.session_state: st.session_state.user_lang = 'ko'

# DB 로드 (캐싱 적용)
@st.cache_data
def load_databases():
    return saju_engine.load_all_dbs()

# Google Sheets 로깅 함수 (비동기 처리는 Streamlit 특성상 어려우므로 try-except로 가볍게 처리)
def log_to_google_sheets(data):
    """
    Secrets에 설정된 구글 인증 정보를 사용하여 데이터를 시트에 추가합니다.
    st.secrets["google_auth"] 및 st.secrets["sheet_url"] 필요.
    """
    # [TODO] 실제 배포 시 주석 해제 및 secrets 설정 필요
    # try:
    #     credentials = Credentials.from_service_account_info(
    #         st.secrets["google_auth"],
    #         scopes=["https://www.googleapis.com/auth/spreadsheets"]
    #     )
    #     gc = gspread.authorize(credentials)
    #     sh = gc.open_by_url(st.secrets["sheet_url"])
    #     worksheet = sh.sheet1
    #     worksheet.append_row(data)
    # except Exception as e:
    #     print(f"Logging Error: {e}") # 사용자에게는 에러를 보이지 않음
    pass

# ==========================================
# 2. UI 구성 (User Interface)
# ==========================================

st.title("🔮 신령 (Sinryeong)")
st.markdown("### 당신의 운명을 읽어주는 AI 도사")

# 탭 구성: 개인 분석 / 궁합 분석
tab1, tab2 = st.tabs(["👤 개인 사주 분석", "💞 궁합 분석"])

# --- [Tab 1] 개인 사주 분석 ---
with tab1:
    with st.form("personal_form"):
        st.subheader("사주 정보 입력")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("이름", placeholder="예: 홍길동")
            gender = st.selectbox("성별", ["남", "여"])
        with col2:
            birth_date = st.date_input("생년월일", min_value=datetime(1900, 1, 1))
            birth_time = st.time_input("태어난 시간")
            
        city = st.text_input("태어난 도시 (예: Seoul, Busan)", placeholder="도시 이름 (영어 권장)")
        
        submitted = st.form_submit_button("🔮 운세 보기")
        
        if submitted:
            if not name or not city:
                st.error("이름과 태어난 도시는 필수 입력 사항입니다.")
            else:
                # 로딩 애니메이션
                with st.spinner('신령님이 천기를 살피고 계십니다...'):
                    # 1. 입력 데이터 가공
                    birth_dt = datetime.combine(birth_date, birth_time)
                    user_data = {
                        "name": name,
                        "gender": gender,
                        "birth_dt": birth_dt,
                        "city": city
                    }
                    
                    # 2. 사주 엔진 호출
                    db = load_databases()
                    try:
                        report = saju_engine.process_saju_input(user_data, db)
                        st.session_state.report_data = report
                        st.session_state.step = 1 # 결과 화면으로 전환
                        st.session_state.chat_count = 0 # 채팅 카운트 초기화
                        st.session_state.messages = [] # 채팅 기록 초기화
                        
                        # [TODO] 로그 저장
                        # log_to_google_sheets([str(datetime.now()), "Personal", name, city])
                        
                    except Exception as e:
                        st.error(f"분석 중 오류가 발생했습니다: {e}")

# --- [Tab 2] 궁합 분석 ---
with tab2:
    st.info("💞 궁합 분석 기능은 준비 중입니다. (업데이트 예정)")
    # [TODO] 궁합 분석 폼 구현 (유저 A, B 입력 받기 -> process_love_compatibility 호출)


# ==========================================
# 3. 결과 리포트 및 채팅 (Result & Chat)
# ==========================================

if st.session_state.step >= 1 and st.session_state.report_data:
    report = st.session_state.report_data
    
    st.divider()
    st.header(f"📜 {report['user']['name']}님의 사주 분석서")
    
    # 3-1. 핵심 분석 결과 출력 (카드 형태)
    for analysis in report['analytics']:
        with st.expander(f"{analysis['type']} - {analysis['title']}", expanded=True):
            st.markdown(analysis['content'])
            
    st.divider()
    
    # 3-2. AI 신령님과의 채팅 (Freemium)
    st.subheader("💬 신령님께 물어보세요")
    
    # 채팅 기록 표시
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # 채팅 입력
    if prompt := st.chat_input("궁금한 점을 물어보게. (예: 제 재물운은 언제 풀리나요?)"):
        # 무료 질문 횟수 제한 체크
        if st.session_state.chat_count >= 3:
            st.warning("🔒 무료 질문 횟수가 끝났네. 더 깊은 대화는 복채(구독)가 필요해.")
            st.button("복채 내고 계속하기 (준비 중)", disabled=True)
        else:
            # 사용자 메시지 추가
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
                
            # AI 응답 생성 (Groq API 연동 시뮬레이션)
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                
                # [TODO] 실제 Groq API 호출 로직
                # client = Groq(api_key=st.secrets["groq_api_key"])
                # ... (System Prompt에 report 내용 주입)
                
                # 더미 응답 (테스트용)
                dummy_response = f"허허, 자네의 사주를 보니 '{prompt}'에 대한 답은 명확하네. 자네는 {report['saju']['day_gan']}일간이라..."
                
                # 타이핑 효과
                for chunk in dummy_response.split():
                    full_response += chunk + " "
                    time.sleep(0.05)
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
                
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.session_state.chat_count += 1
