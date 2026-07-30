from fastapi import FastAPI
from pydantic import BaseModel
import re

app = FastAPI(title="피싱 탐지 시연용 프로토타입 서버")

# 클라이언트(앱/웹)에서 보내는 데이터 형식을 정의합니다.
class MessageRequest(BaseModel):
    message: str
    url: str | None = None

@app.post("/analyze")
def analyze_phishing(data: MessageRequest):
    text = data.message
    url = data.url if data.url else ""
    
    risk_score = 10
    detected_type = "정상 (안전)"
    reasons = []

    # [룰베이스 1] 국민은행 사칭 사기 시나리오 모의 구현
    if "국민은행" in text and ("입금" in text or "긴급" in text or "대출" in text):
        if "kb-secure" not in url and "kbstar.com" not in url:
            risk_score = 95
            detected_type = "국민은행 사칭 피싱 (고위험)"
            reasons.append("본문에 '국민은행'과 긴급 행위 요구(입금/대출)가 포함되어 있으나, 연결된 URL이 공식 도메인과 일치하지 않습니다.")
    
    # [룰베이스 2] 택배 사칭 사기 시나리오 모의 구현
    elif "택배" in text or "배송" in text:
        if "cjlogistics" not in url and "hanjin" not in url:
            risk_score = 85
            detected_type = "택배 사칭 피싱 (주의)"
            reasons.append("택배 배송 안내 문구이나, 의심스러운 외부 링크 주소가 포함되어 있습니다.")
            
    # [룰베이스 3] 단축 URL 감지
    if "bit.ly" in url or "t.co" in url or "is.gd" in url:
        risk_score += 20
        reasons.append("단축 URL(리디렉션 의심 주소)이 사용되었습니다.")

    if not reasons:
        reasons.append("특이 사기 패턴이 발견되지 않은 안전한 메시지입니다.")

    # 최종 결과 반환 (JSON 형태)
    return {
        "status": "success",
        "risk_score": min(risk_score, 100),
        "detected_type": detected_type,
        "reasons": reasons,
        "analyzed_url": url
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)