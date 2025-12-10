import json
import os
import math
import ephem
from datetime import datetime, timedelta
import pytz
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from typing import Dict, Any, List, Optional, Tuple

# ==========================================
# 1. 상수 및 기본 맵핑 (Constants & Maps) - V2.1 보강 (토 오행 분리)
# ==========================================
GAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]

# V2.1: 조후 분석을 위한 토(土) 오행 분리 (무/기/진/축/술/미)
OHENG_MAP = {
    '갑': '목', '을': '목', '병': '화', '정': '화', '경': '금', '신': '금', '임': '수', '계': '수',
    '인': '목', '묘': '목', '사': '화', '오': '화', '신': '금', '유': '금', '해': '수', '자': '수',
    
    # 토 오행: 무/술/미는 조토(Dry), 기/진/축은 습토(Wet)로 가정 (조후 판단 강화)
    '무': '토_조', '기': '토_습', 
    '진': '토_습', '축': '토_습', 
    '술': '토_조', '미': '토_조'
}

SIBSEONG_GROUP_MAP = {
    '비견': '비겁', '겁재': '비겁', '식신': '식상', '상관': '식상',
    '편재': '재성', '정재': '재성', '편관': '관성', '정관': '관성', '편인': '인성', '정인': '인성',
}
JIJANGGAN_MAP = {
    '자': {'계': 1.0}, '축': {'계': 0.25, '신': 0.25, '기': 0.5},
    '인': {'무': 0.25, '병': 0.25, '갑': 0.5}, '묘': {'을': 1.0},
    '진': {'을': 0.25, '계': 0.25, '무': 0.5}, '사': {'무': 0.25, '경': 0.25, '병': 0.5},
    '오': {'병': 0.5, '기': 0.5}, '미': {'정': 0.25, '을': 0.25, '기': 0.5},
    '신': {'무': 0.25, '임': 0.25, '경': 0.5}, '유': {'신': 1.0},
    '술': {'신': 0.25, '정': 0.25, '무': 0.5}, '해': {'무': 0.25, '갑': 0.25, '임': 0.5}
}
SIBSEONG_MAP = {}
for i, day in enumerate(GAN):
    for j, target in enumerate(GAN):
        day_elem_idx = i // 2
        target_elem_idx = j // 2
        day_yin_yang = i % 2
        target_yin_yang = j % 2
        diff = (target_elem_idx - day_elem_idx) % 5
        if diff == 0: val = '비견' if day_yin_yang == target_yin_yang else '겁재'
        elif diff == 1: val = '식신' if day_yin_yang == target_yin_yang else '상관'
        elif diff == 2: val = '편재' if day_yin_yang == target_yin_yang else '정재'
        elif diff == 3: val = '편관' if day_yin_yang == target_yin_yang else '정관'
        elif diff == 4: val = '편인' if day_yin_yang == target_yin_yang else '정인'
        SIBSEONG_MAP[(day, target)] = val

JIJI_INTERACTIONS = {
    ('자', '축'): '자축합', ('인', '해'): '인해합', ('묘', '술'): '묘술합', 
    ('진', '유'): '진유합', ('사', '신'): '사신합', ('오', '미'): '오미합', 
    ('자', '오'): '자오충', ('묘', '유'): '묘유충', ('인', '신'): '인신충', 
    ('사', '해'): '사해충', ('축', '미'): '축미충', ('진', '술'): '진술충',
    ('인', '사'): '인사신형', ('사', '신'): '인사신형', ('축', '술'): '축술미형',
    ('술', '미'): '축술미형', ('자', '묘'): '자묘형', ('오', '오'): '오오형/진진형/유유형/해해형'
}
GAN_LIST = ['갑', '을', '병', '정', '무', '기', '경', '신', '임', '계']
JI_LIST = ['자', '축', '인', '묘', '진', '사', '오', '미', '신', '유', '술', '해']

# ==========================================
# 0. 데이터베이스 로딩 함수 (V2.1 보강 - A)
# ==========================================
def load_all_dbs() -> Dict[str, Any]:
    """모든 JSON DB 파일을 로드하여 딕셔너리로 반환"""
    db = {}
    db_files = {
        'identity': 'identity_db.json',
        'career': 'career_db.json',
        'health': 'health_db.json',
        'love': 'love_db.json',
        'timeline': 'timeline_db.json',
        'shinsal': 'shinsal_db.json',
        'lifecycle_pillar': 'lifecycle_pillar_db.json',
        'five_elements_matrix': 'five_elements_matrix.json',
        'symptom_mapping': 'symptom_mapping.json',
        'compatibility': 'compatibility_db.json'
    }
    
    # **주의:** 실제 환경에서는 os.path.join 등을 사용하여 파일 경로를 지정해야 함.
    # 이 로직은 파일 I/O가 가능한 환경을 전제로 합니다.
    for key, filename in db_files.items():
        try:
            current_dir = os.path.dirname(__file__)
            file_path = os.path.join(current_dir, 'db_data', filename) # db_data 폴더에 파일이 있다고 가정
            
            # 현재 환경 제약으로 인해 파일을 로드하는 대신,
            # '파일이 존재한다'고 가정하고 빈 딕셔너리 대신 실제 로딩 코드를 남겨둡니다.
            # with open(file_path, 'r', encoding='utf-8') as f:
            #     db[key] = json.load(f)
            
            # 임시 (실제 파일 I/O 필요):
            db[key] = {} # 실제 데이터를 로드해야 함
            
        except FileNotFoundError:
            # print(f"경고: 데이터베이스 파일 {filename}을 찾을 수 없습니다. 빈 데이터 사용.")
            db[key] = {} 
        except json.JSONDecodeError:
            # print(f"경고: 데이터베이스 파일 {filename} JSON 디코딩 오류. 빈 데이터 사용.")
            db[key] = {}

    return db

# ==========================================
# 2. 정밀 천문 계산 (Julian Day Algorithm) - V2.1 보강 (B)
# ==========================================
def get_julian_day_number(year, month, day):
    if month <= 2: year -= 1; month += 12
    A = year // 100
    B = 2 - A + (A // 4)
    JDN = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524
    return JDN

def get_ganji_from_jdn(jdn):
    gan_idx = (jdn + 9) % 10
    ji_idx = (jdn + 1) % 12
    return GAN[gan_idx], JI[ji_idx]

def get_solar_term_month(dt: datetime) -> Tuple[str, int]:
    sun = ephem.Sun()
    date_ephem = ephem.Date(dt)
    sun.compute(date_ephem)
    lon_deg = math.degrees(sun.hlon)
    if lon_deg < 0: lon_deg += 360
    adjusted_lon = lon_deg - 315
    if adjusted_lon < 0: adjusted_lon += 360
    month_idx = int(adjusted_lon // 30)
    month_ji_char = JI[(2 + month_idx) % 12]
    return month_ji_char, month_idx

# V2.1 보강: 경도 및 시차를 반영하여 진(眞) 시간 계산
def get_true_local_time(dt: datetime, city_name: str) -> datetime:
    """출생 도시의 경도와 시차를 반영한 정확한 현지 시간(Local True Time)을 계산"""
    try:
        # 1. 경도 및 시간대(Timezone) 찾기
        geolocator = Nominatim(user_agent="Shinryeong_App")
        location = geolocator.geocode(city_name)
        
        if not location:
            # 도시 정보가 없으면 서울 기준으로 진행
            city_name = "Seoul"
            location = geolocator.geocode(city_name)

        longitude = location.longitude
        
        # 2. 표준시(Standard Time) 설정: 대한민국 표준 경도 135도 (KST 기준)
        STANDARD_MERIDIAN = 135
        
        # 3. 경도 시차 계산 (1도당 4분 차이)
        # 현지 경도와 표준 경도의 차이를 이용한 시차 보정
        longitude_diff_min = (longitude - STANDARD_MERIDIAN) * 4
        
        # 4. 경도 시차 보정
        # '경도가 표준 경도보다 동쪽(양수)이면 시간이 빠르므로 빼주고, 서쪽(음수)이면 느리므로 더해줌'
        true_local_time = dt - timedelta(minutes=longitude_diff_min)
        
        return true_local_time

    except Exception as e:
        # print(f"시간 계산 오류 발생 ({city_name}): {e}. 입력 시간을 그대로 사용합니다.")
        return dt # 오류 시 입력 시간을 그대로 사용

def calculate_saju_pillars(dt: datetime) -> Dict[str, str]:
    # dt는 이제 이미 get_true_local_time을 통해 보정된 '진시간'이어야 함
    jdn = get_julian_day_number(dt.year, dt.month, dt.day)
    day_gan, day_ji = get_ganji_from_jdn(jdn)
    
    sun = ephem.Sun()
    sun.compute(ephem.Date(dt))
    lon = math.degrees(sun.hlon)
    if lon < 0: lon += 360
    
    saju_year = dt.year
    if 270 <= lon < 315 or (dt.month == 1 and lon < 315):
        saju_year -= 1
        
    year_gan_idx = (saju_year - 4) % 10
    year_ji_idx = (saju_year - 4) % 12
    year_gan = GAN[year_gan_idx]
    year_ji = JI[year_ji_idx]

    month_ji_char, month_idx_from_in = get_solar_term_month(dt)
    month_gan_start_idx = (year_gan_idx % 5 * 2 + 2) % 10
    month_gan = GAN[(month_gan_start_idx + month_idx_from_in) % 10]
    month_ji = month_ji_char
    
    hour = dt.hour
    if hour >= 23 or hour < 1: time_ji_idx = 0
    else: time_ji_idx = (hour + 1) // 2 % 12
        
    time_gan_start_idx = (GAN.index(day_gan) % 5 * 2) % 10
    time_gan = GAN[(time_gan_start_idx + time_ji_idx) % 10]
    time_ji = JI[time_ji_idx]
    
    return {
        'year_gan': year_gan, 'year_ji': year_ji,
        'month_gan': month_gan, 'month_ji': month_ji,
        'day_gan': day_gan, 'day_ji': day_ji,
        'time_gan': time_gan, 'time_ji': time_ji
    }
# (Part 1에 이어 붙이세요)

# ==========================================
# 3. 데이터 및 십성 계산 (Calculations) - V2.1 보강
# ==========================================
def get_db_content(db, category, key, subkey=None, subsubkey=None, fallback=""):
    try:
        data = db.get(category, {})
        if subkey:
            if subsubkey:
                return data.get(key, {}).get(subkey, {}).get(subsubkey, fallback)
            return data.get(key, {}).get(subkey, fallback)
        return data.get(key, fallback)
    except:
        return fallback

def calculate_sibseong_counts(day_gan: str, saju_pillars: Dict[str, str]) -> Dict[str, Any]:
    counts = {s: 0.0 for s in SIBSEONG_GROUP_MAP.keys()}
    group_counts = {'비겁': 0.0, '식상': 0.0, '재성': 0.0, '관성': 0.0, '인성': 0.0}

    for target in [saju_pillars['year_gan'], saju_pillars['month_gan'], saju_pillars['time_gan']]:
        sibseong = SIBSEONG_MAP[(day_gan, target)]
        counts[sibseong] += 1.0

    for ji in [saju_pillars['year_ji'], saju_pillars['month_ji'], saju_pillars['day_ji'], saju_pillars['time_ji']]:
        if ji in JIJANGGAN_MAP:
            for target_gan, ratio in JIJANGGAN_MAP[ji].items():
                sibseong = SIBSEONG_MAP[(day_gan, target_gan)]
                counts[sibseong] += ratio
                
    for sib, group in SIBSEONG_GROUP_MAP.items():
        group_counts[group] += counts[sib]
    
    # 일지 암장간 가중치 추가
    day_ji_gan = next(iter(JIJANGGAN_MAP.get(saju_pillars['day_ji'], {}).keys()), None)
    if day_ji_gan:
        day_ji_sibseong = SIBSEONG_MAP[(day_gan, day_ji_gan)]
        counts[day_ji_sibseong] += 0.5
        group_counts[SIBSEONG_GROUP_MAP[day_ji_sibseong]] += 0.5
    
    return {'raw_counts': counts, 'group_counts': group_counts}

# [saju_engine.py] 내부 calculate_five_elements 함수 교체 및 보강

def calculate_five_elements(saju_pillars: Dict[str, str]) -> Dict[str, Any]:
    """
    오행 카운트 계산 (V2.2 보강: 단순 개수 vs 지장간 포함 가중치)
    Return:
        - visual_counts: 명식에 보이는 글자 수 (초보자용)
        - weighted_counts: 지장간 비율을 반영한 실질 세력 (전문가용)
    """
    # 1. 단순 개수 (Visual Count)
    visual_counts = {'목': 0, '화': 0, '금': 0, '수': 0, '토_습': 0, '토_조': 0}
    
    # 2. 가중치 점수 (Weighted Score - 지장간 반영)
    # 천간: 1.0점 / 지지: 지장간 비율대로 분산 (예: 해수 -> 무토 0.25, 갑목 0.25, 임수 0.5)
    weighted_counts = {'목': 0.0, '화': 0.0, '금': 0.0, '수': 0.0, '토_습': 0.0, '토_조': 0.0}

    # 천간 계산 (Visual & Weighted 동일하게 1.0)
    for gan in [saju_pillars['year_gan'], saju_pillars['month_gan'], saju_pillars['day_gan'], saju_pillars['time_gan']]:
        elem = OHENG_MAP[gan]
        visual_counts[elem] += 1
        weighted_counts[elem] += 1.0

    # 지지 계산 (Visual=1.0, Weighted=지장간 비율)
    for ji in [saju_pillars['year_ji'], saju_pillars['month_ji'], saju_pillars['day_ji'], saju_pillars['time_ji']]:
        # Visual
        if ji in OHENG_MAP:
            visual_counts[OHENG_MAP[ji]] += 1
            
        # Weighted (지장간 분해)
        if ji in JIJANGGAN_MAP:
            for hidden_gan, ratio in JIJANGGAN_MAP[ji].items():
                hidden_elem = OHENG_MAP[hidden_gan]
                # 지장간의 토(土)는 습/조 구분이 애매할 수 있으나, OHENG_MAP 매핑을 따름
                weighted_counts[hidden_elem] += ratio

    # 토(土) 합산 처리
    visual_counts['토'] = visual_counts['토_습'] + visual_counts['토_조']
    weighted_counts['토'] = weighted_counts['토_습'] + weighted_counts['토_조']

    return {
        "visual": visual_counts,
        "weighted": weighted_counts
    }

# ==========================================
# 4. 스토리텔링 생성기 (Narrative Generator) - 9개 항목 강제 구현 (V2.1 보강)
# (Rule 9, 10, 5, 8, 11 포함)
# ==========================================

# A. 🔮 타고난 에너지 요약
def generate_intro_summary(saju_pillars, oheng_counts, sibseong_data, db):
    day_gan = saju_pillars['day_gan']
    day_ji = saju_pillars['day_ji']
    
    simple_oheng_counts = {k: v for k, v in oheng_counts.items() if k not in ['토_습', '토_조']}
    main_elem = max(simple_oheng_counts, key=simple_oheng_counts.get)
    main_sibseong = max(sibseong_data['group_counts'], key=sibseong_data['group_counts'].get)
    
    identity_key = f"{day_gan}_{day_ji}"
    identity_data = get_db_content(db, 'identity', identity_key)
    main_keyword = identity_data.get('keywords', ['특별한'])[0]

    story = f"그대는 **{day_gan}** 일간으로 태어났으며, 사주 전반에 **{main_elem}** 기운과 **{main_sibseong}**의 성향이 가장 강하게 지배하고 있네. 이 기운이 자네의 삶을 이끌어갈 중심 축이니 잘 새겨듣게."
    
    if main_elem == '금': story += f"마치 가을 산의 거대한 바위처럼 냉철하고 맺고 끊음이 확실한 결단력을 가졌구먼. "
    elif main_elem == '토': story += f"넓은 대지처럼 포용력이 있으나, 한번 고집을 부리면 산처럼 움직이지 않는구먼. "
    
    story += f"특히 자네의 본원(자아)인 일주(**{day_gan}{day_ji}**)를 보니, **'{main_keyword}'**의 키워드가 자네의 무의식을 지배하고 있어."
    return story

# B. 👤 일주(日柱) 기질 분석
def generate_identity_analysis(saju_pillars, db):
    key = f"{saju_pillars['day_gan']}_{saju_pillars['day_ji']}"
    data = get_db_content(db, 'identity', key)
    
    if not data: return "데이터가 희미하네. 하지만 자네는 특별한 기운을 가졌어."

    story = f"**{saju_pillars['day_gan']}** 일간인 그대는 **{data.get('ko').split('.')[0]}.**"
    story += f" {data.get('ko')}. "
    story += f"자네는 **[{', '.join(data.get('keywords', []))}]**의 성향이 강하니, "
    story += "남들이 흉내 낼 수 없는 자네만의 무기이자, 동시에 자네를 힘들게 하는 족쇄가 될 수도 있음을 명심하게."
    return story

# C. ☔ 환경 및 건강 진단 (콜드 리딩) - Rule 10 구현
def generate_health_diagnosis(oheng_counts, saju_pillars, db):
    is_dry_hot = (oheng_counts.get('화', 0) >= 3.0) or \
                 (oheng_counts.get('화', 0) + oheng_counts.get('토_조', 0) >= 4.0)
    is_cold_wet = (oheng_counts.get('수', 0) >= 3.0) or \
                  (oheng_counts.get('수', 0) + oheng_counts.get('토_습', 0) >= 4.0)
                  
    diag_key = ""
    if is_dry_hot: diag_key = "Dry_Hot_Chart"
    elif is_cold_wet: diag_key = "Cold_Wet_Chart"
        
    data = get_db_content(db, 'symptom_mapping', 'symptom_map', diag_key)
    
    if not data: return "자네의 오행은 비교적 조화롭네. 건강은 자네가 지키는 법이지."

    story = f"**☔ {data.get('name')} (환경 진단)** - 이 신령이 자네의 환경을 먼저 짚어보네."
    story += f"\n* **환경/주거지:** {data.get('environment_cue')}"
    story += f"\n* **신체 증상:** {', '.join(data.get('physical_symptoms', []))}"
    story += f"\n* **정서 리스크:** {data.get('emotional_state')}"

    remedy_map = {'Dry_Hot_Chart': 'fire_problem', 'Cold_Wet_Chart': 'water_problem'}
    remedy_key = remedy_map.get(diag_key)
    remedy_data = get_db_content(db, 'health', 'health_remedy', remedy_key)
    
    story += f"\n\n**신령의 처방:** \"{data.get('shamanic_voice')}\" "
    story += f"몸의 기운을 보강하려면, {remedy_data.get('action_remedy', '규칙적인 생활을')}."
    return story

# D. ⚔️ 특수 살성 및 리스크 (괴강, 재다신약 등) - Rule 5, 8, 11 구현
def generate_special_risks(saju_pillars, sibseong_data, db):
    day_ganji = saju_pillars['day_gan'] + saju_pillars['day_ji']
    is_gwegang = day_ganji in ['경진', '임진', '무술', '경술', '무진']
    
    jaeseong_count = sibseong_data['group_counts'].get('재성', 0)
    self_strength = sibseong_data['group_counts'].get('비겁', 0) + sibseong_data['group_counts'].get('인성', 0)
    
    # Rule 5: 재다신약 로직 조건 강화 (>= 3.5, <= 3.0)
    is_jaedasin_yak = (jaeseong_count >= 3.5) and (self_strength <= 3.0)
    
    lacks = {
        '인성': sibseong_data['group_counts'].get('인성', 0),
        '식상': sibseong_data['group_counts'].get('식상', 0)
    }
    
    results = []
    
    if is_gwegang:
        data = get_db_content(db, 'five_elements_matrix', 'ten_gods_interactions', '무진_괴강살(Gwegang_Star)')
        results.append({
            'title': f"일주(日柱)에 깃든 **괴강살**",
            'content': f"**{data.get('effect_ko', '정보없음')}**"
                       f"\n\n**신령의 처방:** {data.get('remedy_advice', '정보없음')}"
                       f"\n*신령의 일침:* {data.get('shamanic_voice', '정보없음')}"
        })
    
    if is_jaedasin_yak:
        data = get_db_content(db, 'five_elements_matrix', 'ten_gods_interactions', 'Wealth_Dominance')
        results.append({
            'title': "재물에 휘둘리는 **재다신약**",
            'content': f"**{data.get('effect_ko', '정보없음')}** "
                       f"\n\n**신령의 처방:** {data.get('remedy_advice', '정보없음')}"
                       f"\n*신령의 일침:* {data.get('shamanic_voice', '정보없음')}"
        })

    # Rule 8: 인성/식상 결핍 분석 (0.5 이하인 경우)
    for sib_name, count in lacks.items():
        if count <= 0.5:
            if sib_name == '인성':
                results.append({
                    'title': f"정신적 근간 **인성(印星)** 결핍 ({count}점)",
                    'content': f"인성(학문, 어머니, 정신적 지지)이 부족하니, **정신적인 지지나 안정감**이 약하고, **공부나 문서, 계약 운**에서 실속을 챙기기 어려울 수 있네. "
                               f"깊은 사색보다는 **현실적인 행동**이 앞서는 경향이 강하니, 한 번씩 멈추어 배우고 정리하는 시간이 필요하네."
                })
            elif sib_name == '식상':
                 results.append({
                    'title': f"표현력/활동성 **식상(食傷)** 결핍 ({count}점)",
                    'content': f"식상(표현, 재주, 활동력)이 약하니, **내면의 감정을 표현**하는 데 서툴고, **자식(여성)**이나 **식복, 건강** 면에서 부족함을 느낄 수 있네. "
                               f"하고 싶은 말을 꾹 참거나, **행동력 부족**으로 기회를 놓치는 경우가 많으니, 취미나 봉사활동으로 **활동성**을 높여야 하네."
                })
    return results

# E. 💼 직업 및 적성 분석
def generate_career_analysis(sibseong_data, db):
    main_sibseong = max(sibseong_data['group_counts'], key=sibseong_data['group_counts'].get)
    
    mapping = {'비겁': 'Self_Strong', '식상': 'Output_Strong', '재성': 'Wealth_Strong', '관성': 'Official_Strong', '인성': 'Input_Strong'}
    key = mapping.get(main_sibseong)
    data = get_db_content(db, 'career', 'modern_jobs', key)
    
    if not data: return "분석할 데이터가 부족하네."
    
    story = f"그대는 **{main_sibseong}**의 기운이 가장 강하니, 이것이 곧 사회적 능력이네."
    story += f"\n* **타고난 기질:** {data.get('trait', '정보없음')}"
    story += f"\n* **현대 직업:** {data.get('jobs', '정보없음')}"
    story += f"\n* **업무 스타일:** {data.get('work_style', '정보없음')}"
    story += f"\n\n**신령의 충고:** {data.get('shamanic_voice', '정보없음')}"
    return story

# F. 💖 이성/연애 및 재물 심리
def generate_love_psychology(sibseong_data, user_data, db):
    gender = user_data.get('gender')
    jaeseong_count = sibseong_data['group_counts'].get('재성', 0)
    self_strength = sibseong_data['group_counts'].get('비겁', 0) + sibseong_data['group_counts'].get('인성', 0)
    
    story = "그대의 연애 심리는 사주 원국에 깊이 뿌리내리고 있네. "
    
    if gender == '남' and jaeseong_count >= 3.5 and self_strength <= 3.0:
        data = get_db_content(db, 'love', 'conflict_triggers', 'wealth_dominance_male')
        story += f"남성 사주에 재성(여자/돈)은 강하고 신약하니 **재다신약 남성**의 심리가 강하네. "
        story += f"자네는 {data.get('partner_context', '정보없음')}에 휘둘리기 쉽네. "
        story += f"**갈등 원인:** {data.get('fight_reason', '우유부단함')}. "
        story += f"\n\n**신령의 한마디:** \"{data.get('shamanic_voice', '정보없음')}\""
    else:
        # 재다신약 아닐 경우의 기본 해석 (정재가 강할 경우로 가정)
        story += "자네의 **정재** 기운이 강하니, 연애나 결혼 생활에 있어 안정과 착실함을 가장 중요시하네. "
        story += "하지만 지나친 **꼼꼼함**이 때론 상대에게 **잔소리**로 비칠 수 있으니, 유연함을 기르게나. "
    
    return story

# G. ✨ 특수 신살 (도화, 역마, 화개)
def generate_shinsal_analysis(saju_pillars, db):
    shinsal_list = []
    jis = [saju_pillars['year_ji'], saju_pillars['month_ji'], saju_pillars['day_ji'], saju_pillars['time_ji']]
    
    if any(ji in ['자', '묘', '오', '유'] for ji in jis): shinsal_list.append('도화살(Peach_Blossom)')
    if any(ji in ['인', '신', '사', '해'] for ji in jis): shinsal_list.append('역마살(Stationary_Horse)')
    if any(ji in ['진', '술', '축', '미'] for ji in jis): shinsal_list.append('화개살(Art_Cover)')
    
    story = "자네 사주에는 다음의 **특수 신살(神殺)**이 깃들어 있네."
    
    if not shinsal_list:
        story += "특별한 살성은 없으니 평이하나, 큰 재주도 큰 리스크도 없는 무난한 운명이네."
        return story
    
    for shinsal_key in set(shinsal_list):
        data = get_db_content(db, 'shinsal', 'basic_meanings', shinsal_key)
        
        story += f"\n\n**{shinsal_key.split('(')[0]}**"
        story += f"\n- **설명:** {data.get('desc', '정보없음')}"
        story += f"\n- **긍정 발현:** {data.get('positive', '정보없음')}"
        story += f"\n- **부정 발현:** {data.get('negative', '없음')}"

    story += "\n\n이러한 살성들은 잘 쓰면 자네의 **특별한 재능**이 되지만, 잘못 쓰면 **평생의 걸림돌**이 되니 늘 마음을 다스려야 하네."
    return story

# H. ⚡️ 2025년 세운 분석
def generate_yearly_fortune(saju_pillars, db):
    day_gan = saju_pillars['day_gan']
    
    year_data = get_db_content(db, 'timeline', 'yearly_2025_2026', day_gan)
    
    story = f"**⚡️ 2025년 (을사) {get_db_content(db, 'timeline', 'yearly_ganji', '2025', fallback='을사년')} 세운 분석** - **'을사년(乙巳), 푸른 뱀의 해'** 운세"
    story += f"\n\n**주요 기운:** {year_data.get('2025', '정보없음')}"
    
    q4_data = get_db_content(db, 'timeline', 'monthly_highlights_2025', 'Q4_Winter')
    story += f"\n\n**📌 신령의 월별 경고 (Q4):**"
    story += f"\n{q4_data.get('months', '정보없음')}은(는) 올해 마지막 고비네."
    
    sa_hae_data = get_db_content(db, 'compatibility', 'zizhi_interactions', 'Zhi_Chung', '사해충')
    
    story += f"뱀과 돼지가 부딪히니({sa_hae_data.get('ko_desc', '충돌 위험')}), {q4_data.get('risk_event', '리스크 정보 없음')}가 따르네."
    story += f"\n*신령의 일침:* \"{q4_data.get('shamanic_warning', '조심하게')}\""
    
    return story

# I. 🕰️ 라이프사이클 분석 (4단계) - Rule 9 구현
def generate_lifecycle_analysis(saju_pillars, sibseong_data, db):
    day_gan = saju_pillars['day_gan']
    
    year_sib = SIBSEONG_MAP[(day_gan, saju_pillars['year_gan'])]
    month_sib = SIBSEONG_MAP[(day_gan, saju_pillars['month_gan'])]
    day_sib = SIBSEONG_MAP[(day_gan, saju_pillars['day_gan'])]
    time_sib = SIBSEONG_MAP[(day_gan, saju_pillars['time_gan'])]
    
    y_stage_desc = get_db_content(db, 'timeline', 'life_stages_detailed', 'high_school', 'desc')
    y_content = get_db_content(db, 'lifecycle_pillar', 'year_pillar', year_sib, 'ko_desc')
    
    m_stage_desc = get_db_content(db, 'timeline', 'life_stages_detailed', 'social_entry', 'desc')
    m_content = get_db_content(db, 'lifecycle_pillar', 'month_pillar', month_sib, 'ko_desc')
    
    d_stage_desc = get_db_content(db, 'timeline', 'life_stages_detailed', 'expansion', 'desc')
    d_content = get_db_content(db, 'lifecycle_pillar', 'day_pillar', day_sib, 'ko_desc')
    
    t_stage_desc = get_db_content(db, 'timeline', 'life_stages_detailed', 'seniority', 'desc')
    t_content = get_db_content(db, 'lifecycle_pillar', 'time_pillar', time_sib, 'ko_desc')
    
    story = ""
    
    # 초년운 (0~19세)
    story += f"**🕰️ 초년운 (0~19세)** - **'{y_stage_desc}'**의 흐름"
    story += f"\n이 시기의 주요 기운인 **{year_sib}**의 영향으로, {y_content}\n\n"
    
    # 청년운 (20~39세)
    story += f"**🕰️ 청년운 (20~39세)** - **'{m_stage_desc}'**의 흐름"
    story += f"\n이 시기의 주요 기운인 **{month_sib}**의 영향으로, {m_content}\n\n"
    
    # 중년운 (40~59세)
    story += f"**🕰️ 중년운 (40~59세)** - **'{d_stage_desc}'**의 흐름"
    story += f"\n이 시기의 주요 기운인 **{day_sib}**의 영향으로, {d_content}\n\n"
    
    # 말년운 (60세 이후)
    story += f"**🕰️ 말년운 (60세 이후)** - **'{t_stage_desc}'**의 흐름"
    story += f"\n이 시기의 주요 기운인 **{time_sib}**의 영향으로, {t_content}"
    
    return story
# (Part 2에 이어 붙이세요)

# ==========================================
# 5. 메인 프로세서 (Main Processor) - V2.1 통합 (진시간 적용)
# ==========================================

def process_saju_input(user_data: Dict[str, Any], db: Dict) -> Dict[str, Any]:
    # 1-A. 진(眞) 시간 계산 및 적용
    true_dt = get_true_local_time(user_data['birth_dt'], user_data['city'])
    
    # 1-B. 만세력 및 기본 데이터 산출
    saju_pillars = calculate_saju_pillars(true_dt)
    oheng_counts = calculate_five_elements(saju_pillars)
    sibseong_data = calculate_sibseong_counts(saju_pillars['day_gan'], saju_pillars)
    
    # 2. 9가지 분석 항목 생성 (A-I)
    analytics_data = []

    analytics_data.append({"type": "INTRO", "title": "🔮 타고난 에너지 요약", "content": generate_intro_summary(saju_pillars, oheng_counts, sibseong_data, db)})
    analytics_data.append({"type": "IDENTITY", "title": "👤 일주(日柱) 기질 분석", "content": generate_identity_analysis(saju_pillars, db)})
    analytics_data.append({"type": "HEALTH", "title": "☔ 환경 및 건강 진단", "content": generate_health_diagnosis(oheng_counts, saju_pillars, db)})

    special_risks = generate_special_risks(saju_pillars, sibseong_data, db)
    if special_risks:
        content = "\n\n---\n\n".join([f"**{item['title']}**\n{item['content']}" for item in special_risks])
        analytics_data.append({"type": "SPECIAL", "title": "⚔️ 특수 살성 및 리스크 진단", "content": content})

    analytics_data.append({"type": "CAREER", "title": "💼 직업 및 적성 분석", "content": generate_career_analysis(sibseong_data, db)})
    analytics_data.append({"type": "LOVE", "title": "💖 이성/연애 및 재물 심리", "content": generate_love_psychology(sibseong_data, user_data, db)})
    analytics_data.append({"type": "SHINSAL", "title": "✨ 특수 신살 (도화, 역마, 화개)", "content": generate_shinsal_analysis(saju_pillars, db)})
    analytics_data.append({"type": "FORTUNE", "title": "⚡️ 2025년 세운 분석", "content": generate_yearly_fortune(saju_pillars, db)})
    analytics_data.append({"type": "LIFECYCLE", "title": "🕰️ 라이프사이클 분석", "content": generate_lifecycle_analysis(saju_pillars, sibseong_data, db)})

    # UX 개선을 위해 오행/십성 카운트 및 진시간 정보를 추가 반환
    return {
        "user": user_data,
        "true_dt": true_dt, # 진시간 추가
        "saju": saju_pillars,
        "oheng_counts": oheng_counts, 
        "sibseong_data": sibseong_data, 
        "analytics": analytics_data
    }

def get_zizhi_interaction_data(ji1: str, ji2: str, db: Dict) -> Tuple[Optional[str], Optional[Dict]]:
    """두 지지의 상호작용을 계산하고 DB에서 데이터를 가져오는 함수"""
    pair = tuple(sorted([ji1, ji2]))
    
    interaction_key = None
    for k, v in JIJI_INTERACTIONS.items():
        if len(k) == 2 and set(k) == set(pair):
            interaction_key = v
            break
    if not interaction_key: return None, None
    
    source = None
    if '합' in interaction_key: source = 'Six_Harmonies'
    elif '충' in interaction_key: source = 'Zhi_Chung'
    elif '형' in interaction_key: source = 'Zhi_Hyeong'
    
    if source:
        data = get_db_content(db, 'compatibility', 'zizhi_interactions', source, interaction_key)
        if data: return interaction_key, data
    return None, None

def check_ding_ren_harmony(saju_a: Dict, saju_b: Dict) -> bool:
    """丁壬 합(合)이 사주 명식 내에 존재하는지 확인하는 함수 (Rule 6 지원)"""
    gan_list = [saju_a['year_gan'], saju_a['month_gan'], saju_a['day_gan'], saju_a['time_gan'],
                saju_b['year_gan'], saju_b['month_gan'], saju_b['day_gan'], saju_b['time_gan']]
    return '정' in gan_list and '임' in gan_list

def process_love_compatibility(user_a, user_b, db):
    # 진시간 적용
    true_dt_a = get_true_local_time(user_a['birth_dt'], user_a.get('city', 'Seoul'))
    true_dt_b = get_true_local_time(user_b['birth_dt'], user_b.get('city', 'Seoul'))
    
    saju_a = calculate_saju_pillars(true_dt_a)
    saju_b = calculate_saju_pillars(true_dt_b)
    
    gan_a, gan_b = saju_a['day_gan'], saju_b['day_gan']
    ji_a, ji_b = saju_a['day_ji'], saju_b['day_ji']
    
    comp_key = f"{gan_a}_{gan_b}"
    comp_data = get_db_content(db, 'compatibility', comp_key)
    
    base_score = comp_data.get('score', 50)
    adjustment = 0
    
    analytics = []
    zizhi_analysis = []
    
    # 2-1. 일지 (배우자 궁) 상호작용
    ji_interaction_key, ji_data = get_zizhi_interaction_data(ji_a, ji_b, db)
    if ji_interaction_key and ji_data:
        is_clash = '충' in ji_interaction_key or '형' in ji_interaction_key
        prefix = '💥' if is_clash else '✨'
        score_change = -ji_data.get('score_deduction', 0) if is_clash else ji_data.get('score_bonus', 0)
        adjustment += score_change
        zizhi_analysis.append(f"{prefix} **일지(日支)** 상호작용 ({'충돌' if is_clash else '화합'}): {ji_interaction_key}")
        zizhi_analysis.append(f"충돌/화합 형국: {ji_data.get('ko_desc', '정보없음')}")
        zizhi_analysis.append(f"관계 리스크/이득: {ji_data.get('risk', '정보없음')}")
        zizhi_analysis.append(f"점수 영향: {'-' if is_clash else '+'}{abs(score_change)}점 (일지 충돌은 매우 흉함)")

    # 2-2. 월지 (사회/환경 궁) 상호작용
    month_interaction_key, month_data = get_zizhi_interaction_data(saju_a['month_ji'], saju_b['month_ji'], db)
    if month_interaction_key and month_data:
        is_clash = '충' in month_interaction_key or '형' in month_interaction_key
        prefix = '💥' if is_clash else '✨'
        score_change = -month_data.get('score_deduction', 0) if is_clash else month_data.get('score_bonus', 0)
        adjustment += score_change
        zizhi_analysis.append(f"{prefix} **월지(月支)** 상호작용 ({'충돌' if is_clash else '육합/삼합'}): {month_interaction_key}")
        zizhi_analysis.append(f"충돌/화합 형국: {month_data.get('ko_desc', '정보없음')}")
        zizhi_analysis.append(f"관계 리스크/이득: {month_data.get('risk', '정보없음')}")
        zizhi_analysis.append(f"점수 영향: {'-' if is_clash else '+'}{abs(score_change)}점")

    final_score = max(0, min(100, base_score + adjustment))
    
    synergy_data = get_db_content(db, 'love', 'synergy_patterns', 'Five_Elements_Temperature_Complement', '조열보완')
    synergy_desc = f"습윤 보완의 인연. A의 뜨거운 기운을 B가 식혀주는 조후의 인연"
    synergy_desc += f"\n{synergy_data.get('synergy_ko', '정보없음')}" 

    special_pattern_desc = ""
    if check_ding_ren_harmony(saju_a, saju_b) and comp_key in ['정_임', '임_정']:
        adv = get_db_content(db, 'love', 'shamanic_advice', 'jung_im_harmony_deep_advice')
        special_pattern_desc = f"**🔥 특수 연애 패턴 (丁壬合)** - {adv.get('title')}"
        special_pattern_desc += f"\n{adv.get('advice')}"
        special_pattern_desc += f"\n* {adv.get('compatibility_score_note')}"

    analytics.append({
        "type": "RESULT", 
        "title": f"💖 일간(日干) 궁합 분석 - {user_a['name']}({gan_a}) ❤️ {user_b['name']}({gan_b})의 최종 궁합 (총점: **{final_score}점**)", 
        "content": f"{comp_data.get('ko_relation', '분석 불가')} "
                   f"\n\n**천간 기본 점수:** {base_score}점 (100점 만점)"
                   f"\n**최종 점수 합산:** {base_score}점 + ({'+' if adjustment > 0 else ''}{adjustment}점) = **{final_score}점**"
    })
    
    if zizhi_analysis:
        analytics.append({
            "type": "INTERACTION", 
            "title": "💥 지지(地支) 상호작용 진단", 
            "content": "\n\n---\n\n".join(zizhi_analysis)
        })

    analytics.append({"type": "TEMPERATURE", "title": "🌡️ 오행 온도(調候) 보완 분석", "content": synergy_desc})

    if special_pattern_desc:
        analytics.append({"type": "PSYCHOLOGY", "title": "⚔️ 특수 패턴 및 처방", "content": special_pattern_desc})
        
    return {
        "user_a": {"user": user_a, "saju": saju_a, "oheng_counts": calculate_five_elements(saju_a)},
        "user_b": {"user": user_b, "saju": saju_b, "oheng_counts": calculate_five_elements(saju_b)},
        "analytics": analytics
    }
