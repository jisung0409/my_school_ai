import streamlit as st
import requests
import datetime
import google.generativeai as genai

# --- [1] 학교 및 지역 설정 (강화고등학교) ---
OFFICE_CODE = "E10"  # 인천광역시교육청
SCHOOL_CODE = "7311068" # 강화고등학교

# --- [2] 날짜 로직 (오늘 날짜 기준) ---
def get_target_info():
    now = datetime.datetime.now()
    # API 조회를 위한 YYYYMMDD 형식
    target_date_str = now.strftime("%Y%m%d")
    # 화면 표시를 위한 월/일 형식
    target_date_pretty = now.strftime("%m월 %d일")
    return target_date_str, target_date_pretty

target_date_str, target_date_pretty = get_target_info()

# --- [3] 실시간 급식 데이터 가져오기 (나이스 API) ---
def get_meal_info(date):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "MLSV_YMD": date
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()
        if 'mealServiceDietInfo' in data:
            # 급식 메뉴 문자열 정리 (줄바꿈 제거 및 쉼표 처리)
            meal = data['mealServiceDietInfo'][1]['row'][0]['DDISH_NM']
            clean_meal = meal.replace("<br/>", ", ")
            # 알레르기 정보 숫자 제거 (선택 사항)
            import re
            clean_meal = re.sub(r'\([0-9.]+\)', '', clean_meal)
            return clean_meal
        return "⚠️ 오늘 급식 정보가 등록되지 않았습니다."
    except Exception as e:
        return f"❌ 급식 데이터를 가져오는 중 오류 발생: {e}"

# --- [4] 실시간 시간표 데이터 가져오기 (나이스 API) ---
def get_timetable(date, grade, class_nm):
    url = "https://open.neis.go.kr/hub/hisTimetable"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE, 
        "ALL_TI_YMD": date,
        "GRADE": grade,
        "CLASS_NM": class_nm
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()
        if 'hisTimetable' in data:
            rows = data['hisTimetable'][1]['row']
            # 오후 수업(5, 6, 7교시)만 필터링
            afternoon = [f"{r['PERIO']}교시: {r['ITM_NM']}" for r in rows if r['PERIO'] in ['5', '6', '7']]
            if not afternoon:
                return "오후 수업 정보가 없습니다."
            return " | ".join(afternoon)
        return "⚠️ 오늘 시간표 정보가 등록되지 않았습니다."
    except Exception as e:
        return f"❌ 시간표 데이터를 가져오는 중 오류 발생: {e}"

# --- [5] UI 구성 및 API 키 설정 ---
st.set_page_config(page_title="강화고 AI 매니저", page_icon="🛡️", layout="wide")
st.title("🛡️ 강화고 실시간 AI 컨디션 매니저")

# API 키 우선순위: Secrets -> Sidebar
api_key = ""
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("✅ 시스템 API 키가 연결되었습니다.")
else:
    with st.sidebar:
        st.warning("🔑 API 키를 설정해주세요.")
        user_input = st.text_input("Gemini API Key", type="password")
        api_key = user_input.strip()

with st.sidebar:
    st.divider()
    st.header("👤 학생 정보")
    grade = st.selectbox("학년", ["1", "2", "3"])
    class_num = st.number_input("반", min_value=1, max_value=15, value=1)

# 데이터 로딩
st.info(f"📅 **{target_date_pretty}**의 실시간 데이터를 분석합니다.")
current_meal = get_meal_info(target_date_str)
current_timetable = get_timetable(target_date_str, grade, str(class_num))

# 대시보드 출력
col1, col2 = st.columns(2)
with col1:
    st.subheader("🍱 오늘의 급식")
    st.success(current_meal)
with col2:
    st.subheader("📅 오후 수업 (5-7교시)")
    st.warning(current_timetable)

# --- [6] AI 분석 실행 (Gemini 2.5-flash) ---
if st.button("🧠 실시간 데이터 기반 AI 분석 시작"):
    if not api_key:
        st.error("API 키를 입력하거나 Secrets 설정을 완료해 주세요!")
    elif "정보가 등록되지 않았습니다" in current_meal:
        st.error("분석할 급식 데이터가 없습니다. 학교에서 식단을 등록했는지 확인해 주세요.")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            prompt = f"""
            너는 강화고등학교의 보건 선생님이자 영양사야. 
            오늘의 실제 데이터({target_date_pretty})를 바탕으로 학생들에게 맞춤형 컨디션 리포트를 작성해줘.

            [입력 데이터]
            - 식단: {current_meal}
            - 오후 수업: {current_timetable}

            [작성 항목]
            1. 오늘의 혈당 스파이크 위험도 (시각적 게이지 포함)
            2. 급식 메뉴를 활용한 최적의 식사 순서 (식이섬유-단백질-탄수화물 순)
            3. 오후 수업 과목들을 고려한 집중력 유지 전략
            4. 오늘 컨디션에 딱 맞는 강화고인의 응원 한마디

            강화고 학생들에게 친근한 형/누나처럼 힙하게, 이모지를 듬뿍 섞어서 작성해줘!
            """
            
            with st.spinner('실시간 데이터를 바탕으로 보건 선생님이 분석 중...'):
                response = model.generate_content(prompt)
                st.balloons()
                st.markdown("---")
                st.subheader(f"📝 {target_date_pretty} 실시간 컨디션 리포트")
                st.markdown(response.text)
                
        except Exception as e:
            st.error(f"AI 분석 중 오류 발생: {e}")
