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

# --- [3] API 데이터 호출 함수 (나이스 키 적용) ---
def fetch_neis_data(url, extra_params, key_name):
    # Secrets에서 나이스 API 키 가져오기
    neis_key = st.secrets.get("NEIS_API_KEY", "")
    
    params = {
        "Type": "json",
        "KEY": neis_key, # 발급받은 키가 여기 들어갑니다!
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
    }
    params.update(extra_params)
    
    try:
        res = requests.get(url, params=params)
        data = res.json()
        if key_name in data:
            return data[key_name][1]['row']
        return None
    except:
        return None

# --- [4] UI 설정 ---
st.set_page_config(page_title="강화고 AI 매니저", page_icon="🛡️", layout="wide")
st.title("🛡️ 강화고 실시간 AI 컨디션 매니저")

# Gemini API 키 설정
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
if not gemini_api_key:
    gemini_api_key = st.sidebar.text_input("Gemini API Key", type="password").strip()

# --- [5] 실시간 데이터 로드 (나이스 API 정식 요청) ---
meal_rows = fetch_neis_data(
    "https://open.neis.go.kr/hub/mealServiceDietInfo", 
    {"MLSV_YMD": target_date_str}, 
    'mealServiceDietInfo'
)

# 학년/반 설정 (시간표용)
with st.sidebar:
    st.divider()
    grade = st.selectbox("학년", ["1", "2", "3"])
    class_num = st.number_input("반", min_value=1, max_value=15, value=1)

timetable_rows = fetch_neis_data(
    "https://open.neis.go.kr/hub/hisTimetable", 
    {"ALL_TI_YMD": target_date_str, "GRADE": grade, "CLASS_NM": str(class_num)}, 
    'hisTimetable'
)

# --- [6] 화면 표시 및 편집 가능 구역 ---
st.info(f"📅 **{target_date_pretty}** 실시간 데이터 분석 중")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🍱 오늘의 급식")
    if meal_rows:
        raw_meal = meal_rows[0]['DDISH_NM'].replace("<br/>", ", ")
        clean_meal = re.sub(r'\([0-9.]+\)', '', raw_meal)
        final_meal = st.text_area("식단 확인 (수정 가능)", value=clean_meal, height=100)
    else:
        st.warning("⚠️ API에 급식 정보가 없습니다. 직접 입력해주세요.")
        final_meal = st.text_area("오늘의 메뉴 입력", placeholder="예: 돈까스, 샐러드...", height=100)

with col2:
    st.subheader("📅 오후 수업 (5-7교시)")
    if timetable_rows:
        afternoon = [f"{r['PERIO']}교시: {r['ITM_NM']}" for r in timetable_rows if r['PERIO'] in ['5', '6', '7']]
        clean_timetable = " | ".join(afternoon)
        final_timetable = st.text_area("시간표 확인 (수정 가능)", value=clean_timetable, height=100)
    else:
        st.warning("⚠️ API에 시간표가 없습니다. 직접 입력해주세요.")
        final_timetable = st.text_area("오후 수업 입력", placeholder="예: 5교시 수학...", height=100)

# --- [7] Gemini 2.5 분석 실행 ---
if st.button("🧠 AI 분석 리포트 생성"):
    if not gemini_api_key:
        st.error("Gemini API 키가 필요합니다!")
    elif not final_meal or not final_timetable:
        st.error("분석할 데이터가 부족합니다.")
    else:
        try:
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            prompt = f"""
            너는 강화고등학교의 영양사 겸 보건 선생님이야.
            오늘의 급식({final_meal})과 오후 수업({final_timetable})을 분석해서
            학생들이 최고의 컨디션을 유지할 수 있게 팁을 줘.
            혈당 스파이크 지수와 식사 순서를 포함하고, 말투는 아주 친근하게!
            """
            
            with st.spinner('Gemini 2.5가 분석 중...'):
                response = model.generate_content(prompt)
                st.balloons()
                st.markdown("---")
                st.markdown(response.text)
        except Exception as e:
            st.error(f"분석 실패: {e}")
