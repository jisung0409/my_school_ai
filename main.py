import streamlit as st
import google.generativeai as genai

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
        prompt = f"""
        너는 고등학생 전문 영양사이며 학습 컨디션 조절 전문가야.
        오늘의 급식: {dummy_meal}
        오후 수업: {dummy_schedule}
        
        위 데이터를 바탕으로 다음을 분석해줘:
        1. '혈당 스파이크' 위험도 (1~100%)와 이유.
        2. 수업 집중력을 높이기 위한 급식 섭취 순서(메뉴 이름을 언급하며).
        3. 수업 특성에 맞는 매점 간식 추천 혹은 주의사항.
        
        전문적이면서도 고등학생에게 다정한 말투로 말해줘.
        """
        
        response = model.generate_content(prompt)
        st.markdown("---")
        st.subheader("🧠 AI 컨디션 가이드")
        st.write(response.text)
else:
    st.warning("왼쪽 사이드바에 Gemini API Key를 입력하면 시작할 수 있습니다.")