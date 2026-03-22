import streamlit as st
import google.generativeai as genai
from neispy import Neispy
import datetime
import asyncio

# --- [1] API 및 학교 기본 설정 ---
# Streamlit Secrets에 NEIS_API_KEY와 GEMINI_API_KEY를 꼭 넣어주세요!
NEIS_KEY = st.secrets.get("NEIS_API_KEY", "")
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
SCH_CODE = "7311068" # 강화고등학교
EDU_CODE = "E10"     # 인천광역시교육청

# --- [2] 날짜 로직 (한국 시간 KST 시차 보정) ---
def get_today_kst():
    # 서버 시간(UTC)에 9시간을 더해 한국 시간으로 변환
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_kst = now_utc + datetime.timedelta(hours=9)
    return now_kst.strftime("%Y%m%d"), now_kst.strftime("%m월 %d일")

target_date_str, target_date_pretty = get_today_kst()

# --- [3] 데이터 수집 함수 (neispy 비동기 방식) ---
async def fetch_school_data(grade, class_nm):
    if not NEIS_KEY:
        return "나이스 API 키가 설정되지 않았습니다.", "나이스 API 키가 설정되지 않았습니다."
        
    async with Neispy(KEY=NEIS_KEY) as neis:
        # 1. 급식 정보 가져오기
        try:
            meal_data = await neis.mealServiceDietInfo(EDU_CODE, SCH_CODE, MLSV_YMD=target_date_str)
            meal_res = meal_data[0].DDISH_NM.replace("<br/>", ", ")
        except Exception as e:
            # INFO-200 등 데이터가 없는 경우를 포함한 예외 처리
            meal_res = f"데이터 없음 (사유: {e})"

        # 2. 시간표 정보 가져오기
        try:
            tt_data = await neis.hisTimetable(EDU_CODE, SCH_CODE, ALL_TI_YMD=target_date_str, GRADE=grade, CLASS_NM=class_nm)
            afternoon = [f"{t.PERIO}교시: {t.ITM_NM}" for t in tt_data if t.PERIO in ['5', '6', '7']]
            tt_res = " | ".join(afternoon) if afternoon else "오후 수업 정보 없음"
        except Exception as e:
            tt_res = f"데이터 없음 (사유: {e})"
            
        return meal_res, tt_res

# --- [4] UI 구성 ---
st.set_page_config(page_title="강화고 AI 매니저", page_icon="🛡️", layout="wide")
st.title("🛡️ 강화고 실시간 AI 컨디션 매니저")

with st.sidebar:
    st.header("👤 학생 정보")
    grade = st.selectbox("학년", ["1", "2", "3"])
    class_num = st.number_input("반", min_value=1, max_value=15, value=1)
    st.divider()
    st.caption("날짜 기준: 한국 표준시(KST)")

# 비동기 실행을 위한 이벤트 루프 생성 및 실행
try:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    meal_raw, tt_raw = loop.run_until_complete(fetch_school_data(grade, str(class_num)))
except Exception as e:
    meal_raw, tt_raw = f"연동 실패: {e}", f"연동 실패: {e}"

# --- [5] 화면 표시 및 데이터 편집 ---
st.info(f"📅 **{target_date_pretty}** 분석 리포트")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🍱 오늘의 급식")
    # 나이스에 데이터가 없을 때(INFO-200 등) 수동 입력 유도
    if "데이터 없음" in meal_raw or not meal_raw:
        st.warning("📍 학교에서 급식을 등록하지 않았습니다.")
        final_meal = st.text_area("메뉴를 직접 입력해주세요!", placeholder="예: 돈까스, 샐러드...", height=150)
    else:
        final_meal = st.text_area("식단 확인 (수정 가능)", value=meal_raw, height=150)

with col2:
    st.subheader("📅 오후 수업 (5-7교시)")
    if "데이터 없음" in tt_raw or not tt_raw:
        st.warning("📍 시간표 정보가 등록되지 않았습니다.")
        final_timetable = st.text_area("오후 수업을 직접 입력해주세요!", placeholder="예: 5교시 수학, 6교시 영어...", height=150)
    else:
        final_timetable = st.text_area("시간표 확인 (수정 가능)", value=tt_raw, height=150)

# --- [6] AI 분석 실행 (Gemini 2.5-flash) ---
if st.button("🧠 AI 보건 선생님 분석 시작"):
    if not GEMINI_KEY:
        st.error("Gemini API 키가 없습니다. 사이드바나 Secrets를 확인해주세요.")
    elif not final_meal or not final_timetable:
        st.warning("분석할 식단이나 시간표를 입력해주세요!")
    else:
        try:
            genai.configure(api_key=GEMINI_KEY)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            prompt = f"""
            너는 강화고등학교의 보건 선생님이자 영양사야. 
            오늘의 급식({final_meal})과 오후 수업({final_timetable})을 바탕으로 학생들에게 리포트를 써줘.
            
            1. 혈당 스파이크 지수 (게이지 이모지 활용)
            2. 메뉴 구성을 고려한 추천 식사 순서
            3. 오후 수업 과목에 따른 집중력 관리 팁
            
            강화고 학생들에게 친근하고 힙한 말투로, 이모지를 섞어서 써줘!
            """
            
            with st.spinner('Gemini 2.5가 분석 중입니다...'):
                response = model.generate_content(prompt)
                st.balloons()
                st.markdown("---")
                st.subheader(f"📝 {target_date_pretty} AI 컨디션 리포트")
                st.markdown(response.text)
        except Exception as e:
            st.error(f"AI 분석 중 오류가 발생했습니다: {e}")
