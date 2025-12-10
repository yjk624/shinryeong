import streamlit as st
import pandas as pd
from datetime import datetime
import time
import saju_engine  # V2.1 엔진 임포트

# ==========================================
# 1. 페이지 설정 및 스타일 (CSS)
# ==========================================
st.set_page_config(
    page_title="신령 (Sinryeong)",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# [CSS] 스타일링: 카드 UI, 만세력 테이블, 폰트
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700&display=swap');
    
    .stApp { background-color: #f8f9fa; font-family: 'Noto Serif KR', serif; }
    
    /* 버튼 스타일 */
    div.stButton > button { 
        width: 100%; border-radius: 8px; font-weight: bold; 
        background-color: #5e35b1; color: white; border: none;
        padding: 0.6rem 1rem; transition: all 0.3s;
    }
    div.stButton > button:hover { background-color: #4527a0; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
    
    /* 리포트 카드 스타일 */
    .report-card { 
        background-color: white !important; 
        padding: 25px; 
        border-radius: 12px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); 
        margin-bottom: 20px; 
        border-left: 5px solid #5e35b1; 
    }
    
    .card-type {
        color: #7e57c2; font-size: 0.85rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; display: block;
    }
    
    .card-title {
        color: #2c2c2c; font-size: 1.3rem; font-weight: 700;
        margin-bottom: 15px; border-bottom: 1px solid #f0f0f0; padding-bottom: 10px;
    }
    
    .card-content {
        color: #444; font-size: 1.05rem; line-height: 1.7; white-space: pre-wrap;
    }

    /* 만세력 테이블 스타일 */
    .saju-table {
        width: 100%; text-align: center; border-collapse: collapse; margin-bottom: 1rem;
        background-color: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .saju-table th { background-color: #ede7f6; color: #5e35b1; padding: 10px; font-weight: bold; }
    .saju-table td { padding: 15px; font-size: 1.2rem; font-weight: bold; border-bottom: 1px solid #eee; }
    .gan { color: #333; }
    .ji { color: #555; }
    
    /* 오행 색상 */
    .wood { color: #4CAF50; } .fire { color: #E91E63; } .earth { color: #FFC107; } 
    .metal { color: #9E9E9E; } .water { color: #2196F3; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 세션 상태 및 DB 로딩
# ==========================================
if 'chat_count' not in st.session_state: st.session_state.chat_count = 0
if 'messages' not in st.session_state: st.session_state.messages = []
if 'report' not in st.session_state: st.session_state.report = None

@st.cache_data
def load_db_cached():
    return saju_engine.load_all_dbs()

db = load_db_cached()

# ==========================================
# 3. 헬퍼 함수: 시각화 및 데이터 포맷팅
# ==========================================
def get_oheng_color(char):
    """글자에 따른 오행 색상 클래스 반환"""
    # saju_engine의 OHENG_MAP을 활용하면 좋으나, 간단히 처리
    mapping = saju_engine.OHENG_MAP
    elem = mapping.get(char, '')
    if '목' in elem: return 'wood'
    if '화' in elem: return 'fire'
    if '토' in elem: return 'earth'
    if '금' in elem: return 'metal'
    if '수' in elem: return 'water'
    return ''

def draw_saju_table(saju, name="본인"):
    """만세력 테이블 그리기 (HTML)"""
    html = f"""
    <div style="margin-bottom: 20px;">
        <h4 style="text-align:center; color:#5e35b1;">{name}의 사주 명식</h4>
        <table class="saju-table">
            <thead>
                <tr> <th>시주(말년)</th> <th>일주(중년)</th> <th>월주(청년)</th> <th>연주(초년)</th> </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="gan {get_oheng_color(saju['time_gan'])}">{saju['time_gan']}</td>
                    <td class="gan {get_oheng_color(saju['day_gan'])}">{saju['day_gan']}</td>
                    <td class="gan {get_oheng_color(saju['month_gan'])}">{saju['month_gan']}</td>
                    <td class="gan {get_oheng_color(saju['year_gan'])}">{saju['year_gan']}</td>
                </tr>
                <tr>
                    <td class="ji {get_oheng_color(saju['time_ji'])}">{saju['time_ji']}</td>
                    <td class="ji {get_oheng_color(saju['day_ji'])}">{saju['day_ji']}</td>
                    <td class="ji {get_oheng_color(saju['month_ji'])}">{saju['month_ji']}</td>
                    <td class="ji {get_oheng_color(saju['year_ji'])}">{saju['year_ji']}</td>
                </tr>
            </tbody>
        </table>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# [app.py] draw_stats_charts 함수 수정

def draw_stats_charts(oheng_data, sibseong_data):
    """오행 및 십성 차트 그리기 (V2.2 보강: 산출 근거 추가)"""
    col1, col2 = st.columns(2)
    
    # oheng_data는 이제 {'visual': ..., 'weighted': ...} 구조임
    visual = oheng_data['visual']
    weighted = oheng_data['weighted']
    
    with col1:
        st.caption("📊 오행 분포 (실질 세력)")
        # 그래프는 '가중치 점수(Weighted)'를 기준으로 그리는 것이 정확함 (신령의 추천)
        simple_oheng = {k: v for k, v in weighted.items() if k in ['목', '화', '토', '금', '수']}
        df_oheng = pd.DataFrame.from_dict(simple_oheng, orient='index', columns=['세력(점)'])
        st.bar_chart(df_oheng, color="#7e57c2", height=200)
        
    with col2:
        st.caption("🌟 십성 강약 (성격 패턴)")
        df_sib = pd.DataFrame.from_dict(sibseong_data['group_counts'], orient='index', columns=['점수'])
        st.bar_chart(df_sib, color="#26a69a", height=200)

    # [옥에 티 보완] 산출 근거 설명 (Expander)
    with st.expander("ℹ️ 점수가 왜 이렇게 나왔나요? (산출 근거 보기)"):
        st.markdown("""
        **신령 엔진의 정밀 분석 로직:**
        단순히 글자 개수만 세는 것이 아니라, **지지 속에 숨겨진 기운(지장간)**까지 정밀하게 계산한 '실질 세력' 점수입니다.
        
        * **천간(하늘의 글자):** 1글자당 **1.0점**
        * **지지(땅의 글자):** 글자 속에 숨은 성분(**지장간**)의 비율에 따라 점수가 나뉩니다.
          *(예: 돼지 '해(亥)'는 겉으로는 물이지만, 속에 '무토(흙)'와 '갑목(나무)'을 품고 있어 점수가 분산됩니다.)*
        """)
        
        # 비교 테이블 생성
        st.markdown("###### 🔍 개수 vs 실질 세력 비교")
        
        # 데이터프레임 생성을 위한 데이터 가공
        comparison_data = {
            '오행': ['목', '화', '토', '금', '수'],
            '눈에 보이는 개수 (개)': [visual['목'], visual['화'], visual['토'], visual['금'], visual['수']],
            '실질 세력 점수 (점)': [f"{weighted['목']:.1f}", f"{weighted['화']:.1f}", f"{weighted['토']:.1f}", f"{weighted['금']:.1f}", f"{weighted['수']:.1f}"]
        }
        df_comp = pd.DataFrame(comparison_data)
        st.dataframe(df_comp, hide_index=True, use_container_width=True)
        
        st.caption("※ 실질 세력 점수가 높을수록 해당 오행의 기운이 내 삶에 미치는 영향력이 큽니다.")
# ==========================================
# 4. 메인 UI 구성
# ==========================================
st.title("🔮 신령 (Sinryeong)")
st.markdown("##### 당신의 운명을 꿰뚫어 보는 AI 도사")

tab1, tab2 = st.tabs(["👤 개인 사주 분석", "💞 궁합 분석"])

# --- Tab 1: 개인 사주 ---
with tab1:
    with st.form("personal_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("이름", placeholder="예: 홍길동")
            gender = st.selectbox("성별", ["남", "여"])
        with col2:
            birth_date = st.date_input("생년월일", min_value=datetime(1900, 1, 1), value=datetime(1995, 1, 1))
            birth_time = st.time_input("태어난 시간", value=datetime.now().time())
        
        # 진시간 계산을 위한 도시 입력
        city = st.text_input("태어난 도시 (영문)", placeholder="예: Seoul, Busan, New York", help="정확한 만세력을 위해 태어난 도시가 필요하네.")
        
        submit_p = st.form_submit_button("🔮 내 운명 확인하기")
        
        if submit_p:
            if not name:
                st.warning("이름을 입력하게나.")
            else:
                with st.spinner("신령님이 천기를 살피는 중... (진시간 계산 중)"):
                    user_data = {
                        "name": name, "gender": gender,
                        "birth_dt": datetime.combine(birth_date, birth_time),
                        "city": city if city else "Seoul"
                    }
                    try:
                        report = saju_engine.process_saju_input(user_data, db)
                        st.session_state.report = report
                        st.session_state.messages = [] 
                        st.session_state.chat_count = 0
                    except Exception as e:
                        st.error(f"분석 중 오류가 발생했네. 도시 이름을 영문으로 정확히 적었는지 확인하게: {e}")

# --- Tab 2: 궁합 분석 ---
with tab2:
    st.info("💞 두 사람의 태어난 곳과 시간을 정확히 입력해야 진정한 궁합이 나오네.")
    with st.form("love_form"):
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("###### 본인 (A)")
            name_a = st.text_input("이름", key="na")
            date_a = st.date_input("생일", key="da", value=datetime(1990, 1, 1))
            time_a = st.time_input("시간", key="ta")
            city_a = st.text_input("도시 (영문)", key="ca", placeholder="Seoul")
            
        with col_b:
            st.markdown("###### 상대방 (B)")
            name_b = st.text_input("이름", key="nb")
            date_b = st.date_input("생일", key="db", value=datetime(1992, 1, 1))
            time_b = st.time_input("시간", key="tb")
            city_b = st.text_input("도시 (영문)", key="cb", placeholder="Seoul")
            
        submit_l = st.form_submit_button("💞 궁합 보기")
        
        if submit_l:
            if not name_a or not name_b:
                st.warning("두 사람의 이름은 필수라네.")
            else:
                with st.spinner("두 사람의 인연을 엮어보는 중..."):
                    u_a = {"name": name_a, "gender": "?", "birth_dt": datetime.combine(date_a, time_a), "city": city_a if city_a else "Seoul"}
                    u_b = {"name": name_b, "gender": "?", "birth_dt": datetime.combine(date_b, time_b), "city": city_b if city_b else "Seoul"}
                    try:
                        comp_report = saju_engine.process_love_compatibility(u_a, u_b, db)
                        st.session_state.report = comp_report
                        st.session_state.messages = []
                        st.session_state.chat_count = 0
                    except Exception as e:
                        st.error(f"계산 중 실수가 있었구먼: {e}")

# ==========================================
# 5. 결과 리포트 렌더링
# ==========================================
if st.session_state.report:
    report = st.session_state.report
    is_comp = 'user_a' in report 
    
    st.divider()
    
    # 5-1. 헤더 및 대시보드 (Visuals)
    if is_comp:
        # 궁합 대시보드
        st.subheader(f"💞 {report['user_a']['user']['name']} & {report['user_b']['user']['name']}의 인연")
        col1, col2 = st.columns(2)
        with col1:
            draw_saju_table(report['user_a']['saju'], report['user_a']['user']['name'])
        with col2:
            draw_saju_table(report['user_b']['saju'], report['user_b']['user']['name'])
            
    else:
        # 개인 분석 대시보드
        true_time_str = report['true_dt'].strftime('%Y년 %m월 %d일 %H시 %M분')
        st.subheader(f"📜 {report['user']['name']}님의 사주 분석서")
        st.caption(f"📍 적용된 진(眞) 시간: {true_time_str} ({report['user']['city']})")
        
        draw_saju_table(report['saju'])
        draw_stats_charts(report['oheng_counts'], report['sibseong_data'])
    
    st.divider()

    # 5-2. 분석 카드 (Analytics Cards)
    for item in report['analytics']:
        # 아이콘 매핑
        icon = ""
        if item['type'] == 'INTRO': icon = "🔮"
        elif item['type'] == 'IDENTITY': icon = "👤"
        elif item['type'] == 'HEALTH': icon = "☔"
        elif item['type'] == 'CAREER': icon = "💼"
        elif item['type'] == 'LOVE': icon = "💖"
        elif item['type'] == 'RESULT': icon = "🏆"
        
        st.markdown(f"""
        <div class="report-card">
            <span class="card-type">{icon} {item['type']} ANALYSIS</span>
            <div class="card-title">{item['title']}</div>
            <div class="card-content">{item['content']}</div>
        </div>
        """, unsafe_allow_html=True)

    # 5-3. 챗봇 (Interactive Chat)
    st.divider()
    st.markdown("### 💬 신령님에게 물어보게")
    
    # 채팅 기록 표시
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # 입력 제한 (3회)
    if st.session_state.chat_count >= 3:
        st.info("🔒 오늘은 여기까지. 더 깊은 천기는 복채(구독)가 필요하네.")
    else:
        if prompt := st.chat_input("재물운이 어떤가요? 조심할 점은 무엇인가요?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
                
            with st.chat_message("assistant"):
                msg_placeholder = st.empty()
                full_response = ""
                
                # [Context-Aware Dummy Chatbot]
                # 실제 LLM 연결 전, 리포트 내용을 기반으로 한 간단한 키워드 매칭 응답
                context_response = "음, 그건 내 전문이지. "
                prompt_lower = prompt.lower()
                
                if "돈" in prompt or "재물" in prompt:
                    context_response = "자네 사주의 재성(Money)을 보니 욕심을 부리면 탈이 나겠어. 위에 적힌 '직업 및 적성'을 다시 정독하게."
                elif "연애" in prompt or "결혼" in prompt or "여자" in prompt or "남자" in prompt:
                    context_response = "사랑은 흐르는 물과 같네. 억지로 잡으려 하지 말고, '연애 심리' 파트의 조언대로 하게나."
                elif "건강" in prompt:
                    context_response = "몸이 곧 자산이네. '건강 진단'에서 말한 색깔의 옷을 자주 입게."
                else:
                    context_response = "허허, 천기누설은 함부로 하는 게 아니네. 하지만 자네의 운세는 자네 마음먹기에 달렸다는 걸 잊지 말게."

                # 타이핑 효과
                for chunk in context_response.split():
                    full_response += chunk + " "
                    time.sleep(0.05)
                    msg_placeholder.markdown(full_response + "▌")
                msg_placeholder.markdown(full_response)
                
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.session_state.chat_count += 1
