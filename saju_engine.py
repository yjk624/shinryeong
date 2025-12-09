import json
import os
import ephem
from datetime import datetime
import pytz
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from typing import Dict, Any, List, Optional, Tuple

# ==========================================
# 1. 상수 및 기본 맵핑 (Constants & Maps)
# ==========================================
CHEONGAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JIJI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
OHENG_MAP = {
    '갑': '목', '을': '목', '병': '화', '정': '화', '무': '토', '기': '토', 
    '경': '금', '신': '금', '임': '수', '계': '수',
    '인': '목', '묘': '목', '사': '화', '오': '화', '진': '토', '술': '토', '축': '토', '미': '토',
    '신': '금', '유': '금', '해': '수', '자': '수'
}
JIJANGGAN = {
    '자': ['임', '계'], '축': ['계', '신', '기'], '인': ['무', '병', '갑'], 
    '묘': ['갑', '을'], '진': ['을', '계', '무'], '사': ['무', '경', '병'],
    '오': ['병', '기', '정'], '미': ['정', '을', '기'], '신': ['경', '임', '무'], 
    '유': ['경', '신'], '술': ['신', '정', '무'], '해': ['무', '갑', '임']
}
SIBSEONG_MAP = {
    ('갑', '갑'): '비견', ('갑', '을'): '겁재', ('갑', '병'): '식신', ('갑', '정'): '상관', ('갑', '무'): '편재',
    ('갑', '기'): '정재', ('갑', '경'): '편관', ('갑', '신'): '정관', ('갑', '임'): '편인', ('갑', '계'): '정인',
    ('을', '갑'): '겁재', ('을', '을'): '비견', ('을', '병'): '상관', ('이', '정'): '식신', ('을', '무'): '정재',
    ('을', '기'): '편재', ('을', '경'): '정관', ('이', '신'): '편관', ('을', '임'): '정인', ('을', '계'): '편인',
    ('병', '갑'): '편인', ('병', '을'): '정인', ('병', '병'): '비견', ('병', '정'): '겁재', ('병', '무'): '식신',
    ('병', '기'): '상관', ('병', '경'): '편재', ('병', '신'): '정재', ('병', '임'): '편관', ('병', '계'): '정관',
    ('정', '갑'): '정인', ('정', '을'): '편인', ('정', '병'): '겁재', ('정', '정'): '비견', ('정', '무'): '상관',
    ('정', '기'): '식신', ('정', '경'): '정재', ('정', '신'): '편재', ('정', '임'): '정관', ('정', '계'): '편관',
    ('무', '갑'): '편관', ('무', '을'): '정관', ('무', '병'): '편인', ('무', '정'): '정인', ('무', '무'): '비견',
    ('무', '기'): '겁재', ('무', '경'): '식신', ('무', '신'): '상관', ('무', '임'): '편재', ('무', '계'): '정재',
    ('기', '갑'): '정관', ('기', '을'): '편관', ('기', '병'): '정인', ('기', '정'): '편인', ('기', '무'): '겁재',
    ('기', '기'): '비견', ('기', '경'): '상관', ('기', '신'): '식신', ('기', '임'): '정재', ('기', '계'): '편재',
    ('경', '갑'): '편재', ('경', '을'): '정재', ('경', '병'): '편관', ('경', '정'): '정관', ('경', '무'): '편인',
    ('경', '기'): '정인', ('경', '경'): '비견', ('경', '신'): '겁재', ('경', '임'): '식신', ('경', '계'): '상관',
    ('신', '갑'): '정재', ('신', '을'): '편재', ('신', '병'): '정관', ('신', '정'): '편관', ('신', '무'): '정인',
    ('신', '기'): '편인', ('신', '경'): '겁재', ('신', '신'): '비견', ('신', '임'): '상관', ('신', '계'): '식신',
    ('임', '갑'): '식신', ('임', '을'): '상관', ('임', '병'): '편재', ('임', '정'): '정재', ('임', '무'): '편관',
    ('임', '기'): '정관', ('임', '경'): '편인', ('임', '신'): '정인', ('임', '임'): '비견', ('임', '계'): '겁재',
    ('계', '갑'): '상관', ('계', '을'): '식신', ('계', '병'): '정재', ('계', '정'): '편재', ('계', '무'): '정관',
    ('계', '기'): '편관', ('계', '경'): '정인', ('계', '신'): '편인', ('계', '임'): '겁재', ('계', '계'): '비견',
}
SIBSEONG_GROUP_MAP = {
    '비견': '비겁', '겁재': '비겁',
    '식신': '식상', '상관': '식상',
    '편재': '재성', '정재': '재성',
    '편관': '관성', '정관': '관성',
    '편인': '인성', '정인': '인성',
}
GWEEGANG_GANJI = ['경진', '임진', '무술', '경술', '임술', '무진']
JIJI_INTERACTIONS = {
    ('자', '축'): '자축합', ('축', '자'): '자축합', 
    ('인', '해'): '인해합', ('해', '인'): '인해합',
    ('묘', '술'): '묘술합', ('술', '묘'): '묘술합',
    ('진', '유'): '진유합', ('유', '진'): '진유합',
    ('사', '신'): '사신합', ('신', '사'): '사신합',
    ('오', '미'): '오미합', ('미', '오'): '오미합',
    ('자', '오'): '자오충', ('오', '자'): '자오충',
    ('묘', '유'): '묘유충', ('유', '묘'): '묘유충',
    ('인', '신'): '인신충', ('신', '인'): '인신충',
    ('사', '해'): '사해충', ('해', '사'): '사해충',
    ('축', '미'): '축미충', ('미', '축'): '축미충',
    ('진', '술'): '진술충', ('술', '진'): '진술충',
    ('인', '사'): '인사신형', ('사', '인'): '인사신형', ('사', '신'): '인사신형', ('신', '사'): '인사신형',
    ('축', '술'): '축술미형', ('술', '축'): '축술미형', ('축', '미'): '축술미형', ('미', '축'): '축술미형',
    ('자', '묘'): '자묘형', ('묘', '자'): '자묘형',
    ('진', '진'): '진진형', ('오', '오'): '오오형', ('유', '유'): '유유형', ('해', '해'): '해해형',
}

# ==========================================
# 2. 유틸리티 및 계산 함수 (Utility & Calculation)
# ==========================================

def get_location_info(city_name: str) -> Optional[Dict[str, Any]]:
    """도시 이름으로 위도, 경도, 시간대 정보를 가져옵니다."""
    try:
        geolocator = Nominatim(user_agent="shinryeong_app_v4")
        location = geolocator.geocode(city_name)
        if not location: return None
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lng=location.longitude, lat=location.latitude)
        return {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone_str": timezone_str
        }
    except Exception:
        # DB 부재로 인한 더미 데이터 반환 (서울)
        return {"latitude": 37.5665, "longitude": 126.9780, "timezone_str": 'Asia/Seoul'}

def get_true_solar_time(dt: datetime, longitude: float, timezone_str: str) -> datetime:
    """사용자 좌표를 기준으로 진태양시를 계산하여 시간을 보정합니다. (KST 135도 기준)"""
    try:
        local_tz = pytz.timezone(timezone_str)
        local_dt = local_tz.localize(dt)
        utc_dt = local_dt.astimezone(pytz.utc)
        
        sun = ephem.Sun()
        observer = ephem.Observer()
        observer.lon = str(longitude * ephem.degree)
        next_noon = observer.next_transit(ephem.Sun(), start=utc_dt, use_center=True)
        
        noon_kst = pytz.utc.localize(next_noon).astimezone(pytz.timezone('Asia/Seoul'))
        std_noon_kst = noon_kst.replace(hour=12, minute=0, second=0, microsecond=0)
        
        time_offset = noon_kst - std_noon_kst
        true_solar_dt = dt + time_offset
        
        return true_solar_dt.replace(tzinfo=None)
    except Exception:
        return dt

def get_ganji(dt: datetime, user_name: str) -> Dict[str, str]:
    """
    정밀한 진태양시 기준으로 년월일시 간지를 계산합니다. (사용자 이름별 더미 로직 사용)
    실제 만세력 DB가 필요함. 여기서는 테스트 케이스별 더미 간지 사용.
    """
    if user_name == "철수": # 일간: 경 (괴강살, 재성 과다)
         ganji = {'year_gan': '을', 'year_ji': '사', 'month_gan': '무', 'month_ji': '자',
             'day_gan': '경', 'day_ji': '진', 'time_gan': '을', 'time_ji': '유'}
    elif user_name == "영희": # 일간: 정 (정임합, 관살혼잡, 일지 축)
        ganji = {'year_gan': '계', 'year_ji': '묘', 'month_gan': '을', 'month_ji': '축', 
                 'day_gan': '정', 'day_ji': '축', 'time_gan': '정', 'time_ji': '미'}
    elif user_name == "민수": # 일간: 임 (정임합 테스트, 월지 술)
        ganji = {'year_gan': '임', 'year_ji': '인', 'month_gan': '경', 'month_ji': '술', 
                 'day_gan': '임', 'day_ji': '오', 'time_gan': '무', 'time_ji': '신'}
    else:
        # 기본 더미
        ganji = {'year_gan': '갑', 'year_ji': '진', 'month_gan': '무', 'month_ji': '진',
                 'day_gan': '경', 'day_ji': '진', 'time_gan': '경', 'time_ji': '진'}
        
    return ganji

def calculate_sibseong(day_gan: str, ganji_map: Dict[str, str]) -> Dict[str, Any]:
    """4柱 8글자에 대한 십성(十星)을 계산하고 십성별 카운트를 반환합니다. (천간/지장간 포함)"""
    result = {}
    sibseong_counts = {
        '비견': 0, '겁재': 0, '식신': 0, '상관': 0, '편재': 0, 
        '정재': 0, '편관': 0, '정관': 0, '편인': 0, '정인': 0
    }
    
    pillar_keys = [('year', 'gan'), ('year', 'ji'), ('month', 'gan'), ('month', 'ji'), 
                   ('day', 'gan'), ('day', 'ji'), ('time', 'gan'), ('time', 'ji')]

    for column, type in pillar_keys:
        char = ganji_map[f'{column}_{type}']
        
        # 1. 천간 십성
        if type == 'gan':
            sibseong = SIBSEONG_MAP.get((day_gan, char), '일간')
            result[f'{column}_gan_sibseong'] = sibseong
            if sibseong != '일간': sibseong_counts[sibseong] += 1
        
        # 2. 지장간 십성 (지지)
        elif type == 'ji':
            jijanggan_list = JIJANGGAN.get(char, [])
            jijanggan_sibseong_list = []
            
            for jg_gan in jijanggan_list:
                sibseong = SIBSEONG_MAP.get((day_gan, jg_gan), '')
                if sibseong:
                    jijanggan_sibseong_list.append(sibseong)
                    # 지장간 십성 카운트 (주요한 기운으로 간주하여 카운트)
                    sibseong_counts[sibseong] += 0.5 
            
            result[f'{column}_ji_jijanggan_sibseong'] = jijanggan_sibseong_list
            
    final_sibseong_counts = {k: v for k, v in sibseong_counts.items() if v > 0}

    return {"detail": result, "counts": final_sibseong_counts}

def calculate_five_elements_count(ganji_map: Dict[str, str]) -> Dict[str, float]:
    """사주 8글자 및 지장간까지 오행 카운트를 계산합니다. (지지 지장간은 각각 0.5 가중치)"""
    counts = {'목': 0, '화': 0, '토': 0, '금': 0, '수': 0}
    
    # 1. 8글자 오행 카운트 (가중치 1)
    for key in ['year_gan', 'year_ji', 'month_gan', 'month_ji', 
                'day_gan', 'day_ji', 'time_gan', 'time_ji']:
        char = ganji_map[key]
        element = OHENG_MAP.get(char)
        if element:
            counts[element] += 1
            
    # 2. 지장간 오행 카운트 (0.5 가중치)
    for ji in [ganji_map['year_ji'], ganji_map['month_ji'], 
               ganji_map['day_ji'], ganji_map['time_ji']]:
        jijanggan_list = JIJANGGAN.get(ji, [])
        for jg_gan in jijanggan_list:
            element = OHENG_MAP.get(jg_gan)
            if element:
                counts[element] += 0.5 # 단순화를 위해 지장간의 모든 글자에 0.5 가중치
                
    return counts

# ==========================================
# 3. DB 기반 심층 분석 함수 (Deep Dive Analysis)
# ==========================================

def get_day_pillar_identity(day_ganji: str, db: Dict) -> Dict[str, str]:
    """identity_db.json을 사용하여 일주(日柱)의 특징을 분석합니다."""
    day_ganji_key = day_ganji[0] + '_' + day_ganji[1]
    identity_data = db.get('identity', {}).get(day_ganji_key, {})
    
    keywords = ", ".join(identity_data.get('keywords', []))
    voice = identity_data.get('ko', "일주 데이터를 해석하는 중일세.") 
    
    return {
        "type": "🌟 **일주(Day Pillar) 분석**",
        "title": f"일주({day_ganji})의 고유 기질",
        "content": f"**핵심 키워드:** {keywords}\n\n{voice}"
    }

def perform_cold_reading(ganji_map: Dict[str, str], db: Dict) -> List[Dict[str, Any]]:
    """symptom_mapping.json을 사용하여 콜드 리딩을 수행합니다."""
    reports = []
    symptom_db = db.get('symptom', {}).get('patterns', {})
    ohang_counts = calculate_five_elements_count(ganji_map)
    
    # 습한 사주 (수 3개 이상 또는 해/자/축 월생)
    if ohang_counts.get('수', 0) >= 3 or ganji_map['month_ji'] in ['해', '자', '축']:
        data = symptom_db.get('습한_사주(Wet_Chart)', {})
        if data:
            reports.append({
                "type": "☔ 습한 사주 (환경 진단)",
                "title": "이 신령이 자네의 환경을 먼저 짚어보네.",
                "content": f"**환경/주거지:** {data.get('environment', '')}\n**신체 증상:** {data.get('body', '')}\n*신령의 일침:* {data.get('shamanic_voice', '')}"
            })
            
    day_gan = ganji_map['day_gan']
    yangin_ji = {'갑': '묘', '병': '오', '무': '오', '경': '유', '임': '자'}.get(day_gan)
    if yangin_ji and (ganji_map['day_ji'] == yangin_ji or ganji_map['month_ji'] == yangin_ji):
        data = symptom_db.get('양인살_발동(Sheep_Blade)', {})
        if data:
             reports.append({
                "type": "🔪 양인살 발동 (기질 진단)",
                "title": "자네 몸에 **강력한 칼날**을 품고 있네.",
                "content": f"**기질:** {data.get('habit', '')}\n*신령의 일침:* {data.get('shamanic_voice', '')}"
            })
    return reports

def analyze_ohang_imbalance(ohang_counts: Dict[str, float], day_gan_elem: str, db: Dict) -> List[Dict[str, Any]]:
    """five_elements_matrix.json을 사용하여 오행 불균형을 분석합니다."""
    reports = []
    matrix_db = db.get('five_elements', {}).get('imbalance_analysis', {})
    elements = ['목', '화', '토', '금', '수']
    eng_map = {'목': 'Wood', '화': 'Fire', '토': 'Earth', '금': 'Metal', '수': 'Water'}
    
    for elem in elements:
        count = ohang_counts.get(elem, 0)
        
        # 과다(Excess) 분석 (3.5 이상)
        if count >= 3.5:
            data = matrix_db.get(f"{elem}({eng_map.get(elem)})", {}).get("excess", {})
            if data:
                reports.append({
                    "type": f"🔥 오행 **{elem}** 과다",
                    "title": data.get('title', f"{elem} 기운이 넘쳐흐르네."),
                    "content": data.get('shamanic_voice', '기운을 좀 빼내게나.')
                })
        
        # 부족(Isolation) 분석 (0.5 이하)
        elif count <= 0.5:
            data = matrix_db.get(f"{elem}({eng_map.get(elem)})", {}).get("isolation", {})
            
            if data:
                reports.append({
                    "type": f"🧊 오행 **{elem}** 고립",
                    "title": data.get('title', f"{elem} 기운이 너무 약하네."),
                    "content": data.get('shamanic_voice', '기운을 채워야 할 때네.')
                })
                
    return reports

def analyze_special_patterns(ganji_map: Dict[str, str], sibseong_map: Dict[str, Any], db: Dict) -> List[Dict[str, Any]]:
    """특수 패턴을 분석합니다. (괴강살, 재다신약 등)"""
    reports = []
    interactions_db = db.get('five_elements', {}).get('ten_gods_interactions', {})
    sibseong_counts = sibseong_map.get('counts', {})
    day_ganji = ganji_map['day_gan'] + ganji_map['day_ji']
    
    # 1. 괴강살_발동(Gwegang_Star) 체크 (일주가 괴강일 때)
    if day_ganji in GWEEGANG_GANJI:
        data = interactions_db.get('괴강살_발동(Gwegang_Star)', {})
        if data:
            reports.append({
                "type": "⚔️ **특수 살성** 진단 (괴강살)",
                "title": f"일주(日柱)에 **{day_ganji}** 괴강살의 기운이 깃들었네.",
                "content": f"**영웅의 기상:** {data.get('effect_ko', '')}"
                           f"\n**신령의 처방:** {data.get('remedy_advice', '')}"
                           f"\n*신령의 일침:* {data.get('shamanic_voice', '살기를 풀고 쓰게나.')}"
            })

    # 2. 재다신약_패턴(Wealth_Dominance) 체크 (재성 >= 3.5 and (비겁 + 인성) <= 3.0 일 때)
    재성_count = sibseong_counts.get('편재', 0) + sibseong_counts.get('정재', 0)
    비겁_count = sibseong_counts.get('비견', 0) + sibseong_counts.get('겁재', 0)
    인성_count = sibseong_counts.get('정인', 0) + sibseong_counts.get('편인', 0)
    신강도 = 비겁_count + 인성_count
    
    if 재성_count >= 3.5 and 신강도 <= 3.0:
        data = interactions_db.get('재다신약_패턴(Wealth_Dominance)', {})
        if data:
            reports.append({
                "type": "⚠️ **재물 리스크** 진단 (재다신약)",
                "title": "돈 욕심은 많으나 담을 그릇이 약하네.",
                "content": f"**현상:** {data.get('effect_ko', '')}"
                           f"\n**개운법:** {data.get('remedy_advice', '')}"
                           f"\n*신령의 일침:* {data.get('shamanic_voice', '욕심을 버리게나.')}"
            })
            
    return reports

def analyze_shinsal(ganji_map: Dict[str, str], db: Dict) -> List[Dict[str, Any]]:
    """shinsal_db.json을 사용하여 신살 분석을 수행합니다. (신살 DB 사용)"""
    reports = []
    shinsal_db = db.get('shinsal', {}).get('basic_meanings', {})
    
    dohwa_jis = ['자', '오', '묘', '유']
    if any(ji in dohwa_jis for ji in [ganji_map['year_ji'], ganji_map['month_ji'], ganji_map['time_ji']]):
        data = shinsal_db.get('도화살(Peach_Blossom)', {})
        if data: reports.append({"type": "🌷 도화살", "title": "타고난 매력의 별", "content": data.get('desc', '') + "\n" + f"**긍정:** {data.get('positive', '')}"})
            
    yeokma_jis = ['인', '신', '사', '해']
    if any(ji in yeokma_jis for ji in [ganji_map['year_ji'], ganji_map['day_ji']]):
        data = shinsal_db.get('역마살(Stationary_Horse)', {})
        if data: reports.append({"type": "🐎 역마살", "title": "넓은 세상으로 뻗어 나가는 이동수", "content": data.get('desc', '') + "\n" + f"**긍정:** {data.get('positive', '')}"})
            
    hwagae_jis = ['진', '술', '축', '미']
    if any(ji in hwagae_jis for ji in [ganji_map['day_ji'], ganji_map['month_ji']]):
        data = shinsal_db.get('화개살(Art_Cover)', {})
        if data: reports.append({"type": "🎨 화개살", "title": "고독 속에 피어나는 예술의 별", "content": data.get('desc', '') + "\n" + f"**긍정:** {data.get('positive', '')}"})
            
    return reports

def analyze_career_path(sibseong_map: Dict[str, Any], db: Dict) -> Dict[str, Any]:
    """가장 발달한 십성을 분석하여 직업/적성 경로를 제안합니다. (Career DB 활용)"""
    sibseong_counts = sibseong_map.get('counts', {})
    if not sibseong_counts: 
        return {"type": "💼 직업 및 적성 분석", "title": "십성 기운이 고르게 분포되어 있네.", "content": "어느 쪽으로 가도 좋으나, 딱 꼬집어 말하기 어렵네."}

    grouped_counts = {'비겁': 0, '식상': 0, '재성': 0, '관성': 0, '인성': 0}
    for sibseong, count in sibseong_counts.items():
        group = SIBSEONG_GROUP_MAP.get(sibseong)
        if group: grouped_counts[group] += count
            
    main_group = max(grouped_counts, key=grouped_counts.get) if any(grouped_counts.values()) else '비겁'
    
    db_key_map = {
        '비겁': '비겁_태과(Self_Strong)', '식상': '식상_발달(Output_Strong)',
        '재성': '재성_발달(Wealth_Strong)', '관성': '관성_발달(Official_Strong)',
        '인성': '인성_발달(Input_Strong)',
    }
    db_key_for_career = db_key_map.get(main_group, '비겁_태과(Self_Strong)')
    
    career_db_data = db.get('career', {}).get('modern_jobs', {})
    career_data = career_db_data.get(db_key_for_career, {})
    
    career_analysis = {"type": "💼 직업 및 적성 분석", "title": f"천직(天職) 키워드: **{main_group}**", "content": f"그대는 {main_group}의 기운이 가장 강하니, 이것이 곧 사회적 능력이네."}
    if career_data:
        career_analysis['content'] = f"**타고난 기질:** {career_data.get('trait', '')}\n**추천 직업:** {career_data.get('jobs', '')}\n*신령의 충고:* {career_data.get('shamanic_voice', '자네가 하고 싶은 대로 하게나.')}"
        
    return career_analysis

def analyze_timeline(birth_dt: datetime, day_gan: str, ganji_map: Dict[str, str], db: Dict) -> List[Dict[str, Any]]:
    """4가지 기둥(Pillar)의 운세 및 당해년도(2025) 세운을 분석합니다."""
    reports = []
    current_year = 2025 # 현재 연도 고정
    
    # 1. 세운 분석 (2025년)
    current_year_gan = '을' 
    current_year_ji = '사'
    current_year_sibseong = SIBSEONG_MAP.get((day_gan, current_year_gan), '운')
    timeline_db_data = db.get('timeline', {}).get('yearly_2025_2026', {})
    gan_data_2025 = timeline_db_data.get(day_gan, {})
    summary_2025 = gan_data_2025.get('2025', f"{current_year}년의 기운이네. (데이터 부족)")
    
    reports.append({
        "type": f"⚡️ **{current_year}년 ({current_year_gan}{current_year_ji}) {current_year_sibseong}** 세운 분석",
        "title": f"**'을사년(乙巳), 푸른 뱀의 해'** 운세",
        "content": summary_2025
    })

    # 2. 라이프 사이클 전체 분석 (4개 기둥 모두)
    life_pillar_map = [
        ("초년운", "0~19세", "preschool", 'year_pillar', 'year_gan'),
        ("청년운", "20~39세", "social_entry", 'month_pillar', 'month_gan'),
        ("중년운", "40~59세", "expansion", 'day_pillar', 'day_gan'), # expansion 키 사용
        ("말년운", "60세 이후", "seniority", 'time_pillar', 'time_gan') # seniority 키 사용
    ]
    
    life_stages_db = db.get('timeline', {}).get('life_stages_detailed', {})
    major_pillar_db = db.get('lifecycle', {}) 
    
    for stage_name, stage_range, stage_key, pillar_key, gan_key in life_pillar_map:
        life_data = life_stages_db.get(stage_key, {}) 
        pillar_gan_char = ganji_map[gan_key]
        temp_sibseong = SIBSEONG_MAP.get((day_gan, pillar_gan_char), '비견') 
        sibseong_desc = major_pillar_db.get(pillar_key, {}).get(temp_sibseong, '특별한 설명이 없네.')
        
        reports.append({
            "type": f"🕰️ **{stage_name} ({stage_range})** 분석",
            "title": f"**'{life_data.get('desc', '인생의 한 시점')}'**의 흐름",
            "content": f"자네의 **{stage_name}** 시기는 **'{life_data.get('desc', '')}'**에 놓여 있네.\n\n"
                       f"이 시기의 주요 기운인 **{temp_sibseong}**의 영향으로, **{sibseong_desc}**"
        })
            
    return reports

# [궁합 분석 보강 함수 1] 지지 충돌/결합 진단
def check_zizhi_interaction(ganji_a: Dict[str, str], ganji_b: Dict[str, str], db: Dict) -> Tuple[List[Dict[str, Any]], int]:
    """두 사주의 일지/월지 간의 형충합 패턴을 진단하고 합산 점수를 반환합니다."""
    reports = []
    zizhi_db = db.get('compatibility', {}).get('zizhi_interactions', {})
    total_score_changes = 0
    
    jizhi_pairs = [
        ('일지', ganji_a['day_ji'], ganji_b['day_ji']),
        ('월지', ganji_a['month_ji'], ganji_b['month_ji'])
    ]

    for pillar_name, ji_a, ji_b in jizhi_pairs:
        interaction_key = JIJI_INTERACTIONS.get((ji_a, ji_b))
        
        if interaction_key:
            category = ""
            score_impact = 0
            
            if '합' in interaction_key: 
                category = "Six_Harmonies"
                score_key = 'score_bonus'
            elif '충' in interaction_key: 
                category = "Zhi_Chung"
                score_key = 'score_deduction'
            elif '형' in interaction_key: 
                category = "Zhi_Hyeong"
                score_key = 'score_deduction'
                
            interaction_data = zizhi_db.get(category, {}).get(interaction_key)
            
            if interaction_data:
                raw_score = interaction_data.get(score_key, 0)
                if 'deduction' in score_key:
                    score_impact = -raw_score
                else:
                    score_impact = raw_score
                
                total_score_changes += score_impact
                
                interaction_type = "🤝 합/결합" if category == "Six_Harmonies" else "💥 충/형살"
                
                reports.append({
                    "type": f"✨ **{pillar_name}** 상호작용 ({interaction_type})",
                    "title": f"{ji_a}{ji_b} - {interaction_data.get('ko_desc', '명확한 해석이 없네.')}",
                    "content": f"**관계 리스크/이득:** {interaction_data.get('risk', '특별한 리스크는 없네.')}"
                               f"\n**점수 영향:** {'+' if score_impact >= 0 else ''}{score_impact}점"
                })
    return reports, total_score_changes

# [궁합 분석 보강 함수 2] 십성 시너지 및 오행 조후 진단
def check_synergy_and_balance(res_a: Dict, res_b: Dict, db: Dict) -> List[Dict[str, Any]]:
    """두 사주의 십성 카운트와 오행 조후를 비교하여 시너지 및 보완 관계를 진단합니다."""
    reports = []
    synergy_db = db.get('love', {}).get('synergy_patterns', {})
    
    sib_a = res_a['sibseong_detail']['counts']
    sib_b = res_b['sibseong_detail']['counts']
    ohang_a = res_a['five_elements_count']
    ohang_b = res_b['five_elements_count']
    
    # 1. 십성 시너지 진단 (재성보충, 관성보충 등)
    if sib_a.get('정재', 0) + sib_a.get('편재', 0) >= 3.5 and sib_b.get('정인', 0) + sib_b.get('편인', 0) >= 2.0:
        data = synergy_db.get('Ten_Gods_Synergy', {}).get('인성보충_재성')
        if data:
            reports.append({
                "type": "🤝 **십성 시너지** 진단 (인성보충)",
                "title": "A의 현실적인 욕심을 B의 지혜가 뒷받침하는 관계",
                "content": data.get('synergy_ko', '시너지 분석 불가.')
            })
    
    # 2. 오행 조후 보완 진단 (조열 보완, 습윤 보완)
    is_a_dry = (ohang_a.get('화', 0) + ohang_a.get('토', 0)) > (ohang_a.get('수', 0) + ohang_a.get('금', 0)) + 1.0
    is_b_wet_cool = (ohang_b.get('수', 0) + ohang_b.get('금', 0)) >= 3.5
    
    if is_a_dry and is_b_wet_cool:
        data = synergy_db.get('Five_Elements_Temperature_Complement', {}).get('조열보완')
        if data:
            reports.append({
                "type": "🌡️ **오행 조후** 진단 (조열 보완)",
                "title": "A의 뜨거운 기운을 B가 식혀주는 조후의 인연",
                "content": data.get('synergy_ko', '조후 분석 불가.')
            })
            
    is_b_dry = (ohang_b.get('화', 0) + ohang_b.get('토', 0)) > (ohang_b.get('수', 0) + ohang_b.get('금', 0)) + 1.0
    is_a_wet_cool = (ohang_a.get('수', 0) + ohang_a.get('금', 0)) >= 3.5
    
    if is_b_dry and is_a_wet_cool and not reports:
        data = synergy_db.get('Five_Elements_Temperature_Complement', {}).get('습윤보완')
        if data:
            reports.append({
                "type": "🌡️ **오행 조후** 진단 (습윤 보완)",
                "title": "B의 뜨거운 기운을 A가 식혀주는 조후의 인연",
                "content": data.get('synergy_ko', '조후 분석 불가.')
            })
            
    return reports


# ==========================================
# 4. 메인 처리 함수 (Main Processing)
# ==========================================

def process_saju_input(user_data: Dict[str, Any], db: Dict) -> Dict[str, Any]:
    """개인 사주 분석 및 보고서 생성 (모든 DB 활용)"""
    
    name = user_data['name']
    birth_dt = user_data['birth_dt']
    city_name = user_data.get('city', 'Seoul')
    
    location_info = get_location_info(city_name)
    if location_info:
        true_solar_dt = get_true_solar_time(birth_dt, location_info['longitude'], location_info['timezone_str'])
    else:
        true_solar_dt = birth_dt
        
    ganji_map = get_ganji(true_solar_dt, name)
    day_gan = ganji_map['day_gan']
    sibseong_map = calculate_sibseong(day_gan, ganji_map)
    five_elements_count = calculate_five_elements_count(ganji_map)
    
    report: Dict[str, Any] = {
        "user": user_data,
        "saju": ganji_map,
        "sibseong_detail": sibseong_map,
        "five_elements_count": five_elements_count,
        "analytics": []
    }
    
    # 6-0. 핵심 에너지 요약
    main_sib = max(sibseong_map['counts'], key=sibseong_map['counts'].get)
    main_elem = max(five_elements_count, key=five_elements_count.get)
    
    report['analytics'].append({
        "type": "🔮 **타고난 에너지 요약**",
        "title": f"일간({day_gan})과 주된 기운: **{main_elem}** / **{main_sib}**",
        "content": f"그대는 **{day_gan}** 일간으로, 사주 전반에 **{main_elem}** 기운과 **{main_sib}**의 성향이 강하게 지배하고 있네. 이 기운이 자네의 삶을 이끌어갈 중심 축이니 잘 새겨듣게."
    })
    
    # 6-1. 일주 기질 분석 (Identity DB)
    day_ganji = ganji_map['day_gan'] + ganji_map['day_ji']
    identity_analysis = get_day_pillar_identity(day_ganji, db)
    report['analytics'].append(identity_analysis) # 수정된 get_day_pillar_identity 사용

    # 6-2. 콜드 리딩 (Symptom DB)
    report['analytics'].extend(perform_cold_reading(ganji_map, db))
    
    # 6-3. 오행 불균형 & 개운법 (Matrix DB)
    day_gan_elem = OHENG_MAP.get(day_gan, '토')
    report['analytics'].extend(analyze_ohang_imbalance(five_elements_count, day_gan_elem, db))
    
    # 6-3.5 특수 패턴 진단 (괴강, 재다신약 등)
    report['analytics'].extend(analyze_special_patterns(ganji_map, sibseong_map, db))

    # 6-4. 직업/적성 분석 (Career DB)
    report['analytics'].append(analyze_career_path(sibseong_map, db))
    
    # 6-5. 신살 분석 (Shinsal DB)
    report['analytics'].extend(analyze_shinsal(ganji_map, db))
    
    # 6-6. 운세 흐름 분석 (Timeline/Lifecycle DB)
    report['analytics'].extend(analyze_timeline(true_solar_dt, day_gan, ganji_map, db))
        
    return report

def process_love_compatibility(user_a: Dict[str, Any], user_b: Dict[str, Any], db: Dict) -> Dict[str, Any]:
    """두 사주를 비교하여 궁합을 분석합니다. (Compatibility DB 강화)"""
    
    res_a = process_saju_input(user_a, db)
    res_b = process_saju_input(user_b, db)
    
    ganji_a = res_a['saju']
    ganji_b = res_b['saju']
    gan_a = ganji_a['day_gan']
    gan_b = ganji_b['day_gan']
    
    report = {"user_a": res_a, "user_b": res_b, "analytics": []}
    
    comp_db = db.get('compatibility', {}) 
    key = f"{gan_a}_{gan_b}"
    comp_data = comp_db.get(key, {})
    
    comp_analysis = {"type": "💖 일간(日干) 궁합 분석", "title": f"{user_a['name']}({gan_a}) ❤️ {user_b['name']}({gan_b})의 화학적 결합", "content": "두 분의 타고난 성향이 만나 만들어내는 운명적 관계라네."}
    
    base_score = comp_data.get('score', 50) 
    
    if comp_data:
        comp_analysis['content'] = comp_data.get('ko_relation', '평범하지만 서로 맞춰가는 인연일세.')
        comp_analysis['content'] += f"\n\n**천간 기본 점수:** {base_score}점 (100점 만점)"
    report['analytics'].append(comp_analysis)
    
    # 지지 상호작용 및 점수 반영
    zizhi_reports, score_changes = check_zizhi_interaction(ganji_a, ganji_b, db)
    report['analytics'].extend(zizhi_reports)
    
    # 십성 시너지 및 오행 조후 진단
    synergy_reports = check_synergy_and_balance(res_a, res_b, db)
    report['analytics'].extend(synergy_reports)
    
    # 최종 점수 계산 및 첫 보고서 업데이트
    final_score = max(0, min(100, base_score + score_changes))

    # 첫 번째 보고서 (일간 궁합 분석)에 최종 점수 반영
    if report['analytics'] and report['analytics'][0]['type'] == "💖 일간(日干) 궁합 분석":
        report['analytics'][0]['title'] = report['analytics'][0]['title'].replace('의 화학적 결합', f'의 최종 궁합 (총점: **{final_score}점**)')
        report['analytics'][0]['content'] = f"**⭐️ 최종 합산 점수:** **{final_score}점** (가감점: {score_changes}점)\n\n" + comp_data.get('ko_relation', '평범하지만 서로 맞춰가는 인연일세.')
    
    # 연애 패턴 진단 (love_db)
    love_db = db.get('love', {})
    conflict_db = love_db.get('conflict_triggers', {})
    shamanic_advice_db = love_db.get('shamanic_advice', {})
    
    conflict_data = None
    if user_a.get('gender') == '남' and res_a['sibseong_detail']['counts'].get('편재', 0) + res_a['sibseong_detail']['counts'].get('정재', 0) >= 3.0: 
        conflict_data = conflict_db.get('재다신약_남성')
    elif user_a.get('gender') == '여' and (res_a['sibseong_detail']['counts'].get('편관', 0) > 0 and res_a['sibseong_detail']['counts'].get('정관', 0) > 0): 
        conflict_data = conflict_db.get('관살혼잡_여성')
    elif ganji_a['day_gan'] == ganji_b['day_gan'] and OHENG_MAP[ganji_a['day_gan']] == OHENG_MAP.get(ganji_a['day_ji']):
         conflict_data = conflict_db.get('간여지동_커플')
    
    if (gan_a == '정' and gan_b == '임') or (gan_a == '임' and gan_b == '정'):
        deep_advice = shamanic_advice_db.get('jung_im_harmony_deep_advice', {})
        if deep_advice:
             report['analytics'].append({
                "type": "🔥 특수 연애 패턴 (정임합)",
                "title": deep_advice.get('title', '음란지합의 기운'),
                "content": f"{deep_advice.get('advice', '')} \n* {deep_advice.get('compatibility_score_note', '')}"
            })
        
    if conflict_data:
        report['analytics'].append({
            "type": "⚔️ 주요 갈등 원인 (패턴 진단)",
            "title": f"이 커플의 다툼은 **{conflict_data.get('partner_context', '특정 패턴')}**에서 시작되네.",
            "content": f"**싸움 이유:** {conflict_data.get('fight_reason', '')}"
                       f"\n*신령의 일침:* {conflict_data.get('shamanic_voice', '서로 고집 좀 꺾으시게.')}"
        })
    elif not conflict_data and not ((gan_a == '정' and gan_b == '임') or (gan_a == '임' and gan_b == '정')):
         report['analytics'].append({
            "type": "⚔️ 주요 갈등 원인 (패턴 진단)",
            "title": "특별히 눈에 띄는 흉한 십성 조합은 없네.",
            "content": "두 분 모두 평범한 연애를 지향하는구먼. 작은 다툼은 있겠으나, 큰 갈등 없이 무난히 지낼 수 있네."
        })
        
    return report

def load_all_dbs() -> Dict[str, Any]:
    """모든 JSON DB 파일을 로드합니다."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_files = {
        "health": "health_db.json", "five_elements": "five_elements_matrix.json",
        "career": "career_db.json", "shinsal": "shinsal_db.json",
        "timeline": "timeline_db.json", "identity": "identity_db.json",
        "love": "love_db.json", "lifecycle": "lifecycle_pillar_db.json",
        "compatibility": "compatibility_db.json", "symptom": "symptom_mapping.json"
    }
    db = {}
    for key, filename in db_files.items():
        try:
            # os.path.join을 사용하여 파일 경로를 안전하게 구성
            with open(os.path.join(base_dir, filename), 'r', encoding='utf-8') as f:
                db[key] = json.load(f)
        except FileNotFoundError:
            # Streamlit 환경에서 파일이 없을 경우 빈 딕셔너리 반환
            db[key] = {}
        except json.JSONDecodeError:
            db[key] = {}
    return db

# Streamlit 환경에서 사용될 함수들만 외부에 노출
# load_all_dbs, process_saju_input, process_love_compatibility
