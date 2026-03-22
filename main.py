import streamlit as st
import requests
import datetime
import google.generativeai as genai
import re

# --- [1] 학교 및 지역 설정 ---
OFFICE_CODE = "E10"  # 인천광역시교육청
SCHOOL_CODE = "7311068" # 강화고등학교

# --- [2] 날짜 로직 ---
def get_target_info():
    now = datetime.datetime.now()
    return now.strftime("%Y%m%d"), now.strftime("%m월 %d일")

target_date_str, target_date_pretty = get_target_info()

# --- [3] 데이터 수집 함수 (API 호출) ---
def fetch_api_data(url, params, key):
    try:
        res = requests.get(url, params=params)
        data = res.json()
        if key in data:
            return data[key][1]['row']
        return None
    except:
        return None

# --- [4] UI 및 로직 시작 ---
st.set_page_config(page_title="강화고 AI 매니저", page_icon="🛡️", layout="wide")
st.title("🛡️ 강화고 실시간 AI 컨디션 매니저")

# API 키 설정 (Secrets 또는 Sidebar)
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    with st.sidebar:
        st.warning("🔑 API 키를 설정해주세요.")
        api_key = st.text_input("Gemini API Key", type="password").strip()

with st.sidebar:
    st.divider()
    st.header("👤 학생 정보")
    grade = st.selectbox("학년", ["1", "2", "3"])
    class_num = st.number_input("반", min_value=1, max_value=15, value=1)

# --- [5] 실시간 데이터 로드 시도 ---
meal_rows = fetch_api_data("https://open.neis.go.kr/hub/mealServiceDietInfo", 
                          {"Type": "json", "ATPT_OFCDC_SC_CODE": OFFICE_CODE, "SD_SCHUL_CODE": SCHOOL_CODE, "MLSV_YMD": target_date_str}, 
                          'mealServiceDietInfo')

timetable_rows = fetch_api_data("https://open.neis.go.kr/hub/hisTimetable", 
                               {"Type": "json", "ATPT_OFCDC_SC_CODE": OFFICE_CODE, "SD_SCHUL_CODE": SCHOOL_CODE, "ALL_TI_YMD": target_date_str, "GRADE": grade, "CLASS_NM": str(class_num)}, 
                               'hisTimetable')

# --- [6] 데이터 표시 및 수동 입력 로직 ---
st.info(f"📅 **{target_date_pretty}** 분석 리포트")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🍱 오늘의 급식")
    if meal_rows:
        meal_text = meal_rows[0]['DDISH_NM'].replace("<br/>", ", ")
        meal_text = re.sub(r'\([0-9.]+\)', '', meal_text) # 알레르기 번호 제거
        current_meal = st.text_area("식단 확인/수정", value=meal_text, height=100)
    else:
        st.error("⚠️ 급식 정보가 API에 없습니다.")
        current_meal = st.text_area("직접 식단을 입력해주세요 (예: 제육볶음, 된장국...)", height=100)

with col2:
    st.subheader("📅 오후 수업 (5-7교시)")
    if timetable_rows:
        afternoon = [f"{r['PERIO']}교시: {r['ITM_NM']}" for r in timetable_rows if r['PERIO'] in ['5', '6', '7']]
        timetable_text = " | ".join(afternoon)
        current_timetable = st.text_area("시간표 확인/수정", value=timetable_text, height=100)
    else:
        st.error("⚠️ 시간표 정보가 API에 없습니다.")
        current_timetable = st.text_area("직접 수업을 입력해주세요 (예: 5교시 수학, 6교시 영어...)", height=100)

# --- [7] AI 분석 실행 ---
if st.button("🧠 AI 분석 시작 (Gemini 2.5-flash)"):
    if not api_key:
        st.error("API 키를 입력해주세요!")
    elif not current_meal or not current_timetable:
        st.warning("식단과 시간표를 모두 입력해야 분석이 가능합니다.")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            prompt = f"강화고 영양사 선생님으로서 {target_date_pretty} 식단({current_meal})과 오후 수업({current_timetable})을 분석해서 혈당 스파이크 지수, 식사 순서, 수업 집중 전략을 힙하게 알려줘!"
            
            with st.spinner('차세대 AI가 분석 중...'):
                response = model.generate_content(prompt)
                st.balloons()
                st.markdown("---")
                st.subheader("📝 맞춤형 컨디션 리포트")
                st.markdown(response.text)
        except Exception as e:
            st.error(f"오류 발생: {e}")
