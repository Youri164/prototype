import time
import streamlit as st
import re

# 페이지 기본 설정
st.set_page_config(
    page_title="피싱 탐지 AI 프로토타입",
    page_icon="🛡️",
    layout="centered"
)

# --- [Streamlit 기본 UI 요소 숨기기 + 카드형 다크 디자인 CSS] ---
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    .stAppToolbar {display: none;}
    [data-testid="stHeader"] {display: none;}

    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Pretendard, sans-serif;
    }

    h1 {
        font-weight: 800 !important;
        letter-spacing: -0.5px;
    }

    .stTextArea textarea {
        background-color: #1C1F26;
        border: 1px solid #2A2E37;
        border-radius: 12px;
        color: #FAFAFA;
    }

    /* 기본 버튼 (사기위험분석 실행 버튼) - 빨강 유지 */
    .stFormSubmitButton button {
        background: linear-gradient(135deg, #FF4B4B, #FF7A5C);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 700;
        width: 100%;
        transition: transform 0.15s ease;
    }
    .stFormSubmitButton button:hover {
        transform: scale(1.01);
        opacity: 0.95;
    }

    [data-testid="stMetric"] {
        background-color: #1C1F26;
        border: 1px solid #2A2E37;
        border-radius: 14px;
        padding: 14px 16px;
    }
    /* 앱 내 모든 st.columns를 화면 폭과 무관하게 가로로 강제 */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 8px;
    }
    div[data-testid="stHorizontalBlock"] > div {
        width: 100% !important;
        flex: 1 1 0 !important;
        min-width: 0 !important;
    }

    /* 컬럼 안에 있는 버튼(=예시 버튼)만 블루그레이 톤으로 */
    div[data-testid="stHorizontalBlock"] button {
        background: #4A5A6A;
        color: #F0F0F0;
        border: none;
        border-radius: 12px 12px 0 0;
        padding: 10px 16px;
        font-weight: 600;
        width: 100%;
        transition: opacity 0.15s ease;
    }
    .example-marker + div[data-testid="stHorizontalBlock"] button:hover {
        opacity: 0.85;
    }
    /* 예시 버튼 줄과 바로 아래 입력 카드 사이 간격 제거 (붙어보이게) */
    .example-marker + div[data-testid="stHorizontalBlock"] {
        margin-bottom: -18px;
    }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("🛡️ AI 기반 메시지 피싱 탐지 시스템")
st.markdown("수신한 문자 메시지 전체(본문+링크)를 한 번에 붙여넣어 사기 위험도를 분석하세요.")

st.markdown("---")

# 1. 국내 주요 은행 공식 도메인 및 키워드 딕셔너리 정의
BANK_DOMAINS = {
    "국민은행": {"official": "kbstar.com", "keywords": ["국민은행", "KB국민"]},
    "우리은행": {"official": "wooribank.com", "keywords": ["우리은행"]},
    "신한은행": {"official": "shinhan.com", "keywords": ["신한은행", "신한"]},
    "하나은행": {"official": "kebhana.com", "keywords": ["하나은행", "KEB하나"]},
    "농협": {"official": "nonghyup.com", "keywords": ["농협", "NH농협"]},
    "기업은행": {"official": "ibk.co.kr", "keywords": ["기업은행", "IBK"]}
}

# --- [시연용 예시 문구] ---
TRUE_EXAMPLE = """KB국민은행 이벤트를 소개합니다.
100% 당첨은 기본! 쓰면 쓸수록 혜택 Level Up
▶ 휴캉스패키지 미션 참여하기
https://my.kbstar.com/yt3hyXW5"""

FAKE_EXAMPLE = """[국민은행] 대출도 Get, 이벤트로 금도 Get! 2배로 Get Get!!
[http://kb.star.events.com/3747482/dvjvlw]"""

# --- [카드 섹션을 만들어주는 헬퍼 함수] ---
def card_start(title=None):
    html = """
    <div style="
        background-color: #1C1F26;
        border: 1px solid #2A2E37;
        border-radius: 16px;
        padding: 22px 22px 8px 22px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.25);
        margin-bottom: 18px;
    ">
    """
    if title:
        html += f'<div style="font-size:18px; font-weight:700; color:#FAFAFA; margin-bottom:12px;">{title}</div>'
    st.markdown(html, unsafe_allow_html=True)

def card_end():
    st.markdown("</div>", unsafe_allow_html=True)


# --- [입력창 상태 초기화] ---
if "msg_input" not in st.session_state:
    st.session_state.msg_input = ""

# --- [시연용 예시 선택 버튼 - 박스 없이, 입력 카드 위에 붙여서 배치] ---
st.markdown('<div class="example-marker"></div>', unsafe_allow_html=True)
ex_col1, ex_col2 = st.columns(2)
with ex_col1:
    if st.button("✅ 예시1 (정상)"):
        st.session_state.msg_input = TRUE_EXAMPLE
with ex_col2:
    if st.button("🚨 예시2 (피싱)"):
        st.session_state.msg_input = FAKE_EXAMPLE


with st.form("phishing_form"):
    card_start("📥 분석 대상 입력")

    full_text_input = st.text_area(
        "문자 메시지 전체 내용 (본문 + 링크 포함)",
        height=150,
        placeholder="[국민은행] 긴급 대출 안내. 아래 링크를 확인하세요.\nhttps://kb-secure-login.com/event",
        label_visibility="collapsed",
        key="msg_input"
    )

    submitted = st.form_submit_button("🔍 사기 위험 분석 실행")
    card_end()

if submitted:
    if not full_text_input.strip():
        st.warning("⚠️ 분석할 메시지 내용을 입력해주세요.")
    else:
        with st.spinner("🔄 텍스트 내 URL 추출 및 피싱 패턴 정밀 분석 중..."):

            text = full_text_input

            # --- [텍스트 내부에서 URL 자동 추출 로직] ---
            url_pattern = r'https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'
            extracted_urls = re.findall(url_pattern, text)
            found_url = extracted_urls[0] if extracted_urls else ""

            risk_score = 10
            detected_type = "정상 (안전)"
            reasons = []

            for bank_name, info in BANK_DOMAINS.items():
                has_keyword = any(kw in text for kw in info["keywords"])

                if has_keyword:
                    official_domain = info["official"]

                    if found_url:
                        if official_domain in found_url:
                            reasons.append(f"'{bank_name}' 관련 메시지이며, 공식 도메인({official_domain})이 확인되었습니다.")
                        else:
                            risk_score = 90
                            detected_type = f"{bank_name} 사칭 피싱 (고위험)"
                            reasons.append(f"⚠️ 본문에 '{bank_name}'이 언급되었으나, 연결된 링크 주소가 공식 도메인({official_domain})과 일치하지 않거나 변형(타이포스쿼팅)되었습니다.")
                    else:
                        risk_score = 50
                        detected_type = f"{bank_name} 관련 주의 문자"
                        reasons.append(f"'{bank_name}' 사칭 문구는 있으나 확인된 링크가 없습니다. 공식 번호인지 확인하세요.")

            if any(short in found_url for short in ["bit.ly", "t.co", "is.gd", "url.kr", "Me2.do"]):
                risk_score += 25
                reasons.append("🚨 주소를 숨기기 위한 단축 URL(리디렉션 의심)이 포함되어 있습니다.")

            if not reasons:
                reasons.append("특이 사기 패턴 및 의심스러운 외부 링크가 발견되지 않았습니다.")

            risk_score = min(max(risk_score, 0), 100)

            st.markdown("---")

            card_start("📊 분석 결과 리포트")

            def get_gauge_color(score):
                if score >= 80:
                    return "#FF4B4B"
                elif score <= 30:
                    return "#2ECC71"
                else:
                    return "#F5A623"

            final_color = get_gauge_color(risk_score)
            gauge_placeholder = st.empty()

            for i in range(0, risk_score + 1, 2):
                current_color = get_gauge_color(i)
                gauge_placeholder.markdown(
                    f"""
                    <div style="background-color:#0E1117; border-radius:10px; width:100%; height:35px; overflow:hidden;">
                        <div style="
                            width:{i}%;
                            background-color:{current_color};
                            height:100%;
                            border-radius:10px;
                            text-align:right;
                            color:white;
                            font-weight:bold;
                            line-height:35px;
                            padding-right:10px;
                            transition: width 0.1s ease-in-out;
                            white-space:nowrap;">
                            {i}점
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                time.sleep(0.02)

            gauge_placeholder.markdown(
                f"""
                <div style="background-color:#0E1117; border-radius:10px; width:100%; height:35px; overflow:hidden;">
                    <div style="
                        width:{risk_score}%;
                        background-color:{final_color};
                        height:100%;
                        border-radius:10px;
                        text-align:right;
                        color:white;
                        font-weight:bold;
                        line-height:35px;
                        padding-right:10px;
                        white-space:nowrap;">
                        {risk_score}점
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown(f"**위험도 점수: {risk_score}점 / 100점**")

            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="판정 사기 유형", value=detected_type)
            with col2:
                st.metric(label="추출된 링크", value=found_url if found_url else "없음")

            card_end()

            card_start()
            if risk_score >= 80:
                st.error("🚨 **고위험 경고:** 해당 메시지는 피싱 사기일 확률이 매우 높습니다! 절대 링크를 누르지 마세요.")
            elif risk_score >= 40:
                st.warning("⚠️ **주의 요망:** 의심스러운 패턴이 감별되었습니다. 신중히 확인하세요.")
            else:
                st.success("✅ **안전:** 특이 사기 패턴이 발견되지 않았습니다.")
            card_end()

            card_start("📌 세부 위험 판단 근거")
            for idx, reason in enumerate(reasons, 1):
                st.markdown(f"{idx}. {reason}")
            card_end()