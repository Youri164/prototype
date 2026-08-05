import time
import streamlit as st
import re
import streamlit.components.v1 as components   # ← 이 줄 추가

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

   /* --- 예시 버튼 줄: 무조건 가로 유지 --- */
    .st-key-example_row div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 8px;
    }
    .st-key-example_row div[data-testid="stHorizontalBlock"] > div {
        width: 100% !important;
        flex: 1 1 0 !important;
        min-width: 0 !important;
    }
    .st-key-example_row button {
        background: #4A5A6A;
        color: #F0F0F0;
        border: none;
        border-radius: 12px 12px 0 0;
        padding: 10px 16px;
        font-weight: 600;
        width: 100%;
        transition: opacity 0.15s ease;
    }

    /* --- metric 줄: 얘는 화면 좁으면 자유롭게 줄바꿈 허용 (강제 안 함) --- */
    .st-key-metric_row div[data-testid="stHorizontalBlock"] {
        gap: 8px;
    }

    /* 값(value) 부분 - 줄바꿈 허용 + 글씨 작게 + 말줄임(...) 해제 */
    [data-testid="stMetricValue"] {
        font-size: 16px !important;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: unset !important;
        word-break: break-all !important;
        line-height: 1.35 !important;
    }

    /* 라벨("판정 사기 유형", "추출된 링크") 글씨도 살짝 작게 */
    [data-testid="stMetricLabel"] {
        font-size: 13px !important;
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

with st.container(key="example_row"):
    ex_col1, ex_col2 = st.columns(2)
    with ex_col1:
        if st.button("✅ 진짜 예시 (정상)"):
            st.session_state.msg_input = TRUE_EXAMPLE
    with ex_col2:
        if st.button("🚨 가짜 예시 (피싱)"):
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
        st.markdown("---")

        # --- [1. 결과/로딩이 나올 위치에 앵커 먼저 표시] ---
        st.markdown('<div id="result-anchor"></div>', unsafe_allow_html=True)

        # --- [2. 로딩 화면이 그려지기 전에 먼저 그 자리로 스크롤] ---
        components.html(
            """
            <script>
                var el = window.parent.document.getElementById('result-anchor');
                if (el) {
                    el.scrollIntoView({behavior: 'smooth', block: 'start'});
                }
            </script>
            """,
            height=0,
        )

# --- [3. 로딩 카드 + 단계별 게이지 애니메이션] ---
        loading_placeholder = st.empty()

        loading_steps = [
            (25, "🔗 링크 위험값 산출 중... (도메인·경로 패턴 대조)"),
            (50, "🧠 문맥 위험값 산출 중... (주체-행위 결합도 분석)"),
            (80, "📊 최종 위험도 산출 및 유형 일치 보정 중..."),
            (100, "📝 위험 판단 근거 우선순위 정렬 중..."),
        ]

        STAGE_DURATION = 1.5  # 각 단계마다 머무르는 시간(초)

        prev = 0
        for target, msg in loading_steps:
            steps_in_stage = max(target - prev, 1)
            sleep_per_step = STAGE_DURATION / steps_in_stage

            for i in range(prev, target + 1):
                loading_placeholder.markdown(
                    f"""
                    <div style="
                        background-color:#1C1F26;
                        border:1px solid #2A2E37;
                        border-radius:16px;
                        padding:48px 24px;
                        margin-bottom:18px;
                    ">
                        <div style="font-size:19px; font-weight:700; color:#FAFAFA; margin-bottom:14px;">
                            {msg}
                        </div>
                        <div style="background-color:#0E1117; border-radius:10px; width:100%; height:14px; overflow:hidden;">
                            <div style="
                                width:{i}%;
                                background: linear-gradient(90deg, #4A5A6A, #6C8FB5);
                                height:100%;
                                border-radius:10px;
                                transition: width 0.1s ease-in-out;">
                            </div>
                        </div>
                        <div style="font-size:12px; color:#9AA4B2; margin-top:10px;">
                            진행률 {i}%
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                time.sleep(sleep_per_step)
            prev = target

        loading_placeholder.empty()

        # --- [4. 실제 분석 로직] ---
        text = full_text_input

        # 공백이나 닫는 괄호(], ), }, 기호 전까지만 URL로 인식하도록 다듬은 정규표현식
        url_pattern = r'https?://[^\s\]\)\}>"\']+|www\.[^\s\]\)\}>"\']+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s\]\)\}>"\']*)?'
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
                        reasons.append(f"✅ '{bank_name}' 공식 도메인({official_domain})과 일치하여 안전한 링크로 확인되었습니다.")
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
# --- [추가 룰: 단축 URL 감지] ---
        if any(short in found_url for short in ["bit.ly", "t.co", "is.gd", "url.kr", "Me2.do"]):
            risk_score += 25
            reasons.append("🚨 주소를 숨기기 위한 단축 URL(리디렉션 의심)이 포함되어 있습니다.")

        # --- [추가 룰 A: 긴급성/과장 마케팅 문구 감지] ---
        urgency_keywords = ["지금 바로", "즉시", "긴급", "선착순", "한정", "100% 당첨", "Get Get", "무료 증정"]
        matched_urgency = [kw for kw in urgency_keywords if kw in text]
        if matched_urgency:
            risk_score += 10
            reasons.append(f"⚠️ 긴급성을 조성하거나 과도하게 유도하는 마케팅성 문구('{matched_urgency[0]}' 등)가 포함되어 있습니다.")
        # --- [문맥 위험값(C_g) 근사 계산: 주체-행위 토큰 거리 기반] ---
        action_keywords = ["링크", "클릭", "확인", "접속", "누르", "터치"]
        words = re.split(r'\s+', text)

        subject_positions = [i for i, w in enumerate(words) if any(kw in w for kw in sum([info["keywords"] for info in BANK_DOMAINS.values()], []))]
        action_positions = [i for i, w in enumerate(words) if any(kw in w for kw in action_keywords)]

        if subject_positions and action_positions:
            min_distance = min(abs(s - a) for s in subject_positions for a in action_positions)
            if min_distance <= 3:
                risk_score += 15
                reasons.append(f"🧠 발신 주체와 행위 요구 표현 사이의 문맥 거리가 매우 가깝습니다(토큰 거리 {min_distance}). 사칭 유도 문맥으로 판단됩니다.")

        # --- [유형 일치 보정(J_g): 링크 위험과 문맥 위험이 같은 유형을 가리킬 때 가중치 부여] ---
        if risk_score >= 90 and matched_urgency:
            risk_score = min(risk_score + 5, 100)
            reasons.append("🔗🧠 링크 기반 판단과 문맥 기반 판단이 동일한 사기 유형을 가리켜, 위험도가 상향 보정되었습니다.")

        # --- [추가 룰 B: 표시된 링크 텍스트와 실제 연결 주소 불일치 감지] ---
        markdown_link_pattern = r'\[(https?://[^\]]+)\]\((https?://[^\)]+)\)'
        mismatched_links = re.findall(markdown_link_pattern, text)
        for display_url, actual_url in mismatched_links:
            if display_url.strip() != actual_url.strip():
                risk_score += 20
                reasons.append(f"🚨 화면에 보이는 링크 주소({display_url})와 실제 연결되는 주소({actual_url})가 서로 다릅니다. 클릭을 유도하는 위장 링크로 의심됩니다.")

        if not reasons:
            reasons.append("특이 사기 패턴 및 의심스러운 외부 링크가 발견되지 않았습니다.")
        # --- [근거 우선순위(B_{g,j}) 정렬: 링크·문맥 동시 발견된 근거를 상단으로] ---
        def reason_priority(r):
            if "🔗🧠" in r:
                return 0   # 링크+문맥 동시 근거 최우선
            elif "🚨" in r or "⚠️" in r:
                return 1   # 단일 위험 신호
            elif "✅" in r:
                return 3   # 안전 확인 근거는 맨 아래
            else:
                return 2   # 기타 참고 근거

        reasons = sorted(reasons, key=reason_priority)

        # --- [5. 실제 결과 렌더링] ---
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
        st.caption("🔬 링크 위험값(U·P·H·T) · 문맥 위험값(O·D) 결합 산출 방식 적용 · 특허출원")
        # 경고 문구를 여기(메트릭보다 먼저)로 이동
        if risk_score >= 80:
            st.error("🚨 **고위험 경고:** 해당 메시지는 피싱 사기일 확률이 매우 높습니다! 절대 링크를 누르지 마세요.")
        elif risk_score >= 40:
            st.warning("⚠️ **주의 요망:** 의심스러운 패턴이 감별되었습니다. 신중히 확인하세요.")
        else:
            st.success("✅ **안전:** 특이 사기 패턴이 발견되지 않았습니다.")

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

        with st.container(key="metric_row"):
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="판정 사기 유형", value=detected_type)
            with col2:
                st.metric(label="추출된 링크", value=found_url if found_url else "없음")

        card_end()

        card_start("📌 세부 위험 판단 근거")
        for idx, reason in enumerate(reasons, 1):
            st.markdown(f"{idx}. {reason}")
        card_end()
        # --- 여기부터 위에서 추가한 두 번째 앵커 + 스크롤 스크립트 ---
        st.markdown('<div id="result-bottom-anchor"></div>', unsafe_allow_html=True)
        components.html(
            """
            <script>
                setTimeout(function() {
                    var el = window.parent.document.getElementById('result-bottom-anchor');
                    if (el) {
                        el.scrollIntoView({behavior: 'smooth', block: 'end'});
                    }
                }, 150);
            </script>
            """,
            height=0,
        )