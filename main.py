import streamlit as st
import google.generativeai as genai



# --- 우리 학교 매점 도감 ---
STORE_ITEMS = {
    "음료": ["단 음료(주스/탄산)", "카페인 음료(커피/에너지드링크)", "생수", "이온음료"],
    "아이스크림": ["유제품류(바닐라/초코)", "과일샤베트류", "초콜릿 코팅류"],
    "스낵": ["새우깡(짭짤한 과자)", "도리토스", "닭다리 스낵"],
    "헬시/간편식": ["단백질바", "훈제계란", "초콜릿", "닭가슴살"],
    "냉동/조리": ["냉동만두", "포켓치킨(매콤한맛)", "포켓치킨(달달한맛)"]
}


# 사이드바에서 설정
st.sidebar.title("⚙️ 설정")
api_key = st.sidebar.text_input("Gemini API Key를 입력하세요", type="password")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    st.title("🏫 우리반 AI 컨디션 매니저")

    # (임시) 나이스 API 대신 사용할 가짜 데이터
    dummy_meal = "보리밥, 쇠고기미역국, 떡볶이, 김말이튀김, 깍두기, 쥬시쿨"
    dummy_schedule = "5교시: 수학, 6교시: 영어, 7교시: 체육"

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🍱 오늘의 급식")
        st.info(dummy_meal)
    with col2:
        st.subheader("📅 오후 시간표")
        st.warning(dummy_schedule)

    if st.button("AI 전문가 분석 시작"):
        # 프롬프트에 들어갈 매점 요약 텍스트 생성
store_info = ""
for category, items in STORE_ITEMS.items():
    store_info += f"- {category}: {', '.join(items)}\n"

prompt = f"""
너는 고등학교 보건 선생님이자 영양 전문 AI야. 
학생의 '수업 집중력'과 '신체 건강'을 최우선으로 생각해서 조언해줘.

[입력 데이터]
- 오늘의 급식: {dummy_meal}
- 오후 수업: {dummy_schedule}
- 매점 메뉴: 
{store_info}

[분석 가이드라인]
1. 급식 메뉴 중 '혈당 롤러코스터'를 유발할 위험 요소를 분석해줘.
2. 다음 수업이 정적인지(수학/영어), 동적인지(체육)에 따라 식사 전략을 다르게 줘.
3. 매점 이용 시, '식곤증 방지'를 위해 피해야 할 조합과 추천할 조합을 하나씩 골라줘.
   (예: "다음 시간이 수학이니 당분이 높은 카페인 음료보다는 생수를 마시며 뇌를 깨우세요.")
4. 만약 운동하는 친구라면 매점의 '계란'이나 '닭가슴살'을 언제 먹으면 좋을지도 알려줘.

답변은 고등학생이 읽기 편하게 이모지를 섞어서 친절하게 해줘!
"""
        
        
        response = model.generate_content(prompt)
        st.markdown("---")
        st.subheader("🧠 AI 컨디션 가이드")
        st.write(response.text)
else:
    st.warning("왼쪽 사이드바에 Gemini API Key를 입력하면 시작할 수 있습니다.")
