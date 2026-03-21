import streamlit as st
import requests
import datetime
import google.generativeai as genai

# --- 1. 환경 설정 (강화고등학교 정보) ---
OFFICE_CODE = "E10"  # 인천광역시교육청
SCHOOL_CODE = "7311068" # 강화고등학교

# --- 2. 데이터 수집 함수 ---
def get_meal_info(target_date):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "MLSV_YMD": target_date
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()
        meal_raw = data['mealServiceDietInfo'][1]['row'][0]['DDISH_NM']
        # <br/> 태그 제거 및 텍스트 정제
        meal_clean = meal_raw.replace("<br/>", ", ")
        return meal_clean
    except:
        return "오늘 급식 정보가 없거나 가져올 수 없습니다."

def get_timetable(target_date, grade, class_nm):
    url = "https://open.neis.go.kr/hub/hisTimetable"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "ALL_TI_YMD": target_date,
        "GRADE": grade,
        "CLASS_NM": class_nm
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()
        rows = data['hisTimetable'][1]['row']
        # 점심 이후 5~7교시 추출
        afternoon = [f"{r['PERIO']}교시: {r['ITM_NM']}" for r in rows if r['PERIO'] in ['5', '6', '7']]
        return " | ".join(afternoon)
    except:
        return "시간표 정보가 없습니다."

# --- 3. 매점 데이터 도감 ---
STORE_ITEMS = {
    "음료": ["단 음료(주스/탄산)", "카페인 음료(에너지드링크)", "생수", "이온음료"],
    "아이스크림": ["유제품류", "과일샤베트류", "초코 코팅류"],
    "스낵": ["새우깡", "도리토스", "닭다리 과자"],
    "헬시/간편식": ["단백질바", "훈제계란", "초콜릿", "닭가슴살"],
    "냉동/조리": ["냉동만두", "포켓치킨(매콤)", "포켓치킨(달달)"]
}

# --- 4. Streamlit UI 구성 ---
st.set_page_config(page_title="강화고 컨디션 매니저", page_icon="🛡️")

st.title("🛡️ 강화고 AI 컨디션 매니저")
st.caption("강화고등학교 학생들을 위한 실시간 급식 & 학습 컨디션 가이드")

# 사이드바 설정
with st.sidebar:
    st.header("🔑 설정 & 정보")
    # API 키 입력 (Secrets를 안 쓸 경우 대비)
    user_api_key = st.text_input("Gemini API Key를 입력하세요", type="password")
    
    st.divider()
    grade = st.selectbox("학년", ["1", "2", "3"])
    class_num = st.number_input("반", min_value=1, max_value=15, value=1)
    target_date = datetime.datetime.now().strftime("%Y%m%d")

# 데이터 미리 불러오기
current_meal = get_meal_info(target_date)
current_timetable = get_timetable(target_date, grade, str(class_num))

# 화면 레이아웃
col1, col2 = st.columns(2)
with col1:
    st.subheader("🍱 오늘의 급식")
    st.info(current_meal)

with col2:
    st.subheader("📅 오후 수업 (5-7교시)")
    st.warning(current_timetable)

st.divider()

# --- 5. AI 분석 로직 ---
if st.button("🧠 AI 전문가의 맞춤 컨디션 분석 시작"):
    if not user_api_key:
        st.error("왼쪽 사이드바에 Gemini API Key를 입력해 주세요!")
    else:
        try:
            # API 설정
            genai.configure(api_key=user_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # 매점 정보를 텍스트로 변환
            store_info = "\n".join([f"- {k}: {', '.join(v)}" for k, v in STORE_ITEMS.items()])
            
            # 프롬프트 구성
            prompt = f"""
            너는 강화고등학교의 보건 선생님이자 영양 전문 AI야. 
            아래 데이터를 바탕으로 학생들을 위한 '오후 컨디션 가이드'를 작성해줘.

            [데이터]
            - 급식: {current_meal}
            - 오후 수업: {current_timetable}
            - 매점 메뉴: {store_info}

            [요청사항]
            1. '혈당 스파이크' 지수: 급식 메뉴 중 정제 탄수화물 비중을 분석해 1~100% 점수로 매기고 이유 설명.
            2. 식사 전략: 혈당 안정을 위해 어떤 반찬부터 먹어야 할지 순서 가이드.
            3. 수업 맞춤형 조언: 오후 수업(5-7교시) 과목의 특성(정적/동적)을 고려하여 집중력을 높일 팁 제시.
            4. 매점 꿀조합: 오늘 급식과 수업 스케줄을 고려했을 때, 매점에서 추천할 만한 간식과 절대 피해야 할 간식 1개씩 선정.

            말투는 고등학생에게 말하듯 친근하고 신뢰감 있게 이모지를 섞어서 써줘.
            """
            
            with st.spinner('AI가 식단과 수업을 분석 중입니다...'):
                response = model.generate_content(prompt)
                st.success("✅ 분석 완료!")
                st.markdown(response.text)
                
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

# 하단 정보
st.markdown("---")
st.caption("본 서비스는 나이스 오픈 API와 Google Gemini API를 활용합니다.")
