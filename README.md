# Summary Agent

Analysis 결과와 Question 답변을 통합하여 최종 응답을 생성하는 Agent

## 개요

Supervisor Agent가 수집한 Analysis 결과와 Question 답변을 받아 하나의 한국어 응답으로 통합합니다. LLM은 충돌 감지에만 사용하고, 텍스트 포맷팅은 직접 구현하여 일관된 출력 형식을 보장합니다.

**주요 역할**:
- Analysis 결과를 구조화된 텍스트로 변환
- Question 답변과 Analysis 결과 통합
- 내용 충돌 감지 및 안내

## 디렉토리 구조

```
codecaine-python-summaryagent/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI 애플리케이션 진입점
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       └── invocations.py           # POST /invocations 엔드포인트
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py                    # 환경변수 설정 (Pydantic Settings)
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── agent.py                     # Request/Response 스키마
│   └── services/
│       ├── __init__.py
│       └── summary_agent.py             # 텍스트 포맷팅 및 충돌 감지 로직
├── Dockerfile                           # Docker 이미지 빌드 설정
├── requirements.txt                     # Python 패키지 목록
├── env.example                          # 환경변수 예시
└── README.md                            # 이 문서
```

## 주요 파일 설명

### `app/services/summary_agent.py`
- **SummaryAgent 클래스**: 텍스트 통합 로직
- **3가지 실행 경로**:
  1. Analysis만 있는 경우 → 구조화된 텍스트 반환
  2. Question만 있는 경우 → 답변 그대로 반환
  3. 둘 다 있는 경우 → 통합 + 충돌 감지
- **_format_analysis()**: JSON을 구조화된 텍스트로 변환 (LLM 없이)
- **LLM 분기 처리**: 로컬 테스트(OpenAI) vs AWS 배포(Bedrock)

### `app/api/routes/invocations.py`
- POST `/invocations` 엔드포인트
- Supervisor Agent에서 호출
- Request 검증 및 Response 반환

### `app/core/config.py`
- Pydantic Settings 기반 환경변수 관리
- AWS, LLM 설정

## 전체 흐름

```
Supervisor Agent (결과 수집 완료)
    └─→ POST /invocations
            └─→ SummaryAgent.run()
                    ├─→ [Analysis만] _format_analysis() → 구조화된 텍스트
                    ├─→ [Question만] 답변 그대로 반환
                    └─→ [둘 다] _format_analysis() + 답변 + LLM 충돌 감지
                    └─→ 최종 응답 반환
```

## 출력 형식

### Analysis 결과 포맷

```
[섭취 목적] 피로 개선
[복용 약물] 아스피린

[전반적 평가] 비타민 B군 부족으로 피로 증상 발생 가능
[주요 우려사항] 비타민 B1 부족, 에너지 대사 저하
[생활습관] 규칙적인 식사와 충분한 수면 권장

[필요 영양소]
- 비타민 B1 (Thiamine): 1.2mg — 에너지 대사 촉진
- 비타민 B12 (Cobalamin): 2.4μg — 신경 기능 유지

[영양소 부족량]
- 비타민 B1 (Thiamine): 현재 0mg / 부족 1.2mg
- 비타민 B12 (Cobalamin): 현재 0μg / 부족 2.4μg

[추천 영양제]
1. (브랜드명) 비타민 B 컴플렉스 — 하루 1회 1정
   포함 영양소: 비타민 B1, 비타민 B12
```

### Analysis + Question 통합

```
[섭취 목적] 피로 개선
[복용 약물] 아스피린
...

---

비타민 B군은 에너지 대사에 필수적인 영양소입니다...

---

※ 상충 내용: 없음
```

## API 명세

### POST /invocations

Supervisor Agent에서 호출하는 메인 엔드포인트

**Request Body:**
```json
{
  "cognito_id": "user-123",
  "analysis_result": {
    "intake_purpose": "피로 개선",
    "medications": ["아스피린"],
    "step1": {...},
    "step2": {...},
    "step3": {...}
  },
  "question_result": {
    "answer": "비타민 B군은..."
  }
}
```

**Response:**
```json
{
  "cognito_id": "user-123",
  "response": "[섭취 목적] 피로 개선\n[복용 약물] 아스피린\n..."
}
```

## 환경변수 설정

### 필수 환경변수 (AWS 배포)

```bash
# AWS 설정
AWS_REGION=ap-northeast-2
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
```

### 로컬 테스트용 환경변수

```bash
USE_LOCAL_TEST=true
OPENAI_API_KEY=<OpenAI API Key>
OPENAI_MODEL_ID=gpt-4o-mini
```

## 로컬 실행

### 1. 환경 설정

```bash
# 가상환경 생성
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# 환경변수 설정
cp env.example .env
# .env 파일 편집
```

### 2. Agent 서버 실행

```bash
uvicorn app.main:app --reload --port 8002
```

### 3. 테스트

```bash
curl -X POST http://localhost:8002/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "cognito_id": "test-user",
    "analysis_result": {
      "intake_purpose": "피로 개선",
      "medications": ["아스피린"],
      "step1": {...}
    },
    "question_result": null
  }'
```

## Docker 빌드 및 실행

```bash
# 이미지 빌드
docker build -t summary-agent .

# 컨테이너 실행
docker run -p 8002:8000 --env-file .env summary-agent
```

## AWS 배포

### 1. ECR 푸시

```bash
# ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com

# 이미지 태그 및 푸시
docker tag summary-agent:latest <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com/summary-agent:latest
docker push <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com/summary-agent:latest
```

### 2. AgentCore Runtime 등록

AWS 콘솔 또는 Terraform으로 AgentCore Runtime에 등록

### 3. 환경변수 설정

```bash
USE_LOCAL_TEST=false
AWS_REGION=ap-northeast-2
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
```

### 4. IAM 권한 설정

Agent 실행 Role에 다음 권한 필요:
- `bedrock:InvokeModel`

## 기술 스택

- **Framework**: FastAPI
- **LLM**: AWS Bedrock (Claude 3 Haiku) / OpenAI (로컬)
- **Text Processing**: 직접 구현 (LLM 없이)

## 주요 기능

### 1. 구조화된 텍스트 변환
Analysis JSON을 일관된 형식으로 변환:
- `[섭취 목적]`, `[복용 약물]` 헤더
- `[필요 영양소]`, `[영양소 부족량]`, `[추천 영양제]` 섹션
- LLM 없이 직접 포맷팅하여 안정성 보장

### 2. 충돌 감지
Analysis 결과와 Question 답변 간 내용 충돌 감지:
```
※ 상충 내용: Analysis는 비타민 C 1000mg 권장, Question 답변은 500mg 권장
```

### 3. 유연한 입력 처리
- Analysis만 있는 경우
- Question만 있는 경우
- 둘 다 있는 경우
모두 처리 가능

## 문제 해결

### 출력 형식 깨짐
```bash
# _format_analysis() 로직 확인
# LLM이 아닌 직접 포맷팅이므로 일관성 보장
```

### LLM 호출 실패
```bash
# IAM 권한 확인
aws iam get-role-policy --role-name <role-name> --policy-name <policy-name>

# Bedrock 모델 ID 확인
echo $BEDROCK_MODEL_ID
```
