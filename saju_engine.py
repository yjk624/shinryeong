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
# 1. 상수 및 기본 맵핑 (Constants & Maps)
# ==========================================
GAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]

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

# 십성 맵핑 생성 (자동화)
SIBSEONG_MAP = {}
for i, day in enumerate(GAN):
    for j, target in enumerate(GAN):
        day_elem_idx = i // 2
        target_elem_idx = j // 2
        day_yin_yang = i % 2
        target_yin_yang = j % 2
        
        if day_elem_idx == target_elem_idx:
            SIBSEONG_MAP[(day, target)] = '비견' if day_yin_yang == target_yin_yang else '겁재'
        elif (day_elem_idx + 1) % 5 == target_elem_idx:
            SIBSEONG_MAP[(day, target)] = '식신' if day_yin_yang == target_yin_yang else '상관'
        elif (day_elem_idx + 2) % 5 == target_elem_idx:
            SIBSEONG_MAP[(day, target)] = '편재' if day_yin_yang == target_yin_yang else '정재'
        elif (day_elem_idx + 3) % 5 == target_elem_idx:
            SIBSEONG_MAP[(day, target)] = '편관' if day_yin_yang == target_yin_yang else '정관'
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
# 2. 천문 계산 엔진 (Astronomical Calculation)
# ==========================================

def get_solar_longitude(dt: datetime) -> float:
    """UTC 기준 특정 시각의 태양 황경(Solar Longitude) 계산 (0~360도)"""
    sun = ephem.Sun()
    # PyEphem은 UTC 기준 datetime 객체나 문자열을 받음
    # dt가 timezone info가 없다면 UTC로 가정하거나, KST라면 변환 필요
    # 여기서는 dt가 이미 True Solar Time 보정된 후 UTC로 변환되어 들어온다고 가정하거나,
    # 입력된 dt를 UTC로 변환하여 처리.
    
    # ephem Date 객체로 변환 (UTC 기준)
    date_ephem = ephem.Date(dt)
    sun.compute(date_ephem)
    
    # hlon은 라디안 값이므로 도로 변환
    lon_deg = math.degrees(sun.hlon)
    if lon_deg < 0:
        lon_deg += 360
    return lon_deg

def get_julian_day(dt: datetime) -> float:
    """날짜를 율리우스 적일(Julian Day)로 변환 (일진 계산용)"""
    return ephem.julian_date(dt)

def get_location_info(city_name: str) -> Optional[Dict[str, Any]]:
    """도시 이름 -> 위도, 경도, 타임존"""
    try:
        geolocator = Nominatim(user_agent="shinryeong_v2_1")
        location = geolocator.geocode(city_name)
        if not location: return None
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lng=location.longitude, lat=location.latitude)
        return {"latitude": location.latitude, "longitude": location.longitude, "timezone_str": timezone_str}
    except Exception:
        # Default: Seoul
        return {"latitude": 37.5665, "longitude": 126.9780, "timezone_str": 'Asia/Seoul'}

def calculate_true_solar_time(dt: datetime, longitude: float, timezone_str: str) -> datetime:
    """표준시 -> 진태양시(True Solar Time) 변환"""
    try:
        local_tz = pytz.timezone(timezone_str)
        # 입력된 시간이 naive라면 로컬 타임존으로 가정
        if dt.tzinfo is None:
            local_dt = local_tz.localize(dt)
        else:
            local_dt = dt.astimezone(local_tz)
            
        utc_dt = local_dt.astimezone(pytz.utc)
        
        # 태양의 남중 고도 시간 계산
        observer = ephem.Observer()
        observer.lon = str(longitude) # 도 단위 문자열
        observer.lat = '0' # 위도는 시간 계산에 영향 X
        observer.date = utc_dt
        
        # 태양 위치 계산
        sun = ephem.Sun()
        sun.compute(observer)
        
        # 균시차(Equation of Time) 보정은 ephem next_transit으로 대체 가능
        # 해당 지역의 자오선 통과 시간(남중)과 표준시 자오선(135도 등) 차이 계산
        # 간단하게는 경도차 1도당 4분 보정
        
        # 표준 자오선 (KST: 135.0)
        # 예: 서울(127.0) -> 차이 -8.0도 -> -32분
        # 여기에 균시차까지 더해야 정확하지만, 
        # 명리학에서는 주로 경도에 따른 지방시(LST) 보정을 중요시함.
        
        standard_meridian = 135.0 if 'Seoul' in timezone_str or 'Korea' in timezone_str else 0 # 임시 처리
        # timezone offset 구하기 (분 단위)
        offset_min = local_dt.utcoffset().total_seconds() / 60
        standard_meridian = offset_min / 4 # 역산 (예: 9시간*60 = 540분 / 4 = 135도)
        
        diff_deg = longitude - standard_meridian
        time_diff_minutes = diff_deg * 4
        
        true_solar_dt = dt + timedelta(minutes=time_diff_minutes)
        return true_solar_dt.replace(tzinfo=None) # Naive datetime 반환
        
    except Exception as e:
        print(f"Time calc error: {e}")
        return dt

def calculate_ganji_real(dt: datetime) -> Dict[str, str]:
    """
    [핵심] ephem을 이용한 정밀 사주 계산 로직
    dt: True Solar Time이 적용된 datetime 객체
    """
    
    # UTC 변환 (ephem 계산용)
    # dt는 이미 보정된 지역 시간이므로, 이를 그대로 사용하여 절기 계산
    # (절기 시각은 전 세계 동일 순간이나, 월주 판단은 해당 지역 시간 기준 절기 진입 여부 따짐)
    # 편의상 입력된 dt를 UTC로 간주하고 계산하면 오차가 생길 수 있으므로,
    # 여기서는 단순화하여 '태양 황경'을 기준으로 월을 잡습니다.
    
    solar_lon = get_solar_longitude(dt)
    
    # 1. 연주(Year Pillar) 계산 - 입춘(315도) 기준
    # 입춘점(315도) 이전이면 전년도로 간주
    # 주의: 1월 1일 ~ 입춘 전까지는 전년도 간지
    
    # 태양 황경은 춘분(0도) 기준.
    # 입춘은 315도.
    # 0~315도 사이(춘분~동지~대한)인 경우 -> 해가 바뀌었거나(양력), 아직 안 바뀌었거나(음력/절기)
    # 명리학 연도는 '입춘'에 바뀜.
    
    # 현재 연도의 입춘 시각을 구해서 비교하는 것이 가장 정확하나,
    # 약식으로 황경을 통해 판단.
    # 12월(동지, 270도) 지나고 1월(소한, 285도/대한, 300도) 지남.
    # 315도 미만이면 전년도, 315도 이상이면 금년도? 
    # -> 황경은 360도 루프.
    # 대략 2월 4일 근처.
    
    saju_year = dt.year
    if dt.month == 1:
        saju_year -= 1 # 1월은 무조건 입춘 전
    elif dt.month == 2:
        # 2월은 입춘 시각 전후로 나뉨.
        # 황경 315도 도달 여부 확인
        # 입춘(315도)보다 작으면(314.9...) 전년도
        # 우수(330도) 쪽으로 가고 있으면 현년도
        # 근데 황경은 0~360. 입춘(315) -> 우수(330) -> ... -> 춘분(0)
        # 2월달에 황경이 315보다 작으면 (예: 314도) -> 아직 입춘 전.
        # 315 이상이면 -> 입춘 후.
        if 300 <= solar_lon < 315: # 대한 ~ 입춘 전
            saju_year -= 1
            
    # 천간: 4 = 갑, 5 = 을 ... (연도 끝자리 기준)
    # 1984(갑자) -> 4.
    # 공식: (연도 - 4) % 10
    year_gan_idx = (saju_year - 4) % 10
    year_ji_idx = (saju_year - 4) % 12
    
    year_gan = GAN[year_gan_idx]
    year_ji = JI[year_ji_idx]
    
    # 2. 월주(Month Pillar) 계산 - 절기(Solar Terms) 기준
    # 24절기 매핑 (황경 -> 월지 Index)
    # 인월(1): 입춘(315) ~ 경칩(345)
    # 묘월(2): 경칩(345) ~ 청명(15) ... 0도(춘분) 포함
    # ...
    # 자월(11): 대설(255) ~ 소한(285)
    # 축월(12): 소한(285) ~ 입춘(315)
    
    # 황경을 통해 월지 인덱스 찾기 (인월=0 ... 축월=11 로 매핑 후 보정)
    # 입춘(315)을 0으로 기준 잡기 위해 보정
    
    adj_lon = solar_lon - 315
    if adj_lon < 0: adj_lon += 360
    
    # 한 절기는 15도, 한 달(절기+중기)은 30도
    month_idx_from_in = int(adj_lon // 30) # 0=인월, 1=묘월 ... 11=축월
    
    # 월지 결정
    # JI 리스트: 자(0), 축(1), 인(2)...
    # 인월은 index 2.
    month_ji_idx = (2 + month_idx_from_in) % 12
    month_ji = JI[month_ji_idx]
    
    # 월간 결정 (연두법: 년간 -> 월간)
    # 갑/기 년 -> 병인월 시작 (병=2)
    # 을/경 년 -> 무인월 시작 (무=4)
    # 병/신 년 -> 경인월 시작 (경=6)
    # 정/임 년 -> 임인월 시작 (임=8)
    # 무/계 년 -> 갑인월 시작 (갑=0)
    
    # 공식: (년간idx % 5) * 2 + 2
    month_gan_start_idx = (year_gan_idx % 5 * 2 + 2) % 10
    month_gan_idx = (month_gan_start_idx + month_idx_from_in) % 10
    month_gan = GAN[month_gan_idx]
    
    # 3. 일주(Day Pillar) 계산 - 율리우스 적일 기준
    # 기준일: 1900년 1월 1일 = 갑술일 (일진 계산은 연속적이라 가장 정확)
    base_date = datetime(1900, 1, 1)
    # dt 날짜만 추출
    target_date = datetime(dt.year, dt.month, dt.day)
    days_diff = (target_date - base_date).days
    
    # 1900.1.1 갑술
    # 갑(0), 술(10)
    day_gan_idx = (0 + days_diff) % 10
    day_ji_idx = (10 + days_diff) % 12
    
    # 야자시/조자시 처리 (23:30 ~ 00:00)
    # 현대 명리학 다수설: 23:30 지나면 다음날 자시로 봄 (일진 변경 O) -> 조자시
    # 소수설: 일진은 00:00 변경, 시주는 자시 (일진 변경 X) -> 야자시
    # 여기서는 '조자시' 설 채택 (23:30 넘으면 다음날 일진)
    # (단, calculate_true_solar_time에서 이미 시간이 조정되었을 수 있음)
    # 표준시 기준 23:30은 진태양시로 대략 23:00~24:00 사이.
    # 만약 진태양시 기준으로 시간이 23시를 넘었다면? -> 자시(Next Day)
    
    if dt.hour >= 23:
        # 일진 + 1
        day_gan_idx = (day_gan_idx + 1) % 10
        day_ji_idx = (day_ji_idx + 1) % 12
        # 시지는 자시(0)
        time_ji_idx = 0
    else:
        # 시지 계산 (00:00 ~ 01:00 = 자시? No. 23:30~01:30 = 자시)
        # 진태양시 기준:
        # 23-01: 자, 01-03: 축 ...
        # 공식: (시 + 1) // 2
        time_ji_idx = (dt.hour + 1) // 2 % 12

    day_gan = GAN[day_gan_idx]
    day_ji = JI[day_ji_idx]
    time_ji = JI[time_ji_idx]
    
    # 4. 시주(Time Pillar) 계산 - 일두법
    # 갑/기 일 -> 갑자시
    # 을/경 일 -> 병자시
    # ...
    # 공식: (일간idx % 5 * 2) + 시지idx (단, 자시는 0)
    time_gan_start_idx = (day_gan_idx % 5 * 2) % 10
    time_gan_idx = (time_gan_start_idx + time_ji_idx) % 10
    time_gan = GAN[time_gan_idx]
    
    return {
        'year_gan': year_gan, 'year_ji': year_ji,
        'month_gan': month_gan, 'month_ji': month_ji,
        'day_gan': day_gan, 'day_ji': day_ji,
        'time_gan': time_gan, 'time_ji': time_ji
    }

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
# 3. 분석 함수들 (Analysis Logic - No Changes Needed)
# ==========================================

def get_day_pillar_identity(day_ganji: str, db: Dict) -> Dict[str, str]:
    day_ganji_key = day_ganji[0] + '_' + day_ganji[1]
    identity_data = db.get('identity', {}).get(day_ganji_key, {})
    keywords = ", ".join(identity_data.get('keywords', []))
    voice = identity_data.get('ko', "일주 데이터를 해석하는 중일세.") 
    return {
        "type": "👤 일주(Day Pillar) 분석",
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
    
    # [FIXED Logic] 재다신약: 재성 과다 & 신약
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
    current_year = 2025 # 시스템 날짜 연동 가능
    summary_2025 = db.get('timeline', {}).get('yearly_2025_2026', {}).get(day_gan, {}).get('2025', '운세 데이터 없음')
    reports.append({"type": f"⚡️ 2025년 (을사년) 세운", "title": "푸른 뱀의 해", "content": summary_2025})
    
    # [FIXED Keys] 중년운=expansion, 말년운=seniority(or fallback)
    life_pillar_map = [
        ("초년운", "0~19세", "preschool", 'year_pillar', 'year_gan'),
        ("청년운", "20~39세", "social_entry", 'month_pillar', 'month_gan'),
        ("중년운", "40~59세", "settlement", 'day_pillar', 'day_gan'), # settlement 사용
        ("말년운", "60세 이후", "expansion", 'time_pillar', 'time_gan') # expansion 데이터 활용 (DB 키 한계)
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

def perform_cold_reading(ganji_map: Dict[str, str], db: Dict) -> List[Dict[str, Any]]:
    reports = []
    symptom_db = db.get('symptom', {}).get('patterns', {})
    ohang_counts = calculate_five_elements_count(ganji_map)
    
    if ohang_counts.get('수', 0) >= 3 or ganji_map['month_ji'] in ['해', '자', '축']:
        data = symptom_db.get('습한_사주(Wet_Chart)', {})
        if data:
            reports.append({
                "type": "☔ 습한 사주 (환경 진단)",
                "title": "환경 진단",
                "content": f"**환경/신체:** {data.get('environment', '')} {data.get('body', '')}\n*신령의 일침:* {data.get('shamanic_voice', '')}"
            })
    return reports

def analyze_personal_health_love(ganji_map: Dict[str, str], sibseong_map: Dict[str, Any], db: Dict) -> List[Dict[str, Any]]:
    reports = []
    
    # 1. 건강 (Health) - 가장 약한 오행
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
            
    # 2. 연애 (Love) - 일지 기준
    day_ji = ganji_map['day_ji']
    if day_ji in ['자', '오', '묘', '유']:
        reports.append({"type": "❤️ 연애운 (도화)", "title": "타고난 인기와 매력", "content": "자네는 가만히 있어도 이성이 꼬이는 도화의 기운을 일지에 깔았네."})
    elif day_ji in ['진', '술', '축', '미']: 
         reports.append({"type": "❤️ 연애운 (화개)", "title": "옛 인연과 다시 만날 운", "content": "화려한 연애보다는 정신적으로 통하는 깊은 관계를 선호하네."})
    elif day_ji in ['인', '신', '사', '해']:
        reports.append({"type": "❤️ 연애운 (역마)", "title": "여행지에서 만날 인연", "content": "활동적인 사람과 인연이 깊네. 여행이나 이동 중에 운명의 상대를 만날 확률이 높으니 밖으로 나가게."})
    
    return reports

def check_zizhi_interaction(ganji_a, ganji_b, db):
    reports = []
    zizhi_db = db.get('compatibility', {}).get('zizhi_interactions', {})
    total_score_change = 0
    
    pairs = [('일지', ganji_a['day_ji'], ganji_b['day_ji']), ('월지', ganji_a['month_ji'], ganji_b['month_ji'])]
    for name, a, b in pairs:
        key = JIJI_INTERACTIONS.get((a, b))
        if key:
            cat = 'Six_Harmonies' if '합' in key else 'Zhi_Chung' if '충' in key else 'Zhi_Hyeong'
            data = zizhi_db.get(cat, {}).get(key, {})
            score = data.get('score_bonus', 0) if cat == 'Six_Harmonies' else -data.get('score_deduction', 0)
            total_score_change += score
            reports.append({
                "type": f"✨ {name} 궁합 ({key})",
                "title": f"{a}-{b} 관계",
                "content": f"{data.get('ko_desc', '')}\n**점수 영향:** {score:+d}점"
            })
    return reports, total_score_change

# ==========================================
# 4. 메인 처리 함수 (Main Processing)
# ==========================================

def process_saju_input(user_data: Dict[str, Any], db: Dict) -> Dict[str, Any]:
    name = user_data['name']
    birth_dt = user_data['birth_dt']
    city_name = user_data.get('city', 'Seoul')
    
    location_info = get_location_info(city_name)
    if location_info:
        true_solar_dt = calculate_true_solar_time(birth_dt, location_info['longitude'], location_info['timezone_str'])
    else:
        true_solar_dt = birth_dt # Fallback
        
    # [REAL Calculation Triggered]
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
        "content": f"그대는 **{day_gan}** 일간으로 태어났네. 사주 전반에 **{main_elem}** 기운과 **{main_sib}**의 성향이 강하게 지배하고 있네."
    })
    
    day_ganji = ganji_map['day_gan'] + ganji_map['day_ji']
    report['analytics'].append(get_day_pillar_identity(day_ganji, db))
    
    # 순차적 분석 추가
    report['analytics'].extend(perform_cold_reading(ganji_map, db))
    report['analytics'].extend(analyze_ohang_imbalance(five_elements_count, OHENG_MAP[day_gan], db))
    report['analytics'].extend(analyze_special_patterns(ganji_map, sibseong_map, db))
    report['analytics'].extend(analyze_personal_health_love(ganji_map, sibseong_map, db))
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
    
    # 지지 합충 점수 반영
    zizhi_reports, score_change = check_zizhi_interaction(ganji_a, ganji_b, db)
    final_score = max(0, min(100, base_score + score_change))
    
    comp_analysis = {
        "type": "💖 일간(日干) 궁합 분석", 
        "title": f"최종 궁합 점수: **{final_score}점**", 
        "content": f"{comp_data.get('ko_relation', '')}\n\n(기본 {base_score}점 + 지지 영향 {score_change:+d}점)"
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
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            db[key] = {}
    return db
