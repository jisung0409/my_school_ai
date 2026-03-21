import streamlit as st
import requests
import datetime
import google.generativeai as genai

# --- 1. 기본 설정 (강화고등학교) ---
OFFICE_CODE = "E10" 
SCHOOL_CODE = "7311068"

# --- 2. 날짜 계산 로직 (주말이면 월요일로 점프) ---
def get_target_info():
    now = datetime.datetime.now()
    weekday = now.weekday()  # 월:0 ~ 일:6
    
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

# --- 3. 데이터 수집 함수 (나이스 API + 테스트 데이터) ---
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
            # 주말이나 방학 등 데이터가 없을 때 AI 테스트를 위한 가짜 데이터
            return "현미밥, 등뼈김치찌개, 닭강정, 시금치나물, 깍두기, 사과푸딩"
    except:
        return "비빔밥, 계란후라이, 약고추장, 팽이버섯된장국, 요구르트 (테스트용)"

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
            return "5교시: 수학 | 6교시: 영어 | 7교시: 체육 (테스트용)"
    except:
        return "5교시: 국어 | 6교시: 과학 | 7교시: 자율 (테스트용)"

# --- 4. UI 구성 (Streamlit) ---
st.set_page_config(page_title="강화고 AI 매니저", page_icon="🛡️")
st.title("🛡️ 강화고 AI 컨디션 매니저")

with st.sidebar:
    st.header("🔑 개인 설정")
    user_api_key = st.text_input("Gemini API Key 입력", type="password")
    st.divider()
    grade = st.selectbox("학년", ["1", "2", "3"])
    class_num = st.number_input("반", min_value=1, max_value=15, value=1)

# 상단 안내 배너
if is_weekend:
    st.success(f"🌟 지금은 주말! **다음 주 월요일({target_date_pretty})** 식단을 분석합니다.")
    with st.expander("🌅 강화고인을 위한 월요병 방지 가이드"):
        st.write("1. **취침 시간 조절:** 일요일 밤 11시 전에는 꼭 잠들기!")
        st.write("2. **식단 확인:** 내일 급식 메뉴를 미리 보고 마음의 준비(?) 하기.")
else:
    st.info(f"📅 오늘({target_date_pretty})의 데이터를 분석합니다.")

# 데이터 불러오기
current_meal = get_meal_info(target_date_str)
current_timetable = get_timetable(target_date_str, grade, str(class_num))

# 화면 레이아웃
col1, col2 = st.columns(2)
with col1:
    st.subheader("🍱 분석 대상 식단")
    st.info(current_meal)
with col2:
    st.subheader("📅 오후 수업 (5-7교시)")
    st.warning(current_timetable)

# --- 5. AI 분석 로직 (안정적인 1.0-pro 버전) ---
if st.button("🧠 AI 전문가의 딥-분석 시작"):
    if not user_api_key:
        st.error("왼쪽 사이드바에 Gemini API Key를 입력해 주세요!")
    else:
        try:
            # 1. 공백 제거 및 설정
            api_key = user_api_key.strip()
            genai.configure(api_key=api_key)
            
            # 2. 내 키가 쓸 수 있는 모델 중 가장 좋은 거 하나 고르기
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            if not available_models:
                st.error("이 키로 사용할 수 있는 모델이 하나도 없습니다.")
            else:
                # 1.5-flash가 있으면 쓰고, 없으면 첫 번째 모델 선택
                target_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
                st.info(f"🛰️ 사용 중인 모델: {target_model}")
                
                model = genai.GenerativeModel(target_model)
                response = model.generate_content(f"{current_meal} 분석해줘.")
                st.write(response.text)
                st.balloons()
                
        except Exception as e:
            st.error(f"❌ 최종 오류 발생: {e}")
            prompt = f"""
            너는 강화고등학교의 보건 선생님이자 영양 전문 AI야. 
            아래 데이터를 바탕으로 {target_date_pretty} 리포트를 작성해줘.

            [데이터]
            - 식단: {current_meal}
            - 수업: {current_timetable}

            [요청사항]
            1. '혈당 스파이크' 지수를 게이지 형태로 표현하고 이유 설명.
            2. 급식 메뉴 중 어떤 반찬부터 먹어야 할지 순서 가이드.
            3. 오후 수업 과목 특성을 고려하여 집중력을 높일 팁 제시.
            4. 오늘 식단에 어울리는 매점 간식 1개 추천.

            말투는 강화고 학생에게 말하듯 친근하고 힙하게 이모지를 섞어서 써줘.
            """
            
            with st.spinner('AI 보건선생님이 식단을 분석 중입니다...'):
                response = model.generate_content(prompt)
                st.balloons() 
                st.markdown("---")
                st.subheader(f"📝 {target_date_pretty} 컨디션 리포트")
                st.write(response.text)
                
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
            st.info("API 키가 정확한지, 혹은 할당량이 초과되지 않았는지 확인해 보세요.")
