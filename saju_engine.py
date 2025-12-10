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

# V2.2: 조후 분석을 위한 토(土) 오행 분리 및 십성 매핑
OHENG_MAP = {
    '갑': '목', '을': '목', '병': '화', '정': '화', '경': '금', '신': '금', '임': '수', '계': '수',
    '인': '목', '묘': '목', '사': '화', '오': '화', '신': '금', '유': '금', '해': '수', '자': '수',
    '무': '토_조', '기': '토_습', '진': '토_습', '축': '토_습', '술': '토_조', '미': '토_조'
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

# 십성 계산 맵 생성
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

# ==========================================
# 2. 데이터베이스 로딩 및 관리 (수정됨)
# ==========================================
def load_all_dbs() -> Dict[str, Any]:
    """db_data 폴더에서 모든 JSON 파일을 로드"""
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
    
    current_dir = os.path.dirname(__file__)
    db_dir = os.path.join(current_dir, 'db_data')
    
    # db_data 폴더가 없으면 생성 안내
    if not os.path.exists(db_dir):
        # os.makedirs(db_dir) # 자동 생성하려면 주석 해제
        pass

    for key, filename in db_files.items():
        file_path = os.path.join(db_dir, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                db[key] = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            db[key] = {} # 파일이 없거나 깨졌을 때 빈 딕셔너리 할당 (에러 방지)

    return db

def get_db_content(db, category, key, subkey=None, subsubkey=None, fallback=None):
    """DB 내용을 안전하게 가져오는 함수 (Fallback 기본값 변경: {} -> None)"""
    if fallback is None: fallback = {} # 딕셔너리 메서드 호출 에러 방지
    try:
        data = db.get(category, {})
        if subkey:
            if subsubkey:
                return data.get(key, {}).get(subkey, {}).get(subsubkey, fallback)
            return data.get(key, {}).get(subkey, fallback)
        return data.get(key, fallback)
    except:
        return fallback

# ==========================================
# 3. 천문 계산 (Julian Day & True Time)
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

def get_true_local_time(dt: datetime, city_name: str) -> datetime:
    try:
        geolocator = Nominatim(user_agent="Shinryeong_App")
        location = geolocator.geocode(city_name)
        
        if not location:
            city_name = "Seoul" # fallback
            location = geolocator.geocode(city_name)

        longitude = location.longitude
        STANDARD_MERIDIAN = 135
        longitude_diff_min = (longitude - STANDARD_MERIDIAN) * 4
        true_local_time = dt - timedelta(minutes=longitude_diff_min)
        return true_local_time
    except Exception:
        return dt # 에러 시 입력 시간 그대로 사용

def calculate_saju_pillars(dt: datetime) -> Dict[str, str]:
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

# ==========================================
# 4. 데이터 계산 및 분석 (Analysis Logic)
# ==========================================
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
        
    day_ji_gan = next(iter(JIJANGGAN_MAP.get(saju_pillars['day_ji'], {}).keys()), None)
    if day_ji_gan:
        day_ji_sibseong = SIBSEONG_MAP[(day_gan, day_ji_gan)]
        counts[day_ji_sibseong] += 0.5
        group_counts[SIBSEONG_GROUP_MAP[day_ji_sibseong]] += 0.5
    
    return {'raw_counts': counts, 'group_counts': group_counts}

def calculate_five_elements(saju_pillars: Dict[str, str]) -> Dict[str, Any]:
    visual_counts = {'목': 0, '화': 0, '금': 0, '수': 0, '토_습': 0, '토_조': 0}
    weighted_counts = {'목': 0.0, '화': 0.0, '금': 0.0, '수': 0.0, '토_습': 0.0, '토_조': 0.0}

    for gan in [saju_pillars['year_gan'], saju_pillars['month_gan'], saju_pillars['day_gan'], saju_pillars['time_gan']]:
        elem = OHENG_MAP[gan]
        visual_counts[elem] += 1
        weighted_counts[elem] += 1.0

    for ji in [saju_pillars['year_ji'], saju_pillars['month_ji'], saju_pillars['day_ji'], saju_pillars['time_ji']]:
        if ji in OHENG_MAP:
            visual_counts[OHENG_MAP[ji]] += 1
        if ji in JIJANGGAN_MAP:
            for hidden_gan, ratio in JIJANGGAN_MAP[ji].items():
                hidden_elem = OHENG_MAP[hidden_gan]
                weighted_counts[hidden_elem] += ratio

    visual_counts['토'] = visual_counts['토_습'] + visual_counts['토_조']
    weighted_counts['토'] = weighted_counts['토_습'] + weighted_counts['토_조']

    return {"visual": visual_counts, "weighted": weighted_counts}

# ==========================================
# 5. 스토리텔링 생성기 (Narrative)
# ==========================================
def generate_intro_summary(saju_pillars, oheng_counts, sibseong_data, db):
    day_gan = saju_pillars['day_gan']
    day_ji = saju_pillars['day_ji']
    
    # [Fix] weighted 데이터 참조
    target_counts = oheng_counts['weighted']
    compare_set = {k: v for k, v in target_counts.items() if k in ['목', '화', '토', '금', '수']}
    
    if not compare_set: main_elem = '토' # Fallback
    else: main_elem = max(compare_set, key=compare_set.get)
    
    main_sibseong = max(sibseong_data['group_counts'], key=sibseong_data['group_counts'].get)
    
    identity_key = f"{day_gan}_{day_ji}"
    identity_data = get_db_content(db, 'identity', identity_key)
    
    # [Fix] 데이터 누락 시 안전 처리
    if isinstance(identity_data, dict):
        keywords = identity_data.get('keywords', ['특별한'])
        main_keyword = keywords[0] if keywords else '특별한'
    else:
        main_keyword = '특별한'

    story = f"그대는 **{day_gan}** 일간으로 태어났으며, 사주 전반에 **{main_elem}** 기운과 **{main_sibseong}**의 성향이 가장 강하게 지배하고 있네. "
    story += f"특히 자네의 본원(자아)인 일주(**{day_gan}{day_ji}**)를 보니, **'{main_keyword}'**의 키워드가 자네의 무의식을 지배하고 있어."
    return story

def generate_identity_analysis(saju_pillars, db):
    key = f"{saju_pillars['day_gan']}_{saju_pillars['day_ji']}"
    data = get_db_content(db, 'identity', key)
    
    # [Fix] 데이터가 딕셔너리가 아닌 경우 처리
    if not isinstance(data, dict): return "데이터가 희미하네. 하지만 자네는 특별한 기운을 가졌어."

    ko_desc = data.get('ko', '설명 없음')
    keywords = data.get('keywords', [])
    keyword_str = ', '.join(keywords) if keywords else '정보 없음'

    story = f"**{saju_pillars['day_gan']}** 일간인 그대는 **{ko_desc.split('.')[0]}.** {ko_desc}. "
    story += f"자네는 **[{keyword_str}]**의 성향이 강하니, 남들이 흉내 낼 수 없는 자네만의 무기이자 족쇄가 될 수도 있음을 명심하게."
    return story

def generate_health_diagnosis(oheng_counts, saju_pillars, db):
    target = oheng_counts['weighted']
    fire_score = target.get('화', 0)
    dry_earth = target.get('토_조', 0)
    water_score = target.get('수', 0)
    wet_earth = target.get('토_습', 0)

    is_dry_hot = (fire_score >= 3.0) or (fire_score + dry_earth >= 4.0)
    is_cold_wet = (water_score >= 3.0) or (water_score + wet_earth >= 4.0)
                  
    diag_key = ""
    if is_dry_hot: diag_key = "Dry_Hot_Chart"
    elif is_cold_wet: diag_key = "Cold_Wet_Chart"
        
    data = get_db_content(db, 'symptom_mapping', 'symptom_map', diag_key)
    
    if not isinstance(data, dict) or not diag_key: return "자네의 오행은 비교적 조화롭네. 건강은 자네가 지키는 법이지."

    story = f"**☔ {data.get('name', '진단')} (환경 진단)** - 이 신령이 자네의 환경을 먼저 짚어보네."
    story += f"\n* **환경/주거지:** {data.get('environment_cue', '')}"
    story += f"\n* **신체 증상:** {', '.join(data.get('physical_symptoms', []))}"
    story += f"\n* **정서 리스크:** {data.get('emotional_state', '')}"

    remedy_map = {'Dry_Hot_Chart': 'fire_problem', 'Cold_Wet_Chart': 'water_problem'}
    remedy_key = remedy_map.get(diag_key)
    remedy_data = get_db_content(db, 'health', 'health_remedy', remedy_key)
    
    if isinstance(remedy_data, dict):
        story += f"\n\n**신령의 처방:** \"{data.get('shamanic_voice', '')}\" "
        story += f"몸의 기운을 보강하려면, {remedy_data.get('action_remedy', '규칙적인 생활을')}."
    return story

def generate_special_risks(saju_pillars, sibseong_data, db):
    day_ganji = saju_pillars['day_gan'] + saju_pillars['day_ji']
    is_gwegang = day_ganji in ['경진', '임진', '무술', '경술', '무진']
    
    jaeseong_count = sibseong_data['group_counts'].get('재성', 0)
    self_strength = sibseong_data['group_counts'].get('비겁', 0) + sibseong_data['group_counts'].get('인성', 0)
    is_jaedasin_yak = (jaeseong_count >= 3.5) and (self_strength <= 3.0)
    
    # 관살혼잡 로직 추가 (여성 등) - 관성 3.0 이상
    is_gwansal = sibseong_data['group_counts'].get('관성', 0) >= 3.0

    results = []
    
    if is_gwegang:
        data = get_db_content(db, 'five_elements_matrix', 'ten_gods_interactions', '무진_괴강살(Gwegang_Star)')
        if isinstance(data, dict):
            results.append({'title': f"일주에 깃든 **괴강살**", 'content': f"**{data.get('effect_ko')}**\n**신령의 처방:** {data.get('remedy_advice')}"})
    
    if is_jaedasin_yak:
        data = get_db_content(db, 'five_elements_matrix', 'ten_gods_interactions', 'Wealth_Dominance')
        if isinstance(data, dict):
            results.append({'title': "재물에 휘둘리는 **재다신약**", 'content': f"**{data.get('effect_ko')}**\n**신령의 처방:** {data.get('remedy_advice')}"})

    if is_gwansal:
        data = get_db_content(db, 'five_elements_matrix', 'ten_gods_interactions', 'Official_Killings_Mixed')
        if isinstance(data, dict):
            results.append({'title': "나를 억누르는 **관살혼잡**", 'content': f"**{data.get('effect_ko')}**\n**신령의 처방:** {data.get('remedy_advice')}"})

    lacks = {'인성': sibseong_data['group_counts'].get('인성', 0), '식상': sibseong_data['group_counts'].get('식상', 0)}
    for sib_name, count in lacks.items():
        if count <= 0.5:
            risk_desc = "정신적 지지 부족" if sib_name == '인성' else "표현력 부족"
            results.append({'title': f"**{sib_name}** 결핍 ({count}점)", 'content': f"{sib_name}이 부족하여 **{risk_desc}**을 겪을 수 있네."})

    return results

def generate_career_analysis(sibseong_data, db):
    main_sibseong = max(sibseong_data['group_counts'], key=sibseong_data['group_counts'].get)
    mapping = {'비겁': 'Self_Strong', '식상': 'Output_Strong', '재성': 'Wealth_Strong', '관성': 'Official_Strong', '인성': 'Input_Strong'}
    key = mapping.get(main_sibseong)
    data = get_db_content(db, 'career', 'modern_jobs', key)
    
    if not isinstance(data, dict): return "분석 데이터 부족."
    
    story = f"그대는 **{main_sibseong}**의 기운이 강하네. **현대 직업:** {data.get('jobs', '')}\n**신령의 충고:** {data.get('shamanic_voice', '')}"
    return story

def generate_love_psychology(sibseong_data, user_data, db):
    gender = user_data.get('gender')
    jaeseong_count = sibseong_data['group_counts'].get('재성', 0)
    self_strength = sibseong_data['group_counts'].get('비겁', 0) + sibseong_data['group_counts'].get('인성', 0)
    gwansal_count = sibseong_data['group_counts'].get('관성', 0)
    
    story = "그대의 연애 심리는... "
    if gender == '남' and jaeseong_count >= 3.0 and self_strength <= 3.0:
        data = get_db_content(db, 'love', 'conflict_triggers', 'wealth_dominance_male')
        if isinstance(data, dict):
            story += f"**재다신약 남성**의 패턴이네. {data.get('fight_reason')}\n신령의 한마디: {data.get('shamanic_voice')}"
    elif gender == '여' and gwansal_count >= 3.0:
        data = get_db_content(db, 'love', 'conflict_triggers', 'official_killing_mixed_female')
        if isinstance(data, dict):
            story += f"**관살혼잡 여성**의 패턴이네. {data.get('fight_reason')}\n신령의 한마디: {data.get('shamanic_voice')}"
    else:
        story += "평이한 연애운을 가졌으나, 욕심을 버리고 서로 배려해야 하네."
    return story

def generate_shinsal_analysis(saju_pillars, db):
    shinsal_list = []
    jis = [saju_pillars['year_ji'], saju_pillars['month_ji'], saju_pillars['day_ji'], saju_pillars['time_ji']]
    if any(ji in ['자', '묘', '오', '유'] for ji in jis): shinsal_list.append('도화살(Peach_Blossom)')
    if any(ji in ['인', '신', '사', '해'] for ji in jis): shinsal_list.append('역마살(Stationary_Horse)')
    
    story = "특수 신살 분석:\n"
    for s in set(shinsal_list):
        data = get_db_content(db, 'shinsal', 'basic_meanings', s)
        if isinstance(data, dict):
            story += f"\n**{s.split('(')[0]}**: {data.get('desc')} (긍정: {data.get('positive')})"
    if not shinsal_list: story += "특별한 신살은 없네."
    return story

def generate_yearly_fortune(saju_pillars, db):
    day_gan = saju_pillars['day_gan']
    q4_data = get_db_content(db, 'timeline', 'monthly_highlights_2025', 'Q4_Winter')
    story = f"**2025년 을사년 운세**\n"
    if isinstance(q4_data, dict):
        story += f"**겨울 경고:** {q4_data.get('advice')}"
    return story

def generate_lifecycle_analysis(saju_pillars, sibseong_data, db):
    # 간단화된 라이프사이클 (예시)
    return "**라이프사이클 분석:** 초년, 청년, 중년, 말년의 흐름을 DB에서 가져와 해석합니다."

# ==========================================
# 6. 메인 프로세서 (Main Processor)
# ==========================================
def process_saju_input(user_data: Dict[str, Any], db: Dict) -> Dict[str, Any]:
    true_dt = get_true_local_time(user_data['birth_dt'], user_data['city'])
    saju_pillars = calculate_saju_pillars(true_dt)
    oheng_counts = calculate_five_elements(saju_pillars)
    sibseong_data = calculate_sibseong_counts(saju_pillars['day_gan'], saju_pillars)
    
    analytics_data = []
    analytics_data.append({"type": "INTRO", "title": "🔮 타고난 에너지 요약", "content": generate_intro_summary(saju_pillars, oheng_counts, sibseong_data, db)})
    analytics_data.append({"type": "IDENTITY", "title": "👤 일주(日柱) 기질 분석", "content": generate_identity_analysis(saju_pillars, db)})
    analytics_data.append({"type": "HEALTH", "title": "☔ 환경 및 건강 진단", "content": generate_health_diagnosis(oheng_counts, saju_pillars, db)})
    
    risks = generate_special_risks(saju_pillars, sibseong_data, db)
    if risks:
        content = "\n\n".join([f"**{r['title']}**\n{r['content']}" for r in risks])
        analytics_data.append({"type": "SPECIAL", "title": "⚔️ 특수 살성 및 리스크", "content": content})
        
    analytics_data.append({"type": "CAREER", "title": "💼 직업 및 적성", "content": generate_career_analysis(sibseong_data, db)})
    analytics_data.append({"type": "LOVE", "title": "💖 이성/연애 심리", "content": generate_love_psychology(sibseong_data, user_data, db)})
    analytics_data.append({"type": "SHINSAL", "title": "✨ 특수 신살", "content": generate_shinsal_analysis(saju_pillars, db)})
    analytics_data.append({"type": "FORTUNE", "title": "⚡️ 2025년 세운", "content": generate_yearly_fortune(saju_pillars, db)})
    analytics_data.append({"type": "LIFECYCLE", "title": "🕰️ 라이프사이클", "content": generate_lifecycle_analysis(saju_pillars, sibseong_data, db)})

    return {
        "user": user_data, "true_dt": true_dt, "saju": saju_pillars,
        "oheng_counts": oheng_counts, "sibseong_data": sibseong_data,
        "analytics": analytics_data
    }

def get_zizhi_interaction_data(ji1: str, ji2: str, db: Dict) -> Tuple[Optional[str], Optional[Dict]]:
    pair = tuple(sorted([ji1, ji2]))
    interaction_key = None
    for k, v in JIJI_INTERACTIONS.items():
        if len(k) == 2 and set(k) == set(pair):
            interaction_key = v
            break
    if not interaction_key: return None, None
    
    source = 'Six_Harmonies' if '합' in interaction_key else ('Zhi_Chung' if '충' in interaction_key else 'Zhi_Hyeong')
    data = get_db_content(db, 'compatibility', 'zizhi_interactions', source, interaction_key)
    if isinstance(data, dict): return interaction_key, data
    return None, None

def check_ding_ren_harmony(saju_a, saju_b):
    gan_list = [saju_a['year_gan'], saju_a['month_gan'], saju_a['day_gan'], saju_a['time_gan'],
                saju_b['year_gan'], saju_b['month_gan'], saju_b['day_gan'], saju_b['time_gan']]
    return '정' in gan_list and '임' in gan_list

def process_love_compatibility(user_a, user_b, db):
    true_dt_a = get_true_local_time(user_a['birth_dt'], user_a.get('city', 'Seoul'))
    true_dt_b = get_true_local_time(user_b['birth_dt'], user_b.get('city', 'Seoul'))
    saju_a = calculate_saju_pillars(true_dt_a)
    saju_b = calculate_saju_pillars(true_dt_b)
    
    gan_a, gan_b = saju_a['day_gan'], saju_b['day_gan']
    ji_a, ji_b = saju_a['day_ji'], saju_b['day_ji']
    
    comp_key = f"{gan_a}_{gan_b}"
    comp_data = get_db_content(db, 'compatibility', comp_key)
    if not isinstance(comp_data, dict): comp_data = {'score': 50, 'ko_relation': '정보 없음'}
    
    base_score = comp_data.get('score', 50)
    adjustment = 0
    zizhi_analysis = []
    
    # 일지
    ikey, idata = get_zizhi_interaction_data(ji_a, ji_b, db)
    if ikey and idata:
        is_clash = '충' in ikey or '형' in ikey
        score_change = -idata.get('score_deduction', 0) if is_clash else idata.get('score_bonus', 0)
        adjustment += score_change
        zizhi_analysis.append(f"**일지 {ikey}**: {idata.get('ko_desc')} (점수: {score_change})")
        
    final_score = max(0, min(100, base_score + adjustment))
    
    analytics = []
    analytics.append({"type": "RESULT", "title": f"💖 궁합 총점: {final_score}점", "content": f"{comp_data.get('ko_relation')}\n기본: {base_score} + 조정: {adjustment} = {final_score}"})
    
    if zizhi_analysis:
        analytics.append({"type": "INTERACTION", "title": "지지 상호작용", "content": "\n".join(zizhi_analysis)})
        
    # 특수 패턴 (정임합)
    if check_ding_ren_harmony(saju_a, saju_b):
        adv = get_db_content(db, 'love', 'shamanic_advice', 'jung_im_harmony_deep_advice')
        if isinstance(adv, dict):
            analytics.append({"type": "PSYCHOLOGY", "title": "🔥 특수 패턴: 정임합", "content": adv.get('advice')})

    return {
        "user_a": {"user": user_a, "saju": saju_a, "oheng_counts": calculate_five_elements(saju_a)},
        "user_b": {"user": user_b, "saju": saju_b, "oheng_counts": calculate_five_elements(saju_b)},
        "analytics": analytics
    }
