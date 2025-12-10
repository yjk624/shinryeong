import streamlit as st
from datetime import datetime
import time
import pandas as pd
try:
    import saju_engine
except ImportError:
    st.error("🚨 'saju_engine.py' 파일을 찾을 수 없습니다.")
    st.stop()

st.set_page_config(
    page_title="신령 (Sinryeong)",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# [강력한 CSS 수정] 테마 관계없이 카드 내부 글씨 검은색 고정
st.markdown("""
<style>
    .stApp { background-color: #f7f9fc; font-family: 'Noto Sans KR', sans-serif; }
    div.stButton > button { width: 100%; border-radius: 12px; font-weight: bold; background-color: #4a148c; color: white; }
    
    .report-card { 
        background-color: white !important; 
        padding: 20px; 
        border-radius: 15px; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.05); 
        margin-bottom: 15px; 
        border-left: 5px solid #4a148c; 
    }
    
    /* 카드 내부의 모든 텍스트 요소를 강제로 검은색으로 지정 (다크모드 방지) */
    .report-card h1, .report-card h2, .report-card h3, 
    .report-card h4, .report-card p, .report-card span, .report-card div {
        color: #333333 !important;
    }
    
    .highlight { color: #4a148c !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if 'chat_count' not in st.session_state: st.session_state.chat_count = 0
if 'messages' not in st.session_state: st.session_state.messages = []
if 'report' not in st.session_state: st.session_state.report = None

@st.cache_data
def load_db_cached():
    return saju_engine.load_all_dbs()

db = load_db_cached()

st.title("🔮 신령 (Sinryeong)")
st.markdown("##### 당신의 운명을 읽어주는 AI 도사")

tab1, tab2 = st.tabs(["👤 개인 분석", "💞 궁합 분석"])

with tab1:
    with st.form("personal_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("이름", placeholder="예: 홍길동")
            gender = st.selectbox("성별", ["남", "여"])
        with col2:
            birth_date = st.date_input("생년월일", min_value=datetime(1900, 1, 1))
            birth_time = st.time_input("태어난 시간")
        
        city = st.text_input("태어난 도시 (영문)", placeholder="예: Seoul, Busan")
        submit_p = st.form_submit_button("🔮 내 운명 확인하기")
        
        if submit_p:
            if not name or not city:
                st.warning("이름과 도시는 필수라네.")
            else:
                with st.spinner("신령님이 천기를 살피는 중..."):
                    user_data = {
                        "name": name, "gender": gender,
                        "birth_dt": datetime.combine(birth_date, birth_time),
                        "city": city
                    }
                    try:
                        report = saju_engine.process_saju_input(user_data, db)
                        st.session_state.report = report
                        st.session_state.messages = [] 
                        st.session_state.chat_count = 0
                    except Exception as e:
                        st.error(f"분석 중 오류가 발생했네: {e}")

with tab2:
    st.info("💞 궁합 분석은 두 사람의 생년월일이 필요하네.")
    with st.form("love_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**본인 (A)**")
            name_a = st.text_input("이름(A)")
            date_a = st.date_input("생일(A)", key="da")
        with col_b:
            st.markdown("**상대방 (B)**")
            name_b = st.text_input("이름(B)")
            date_b = st.date_input("생일(B)", key="db")
            
        submit_l = st.form_submit_button("💞 궁합 보기")
        
        if submit_l:
            u_a = {"name": name_a, "gender": "여", "birth_dt": datetime.combine(date_a, datetime.min.time()), "city": "Seoul"}
            u_b = {"name": name_b, "gender": "남", "birth_dt": datetime.combine(date_b, datetime.min.time()), "city": "Seoul"}
            try:
                comp_report = saju_engine.process_love_compatibility(u_a, u_b, db)
                st.session_state.report = comp_report
                st.session_state.messages = []
                st.session_state.chat_count = 0
            except Exception as e:
                st.error(f"오류가 났구먼: {e}")

if st.session_state.report:
    report = st.session_state.report
    is_comp = 'user_a' in report 
    
    st.divider()
    if is_comp:
        st.subheader(f"📜 {report['user_a']['user']['name']} ❤️ {report['user_b']['user']['name']} 궁합서")
    else:
        st.subheader(f"📜 {report['user']['name']}님의 사주 분석서")

    for item in report['analytics']:
        st.markdown(f"""
        <div class="report-card">
            <h4 class="highlight">{item['type']}</h4>
            <h3>{item['title']}</h3>
            <p style="white-space: pre-wrap;">{item['content']}</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown("### 💬 신령님과의 대화")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if st.session_state.chat_count >= 3:
        st.warning("🔒 무료 질문 횟수가 끝났네. 복채(구독)를 내면 더 깊은 이야기를 해주지.")
    else:
        if prompt := st.chat_input("궁금한 것을 물어보게..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
                
            with st.chat_message("assistant"):
                msg_placeholder = st.empty()
                full_response = ""
                dummy_ans = f"허허, '{prompt}'라... 자네 사주에 따르면 지금은 때가 아니야. 조금 더 기다리면 길이 보일 걸세."
                for chunk in dummy_ans.split():
                    full_response += chunk + " "
                    time.sleep(0.05)
                    msg_placeholder.markdown(full_response + "▌")
                msg_placeholder.markdown(full_response)
                
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.session_state.chat_count += 1
