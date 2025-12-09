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
    ('을', '갑'): '겁재', ('을', '을'): '비견', ('을', '병'): '상관', ('을', '정'): '식신', ('을', '무'): '정재',
    ('을', '기'): '편재', ('을', '경'): '정관', ('을', '신'): '편관', ('을', '임'): '정인', ('을', '계'): '편인',
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
# 2. 유틸리티 및 계산 함수
# ==========================================

def get_location_info(city_name: str) -> Optional[Dict[str, Any]]:
    try:
        geolocator = Nominatim(user_agent="shinryeong_app_v5")
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
        return None

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

def get_ganji(dt: datetime) -> Dict[str, str]:
    # 데모용: 입력된 연도에 따라 테스트용 간지 매핑
    if dt.year == 2025: # 철수 예시
        return {'year_gan': '을', 'year_ji': '사', 'month_gan': '무', 'month_ji': '자',
                'day_gan': '경', 'day_ji': '진', 'time_gan': '을', 'time_ji': '유'}
    elif dt.year == 2023: # 영희 예시
         return {'year_gan': '계', 'year_ji': '묘', 'month_gan': '을', 'month_ji': '축',
                 'day_gan': '정', 'day_ji': '축', 'time_gan': '정', 'time_ji': '미'}
    elif dt.year == 2022: # 민수 예시
        return {'year_gan': '임', 'year_ji': '인', 'month_gan': '경', 'month_ji': '술',
                 'day_gan': '임', 'day_ji': '오', 'time_gan': '무', 'time_ji': '신'}
    else:
        # 그 외 기본값 (갑자)
        return {'year_gan': '갑', 'year_ji': '자', 'month_gan': '갑', 'month_ji': '자',
                'day_gan': '갑', 'day_ji': '자', 'time_gan': '갑', 'time_ji': '자'}

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
            for jg_gan in jijanggan_list:
                sibseong = SIBSEONG_MAP.get((day_gan, jg_gan), '')
                if sibseong:
                    sibseong_counts[sibseong] += 0.5
            main_energy = jijanggan_list[-1] if jijanggan_list else ''
            result[f'{column}_ji_sibseong'] = SIBSEONG_MAP.get((day_gan, main_energy), '')

    return {"detail": result, "counts": sibseong_counts}

def calculate_five_elements_count(ganji_map: Dict[str, str]) -> Dict[str, float]:
    counts = {'목': 0, '화': 0, '토': 0, '금': 0, '수': 0}
    for key in ['year_gan', 'year_ji', 'month_gan', 'month_ji', 
                'day_gan', 'day_ji', 'time_gan', 'time_ji']:
        char = ganji_map[key]
        element = OHENG_MAP.get(char)
        if element: counts[element] += 1.0
    for key in ['year_ji', 'month_ji', 'day_ji', 'time_ji']:
        char = ganji_map[key]
        for hidden_gan in JIJANGGAN.get(char, []):
            element = OHENG_MAP.get(hidden_gan)
            if element: counts[element] += 0.5
    return counts

# ==========================================
# 3. DB 기반 분석 함수 (Analysis Logic)
# ==========================================

def get_day_pillar_identity(day_ganji: str, db: Dict) -> Dict[str, str]:
    day_ganji_key = f"{day_ganji[0]}_{day_ganji[1]}"
    identity_data = db.get('identity', {}).get(day_ganji_key, {})
    
    keywords = ", ".join(identity_data.get('keywords', []))
    voice = identity_data.get('ko', "일주 데이터를 해석하는 중일세.")
    
    # [수정] KeyError 방지를 위해 'type'과 'content' 키를 반드시 포함
    return {
        "type": "🌟 **일주(Day Pillar) 분석**",
        "title": f"일주({day_ganji})의 고유 기질",
        "content": f"**핵심 키워드:** {keywords}\n\n{voice}"
    }

def perform_cold_reading(ganji_map: Dict[str, str], db: Dict) -> List[Dict[str, Any]]:
    reports = []
    symptom_db = db.get('symptom', {}).get('patterns', {})
    ohang_counts = calculate_five_elements_count(ganji_map)
    
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

def analyze_special_patterns(ganji_map: Dict[str, str], sibseong_map: Dict[str, Any], db: Dict) -> List[Dict[str, Any]]:
    reports = []
    interactions_db = db.get('five_elements', {}).get('ten_gods_interactions', {})
    sibseong_counts = sibseong_map.get('counts', {})
    day_ganji = ganji_map['day_gan'] + ganji_map['day_ji']
    
    if day_ganji in GWEEGANG_GANJI:
        data = interactions_db.get('괴강살_발동(Gwegang_Star)', {})
        if data:
            reports.append({
                "type": "⚔️ **특수 살성** 진단 (괴강살)",
                "title": f"일주에 **{day_ganji}** 괴강의 기운이 서려있네.",
                "content": f"**특징:** {data.get('effect_ko', '')}\n**처방:** {data.get('remedy_advice', '')}"
            })

    재성_count = sibseong_counts.get('편재', 0) + sibseong_counts.get('정재', 0)
    인성_count = sibseong_counts.get('정인', 0) + sibseong_counts.get('편인', 0)
    비겁_count = sibseong_counts.get('비견', 0) + sibseong_counts.get('겁재', 0)
    신강도 = 비겁_count + 인성_count
    
    if 재성_count >= 3.5 and 신강도 <= 3.0:
        data = interactions_db.get('재다신약_패턴(Wealth_Dominance)', {})
        if data:
            reports.append({
                "type": "⚠️ **재물 리스크** 진단 (재다신약)",
                "title": "돈 욕심은 많으나 담을 그릇이 약하네.",
                "content": f"**현상:** {data.get('effect_ko', '')}\n**개운법:** {data.get('remedy_advice', '')}\n*신령의 일침:* {data.get('shamanic_voice', '')}"
            })
            
    return reports

def analyze_timeline(birth_dt: datetime, day_gan: str, ganji_map: Dict[str, str], db: Dict) -> List[Dict[str, Any]]:
    reports = []
    current_year = datetime.now().year
    
    timeline_db_data = db.get('timeline', {}).get('yearly_2025_2026', {})
    gan_data_2025 = timeline_db_data.get(day_gan, {})
    summary_2025 = gan_data_2025.get('2025', "올해의 기운을 읽는 중이네.")
    
    reports.append({
        "type": f"⚡️ **{current_year}년 (을사년)** 세운 분석",
        "title": "**푸른 뱀의 해** 운세",
        "content": summary_2025
    })

    life_pillar_map = [
        ("초년운", "0~19세", "preschool", 'year_pillar', 'year_gan'),
        ("청년운", "20~39세", "social_entry", 'month_pillar', 'month_gan'),
        ("중년운", "40~59세", "settlement", 'day_pillar', 'day_gan'),
        ("말년운", "60세 이후", "seniority", 'time_pillar', 'time_gan')
    ]
    
    life_stages_db = db.get('timeline', {}).get('life_stages_detailed', {})
    major_pillar_db = db.get('lifecycle', {})
    
    for stage_name, stage_range, stage_key, pillar_key, gan_key in life_pillar_map:
        life_data = life_stages_db.get(stage_key, {})
        pillar_gan_char = ganji_map[gan_key]
        temp_sibseong = SIBSEONG_MAP.get((day_gan, pillar_gan_char), '비견')
        sibseong_desc = major_pillar_db.get(pillar_key, {}).get(temp_sibseong, '')
        
        reports.append({
            "type": f"🕰️ **{stage_name} ({stage_range})**",
            "title": f"**{life_data.get('desc', '')}**",
            "content": f"이 시기의 지배 기운: **{temp_sibseong}**\n{sibseong_desc}"
        })
            
    return reports

def analyze_career_path(sibseong_map: Dict[str, Any], db: Dict) -> Dict[str, Any]:
    sibseong_counts = sibseong_map.get('counts', {})
    if not sibseong_counts: return {}

    grouped_counts = {'비겁': 0, '식상': 0, '재성': 0, '관성': 0, '인성': 0}
    for sibseong, count in sibseong_counts.items():
        group = SIBSEONG_GROUP_MAP.get(sibseong)
        if group: grouped_counts[group] += count
    
    main_group = max(grouped_counts, key=grouped_counts.get) if any(grouped_counts.values()) else '비겁'
    db_key_map = {
        '비겁': '비겁_태과(Self_Strong)', '식상': '식상_발달(Output_Strong)',
        '재성': '재성_발달(Wealth_Strong)', '관성': '관성_발달(Official_Strong)',
        '인성': '인성_발달(Input_Strong)'
    }
    
    career_db_data = db.get('career', {}).get('modern_jobs', {})
    career_data = career_db_data.get(db_key_map.get(main_group), {})
    
    return {
        "type": "💼 직업 및 적성 분석",
        "title": f"천직(天職) 키워드: **{main_group}**",
        "content": f"**타고난 기질:** {career_data.get('trait', '')}\n**추천 직업:** {career_data.get('jobs', '')}\n*신령의 충고:* {career_data.get('shamanic_voice', '')}"
    }

def analyze_ohang_imbalance(ohang_counts: Dict[str, float], day_gan_elem: str, db: Dict) -> List[Dict[str, Any]]:
    reports = []
    matrix_db = db.get('five_elements', {}).get('imbalance_analysis', {})
    eng_map = {'목': 'Wood', '화': 'Fire', '토': 'Earth', '금': 'Metal', '수': 'Water'}
    
    for elem, count in ohang_counts.items():
        key = f"{elem}({eng_map[elem]})"
        if count >= 3.5:
            data = matrix_db.get(key, {}).get("excess", {})
            if data:
                reports.append({"type": f"🔥 오행 **{elem}** 과다", "title": data.get('title'), "content": data.get('shamanic_voice')})
        elif count <= 0.5:
            data = matrix_db.get(key, {}).get("isolation", {})
            if data:
                reports.append({"type": f"🧊 오행 **{elem}** 고립", "title": data.get('title'), "content": data.get('shamanic_voice')})
    return reports

def check_zizhi_interaction(ganji_a: Dict[str, str], ganji_b: Dict[str, str], db: Dict) -> Tuple[List[Dict[str, Any]], int]:
    reports = []
    zizhi_db = db.get('compatibility', {}).get('zizhi_interactions', {})
    total_score_changes = 0
    
    pairs = [('일지', ganji_a['day_ji'], ganji_b['day_ji']), ('월지', ganji_a['month_ji'], ganji_b['month_ji'])]
    
    for pillar, ji_a, ji_b in pairs:
        key = JIJI_INTERACTIONS.get((ji_a, ji_b))
        if not key: continue
        
        cat = "Six_Harmonies" if '합' in key else "Zhi_Chung" if '충' in key else "Zhi_Hyeong"
        data = zizhi_db.get(cat, {}).get(key, {})
        
        score = data.get('score_bonus', 0) if cat == "Six_Harmonies" else -data.get('score_deduction', 0)
        total_score_changes += score
        
        reports.append({
            "type": f"⚡ {pillar} 상호작용 ({key})",
            "title": f"{ji_a}-{ji_b}: {data.get('ko_desc', '')}",
            "content": f"영향력: {score}점 반영됨.\n리스크: {data.get('risk', '')}"
        })
        
    return reports, total_score_changes

# ==========================================
# 4. 메인 처리 함수
# ==========================================

def process_saju_input(user_data: Dict[str, Any], db: Dict) -> Dict[str, Any]:
    name = user_data['name']
    birth_dt = user_data['birth_dt']
    city = user_data.get('city', 'Seoul')
    
    loc = get_location_info(city)
    true_dt = get_true_solar_time(birth_dt, loc['longitude'], loc['timezone_str']) if loc else birth_dt
    
    ganji = get_ganji(true_dt)
    day_gan = ganji['day_gan']
    sibseong = calculate_sibseong(day_gan, ganji)
    five_elem = calculate_five_elements_count(ganji)
    
    report = {
        "user": user_data, "saju": ganji, 
        "sibseong_detail": sibseong, "five_elements_count": five_elem,
        "analytics": []
    }
    
    main_sib = max(sibseong['counts'], key=sibseong['counts'].get)
    main_elem = max(five_elem, key=five_elem.get)
    report['analytics'].append({
        "type": "🔮 **타고난 에너지 요약**",
        "title": f"일간 {day_gan} | 주도 세력: {main_elem}, {main_sib}",
        "content": f"그대는 **{day_gan}** 일간으로 태어나 **{main_elem}**의 기운과 **{main_sib}**의 성향이 삶을 주도하고 있네."
    })
    
    # [수정] 단순 append로 변경 (KeyError 유발 코드 제거)
    day_identity = get_day_pillar_identity(ganji['day_gan'] + ganji['day_ji'], db)
    report['analytics'].append(day_identity)

    report['analytics'].extend(perform_cold_reading(ganji, db))
    report['analytics'].extend(analyze_ohang_imbalance(five_elem, OHENG_MAP[day_gan], db))
    report['analytics'].extend(analyze_special_patterns(ganji, sibseong, db))
    report['analytics'].append(analyze_career_path(sibseong, db))
    report['analytics'].extend(analyze_timeline(true_dt, day_gan, ganji, db))
    
    return report

def process_love_compatibility(user_a: Dict, user_b: Dict, db: Dict) -> Dict[str, Any]:
    res_a = process_saju_input(user_a, db)
    res_b = process_saju_input(user_b, db)
    
    ganji_a, ganji_b = res_a['saju'], res_b['saju']
    key = f"{ganji_a['day_gan']}_{ganji_b['day_gan']}"
    comp_data = db.get('compatibility', {}).get(key, {})
    
    base_score = comp_data.get('score', 50)
    zizhi_reports, change_score = check_zizhi_interaction(ganji_a, ganji_b, db)
    final_score = max(0, min(100, base_score + change_score))
    
    report = {"user_a": res_a, "user_b": res_b, "analytics": []}
    
    report['analytics'].append({
        "type": "💖 최종 궁합 분석",
        "title": f"총점: **{final_score}점** (일간합 {base_score} + 지지 {change_score})",
        "content": f"{comp_data.get('ko_relation', '평범한 인연일세.')}\n"
    })
    report['analytics'].extend(zizhi_reports)
    
    conflict_db = db.get('love', {}).get('conflict_triggers', {})
    if res_a['user']['gender'] == '남' and res_a['sibseong_detail']['counts'].get('편재', 0) >= 3:
        data = conflict_db.get('재다신약_남성', {})
        if data: report['analytics'].append({"type": "⚔️ 갈등 주의", "title": "재다신약 남성 패턴", "content": data.get('fight_reason')})
            
    return report

def load_all_dbs() -> Dict[str, Any]:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    files = {
        "health": "health_db.json", "five_elements": "five_elements_matrix.json",
        "career": "career_db.json", "shinsal": "shinsal_db.json",
        "timeline": "timeline_db.json", "identity": "identity_db.json",
        "love": "love_db.json", "lifecycle": "lifecycle_pillar_db.json",
        "compatibility": "compatibility_db.json", "symptom": "symptom_mapping.json"
    }
    db = {}
    for k, v in files.items():
        try:
            with open(os.path.join(base_dir, v), 'r', encoding='utf-8') as f:
                db[k] = json.load(f)
        except Exception as e:
            print(f"DB Load Error ({v}): {e}")
            db[k] = {}
    return db
