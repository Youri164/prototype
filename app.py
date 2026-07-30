import streamlit as st
import requests

# 페이지 기본 설정
st.set_page_config(
    page_title="피싱 탐지 AI 프로토타입",
    page_icon="🛡️",
    layout="centered"
)

st.title("🛡️ AI 기반 메시지 피싱 탐지 시스템")
st.markdown("수신한 메시지와 링크(URL)를 입력하여 사기 위험도를 실시간으로 분석하세요.")

st.markdown("---")

# 사용자 입력 폼
with st.form("phishing_form"):
    st.subheader("📥 분석 대상 입력")
    
    # 메시지 입력창
    message_input = st.text_area(
        "메시지 본문 내용", 
        placeholder="예: [국민은행] 긴급 대출 대상자로 선정되셨습니다. 아래 링크를 통해 신청하세요."
    )
    
    # 링크(URL) 입력창
    url_input = st.text_input(
        "연결된 링크 (URL)", 
        placeholder="예: https://bit.ly/3xyz 또는 http://kb-secure-login.com"
    )
    
    # 분석 실행 버튼
    submitted = st.form_submit_button("🔍 사기 위험 분석 실행")

if submitted:
    if not message_input.strip():
        st.warning("⚠️ 분석할 메시지 내용을 입력해주세요.")
    else:
        with st.spinner("🔄 문맥 정보 및 링크 주소를 분석 중입니다..."):
            try:
                # FastAPI 백엔드 서버로 데이터 전송 (포트 8000)
                response = requests.post(
                    "http://127.0.0.1:8000/analyze",
                    json={"message": message_input, "url": url_input}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    st.markdown("---")
                    st.subheader("📊 분석 결과 리포트")
                    
                    # 위험도에 따른 색상 및 지표 표시
                    score = result.get("risk_score", 0)
                    detected_type = result.get("detected_type", "알 수 없음")
                    reasons = result.get("reasons", [])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(label="최종 위험도 점수", value=f"{score}점 / 100점")
                    with col2:
                        st.metric(label="판정 사기 유형", value=detected_type)
                    
                    # 위험도 게이지바 느낌의 표현
                    if score >= 80:
                        st.error(f"🚨 **고위험 경고:** 해당 메시지는 피싱 사기일 확률이 매우 높습니다!")
                    elif score >= 40:
                        st.warning(f"⚠️ **주의 요망:** 의심스러운 패턴이 발견되었습니다. 주의하세요.")
                    else:
                        st.success(f"✅ **안전:** 특이 사기 패턴이 발견되지 않았습니다.")
                    
                    # 위험 판단 근거 출력
                    st.markdown("### 📌 세부 위험 판단 근거")
                    for idx, reason in enumerate(reasons, 1):
                        st.markdown(f"{idx}. {reason}")
                        
                else:
                    st.error("❌ 백엔드 서버와의 통신에 실패했습니다. FastAPI 서버가 켜져 있는지 확인해주세요.")
                    
            except Exception as e:
                st.error(f"❌ 서버 연결 에러 발생: {e}")