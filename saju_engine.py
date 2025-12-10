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
# 십성 맵핑 (일간 기준)
SIBSEONG_MAP = {}
for i, day in enumerate(CHEONGAN):
    for j, target in enumerate(CHEONGAN):
        # 오행 인덱스 (0:목, 1:화, 2:토, 3:금, 4:수)
        day_elem_idx = i // 2
        target_elem_idx = j // 2
        
        # 음양 (0:양, 1:음)
        day_yin_yang = i % 2
        target_yin_yang = j % 2
        
        # 십성 로직
        # 비겁: 오행 같음
        if day_elem_idx == target_elem_idx:
            SIBSEONG_MAP[(day, target)] = '비견' if day_yin_yang == target_yin_yang else '겁재'
        # 식상: 일간이 생함
        elif (day_elem_idx + 1) % 5 == target_elem_idx:
            SIBSEONG_MAP[(day, target)] = '식신' if day_yin_yang == target_yin_yang else '상관'
        # 재성: 일간이 극함
        elif (day_elem_idx + 2) % 5 == target_elem_idx:
            SIBSEONG_MAP[(day, target)] = '편재' if day_yin_yang == target_yin_yang else '정재'
        # 관성: 일간을 극함
        elif (day_elem_idx + 3) % 5 == target_elem_idx:
            SIBSEONG_MAP[(day, target)] = '편관' if day_yin_yang == target_yin_yang else '정관'
        # 인성: 일간을 생함
        elif (day_elem_idx + 4) % 5 == target_elem_idx:
            SIBSEONG_MAP[(day, target)] = '편인' if day_yin_yang == target_yin_yang else '정인'

SIBSEONG_GROUP_MAP = {
    '비견': '비겁', '겁재': '비겁', '식신': '식상', '상관': '식상',
    '편재': '재성', '정재': '재성', '편관': '관성', '정관': '관성', '편인': '인성', '정인': '인성',
}
GWEEGANG_GANJI = ['경진', '임진', '무술', '경술', '임술', '무진']
JIJI_INTERACTIONS = {
    ('자', '축'): '자축합', ('축', '자'): '자축합', ('인', '해'): '인해합', ('해', '인'): '인해합',
    ('묘', '술'): '묘술합', ('술', '묘'): '묘술합', ('진', '유'): '진유합', ('유', '진'): '진유합',
    ('사', '신'): '사신합', ('신', '사'): '사신합', ('오', '미'): '오미합', ('미', '오'): '오미합',
    ('자', '오'): '자오충', ('오', '자'): '자오충', ('묘', '유'): '묘유충', ('유', '묘'): '묘유충',
    ('인', '신'): '인신충', ('신', '인'): '인신충', ('사', '해'): '사해충', ('해', '사'): '사해충',
    ('축', '미'): '축미충', ('미', '축'): '축미충', ('진', '술'): '진술충', ('술', '진'): '진술충',
    ('인', '사'): '인사신형', ('사', '인'): '인사신형', ('사', '신'): '인사신형', ('신', '사'): '인사신형',
    ('축', '술'): '축술미형', ('술', '축'): '축술미형', ('축', '미'): '축술미형', ('미', '축'): '축술미형',
    ('자', '묘'): '자묘형', ('묘', '자'): '자묘형', ('진', '진'): '진진형', ('오', '오'): '오오형', 
    ('유', '유'): '유유형', ('해', '해'): '해해형',
}

# ==========================================
# 2. 만세력 계산 엔진 (Real Calculation)
# ==========================================

def get_solar_term(year, month, day):
    date = datetime(year, month, day)
    sun = ephem.Sun()
    sun.compute(date)
    return math.degrees(sun.hlon)

def calculate_ganji_real(dt: datetime) -> Dict[str, str]:
    """
    1900년 1월 1일(갑술일) 기준 실제 간지 계산 로직
    """
    # 1. 년주 (입춘 기준)
    solar_long = get_solar_term(dt.year, dt.month, dt.day)
    if dt.month < 2 or (dt.month == 2 and dt.day < 4):
        saju_year = dt.year - 1
    elif dt.month == 2 and 4 <= dt.day <= 5:
        if solar_long < 315: saju_year = dt.year - 1
        else: saju_year = dt.year
    else:
        saju_year = dt.year
        
    year_gan_idx = (saju_year - 4) % 10
    year_ji_idx = (saju_year - 4) % 12
    
    # 2. 월주 (절기 기준)
    adj_lon = solar_long - 315
    if adj_lon < 0: adj_lon += 360
    month_idx = min(int(adj_lon // 30), 11)
    
    month_ji = JIJI[(2 + month_idx) % 12] # 인월부터 시작
    
    # 연두법 (년 -> 월)
    year_gan_code = year_gan_idx % 5 
    month_gan_start_idx = (year_gan_code * 2 + 2) % 10
    month_gan_idx = (month_gan_start_idx + month_idx) % 10
    
    # 3. 일주 (일수 계산)
    base_date = datetime(1900, 1, 1) # 갑술일
    delta = dt - base_date
    days_passed = delta.days
    
    day_gan_idx = (0 + days_passed) % 10  # 0=갑
    day_ji_idx = (10 + days_passed) % 12 # 10=술
    
    # 4. 시주 (일두법)
    time_ji_idx = (dt.hour + 1) // 2 % 12
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
        geolocator = Nominatim(user_agent="shinryeong_app_final_v9")
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
    sibseong_counts = {k: 0 for k in SIBSEONG_GROUP_MAP.keys()}
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
            remedy = health_db.get(f"{eng_map.get(elem).lower()}_problem", {})
            
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
    
    life_pillar_map = [
        ("초년운", "0~19세", "preschool", 'year_pillar', 'year_gan'),
        ("청년운", "20~39세", "social_entry", 'month_pillar', 'month_gan'),
        ("중년운", "40~59세", "expansion", 'day_pillar', 'day_gan'),
        ("말년운", "60세 이후", "seniority", 'time_pillar', 'time_gan')
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

def analyze_personal_health_love(ganji_map: Dict[str, str], sibseong_map: Dict[str, Any], db: Dict) -> List[Dict[str, Any]]:
    reports = []
    
    # 1. 건강 (Health)
    ohang_counts = calculate_five_elements_count(ganji_map)
    # 가장 약한 오행 찾기
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
            
    # 2. 연애 (Love)
    day_ji = ganji_map['day_ji']
    if day_ji in ['자', '오', '묘', '유']:
        reports.append({
            "type": "❤️ 연애운 (도화)",
            "title": "타고난 인기와 매력",
            "content": "자네는 가만히 있어도 이성이 꼬이는 도화의 기운을 일지에 깔았네. 인기가 많아 피곤할 수 있으니 어장관리를 잘하게."
        })
    elif day_ji in ['진', '술', '축', '미']: 
         reports.append({
            "type": "❤️ 연애운 (화개)",
            "title": "옛 인연과 다시 만날 운",
            "content": "화려한 연애보다는 정신적으로 통하는 깊은 관계를 선호하네. 헤어진 연인이 다시 연락올 수 있는 기운이야."
        })
    elif day_ji in ['인', '신', '사', '해']:
        reports.append({
            "type": "❤️ 연애운 (역마)",
            "title": "여행지에서 만날 인연",
            "content": "활동적인 사람과 인연이 깊네. 여행이나 이동 중에 운명의 상대를 만날 확률이 높으니 밖으로 나가게."
        })
    
    return reports

def perform_cold_reading(ganji_map: Dict[str, str], db: Dict) -> List[Dict[str, Any]]:
    reports = []
    symptom_db = db.get('symptom', {}).get('patterns', {})
    ohang_counts = calculate_five_elements_count(ganji_map)
    
    # 습한 사주 체크
    if ohang_counts.get('수', 0) >= 3 or ganji_map['month_ji'] in ['해', '자', '축']:
        data = symptom_db.get('습한_사주(Wet_Chart)', {})
        if data:
            reports.append({
                "type": "☔ 습한 사주 (환경 진단)",
                "title": "환경 진단",
                "content": f"**환경/신체:** {data.get('environment', '')} {data.get('body', '')}\n*신령의 일침:* {data.get('shamanic_voice', '')}"
            })
    return reports

def check_zizhi_interaction(ganji_a, ganji_b, db):
    reports = []
    zizhi_db = db.get('compatibility', {}).get('zizhi_interactions', {})
    total_score = 0
    
    pairs = [('일지', ganji_a['day_ji'], ganji_b['day_ji']), ('월지', ganji_a['month_ji'], ganji_b['month_ji'])]
    for name, a, b in pairs:
        key = JIJI_INTERACTIONS.get((a, b))
        if key:
            cat = 'Six_Harmonies' if '합' in key else 'Zhi_Chung' if '충' in key else 'Zhi_Hyeong'
            data = zizhi_db.get(cat, {}).get(key, {})
            score = data.get('score_bonus', 0) if cat == 'Six_Harmonies' else -data.get('score_deduction', 0)
            total_score += score
            reports.append({
                "type": f"✨ {name} 궁합 ({key})",
                "title": f"{a}-{b} 관계",
                "content": f"{data.get('ko_desc', '')}\n점수 영향: {score}점"
            })
    return reports, total_score

def check_synergy_and_balance(res_a, res_b, db):
    return [] # 간소화

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
        
    # [FIX] 실제 계산 로직 사용
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
    
    # [FIX] 누락되었던 연애/건강 분석 함수 호출 추가
    report['analytics'].extend(analyze_personal_health_love(ganji_map, sibseong_map, db))
    
    report['analytics'].extend(perform_cold_reading(ganji_map, db))
    report['analytics'].extend(analyze_ohang_imbalance(five_elements_count, OHENG_MAP[day_gan], db))
    report['analytics'].extend(analyze_special_patterns(ganji_map, sibseong_map, db))
    report['analytics'].append(analyze_career_path(sibseong_map, db))
    report['analytics'].extend(analyze_shinsal(ganji_map, db))
    report['analytics'].extend(analyze_timeline(true_solar_dt, day_gan, ganji_map, db))
        
    return report

def process_love_compatibility(user_a: Dict[str, Any], user_b: Dict[str, Any], db: Dict) -> Dict[str, Any]:
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
    
    base_score = comp_data.get('score', 50)
    
    zizhi_reports, score_changes = check_zizhi_interaction(ganji_a, ganji_b, db)
    final_score = max(0, min(100, base_score + score_changes))
    
    comp_analysis = {
        "type": "💖 일간(日干) 궁합 분석", 
        "title": f"최종 궁합 점수: **{final_score}점**", 
        "content": f"{comp_data.get('ko_relation', '')}\n\n(기본 {base_score}점 + 지지 가감 {score_changes}점)"
    }
    report['analytics'].append(comp_analysis)
    report['analytics'].extend(zizhi_reports)
    
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
