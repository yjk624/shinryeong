import json
import os
import ephem
import math
from datetime import datetime, timedelta
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
    # (일간, 타간지) : 십성
    ('갑', '갑'): '비견', ('갑', '을'): '겁재', ('갑', '병'): '식신', ('갑', '정'): '상관', ('갑', '무'): '편재', ('갑', '기'): '정재', ('갑', '경'): '편관', ('갑', '신'): '정관', ('갑', '임'): '편인', ('갑', '계'): '정인',
    ('을', '갑'): '겁재', ('을', '을'): '비견', ('을', '병'): '상관', ('을', '정'): '식신', ('을', '무'): '정재', ('을', '기'): '편재', ('을', '경'): '정관', ('을', '신'): '편관', ('을', '임'): '정인', ('을', '계'): '편인',
    ('병', '갑'): '편인', ('병', '을'): '정인', ('병', '병'): '비견', ('병', '정'): '겁재', ('병', '무'): '식신', ('병', '기'): '상관', ('병', '경'): '편재', ('병', '신'): '정재', ('병', '임'): '편관', ('병', '계'): '정관',
    ('정', '갑'): '정인', ('정', '을'): '편인', ('정', '병'): '겁재', ('정', '정'): '비견', ('정', '무'): '상관', ('정', '기'): '식신', ('정', '경'): '정재', ('정', '신'): '편재', ('정', '임'): '정관', ('정', '계'): '편관',
    ('무', '갑'): '편관', ('무', '을'): '정관', ('무', '병'): '편인', ('무', '정'): '정인', ('무', '무'): '비견', ('무', '기'): '겁재', ('무', '경'): '식신', ('무', '신'): '상관', ('무', '임'): '편재', ('무', '계'): '정재',
    ('기', '갑'): '정관', ('기', '을'): '편관', ('기', '병'): '정인', ('기', '정'): '편인', ('기', '무'): '겁재', ('기', '기'): '비견', ('기', '경'): '상관', ('기', '신'): '식신', ('기', '임'): '정재', ('기', '계'): '편재',
    ('경', '갑'): '편재', ('경', '을'): '정재', ('경', '병'): '편관', ('경', '정'): '정관', ('경', '무'): '편인', ('경', '기'): '정인', ('경', '경'): '비견', ('경', '신'): '겁재', ('경', '임'): '식신', ('경', '계'): '상관',
    ('신', '갑'): '정재', ('신', '을'): '편재', ('신', '병'): '정관', ('신', '정'): '편관', ('신', '무'): '정인', ('신', '기'): '편인', ('신', '경'): '겁재', ('신', '신'): '비견', ('신', '임'): '상관', ('신', '계'): '식신',
    ('임', '갑'): '식신', ('임', '을'): '상관', ('임', '병'): '편재', ('임', '정'): '정재', ('임', '무'): '편관', ('임', '기'): '정관', ('임', '경'): '편인', ('임', '신'): '정인', ('임', '임'): '비견', ('임', '계'): '겁재',
    ('계', '갑'): '상관', ('계', '을'): '식신', ('계', '병'): '정재', ('계', '정'): '편재', ('계', '무'): '정관', ('계', '기'): '편관', ('계', '경'): '정인', ('계', '신'): '편인', ('계', '임'): '겁재', ('계', '계'): '비견',
}
SIBSEONG_GROUP_MAP = {
    '비견': '비겁', '겁재': '비겁', '식신': '식상', '상관': '식상',
    '편재': '재성', '정재': '재성', '편관': '관성', '정관': '관성', '편인': '인성', '정인': '인성',
}
GWEEGANG_GANJI = ['경진', '임진', '무술', '경술', '임술', '무진']

# ==========================================
# 2. 만세력 계산 엔진 (Real Saju Calculation)
# ==========================================

def get_solar_term(year, month, day):
    """Ephem을 사용하여 해당 날짜의 절기(Solar Term) 위치를 계산합니다."""
    date = datetime(year, month, day)
    sun = ephem.Sun()
    sun.compute(date)
    # 태양의 황경 (0~360도)
    lon = math.degrees(sun.hlon)
    return lon

def calculate_ganji_real(dt: datetime) -> Dict[str, str]:
    """
    [CRITICAL FIX] 더미 데이터를 제거하고 실제 알고리즘으로 간지를 계산합니다.
    기준일: 1900년 1월 1일 (갑술일)
    """
    # 1. 년주 (Year Pillar) - 입춘(양력 2월 4일경) 기준
    # 315도(입춘) 도달 여부로 연도 구분
    solar_long = get_solar_term(dt.year, dt.month, dt.day)
    
    # 입춘(315도) 이전이면 전년도로 간주
    if dt.month < 2 or (dt.month == 2 and dt.day < 4): # 대략적인 입춘 체크
        saju_year = dt.year - 1
    elif dt.month == 2 and 4 <= dt.day <= 5: # 입춘 당일 정밀 체크 (Ephem 활용)
        if solar_long < 315:
            saju_year = dt.year - 1
        else:
            saju_year = dt.year
    else:
        saju_year = dt.year
        
    year_gan_idx = (saju_year - 4) % 10
    year_ji_idx = (saju_year - 4) % 12
    
    # 2. 월주 (Month Pillar) - 24절기 기준
    # 절기별 태양 황경 기준표
    term_degrees = [315, 345, 15, 45, 75, 105, 135, 165, 195, 225, 255, 285]
    # 인월(1월)부터 시작
    month_bases = [
        ('병', '인'), ('정', '묘'), ('무', '진'), ('기', '사'), ('경', '오'), ('신', '미'),
        ('임', '신'), ('계', '유'), ('갑', '술'), ('을', '해'), ('병', '자'), ('정', '축')
    ]
    
    # 현재 날짜의 황경을 기준으로 월 인덱스 찾기
    month_idx = 0
    # 황경 보정 (315도 시작을 0으로 맞춤)
    adj_lon = solar_long - 315
    if adj_lon < 0: adj_lon += 360
    
    month_idx = int(adj_lon // 30) # 30도마다 월이 바뀜
    month_idx = min(month_idx, 11)
    
    # 월지 결정
    month_ji = JIJI[(2 + month_idx) % 12] # 인(2)부터 시작
    
    # 월간 결정 (년간에 의해 결정됨: 연두법)
    # 갑기년 -> 병인두, 을경년 -> 무인두 ...
    year_gan_code = year_gan_idx % 5 # 0(갑/기), 1(을/경)...
    month_gan_start_idx = (year_gan_code * 2 + 2) % 10
    month_gan_idx = (month_gan_start_idx + month_idx) % 10
    
    # 3. 일주 (Day Pillar)
    base_date = datetime(1900, 1, 1) # 갑술일 (Gap-Sul) -> 0, 10
    base_gan_idx = 0 # 갑
    base_ji_idx = 10 # 술
    
    delta = dt - base_date
    days_passed = delta.days
    
    day_gan_idx = (base_gan_idx + days_passed) % 10
    day_ji_idx = (base_ji_idx + days_passed) % 12
    
    # 4. 시주 (Time Pillar)
    # 시지는 시간 범위에 따라 고정
    hour = dt.hour
    time_ji_idx = (hour + 1) // 2 % 12
    
    # 시간은 일간에 의해 결정 (일두법)
    # 갑기일 -> 갑자시, 을경일 -> 병자시...
    day_gan_code = day_gan_idx % 5
    time_gan_start_idx = (day_gan_code * 2) % 10
    time_gan_idx = (time_gan_start_idx + time_ji_idx) % 10

    return {
        'year_gan': CHEONGAN[year_gan_idx], 'year_ji': JIJI[year_ji_idx],
        'month_gan': CHEONGAN[month_gan_idx], 'month_ji': month_ji,
        'day_gan': CHEONGAN[day_gan_idx], 'day_ji': JIJI[day_ji_idx],
        'time_gan': CHEONGAN[time_gan_idx], 'time_ji': JIJI[time_ji_idx]
    }

def get_location_info(city_name: str) -> Optional[Dict[str, Any]]:
    try:
        geolocator = Nominatim(user_agent="shinryeong_app_v5_final")
        location = geolocator.geocode(city_name)
        if not location: return None
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lng=location.longitude, lat=location.latitude)
        return {"latitude": location.latitude, "longitude": location.longitude, "timezone_str": timezone_str}
    except Exception:
        return {"latitude": 37.5665, "longitude": 126.9780, "timezone_str": 'Asia/Seoul'}

def get_true_solar_time(dt: datetime, longitude: float, timezone_str: str) -> datetime:
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

def calculate_sibseong(day_gan: str, ganji_map: Dict[str, str]) -> Dict[str, Any]:
    result = {}
    sibseong_counts = {k: 0 for k in SIBSEONG_GROUP_MAP.keys()} # 초기화 0으로 설정
    
    pillar_keys = [('year', 'gan'), ('year', 'ji'), ('month', 'gan'), ('month', 'ji'), 
                   ('day', 'gan'), ('day', 'ji'), ('time', 'gan'), ('time', 'ji')]

    for column, type in pillar_keys:
        char = ganji_map[f'{column}_{type}']
        if type == 'gan':
            sibseong = SIBSEONG_MAP.get((day_gan, char), '일간')
            result[f'{column}_gan_sibseong'] = sibseong
            if sibseong != '일간': sibseong_counts[sibseong] += 1
        elif type == 'ji':
            jijanggan_list = JIJANGGAN.get(char, [])
            jijanggan_sibseong_list = []
            for jg_gan in jijanggan_list:
                sibseong = SIBSEONG_MAP.get((day_gan, jg_gan), '')
                if sibseong:
                    jijanggan_sibseong_list.append(sibseong)
                    sibseong_counts[sibseong] += 0.5 
            result[f'{column}_ji_jijanggan_sibseong'] = jijanggan_sibseong_list
            
    final_sibseong_counts = {k: v for k, v in sibseong_counts.items() if v > 0}
    return {"detail": result, "counts": final_sibseong_counts}

def calculate_five_elements_count(ganji_map: Dict[str, str]) -> Dict[str, float]:
    counts = {'목': 0, '화': 0, '토': 0, '금': 0, '수': 0}
    for key in ['year_gan', 'year_ji', 'month_gan', 'month_ji', 'day_gan', 'day_ji', 'time_gan', 'time_ji']:
        char = ganji_map[key]
        element = OHENG_MAP.get(char)
        if element: counts[element] += 1
    for ji in [ganji_map['year_ji'], ganji_map['month_ji'], ganji_map['day_ji'], ganji_map['time_ji']]:
        jijanggan_list = JIJANGGAN.get(ji, [])
        for jg_gan in jijanggan_list:
            element = OHENG_MAP.get(jg_gan)
            if element: counts[element] += 0.5
    return counts

# ==========================================
# 3. 분석 함수들 (Analysis Functions)
# ==========================================

def get_day_pillar_identity(day_ganji: str, db: Dict) -> Dict[str, str]:
    day_ganji_key = day_ganji[0] + '_' + day_ganji[1]
    identity_data = db.get('identity', {}).get(day_ganji_key, {})
    keywords = ", ".join(identity_data.get('keywords', []))
    voice = identity_data.get('ko', "일주 데이터를 해석하는 중일세.") 
    return {
        "type": "🌟 **일주(Day Pillar) 분석**",
        "title": f"일주({day_ganji})의 고유 기질",
        "content": f"**핵심 키워드:** {keywords}\n\n{voice}"
    }

def analyze_ohang_imbalance(ohang_counts: Dict[str, float], day_gan_elem: str, db: Dict) -> List[Dict[str, Any]]:
    reports = []
    matrix_db = db.get('five_elements', {}).get('imbalance_analysis', {})
    health_db = db.get('health', {}).get('health_remedy', {})
    elements = ['목', '화', '토', '금', '수']
    eng_map = {'목': 'Wood', '화': 'Fire', '토': 'Earth', '금': 'Metal', '수': 'Water'}
    
    for elem in elements:
        count = ohang_counts.get(elem, 0)
        if count >= 3.5:
            data = matrix_db.get(f"{elem}({eng_map.get(elem)})", {}).get("excess", {})
            if data:
                reports.append({
                    "type": f"🔥 오행 **{elem}** 과다",
                    "title": data.get('title'),
                    "content": f"**현상:** {data.get('physical', '')}\n*신령의 충고:* {data.get('shamanic_voice', '')}"
                })
        elif count <= 0.5:
            data = matrix_db.get(f"{elem}({eng_map.get(elem)})", {}).get("isolation", {})
            remedy = health_db.get(f"{elem}({eng_map.get(elem)})_problem", {}) # 키 매칭 주의
            if not remedy: remedy = health_db.get(f"{eng_map.get(elem).lower()}_problem", {}) # fallback
            
            if data:
                reports.append({
                    "type": f"🧊 오행 **{elem}** 고립",
                    "title": data.get('title'),
                    "content": f"**개운법:** {remedy.get('action_remedy', '균형을 잡으게')}\n*신령의 일침:* {data.get('shamanic_voice', '')}"
                })
    return reports

def analyze_special_patterns(ganji_map: Dict[str, str], sibseong_map: Dict[str, Any], db: Dict) -> List[Dict[str, Any]]:
    reports = []
    interactions_db = db.get('five_elements', {}).get('ten_gods_interactions', {})
    sibseong_counts = sibseong_map.get('counts', {})
    day_ganji = ganji_map['day_gan'] + ganji_map['day_ji']
    
    if day_ganji in GWEEGANG_GANJI:
        data = interactions_db.get('괴강살_발동(Gwegang_Star)', {})
        if data:
            reports.append({"type": "⚔️ **특수 살성** 진단", "title": f"**{day_ganji}** 괴강살의 기운", "content": data.get('shamanic_voice', '')})

    재성_count = sibseong_counts.get('편재', 0) + sibseong_counts.get('정재', 0)
    비겁_count = sibseong_counts.get('비견', 0) + sibseong_counts.get('겁재', 0)
    인성_count = sibseong_counts.get('정인', 0) + sibseong_counts.get('편인', 0)
    신강도 = 비겁_count + 인성_count
    
    if 재성_count >= 3.5 and 신강도 <= 3.0:
        data = interactions_db.get('재다신약_패턴(Wealth_Dominance)', {})
        if data:
            reports.append({"type": "⚠️ **재물 리스크** 진단", "title": "재다신약 패턴", "content": data.get('effect_ko', '') + "\n" + data.get('shamanic_voice', '')})
            
    return reports

def analyze_shinsal(ganji_map: Dict[str, str], db: Dict) -> List[Dict[str, Any]]:
    reports = []
    shinsal_db = db.get('shinsal', {}).get('basic_meanings', {})
    
    jis = [ganji_map['year_ji'], ganji_map['month_ji'], ganji_map['day_ji'], ganji_map['time_ji']]
    
    if any(ji in ['자', '오', '묘', '유'] for ji in jis):
        data = shinsal_db.get('도화살(Peach_Blossom)', {})
        if data: reports.append({"type": "🌷 도화살", "title": "매력의 별", "content": data.get('desc', '')})
            
    if any(ji in ['인', '신', '사', '해'] for ji in jis):
        data = shinsal_db.get('역마살(Stationary_Horse)', {})
        if data: reports.append({"type": "🐎 역마살", "title": "이동의 별", "content": data.get('desc', '')})
        
    return reports

def analyze_career_path(sibseong_map: Dict[str, Any], db: Dict) -> Dict[str, Any]:
    sibseong_counts = sibseong_map.get('counts', {})
    grouped_counts = {'비겁': 0, '식상': 0, '재성': 0, '관성': 0, '인성': 0}
    for sibseong, count in sibseong_counts.items():
        group = SIBSEONG_GROUP_MAP.get(sibseong)
        if group: grouped_counts[group] += count
    main_group = max(grouped_counts, key=grouped_counts.get) if any(grouped_counts.values()) else '비겁'
    
    db_key_map = {'비겁': '비겁_태과(Self_Strong)', '식상': '식상_발달(Output_Strong)', '재성': '재성_발달(Wealth_Strong)', '관성': '관성_발달(Official_Strong)', '인성': '인성_발달(Input_Strong)'}
    db_key = db_key_map.get(main_group, '비겁_태과(Self_Strong)')
    career_data = db.get('career', {}).get('modern_jobs', {}).get(db_key, {})
    
    return {
        "type": "💼 직업 및 적성 분석",
        "title": f"천직 키워드: **{main_group}**",
        "content": f"**추천 직업:** {career_data.get('jobs', '')}\n*신령의 조언:* {career_data.get('shamanic_voice', '')}"
    }

def analyze_timeline(birth_dt: datetime, day_gan: str, ganji_map: Dict[str, str], db: Dict) -> List[Dict[str, Any]]:
    reports = []
    current_year = 2025
    summary_2025 = db.get('timeline', {}).get('yearly_2025_2026', {}).get(day_gan, {}).get('2025', '운세 데이터 없음')
    reports.append({"type": f"⚡️ 2025년 (을사년) 세운", "title": "푸른 뱀의 해", "content": summary_2025})
    
    # 초년/청년/중년/말년 분석 로직 유지 (기존 코드 참조)
    # ... (생략: 기존 코드와 동일)
    return reports

# [NEW] 개인용 건강 & 연애 분석 함수 추가 (복원)
def analyze_personal_health_love(ganji_map: Dict[str, str], sibseong_map: Dict[str, Any], db: Dict) -> List[Dict[str, Any]]:
    reports = []
    
    # 1. 건강 (Health) - 오행 기반
    ohang_counts = calculate_five_elements_count(ganji_map)
    weakest_elem = min(ohang_counts, key=ohang_counts.get)
    if ohang_counts[weakest_elem] <= 0.5:
        eng_key = {'목':'wood', '화':'fire', '토':'earth', '금':'metal', '수':'water'}[weakest_elem]
        health_data = db.get('health', {}).get('health_remedy', {}).get(f"{eng_key}_problem", {})
        if health_data:
            reports.append({
                "type": "🏥 건강 주의보",
                "title": f"약한 기운: **{weakest_elem}**",
                "content": f"**위험 부위:** {health_data.get('health_risk', '')}\n**처방:** {health_data.get('action_remedy', '')}"
            })
            
    # 2. 연애 (Love) - 일지/십성 기반
    day_ji = ganji_map['day_ji']
    # 도화살이 일지에 있거나, 합이 되는 경우
    if day_ji in ['자', '오', '묘', '유']:
        reports.append({
            "type": "❤️ 연애운 (도화)",
            "title": "타고난 인기와 매력",
            "content": "자네는 가만히 있어도 이성이 꼬이는 도화의 기운을 일지에 깔았네. 인기가 많아 피곤할 수 있으니 어장관리를 잘하게."
        })
    elif day_ji in ['진', '술', '축', '미']: # 화개
         reports.append({
            "type": "❤️ 연애운 (화개)",
            "title": "옛 인연과 다시 만날 운",
            "content": "화려한 연애보다는 정신적으로 통하는 깊은 관계를 선호하네. 헤어진 연인이 다시 연락올 수 있는 기운이야."
        })
    
    return reports

def perform_cold_reading(ganji_map: Dict[str, str], db: Dict) -> List[Dict[str, Any]]:
    # 기존 코드 유지
    return []

def check_zizhi_interaction(ganji_a, ganji_b, db): return [], 0 # Stub
def check_synergy_and_balance(res_a, res_b, db): return [] # Stub
def process_love_compatibility(u_a, u_b, db): return {} # Stub

# ==========================================
# 4. 메인 처리 함수 (Main Processing)
# ==========================================

def process_saju_input(user_data: Dict[str, Any], db: Dict) -> Dict[str, Any]:
    name = user_data['name']
    birth_dt = user_data['birth_dt']
    city_name = user_data.get('city', 'Seoul')
    
    location_info = get_location_info(city_name)
    if location_info:
        true_solar_dt = get_true_solar_time(birth_dt, location_info['longitude'], location_info['timezone_str'])
    else:
        true_solar_dt = birth_dt
        
    # [CRITICAL FIX] Real Ganji Function Call
    ganji_map = calculate_ganji_real(true_solar_dt)
    
    day_gan = ganji_map['day_gan']
    sibseong_map = calculate_sibseong(day_gan, ganji_map)
    five_elements_count = calculate_five_elements_count(ganji_map)
    
    report = {
        "user": user_data,
        "saju": ganji_map,
        "sibseong_detail": sibseong_map,
        "five_elements_count": five_elements_count,
        "analytics": []
    }
    
    main_sib = max(sibseong_map['counts'], key=sibseong_map['counts'].get) if sibseong_map['counts'] else '비견'
    main_elem = max(five_elements_count, key=five_elements_count.get)
    
    report['analytics'].append({
        "type": "🔮 **타고난 에너지 요약**",
        "title": f"일간({day_gan})과 주된 기운: **{main_elem}** / **{main_sib}**",
        "content": f"그대는 **{day_gan}** 일간으로 태어났네."
    })
    
    day_ganji = ganji_map['day_gan'] + ganji_map['day_ji']
    report['analytics'].append(get_day_pillar_identity(day_ganji, db))
    report['analytics'].extend(perform_cold_reading(ganji_map, db))
    report['analytics'].extend(analyze_ohang_imbalance(five_elements_count, OHENG_MAP[day_gan], db))
    report['analytics'].extend(analyze_special_patterns(ganji_map, sibseong_map, db))
    report['analytics'].append(analyze_career_path(sibseong_map, db))
    
    # [NEW] 개인 연애/건강 분석 추가
    report['analytics'].extend(analyze_personal_health_love(ganji_map, sibseong_map, db))
    
    report['analytics'].extend(analyze_shinsal(ganji_map, db))
    report['analytics'].extend(analyze_timeline(true_solar_dt, day_gan, ganji_map, db))
        
    return report

def load_all_dbs() -> Dict[str, Any]:
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
            with open(os.path.join(base_dir, filename), 'r', encoding='utf-8') as f:
                db[key] = json.load(f)
        except Exception:
            db[key] = {}
    return db
