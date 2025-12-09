import streamlit as st
from datetime import datetime
import time
import pandas as pd
import asyncio

# 외부 라이브러리 (requirements.txt에 포함 필요)
try:
    import saju_engine
    from groq import Groq
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError as e:
    st.error(f"🚨 필수 라이브러리가 설치되지 않았네: {e}")
    st.stop()

# ==========================================
# 0. 설정 및 비밀키 로드 (Config & Secrets)
# ==========================================
st.set_page_config(
    page_title="신령 (Sinryeong)",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# [CSS] 다크모드 대응 및 모바일 최적화 스타일
st.markdown("""
<style>
    /* 전체 배경 및 폰트 */
    .stApp { background-color: #f7f9fc; font-family: 'Noto Sans KR', sans-serif; }
    
    /* 버튼 스타일 */
    div.stButton > button { 
        width: 100%; border-radius: 12px; font-weight: bold; 
        background-color: #4a148c; color: white; border: none;
        padding: 12px 0; margin-top: 10px;
    }
    div.stButton > button:hover { background-color: #7c43bd; color: white; }
    div.stButton > button:disabled { background-color: #cccccc; color: #666666; cursor: not-allowed; }

    /* 보고서 카드 스타일 (가독성 최우선) */
    .report-card { 
        background-color: white !important; 
        padding: 20px; 
        border-radius: 15px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.08); 
        margin-bottom: 20px; 
        border-left: 6px solid #4a148c; 
        color: #333333 !important;
    }
    .report-card h3 { font-size: 1.3rem; margin-bottom: 10px; font-weight: 700; color: #1a1a1a !important; }
    .report-card h4 { font-size: 0.9rem; color: #4a148c !important; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
    .report-card p { font-size: 1rem; line-height: 1.6; color: #444444 !important; white-space: pre-wrap; }
    
    /* Paywall 스타일 */
    .paywall-container {
        border: 2px dashed #ff9800;
        background-color: #fff3e0;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

# Session State 초기화
if 'chat_count' not in st.session_state: st.session_state.chat_count = 0
if 'messages' not in st.session_state: st.session_state.messages = []
if 'report' not in st.session_state: st.session_state.report = None
if 'user_context' not in st.session_state: st.session_state.user_context = ""

# ==========================================
# 1. 백엔드 유틸리티 함수 (Backend Utils)
# ==========================================

@st.cache_data
def load_db_cached():
    """DB 파일 캐싱 로드"""
    return saju_engine.load_all_dbs()

def log_to_google_sheets(data_row):
    """Google Sheets에 사용자 데이터 비동기(흉내) 저장"""
    try:
        # secrets.toml에 google_auth 섹션이 있어야 함
        if "google_auth" not in st.secrets:
            return # 설정 없으면 패스

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = Credentials.from_service_account_info(
            st.secrets["google_auth"], scopes=scopes
        )
        gc = gspread.authorize(credentials)
        # 시트 이름은 secrets에서 관리하거나 고정
        sheet_url = st.secrets["google_auth"].get("sheet_url")
        if sheet_url:
            sh = gc.open_by_url(sheet_url)
            worksheet = sh.sheet1
            worksheet.append_row(data_row)
    except Exception as e:
        # 로깅 실패가 앱을 멈추게 하면 안 됨
        print(f"Logging Error: {e}")

def get_ai_response(user_input, context):
    """Groq API를 활용한 신령 페르소나 응답 생성"""
    system_prompt = f"""
    당신은 '신령'이라는 이름의 AI 도사입니다. 
    아래 제공된 사용자의 사주 분석 보고서를 바탕으로 질문에 답해야 합니다.
    
    [사주 보고서 요약]
    {context}
    
    [지침]
    1. 말투: "~하게나", "~라네", "~보이는구나" 같은 묵직하고 신비로운 하대(Old sage tone)를 유지하시오.
    2. 할루시네이션 방지: 보고서에 없는 구체적인 미래 예언(예: "너는 로또에 당첨된다")은 피하고, 사주 명식의 기운을 바탕으로 조언하시오.
    3. 길이가 너무 길지 않게 핵심만 3~4문장으로 답변하시오.
    """
    
    try:
        if "groq_api_key" not in st.secrets:
            # API 키가 없을 경우 모의 응답 (데모용)
            time.sleep(1)
            return "허허, 내 아직 천기(API Key)를 받지 못해 답변이 어렵구먼. (secrets.toml 설정을 확인하게)"
            
        client = Groq(api_key=st.secrets["groq_api_key"])
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            model="llama3-8b-8192", # 가성비/속도 최적 모델
            temperature=0.7,
            max_tokens=300,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"천기를 읽는 중에 잡음이 생겼네. 다시 물어보게. (Error: {e})"

# DB 로드
db = load_db_cached()

# ==========================================
# 2. 메인 UI 레이아웃 (Layout)
# ==========================================
st.title("🔮 신령 (Sinryeong)")
st.caption("AI 명리학 도사가 풀어주는 나의 운명")

# 탭 구성
tab1, tab2 = st.tabs(["👤 개인 사주", "💞 궁합 분석"])

# --- Tab 1: 개인 사주 입력 ---
with tab1:
    with st.form("personal_form"):
        st.markdown("##### 📝 사주 정보를 입력하게")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("이름", placeholder="예: 홍길동")
            gender = st.selectbox("성별", ["남", "여"])
        with col2:
            birth_date = st.date_input("생년월일", min_value=datetime(1930, 1, 1), max_value=datetime.today())
            birth_time = st.time_input("태어난 시간")
        
        city = st.text_input("태어난 도시 (영문)", placeholder="예: Seoul, Busan, New York")
        st.caption("※ 해외 출생자는 'City, Country' 형식으로 입력하게.")
        
        submit_p = st.form_submit_button("🔮 내 운명 확인하기")
        
        if submit_p:
            if not name or not city:
                st.warning("이름과 태어난 도시는 필수라네.")
            else:
                with st.spinner("천기를 살피고 있네... 잠시 기다리게."):
                    user_data = {
                        "name": name, "gender": gender,
                        "birth_dt": datetime.combine(birth_date, birth_time),
                        "city": city
                    }
                    try:
                        # 1. 엔진 호출
                        report = saju_engine.process_saju_input(user_data, db)
                        
                        # 2. 세션 상태 업데이트
                        st.session_state.report = report
                        st.session_state.messages = [] 
                        st.session_state.chat_count = 0
                        
                        # 3. AI 컨텍스트 생성 (시스템 프롬프트용 요약)
                        context_summary = f"이름: {name}, 일주: {report['saju']['day_gan']}{report['saju']['day_ji']}. "
                        for ana in report['analytics']:
                            context_summary += f"[{ana['type']}] {ana['title']} - {ana['content'][:50]}... "
                        st.session_state.user_context = context_summary
                        
                        # 4. Google Sheets 로깅
                        log_row = [str(datetime.now()), "Personal", name, gender, str(birth_date), str(birth_time), city, report['saju']['day_gan']]
                        log_to_google_sheets(log_row)
                        
                    except Exception as e:
                        st.error(f"운명을 읽는 도중 문제가 생겼네: {e}")

# --- Tab 2: 궁합 분석 입력 ---
with tab2:
    with st.form("love_form"):
        st.markdown("##### 💞 두 사람의 정보를 입력하게")
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("###### 본인 (A)")
            name_a = st.text_input("이름", key="na")
            gender_a = st.selectbox("성별", ["남", "여"], key="ga")
            date_a = st.date_input("생년월일", key="da", min_value=datetime(1930, 1, 1))
            time_a = st.time_input("태어난 시간", key="ta")
            
        with col_b:
            st.markdown("###### 상대방 (B)")
            name_b = st.text_input("이름", key="nb")
            gender_b = st.selectbox("성별", ["남", "여"], index=1, key="gb") # 기본값 반대 성별
            date_b = st.date_input("생년월일", key="db", min_value=datetime(1930, 1, 1))
            time_b = st.time_input("태어난 시간", key="tb")
            
        city_common = st.text_input("주로 활동하는 도시 (영문)", placeholder="예: Seoul", key="cc")
        
        submit_l = st.form_submit_button("💞 궁합 보기")
        
        if submit_l:
            if not name_a or not name_b:
                st.warning("두 사람의 이름은 꼭 필요하네.")
            else:
                with st.spinner("두 인연의 끈을 살피고 있네..."):
                    u_a = {"name": name_a, "gender": gender_a, "birth_dt": datetime.combine(date_a, time_a), "city": city_common}
                    u_b = {"name": name_b, "gender": gender_b, "birth_dt": datetime.combine(date_b, time_b), "city": city_common}
                    
                    try:
                        comp_report = saju_engine.process_love_compatibility(u_a, u_b, db)
                        st.session_state.report = comp_report
                        st.session_state.messages = []
                        st.session_state.chat_count = 0
                        
                        # 컨텍스트 생성
                        st.session_state.user_context = f"궁합 분석. A: {name_a}, B: {name_b}. 결과 요약: {comp_report['analytics'][0]['content']}"
                        
                        # 로깅
                        log_row = [str(datetime.now()), "Compatibility", f"{name_a}&{name_b}", "-", "-", "-", city_common, "Score:CheckReport"]
                        log_to_google_sheets(log_row)
                        
                    except Exception as e:
                        st.error(f"인연을 읽지 못했네: {e}")

# ==========================================
# 3. 결과 보고서 및 채팅 (Report & Chat)
# ==========================================
if st.session_state.report:
    report = st.session_state.report
    is_comp = 'user_a' in report
    
    # 3-1. 보고서 출력 섹션
    st.divider()
    if is_comp:
        header_text = f"📜 {report['user_a']['user']['name']} ❤️ {report['user_b']['user']['name']} 궁합서"
    else:
        header_text = f"📜 {report['user']['name']}님의 사주 분석서"
    
    st.markdown(f"<h2 style='text-align: center; color: #333;'>{header_text}</h2>", unsafe_allow_html=True)
    st.markdown("---")

    # 분석 카드 렌더링
    for item in report['analytics']:
        st.markdown(f"""
        <div class="report-card">
            <h4>{item['type']}</h4>
            <h3>{item['title']}</h3>
            <p>{item['content']}</p>
        </div>
        """, unsafe_allow_html=True)

    # 3-2. AI 채팅 섹션 (Freemium Logic)
    st.markdown("---")
    st.subheader("💬 신령님께 물어보게")
    st.caption("보고서 내용을 바탕으로 무엇이든 물어보세요. (무료 3회)")

    # 채팅 히스토리 출력
    for msg in st.session_state.messages:
        avatar = "🔮" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            
    # 채팅 입력창 제어 (3회 제한)
    MAX_FREE_TURNS = 3
    
    if st.session_state.chat_count >= MAX_FREE_TURNS:
        st.markdown("""
        <div class="paywall-container">
            <h3>🔒 무료 상담 횟수가 끝났네</h3>
            <p>더 깊은 천기를 듣고 싶다면 복채를 내야 해.</p>
        </div>
        """, unsafe_allow_html=True)
        col_pay1, col_pay2 = st.columns(2)
        with col_pay1:
            st.button("☕️ 커피 한 잔 값으로 계속하기", type="primary")
        with col_pay2:
            if st.button("🔄 처음부터 다시 하기"):
                st.session_state.clear()
                st.rerun()
    else:
        # 입력창 활성화
        if prompt := st.chat_input(f"궁금한 점을 입력하세요 ({st.session_state.chat_count}/{MAX_FREE_TURNS}회 사용)"):
            # 사용자 메시지 표시
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            
            # AI 응답 생성
            with st.chat_message("assistant", avatar="🔮"):
                message_placeholder = st.empty()
                full_response = ""
                
                # 로딩 효과 (UX)
                with st.spinner("신령님이 점괘를 뽑고 계십니다..."):
                    ai_response = get_ai_response(prompt, st.session_state.user_context)
                
                # 타이핑 효과 (UX)
                for chunk in ai_response.split():
                    full_response += chunk + " "
                    time.sleep(0.05)
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
                
            # 세션 업데이트
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.session_state.chat_count += 1
            st.rerun() # 카운트 갱신을 위해 리런
