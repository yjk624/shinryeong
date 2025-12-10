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
# 1. 상수 및 기본 맵핑 (Constants)
# ==========================================
GAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]

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
    ('술', '미'): '축술미형', ('자', '묘'): '자묘형', ('오', '오'): '오오형'
}

# ==========================================
# 2. 데이터베이스 로딩 (Strict Loading)
# ==========================================
def load_all_dbs() -> Dict[str, Any]:
    """
    JSON 파일 로딩 (Strict Mode)
    - 파일이 없으면 콘솔에 에러를 찍고, 해당 키를 비워둠.
    - 파일 경로는 app.py가 실행되는 위치 기준(root)과 db_data 폴더 두 곳을 확인.
    """
    db = {}
    # 로드할 파일 목록 (확장자 제외 키값 매핑)
    db_mapping = {
        'identity': ['identity_db.json'],
        'career': ['career_db.json'],
        'health': ['health_db.json'],
        'love': ['love_db.json'],
        'timeline': ['timeline_db.json'],
        'shinsal': ['shinsal_db.json'],
        'lifecycle_pillar': ['lifecycle_pillar_db.json'],
        'five_elements_matrix': ['five_elements_matrix.json', 'five_elements_matrix_db.json'],
        'symptom_mapping': ['symptom_mapping.json', 'symptom_mapping_db.json'],
        'compatibility': ['compatibility_db.json']
    }
    
    base_dir = os.path.dirname(os.path.abspath(__file__)) # 현재 엔진 파일 위치
    possible_dirs = [base_dir, os.path.join(base_dir, 'db_data'), os.getcwd()]

    print(f"🔄 신령 엔진: 데이터베이스 로딩 시작... (검색 경로: {possible_dirs})")

    for key, filenames in db_mapping.items():
        loaded = False
        for filename in filenames:
            for d in possible_dirs:
                file_path = os.path.join(d, filename)
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            db[key] = json.load(f)
                            print(f"✅ 로드 성공: {key} ({filename})")
                            loaded = True
                            break
                    except Exception as e:
                        print(f"❌ 로드 에러 {filename}: {e}")
            if loaded: break
        
        if not loaded:
            print(f"⚠️ 경고: {key}에 해당하는 파일을 찾을 수 없습니다. (파일명: {filenames})")
            db[key] = {} # 빈 딕셔너리로 초기화하여 KeyError 방지

    return db

def get_db_content(db, category, *keys):
    """
    중첩된 딕셔너리에서 값을 안전하게 가져오되, 
    값이 없으면 None을 반환하여 호출자가 알 수 있게 함.
    """
    data = db.get(category, {})
    for k in keys:
        if isinstance(data, dict):
            data = data.get(k)
        else:
            return None
    return data

# ==========================================
# 3. 천문 계산 (만세력)
# ==========================================
def get_julian_day_number(year, month, day):
    if month <= 2: year -= 1; month += 12
    A = year // 100
    B = 2 - A + (A // 4)
    return int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524

def get_ganji_from_jdn(jdn):
    return GAN[(jdn + 9) % 10], JI[(jdn + 1) % 12]

def get_solar_term_month(dt: datetime) -> Tuple[str, int]:
    sun = ephem.Sun()
    sun.compute(ephem.Date(dt))
    lon = math.degrees(sun.hlon)
    if lon < 0: lon += 360
    adjusted_lon = (lon - 315) % 360
    month_idx = int(adjusted_lon // 30)
    return JI[(2 + month_idx) % 12], month_idx

def get_true_local_time(dt: datetime, city_name: str) -> datetime:
    try:
        geolocator = Nominatim(user_agent="Shinryeong_App_V2.4")
        location = geolocator.geocode(city_name)
        if not location: location = geolocator.geocode("Seoul")
        
        longitude = location.longitude
        # 135도(KST 표준) 기준 경도차 보정. (135 - 경도) * 4분
        # 예: 서울(127도) -> (135-127)*4 = 32분 늦음 -> KST 시간에서 32분을 빼야 진시간
        diff_min = (135 - longitude) * 4 
        return dt - timedelta(minutes=diff_min)
    except:
        return dt

def calculate_saju_pillars(dt: datetime) -> Dict[str, str]:
    jdn = get_julian_day_number(dt.year, dt.month, dt.day)
    day_gan, day_ji = get_ganji_from_jdn(jdn)
    
    sun = ephem.Sun()
    sun.compute(ephem.Date(dt))
    lon = math.degrees(sun.hlon) % 360
    
    saju_year = dt.year
    if 270 <= lon < 315 or (dt.month == 1 and lon < 315): saju_year -= 1
        
    year_gan_idx = (saju_year - 4) % 10
    year_ji_idx = (saju_year - 4) % 12
    
    month_ji, m_idx = get_solar_term_month(dt)
    month_gan = GAN[((year_gan_idx % 5 * 2 + 2) + m_idx) % 10]
    
    hour = dt.hour
    time_ji_idx = 0 if hour >= 23 or hour < 1 else (hour + 1) // 2 % 12
    time_gan = GAN[(GAN.index(day_gan) % 5 * 2 + time_ji_idx) % 10]
    
    return {
        'year_gan': GAN[year_gan_idx], 'year_ji': JI[year_ji_idx],
        'month_gan': month_gan, 'month_ji': month_ji,
        'day_gan': day_gan, 'day_ji': day_ji,
        'time_gan': time_gan, 'time_ji': JI[time_ji_idx]
    }

# ==========================================
# 4. 데이터 계산 (오행/십성)
# ==========================================
def calculate_five_elements(saju_pillars: Dict[str, str]) -> Dict[str, Any]:
    visual = {'목': 0, '화': 0, '금': 0, '수': 0, '토_습': 0, '토_조': 0}
    weighted = {'목': 0.0, '화': 0.0, '금': 0.0, '수': 0.0, '토_습': 0.0, '토_조': 0.0}

    # 천간 (가중치 1.0)
    for k in ['year_gan', 'month_gan', 'day_gan', 'time_gan']:
        elem = OHENG_MAP[saju_pillars[k]]
        visual[elem] += 1
        weighted[elem] += 1.0

    # 지지 (가중치 분산)
    for k in ['year_ji', 'month_ji', 'day_ji', 'time_ji']:
        ji = saju_pillars[k]
        if ji in OHENG_MAP:
            visual[OHENG_MAP[ji]] += 1
        
        if ji in JIJANGGAN_MAP:
            for hidden, ratio in JIJANGGAN_MAP[ji].items():
                weighted[OHENG_MAP[hidden]] += ratio

    visual['토'] = visual['토_습'] + visual['토_조']
    weighted['토'] = weighted['토_습'] + weighted['토_조']
    
    return {"visual": visual, "weighted": weighted}

def calculate_sibseong_counts(day_gan, saju_pillars):
    counts = {s: 0.0 for s in SIBSEONG_GROUP_MAP.keys()}
    groups = {'비겁': 0.0, '식상': 0.0, '재성': 0.0, '관성': 0.0, '인성': 0.0}
    
    # 천간
    for k in ['year_gan', 'month_gan', 'time_gan']:
        s = SIBSEONG_MAP[(day_gan, saju_pillars[k])]
        counts[s] += 1.0
    # 지지
    for k in ['year_ji', 'month_ji', 'day_ji', 'time_ji']:
        ji = saju_pillars[k]
        if ji in JIJANGGAN_MAP:
            for h, r in JIJANGGAN_MAP[ji].items():
                s = SIBSEONG_MAP[(day_gan, h)]
                counts[s] += r
    
    for s, g in SIBSEONG_GROUP_MAP.items():
        groups[g] += counts[s]
        
    return {'group_counts': groups}

# ==========================================
# 5. 분석 및 텍스트 생성 (Strict & Rich)
# ==========================================
def generate_intro_summary(saju, oheng, sibseong, db):
    target = oheng['weighted']
    compare = {k: v for k, v in target.items() if k in ['목', '화', '토', '금', '수']}
    main_elem = max(compare, key=compare.get) if compare else '토'
    main_sib = max(sibseong['group_counts'], key=sibseong['group_counts'].get)
    
    key = f"{saju['day_gan']}_{saju['day_ji']}"
    data = get_db_content(db, 'identity', key)
    
    kwd = "특별함"
    if data and 'keywords' in data:
        kwd = data['keywords'][0]
        
    return f"그대는 **{saju['day_gan']}** 일간이며, **{main_elem}** 기운과 **{main_sib}** 성향이 강하네. 자네의 무의식 키워드는 **'{kwd}'**이라네."

def generate_identity_analysis(saju, db):
    key = f"{saju['day_gan']}_{saju['day_ji']}"
    data = get_db_content(db, 'identity', key)
    
    if not data: return f"**{key}**에 대한 일주 데이터를 DB에서 찾을 수 없네. (identity_db 확인 필요)"
    return f"**{saju['day_gan']}{saju['day_ji']} 일주**: {data.get('ko', '설명 없음')}"

def generate_health_diagnosis(oheng, saju, db):
    target = oheng['weighted']
    fire, dry = target.get('화', 0), target.get('토_조', 0)
    water, wet = target.get('수', 0), target.get('토_습', 0)
    wood = target.get('목', 0)
    metal = target.get('금', 0)
    earth = target.get('토', 0)
    
    key = None
    if fire >= 3.0 or (fire+dry) >= 4.0: key = "Dry_Hot_Chart"
    elif water >= 3.0 or (water+wet) >= 4.0: key = "Cold_Wet_Chart"
    elif wood >= 3.5: key = "Wood_Excess_Chart"
    elif metal >= 3.5: key = "Metal_Excess_Chart"
    elif earth >= 3.5: key = "Earth_Excess_Chart"
    
    if not key: return "자네의 오행은 어느 한쪽으로 치우치지 않아 비교적 건강하네."
    
    data = get_db_content(db, 'symptom_mapping', 'symptom_map', key)
    if not data: return f"**{key}** 패턴이 감지되었으나 상세 설명 데이터가 없네."
    
    return f"**☔ {data.get('name')}**: {data.get('environment_cue')}\n\n**신령의 처방:** \"{data.get('shamanic_voice')}\""

def generate_special_risks(saju, sibseong, db):
    results = []
    
    # 1. 재다신약 (Wealth Dominance)
    jaeseong = sibseong['group_counts'].get('재성', 0)
    my_strength = sibseong['group_counts'].get('비겁', 0) + sibseong['group_counts'].get('인성', 0)
    
    if jaeseong >= 3.0 and my_strength <= 3.0:
        data = get_db_content(db, 'five_elements_matrix', 'ten_gods_interactions', 'Wealth_Dominance')
        if data:
            results.append(f"**💰 {data.get('pattern_name')}**: {data.get('effect_ko')}\n*처방:* {data.get('shamanic_voice')}")
    
    # 2. 관살혼잡 (Official Mixed)
    gwansal = sibseong['group_counts'].get('관성', 0)
    if gwansal >= 3.0:
        data = get_db_content(db, 'five_elements_matrix', 'ten_gods_interactions', 'Official_Killings_Mixed')
        if data:
            results.append(f"**⚔️ {data.get('pattern_name')}**: {data.get('effect_ko')}\n*처방:* {data.get('shamanic_voice')}")

    # 3. 괴강살 (Gwegang) - 정확한 매핑 필요
    day_ganji = saju['day_gan'] + saju['day_ji']
    if day_ganji in ['경진', '임진', '무술', '경술', '무진']:
        # JSON 키가 한글인지 영문인지 확인하여 호출
        # user upload db says keys are like "Wealth_Dominance" but Gwegang key might be distinct
        # Assuming generic handling or check specific key if present in uploaded file
        pass 

    # 4. 결핍 (Lack)
    for star in ['인성', '식상']:
        if sibseong['group_counts'].get(star, 0) <= 0.5:
            results.append(f"**📉 {star} 결핍**: 해당 기운이 부족하여 삶의 균형이 흔들릴 수 있네.")

    return results

def generate_career_analysis(sibseong, db):
    main_sib = max(sibseong['group_counts'], key=sibseong['group_counts'].get)
    mapping = {'비겁': '비겁_태과(Self_Strong)', '식상': '식상_발달(Output_Strong)', 
               '재성': '재성_발달(Wealth_Strong)', '관성': '관성_발달(Official_Strong)', 
               '인성': '인성_발달(Input_Strong)'}
    
    key = mapping.get(main_sib)
    data = get_db_content(db, 'career', 'modern_jobs', key)
    
    if not data: return f"**{main_sib}** 기운이 강하나, 직업 데이터를 불러올 수 없네."
    return f"**{main_sib}** 중심의 커리어: {data.get('jobs')}\n\n**신령의 일침:** {data.get('shamanic_voice')}"

def generate_love_psychology(sibseong, user, db):
    gender = user.get('gender', '남')
    jae = sibseong['group_counts'].get('재성', 0)
    gwan = sibseong['group_counts'].get('관성', 0)
    weak = (sibseong['group_counts'].get('비겁', 0) + sibseong['group_counts'].get('인성', 0)) <= 3.0
    
    key = None
    if gender == '남' and jae >= 3.0 and weak: key = 'wealth_dominance_male' # 재다신약 남
    elif gender == '여' and gwan >= 3.0: key = 'official_killing_mixed_female' # 관살혼잡 여
    
    if key:
        data = get_db_content(db, 'love', 'conflict_triggers', key)
        if data:
            return f"**{data.get('pattern_name')}**: {data.get('desc')}\n⚠️ 갈등요인: {data.get('fight_reason')}\n📢 조언: {data.get('shamanic_voice')}"
            
    return "특별히 치우친 연애 패턴은 보이지 않으니, 서로 배려하면 무탈하네."

def generate_shinsal_analysis(saju, db):
    jis = [saju['year_ji'], saju['month_ji'], saju['day_ji'], saju['time_ji']]
    shinsals = []
    
    if any(j in ['자', '오', '묘', '유'] for j in jis): shinsals.append('도화살(Peach_Blossom)')
    if any(j in ['인', '신', '사', '해'] for j in jis): shinsals.append('역마살(Stationary_Horse)')
    if any(j in ['진', '술', '축', '미'] for j in jis): shinsals.append('화개살(Art_Cover)')
    
    results = []
    for s in shinsals:
        data = get_db_content(db, 'shinsal', 'basic_meanings', s)
        if data:
            results.append(f"**{s.split('(')[0]}**: {data.get('desc')}\n(긍정: {data.get('positive')} / 부정: {data.get('negative')})")
            
    if not results: return "특이한 신살은 발견되지 않았네."
    return "\n\n".join(results)

def generate_yearly_fortune(saju, db):
    day_gan = saju['day_gan']
    # 2025 을사년
    ganji_2025 = "을사" 
    
    # 세운 데이터 (일간 기준) - timeline_db 구조 확인 필요
    # 여기서는 timeline_db가 있다고 가정하고 간단 매핑
    
    q4 = get_db_content(db, 'timeline', 'monthly_highlights_2025', 'Q4_Winter')
    if not q4: return "2025년 운세 데이터를 불러올 수 없네."
    
    return f"**2025년(을사년) 총평:** 변화가 많은 해네.\n\n**📌 겨울(Q4) 경고:** {q4.get('energy')}\n{q4.get('advice')}"

def generate_lifecycle_analysis(saju, sibseong, db):
    day_gan = saju['day_gan']
    # 십성 계산
    pillars = {
        'year': (saju['year_gan'], '초년'),
        'month': (saju['month_gan'], '청년'),
        'day': (saju['day_gan'], '중년'),
        'time': (saju['time_gan'], '말년')
    }
    
    result = ""
    for p, (gan, label) in pillars.items():
        sib = SIBSEONG_MAP[(day_gan, gan)]
        # DB 키 매핑: year_pillar, month_pillar ...
        db_key = f"{p}_pillar" 
        
        # 1. 단계 설명 (desc)
        stage_desc = get_db_content(db, 'lifecycle_pillar', db_key, 'desc')
        if not stage_desc: stage_desc = f"{label}운을 의미하네."
        
        # 2. 십성 해석 (ko_desc)
        content = get_db_content(db, 'lifecycle_pillar', db_key, sib, 'ko_desc')
        if not content: content = f"{sib}의 기운이 지배적이네."
        
        result += f"**🕰️ {stage_desc.split('.')[0]} ({label})**: {content}\n\n"
        
    return result

# ==========================================
# 6. 메인 프로세서 (Main Processor)
# ==========================================
def process_saju_input(user_data: Dict[str, Any], db: Dict) -> Dict[str, Any]:
    true_dt = get_true_local_time(user_data['birth_dt'], user_data['city'])
    saju = calculate_saju_pillars(true_dt)
    oheng = calculate_five_elements(saju)
    sibseong = calculate_sibseong_counts(saju['day_gan'], saju)
    
    analytics = []
    
    # 순서대로 분석 생성 및 추가
    analytics.append({"type": "INTRO", "title": "🔮 타고난 에너지", "content": generate_intro_summary(saju, oheng, sibseong, db)})
    analytics.append({"type": "IDENTITY", "title": "👤 일주 기질", "content": generate_identity_analysis(saju, db)})
    analytics.append({"type": "HEALTH", "title": "☔ 건강 및 환경", "content": generate_health_diagnosis(oheng, saju, db)})
    
    risks = generate_special_risks(saju, sibseong, db)
    if risks:
        analytics.append({"type": "SPECIAL", "title": "⚔️ 특수 살성 및 리스크", "content": "\n\n".join(risks)})
        
    analytics.append({"type": "CAREER", "title": "💼 직업 및 적성", "content": generate_career_analysis(sibseong, db)})
    analytics.append({"type": "LOVE", "title": "💖 연애 심리", "content": generate_love_psychology(sibseong, user_data, db)})
    analytics.append({"type": "SHINSAL", "title": "✨ 신살 분석", "content": generate_shinsal_analysis(saju, db)})
    analytics.append({"type": "FORTUNE", "title": "⚡️ 2025년 운세", "content": generate_yearly_fortune(saju, db)})
    analytics.append({"type": "LIFECYCLE", "title": "🕰️ 인생의 흐름", "content": generate_lifecycle_analysis(saju, sibseong, db)})

    return {
        "user": user_data, "true_dt": true_dt, "saju": saju,
        "oheng_counts": oheng, "sibseong_data": sibseong,
        "analytics": analytics
    }

def process_love_compatibility(user_a, user_b, db):
    # 시간 및 명식 계산
    dt_a = get_true_local_time(user_a['birth_dt'], user_a.get('city', 'Seoul'))
    dt_b = get_true_local_time(user_b['birth_dt'], user_b.get('city', 'Seoul'))
    saju_a, saju_b = calculate_saju_pillars(dt_a), calculate_saju_pillars(dt_b)
    
    # 일간 궁합
    gan_a, gan_b = saju_a['day_gan'], saju_b['day_gan']
    comp_key = f"{gan_a}_{gan_b}"
    comp_data = get_db_content(db, 'compatibility', comp_key)
    if not comp_data: comp_data = {'score': 50, 'ko_relation': '일간 관계 데이터 없음'}
    
    base_score = comp_data.get('score', 50)
    adjustment = 0
    
    # 지지 상호작용 (일지/월지)
    interactions = []
    
    # 1. 일지 (배우자궁)
    ji_a, ji_b = saju_a['day_ji'], saju_b['day_ji']
    pair_ji = tuple(sorted([ji_a, ji_b]))
    
    # JIJI_INTERACTIONS 키 찾기
    found_key = None
    for k, v in JIJI_INTERACTIONS.items():
        if len(k) == 2 and set(k) == set(pair_ji):
            found_key = v
            break
            
    if found_key:
        source = 'Six_Harmonies' if '합' in found_key else ('Zhi_Chung' if '충' in found_key else 'Zhi_Hyeong')
        i_data = get_db_content(db, 'compatibility', 'zizhi_interactions', source, found_key)
        
        if i_data:
            score = i_data.get('score_bonus', 0) if '합' in found_key else -i_data.get('score_deduction', 0)
            adjustment += score
            interactions.append(f"**일지 {found_key}**: {i_data.get('ko_desc')} ({score}점)")
            
    final_score = max(0, min(100, base_score + adjustment))
    
    analytics = []
    analytics.append({"type": "RESULT", "title": f"💖 궁합 총점: {final_score}점", 
                      "content": f"**{comp_data.get('ko_relation')}**\n기본 {base_score}점 + 조정 {adjustment}점"})
    
    if interactions:
        analytics.append({"type": "INTERACTION", "title": "지지 상호작용", "content": "\n".join(interactions)})
        
    return {
        "user_a": {"user": user_a, "saju": saju_a, "oheng_counts": calculate_five_elements(saju_a)},
        "user_b": {"user": user_b, "saju": saju_b, "oheng_counts": calculate_five_elements(saju_b)},
        "analytics": analytics
    }
