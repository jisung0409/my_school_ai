import streamlit as st
import requests
import datetime
import google.generativeai as genai

# --- 1. 환경 설정 및 날짜 로직 ---
OFFICE_CODE = "E10"  # 인천광역시교육청
SCHOOL_CODE = "7311068" # 강화고등학교

def get_target_info():
    now = datetime.datetime.now()
    weekday = now.weekday()  
    is_weekend = False
    if weekday == 5: # 토요일
        target = now + datetime.timedelta(days=2)
        is_weekend = True
    elif weekday == 6: # 일요일
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
        else:
            # 주말이나 데이터가 없을 때 나올 가짜 데이터
            return "현미밥, 등뼈김치찌개, 닭강정, 시금치나물, 깍두기, 사과푸딩"
    except:
        return "테스트 식단: 비빔밥, 계란후라이, 약고추장, 팽이버섯된장국, 요구르트"

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
        else:
            # 시간표 데이터가 없을 때 나올 가짜 데이터
            return "5교시: 수학 | 6교시: 영어 | 7교시: 체육"
    except:
        return "5교시: 국어 | 6교시: 과학 | 7교시: 자율"

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

with st.sidebar:
    st.header("🔑 개인 설정")
    user_api_key = st.text_input("Gemini API Key 입력", type="password")
    st.divider()
    grade = st.selectbox("학년", ["1", "2", "3"])
    class_num = st.number_input("반", min_value=1, max_value=15, value=1)

if is_weekend:
    st.success(f"🌟 지금은 즐거운 주말! **다음 주 월요일({target_date_pretty})**의 정보를 미리 분석합니다.")
    with st.expander("🌅 월요병을 이기는 강화고인의 주말 가이드"):
        st.write("1. **일요일 밤 11시 취침:** 월요일 1교시를 깨우는 비결!")
        st.write("2. **식사 순서 조절:** 내일 급식에 닭강정이 있다면 나물부터 드세요.")
else:
    st.info(f"📅 오늘({target_date_pretty})의 데이터를 분석합니다.")

current_meal = get_meal_info(target_date_str)
current_timetable = get_timetable(target_date_str, grade, str(class_num))

col1, col2 = st.columns(2)
with col1:
    st.subheader("🍱 분석 대상 식단")
    st.info(current_meal)
with col2:
    st.subheader("📅 오후 수업 (5-7교시)")
    st.warning(current_timetable)

# --- 5. AI 분석 로직 ---
if st.button("🧠 AI 전문가의 컨디션 딥-분석 시작"):
    if not user_api_key:
        st.error("왼쪽 사이드바에 API 키를 넣어주세요!")
    else:
        try:
            genai.configure(api_key=user_api_key)
            model = genai.GenerativeModel(model_name='models/gemini-1.5-flash-latest')
            
            store_txt = "\n".join([f"- {k}: {', '.join(v)}" for k, v in STORE_ITEMS.items()])
            
            prompt = f"""
            너는 강화고등학교 AI 보건선생님이야.
            식단: {current_meal}
            오후 수업: {current_timetable}
            매점 메뉴: {store_txt}
            
            위 데이터를 바탕으로 혈당 스파이크 위험도, 식사 순서, 수업 집중 전략을 친구처럼 힙하게 조언해줘!
            """
            
            with st.spinner('AI 보건선생님이 분석 중입니다...'):
                response = model.generate_content(prompt)
                st.balloons() 
                st.markdown("---")
                st.subheader("📝 AI 컨디션 리포트")
                st.write(response.text)
        except Exception as e:
            st.error(f"오류 발생: {e}")
