import streamlit as st
import requests
import datetime
import google.generativeai as genai

# --- [1] 학교 및 지역 설정 ---
OFFICE_CODE = "E10"  # 인천광역시교육청
SCHOOL_CODE = "7311068" # 강화고등학교

# --- [2] 날짜 로직 (주말엔 월요일 데이터로 점프) ---
def get_target_info():
    now = datetime.datetime.now()
    weekday = now.weekday()  # 월:0, 화:1, ..., 토:5, 일:6
    
    is_weekend = False
    if weekday == 5: # 토요일 -> 월요일(+2일)
        target = now + datetime.timedelta(days=2)
        is_weekend = True
    elif weekday == 6: # 일요일 -> 월요일(+1일)
        target = now + datetime.timedelta(days=1)
        is_weekend = True
    else:
        target = now
        
    return target.strftime("%Y%m%d"), is_weekend, target.strftime("%m월 %d일")

target_date_str, is_weekend, target_date_pretty = get_target_info()

# --- [3] 데이터 수집 (나이스 API + 테스트 데이터) ---
def get_meal_info(date):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {"Type": "json", "ATPT_OFCDC_SC_CODE": OFFICE_CODE, "SD_SCHUL_CODE": SCHOOL_CODE, "MLSV_YMD": date}
    try:
        res = requests.get(url, params=params)
        data = res.json()
        if 'mealServiceDietInfo' in data:
            meal = data['mealServiceDietInfo'][1]['row'][0]['DDISH_NM']
            return meal.replace("<br/>", ", ")
        return "현미밥, 등뼈김치찌개, 닭강정, 시금치나물, 깍두기, 사과푸딩 (테스트용)"
    except:
        return "데이터를 불러올 수 없습니다."

def get_timetable(date, grade, class_nm):
    url = "https://open.neis.go.kr/hub/hisTimetable"
    params = {"Type": "json", "ATPT_OFCDC_SC_CODE": OFFICE_CODE, "SD_SCHUL_CODE": SCHOOL_CODE, 
              "ALL_TI_YMD": date, "GRADE": grade, "CLASS_NM": class_nm}
    try:
        res = requests.get(url, params=params)
        data = res.json()
        if 'hisTimetable' in data:
            rows = data['hisTimetable'][1]['row']
            afternoon = [f"{r['PERIO']}교시: {r['ITM_NM']}" for r in rows if r['PERIO'] in ['5', '6', '7']]
            return " | ".join(afternoon)
        return "5교시: 수학 | 6교시: 영어 | 7교시: 체육 (테스트용)"
    except:
        return "시간표 정보 없음"

# --- [4] UI 구성 및 API 키 로직 ---
st.set_page_config(page_title="강화고 AI 매니저", page_icon="🛡️", layout="wide")
st.title("🛡️ 강화고 AI 컨디션 매니저")

# API 키 가져오기 (Secrets 우선, 없으면 사이드바 입력)
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
    grade = st.selectbox("학년", ["1", "2", "3"])
    class_num = st.number_input("반", min_value=1, max_value=15, value=1)

# 상태 안내
if is_weekend:
    st.success(f"🌟 **주말 모드** | 내일 월요일({target_date_pretty})의 컨디션을 분석합니다.")
else:
    st.info(f"📅 **평일 모드** | 오늘({target_date_pretty})의 데이터를 분석합니다.")

current_meal = get_meal_info(target_date_str)
current_timetable = get_timetable(target_date_str, grade, str(class_num))

col1, col2 = st.columns(2)
with col1:
    st.subheader("🍱 분석 대상 식단")
    st.info(current_meal)
with col2:
    st.subheader("📅 오후 수업 (5-7교시)")
    st.warning(current_timetable)

# --- [5] AI 분석 실행 (Gemini 2.5-flash 기준) ---
if st.button("🧠 AI 전문가의 딥-분석 시작"):
    if not api_key:
        st.error("사이드바에 API 키를 입력하거나 Secrets 설정을 확인해 주세요!")
    else:
        try:
            genai.configure(api_key=api_key)
            # 확인된 차세대 모델 사용
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            prompt = f"""
            너는 강화고등학교의 보건 선생님이자 영양사야. 
            날짜: {target_date_pretty}
            식단: {current_meal}
            수업: {current_timetable}

            위 데이터를 바탕으로:
            1. 혈당 스파이크 지수 (게이지 표시)
            2. 최적의 식사 순서 가이드
            3. 오후 수업 집중력 팁 (과목별 맞춤형)
            4. 추천 매점 간식 1개

            학생들에게 말하듯 친근하고 힙하게, 이모지를 섞어서 써줘!
            """
            
            with st.spinner('차세대 모델이 분석 중입니다...'):
                response = model.generate_content(prompt)
                st.balloons()
                st.markdown("---")
                st.subheader(f"📝 {target_date_pretty} AI 컨디션 리포트")
                st.markdown(response.text)
                
        except Exception as e:
            st.error(f"오류 발생: {e}")
