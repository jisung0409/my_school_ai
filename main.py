import streamlit as st
import google.generativeai as genai
from neispy.client import Neispy  # <--- 이 방식으로 바꿔보세요!
import datetime
import asyncio

# --- [1] API 및 학교 설정 ---
# 💡 Streamlit Secrets에 NEIS_API_KEY와 GEMINI_API_KEY가 등록되어 있어야 합니다.
NEIS_KEY = st.secrets.get("NEIS_API_KEY", "")
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
SCH_CODE = "7311068"
EDU_CODE = "E10"

# --- [2] 날짜 설정 ---
now = datetime.datetime.now()
target_date = now.strftime("%Y%m%d")
display_date = now.strftime("%m월 %d일")

# --- [3] 데이터 수집 로직 수정본 ---
async def get_data(grade, class_nm):
    # Neispy 객체 생성
    neis = Neispy(KEY=NEIS_KEY) 
    
    try:
        # 급식 정보
        meal_data = await neis.mealServiceDietInfo(EDU_CODE, SCH_CODE, MLSV_YMD=target_date)
        meal_list = meal_data[0].DDISH_NM.replace("<br/>", ", ")
    except Exception as e:
        meal_list = None

    try:
        # 시간표 정보
        tt_data = await neis.hisTimetable(EDU_CODE, SCH_CODE, ALL_TI_YMD=target_date, GRADE=grade, CLASS_NM=class_nm)
        afternoon = [f"{t.PERIO}교시: {t.ITM_NM}" for t in tt_data if t.PERIO in ['5', '6', '7']]
        timetable = " | ".join(afternoon)
    except Exception as e:
        timetable = None
        
    return meal_list, timetable

# --- [4] UI 구성 ---
st.set_page_config(page_title="강화고 AI 매니저", page_icon="🛡️")
st.title("🛡️ 강화고 실시간 AI 컨디션 매니저")

with st.sidebar:
    st.header("👤 학생 정보")
    grade = st.selectbox("학년", ["1", "2", "3"])
    class_num = st.number_input("반", min_value=1, max_value=15, value=1)
    if not NEIS_KEY or not GEMINI_KEY:
        st.error("⚠️ Secrets에 API 키를 등록해주세요.")

# 비동기 함수 실행을 위한 이벤트 루프 관리
if NEIS_KEY:
    meal, tt = asyncio.run(get_data(grade, str(class_num)))
else:
    meal, tt = None, None

# 데이터 표시 및 수동 수정 가능 구역
st.info(f"📅 **{display_date}** 실시간 데이터 분석")
col1, col2 = st.columns(2)

with col1:
    st.subheader("🍱 오늘의 급식")
    final_meal = st.text_area("식단", value=meal if meal else "", placeholder="데이터가 없으면 직접 입력하세요.", height=100)

with col2:
    st.subheader("📅 오후 수업 (5-7교시)")
    final_timetable = st.text_area("시간표", value=tt if tt else "", placeholder="데이터가 없으면 직접 입력하세요.", height=100)

# --- [5] Gemini 2.5 분석 실행 ---
if st.button("🧠 AI 분석 리포트 생성"):
    if not GEMINI_KEY:
        st.error("Gemini API 키가 설정되지 않았습니다.")
    elif not final_meal or not final_timetable:
        st.warning("분석할 데이터를 입력해주세요.")
    else:
        try:
            genai.configure(api_key=GEMINI_KEY)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            prompt = f"""
            너는 강화고등학교의 보건 선생님이야. 
            오늘의 급식({final_meal})과 수업({final_timetable})을 바탕으로 
            혈당 관리와 집중력 향상을 위한 짧고 힙한 리포트를 작성해줘.
            """
            
            with st.spinner('Gemini 2.5 분석 중...'):
                response = model.generate_content(prompt)
                st.balloons()
                st.markdown("---")
                st.markdown(response.text)
        except Exception as e:
            st.error(f"분석 오류: {e}")
