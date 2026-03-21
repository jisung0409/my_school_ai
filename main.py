import streamlit as st
import requests
import datetime
import google.generativeai as genai

# --- 1. 환경 설정 및 날짜 로직 ---
OFFICE_CODE = "E10"  # 인천광역시교육청
SCHOOL_CODE = "7311068" # 강화고등학교

def get_target_info():
    """오늘이 평일이면 오늘을, 주말이면 다음주 월요일 날짜를 반환"""
    now = datetime.datetime.now()
    weekday = now.weekday()  # 월:0, 화:1, ..., 토:5, 일:6
    
    is_weekend = False
    if weekday == 5: # 토요일 -> 월요일(+2)
        target = now + datetime.timedelta(days=2)
        is_weekend = True
    elif weekday == 6: # 일요일 -> 월요일(+1)
        target = now + datetime.timedelta(days=1)
        is_weekend = True
    else:
        target = now
        
    return target.strftime("%Y%m%d"), is_weekend, target.strftime("%m월 %d일")

target_date_str, is_weekend, target_date_pretty = get_target_info()

# --- 2. 데이터 수집 함수 (나이스 API) ---
def get_meal_info(date):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {"Type": "json", "ATPT_OFCDC_SC_CODE": OFFICE_CODE, "SD_SCHUL_CODE": SCHOOL_CODE, "MLSV_YMD": date}
    try:
        res = requests.get(url, params=params)
        data = res.json()
        if 'mealServiceDietInfo' in data:
            meal = data['mealServiceDietInfo'][1]['row'][0]['DDISH_NM']
            return meal.replace("<br/>", ", ")
        return "등록된 급식 정보가 없습니다. (방학 혹은 휴일)"
    except:
        return "급식 데이터를 불러오는데 실패했습니다."

def get_timetable(date, grade, class_nm):
    url = "https://open.neis.go.kr/hub/hisTimetable"
    params = {"Type": "json", "ATPT_OFCDC_SC_CODE": OFFICE_CODE, "SD_SCHUL_CODE": SCHOOL_CODE, 
              "ALL_TI_YMD": date, "GRADE": grade, "CLASS_NM": class_nm}
    try:
        res = requests.get(url, params=params)
        data = res.json()
        if 'hisTimetable' in data:
            rows = data['hisTimetable'][1]['row']
            # 점심 이후 5~7교시 추출
            afternoon = [f"{r['PERIO']}교시: {r['ITM_NM']}" for r in rows if r['PERIO'] in ['5', '6', '7']]
            return " | ".join(afternoon)
        return "해당 날짜의 시간표 정보가 없습니다."
    except:
        return "시간표 로딩 실패"

# --- 3. 매점 데이터 ---
STORE_ITEMS = {
    "음료": ["단 음료(주스/탄산)", "카페인 음료", "생수", "이온음료"],
    "아이스크림": ["유제품류", "샤베트류", "초코류"],
    "간식": ["새우깡", "도리토스", "단백질바", "훈제계란", "초콜릿"],
    "냉동식품": ["냉동만두", "포켓치킨(매콤)", "포켓치킨(달달)", "닭가슴살"]
}

# --- 4. UI 구성 ---
st.set_page_config(page_title="강화고 컨디션 매니저", page_icon="🛡️")
st.title("🛡️ 강화고 AI 컨디션 매니저")

# 사이드바 설정
with st.sidebar:
    st.header("🔑 개인 설정")
    user_api_key = st.text_input("Gemini API Key 입력", type="password", help="Google AI Studio에서 발급받은 키를 넣어주세요.")
    st.divider()
    grade = st.selectbox("학년", ["1", "2", "3"])
    class_num = st.number_input("반", min_value=1, max_value=15, value=1)

# 주말 알림 배너 및 월요병 팁
if is_weekend:
    st.success(f"🌟 지금은 즐거운 주말! **다음 주 월요일({target_date_pretty})**의 정보를 미리 분석합니다.")
    with st.expander("🌅 월요병을 이기는 강화고인의 주말 가이드"):
        st.write("1. **일요일 밤 11시 취침:** 월요일 1교시 졸음을 물리치는 유일한 방법!")
        st.write("2. **월요일 시간표 미리보기:** 내일 어떤 책을 챙겨야 할지 확인하세요.")
        st.write("3. **적당한 활동:** 일요일에 너무 누워만 있으면 월요일이 더 힘들어요.")
else:
    st.info(f"📅 오늘({target_date_pretty})의 데이터를 분석합니다.")

# 데이터 불러오기 (주말이면 월요일 데이터, 평일이면 오늘 데이터)
current_meal = get_meal_info(target_date_str)
current_timetable = get_timetable(target_date_str, grade, str(class_num))

# 대시보드 레이아웃
col1, col2 = st.columns(2)
with col1:
    st.subheader("🍱 분석 대상 식단")
    st.info(current_meal)
with col2:
    st.subheader("📅 오후 수업 (5-7교시)")
    st.warning(current_timetable)

# --- 5. AI 분석 로직 (404 에러 수정 버전) ---
if st.button("🧠 AI 전문가의 컨디션 딥-분석 시작"):
    if not user_api_key:
        st.error("왼쪽 사이드바에 API 키를 넣어주세요!")
    else:
        try:
            # API 설정
            genai.configure(api_key=user_api_key)
            
            # 404 에러 방지를 위한 표준 모델 호출 (Pro 우선, 에러시 Flash 권장)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            store_txt = "\n".join([f"- {k}: {', '.join(v)}" for k, v in STORE_ITEMS.items()])
            context = "특히 월요일 아침 컨디션과 '월요병' 예방을 중심으로 조언해줘." if is_weekend else "오늘 오후 수업 집중력을 극대화할 수 있게 도와줘."
            
            prompt = f"""
            너는 강화고등학교 학생들의 건강을 책임지는 AI 보건선생님이야.
            아래 데이터를 바탕으로 {target_date_pretty} 식단/수업 분석 리포트를 작성해줘. {context}

            [입력 데이터]
            - 식단: {current_meal}
            - 오후 수업(5-7교시): {current_timetable}
            - 매점 항목: {store_txt}

            [리포트 포함 내용]
            1. 오늘의 혈당 스파이크 위험도 (게이지 형태 [●●●○○] 및 점수)
            2. 급식 메뉴 중 가장 먼저 먹어야 할 것과 나중에 먹어야 할 것
            3. 오후 수업 과목 특성에 따른 집중력 유지 전략
            4. 오늘 식단과 궁합이 가장 잘 맞는 매점 간식 1개 추천
            
            고등학생이 읽는 것이니 말투는 친절하고 힙하게, 이모지를 적절히 섞어서 써줘!
            """
            
            with st.spinner('AI 보건선생님이 식단과 시간표를 분석 중입니다...'):
                response = model.generate_content(prompt)
                st.balloons() 
                st.markdown("---")
                st.subheader(f"📝 {target_date_pretty} AI 컨디션 리포트")
                st.write(response.text)
                
        except Exception as e:
            st.error(f"분석 중 오류 발생: {e}")
            st.info("💡 만약 404 에러가 계속된다면, 코드의 'gemini-1.5-pro'를 'gemini-1.5-flash'로 바꿔보세요.")
