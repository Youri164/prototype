import streamlit as st
import re

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
    
    message_input = st.text_area(
        "메시지 본문 내용", 
        placeholder="예: [국민은행] 긴급 대출 대상자로 선정되셨습니다. 아래 링크를 통해 신청하세요."
    )
    
    url_input = st.text_input(
        "연결된 링크 (URL)", 
        placeholder="예: https://bit.ly/3xyz 또는 http://kb-secure-login.com"
    )
    
    submitted = st.form_submit_button("🔍 사기 위험 분석 실행")

if submitted:
    if not message_input.strip():
        st.warning("⚠️ 분석할 메시지 내용을 입력해주세요.")
    else:
        with st.spinner("🔄 문맥 정보 및 링크 주소를 분석 중입니다..."):
            
            # --- [통합된 룰베이스 분석 로직] ---
            text = message_input
            url = url_input if url_input else ""
            
            risk_score = 10
            detected_type = "정상 (안전)"
            reasons = []

            # 룰 1: 국민은행 사칭
            if "국민은행" in text and ("입금" in text or "긴급" in text or "대출" in text):
                if "kb-secure" not in url and "kbstar.com" not in url:
                    risk_score = 95
                    detected_type = "국민은행 사칭 피싱 (고위험)"
                    reasons.append("본문에 '국민은행'과 긴급 행위 요구가 포함되어 있으나, 연결된 URL이 공식 도메인과 일치하지 않습니다.")
            
            # 룰 2: 택배 사칭
            elif "택배" in text or "배송" in text:
                if "cjlogistics" not in url and "hanjin" not in url:
                    risk_score = 85
                    detected_type = "택배 사칭 피싱 (주의)"
                    reasons.append("택배 배송 안내 문구이나, 의심스러운 외부 링크 주소가 포함되어 있습니다.")
                    
            # 룰 3: 단축 URL 감지
            if "bit.ly" in url or "t.co" in url or "is.gd" in url:
                risk_score += 20
                reasons.append("단축 URL(리디렉션 의심 주소)이 사용되었습니다.")

            if not reasons:
                reasons.append("특이 사기 패턴이 발견되지 않은 안전한 메시지입니다.")
            
            risk_score = min(risk_score, 100)
            # ---------------------------------
            
            st.markdown("---")
            st.subheader("📊 분석 결과 리포트")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="최종 위험도 점수", value=f"{risk_score}점 / 100점")
            with col2:
                st.metric(label="판정 사기 유형", value=detected_type)
            
            if risk_score >= 80:
                st.error(f"🚨 **고위험 경고:** 해당 메시지는 피싱 사기일 확률이 매우 높습니다!")
            elif risk_score >= 40:
                st.warning(f"⚠️ **주의 요망:** 의심스러운 패턴이 발견되었습니다. 주의하세요.")
            else:
                st.success(f"✅ **안전:** 특이 사기 패턴이 발견되지 않았습니다.")
            
            st.markdown("### 📌 세부 위험 판단 근거")
            for idx, reason in enumerate(reasons, 1):
                st.markdown(f"{idx}. {reason}")