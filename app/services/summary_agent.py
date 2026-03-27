"""
summary_agent.py

boto3 Bedrock 직접 호출 기반 Summary Agent 핵심 로직.
LangChain/LangGraph 없이 단순 LLM 호출만 수행.

역할:
  - Supervisor로부터 Analysis Agent 결과와 Question Agent 결과를 받아
    하나의 한국어 응답으로 합산.
  - 결과가 1개이고 Question Agent 결과인 경우: 그대로 자연어로 전달
  - 결과가 1개이고 Analysis Agent 결과인 경우: json 형식을 정해진 형식으로 변환 후 전달
  - 결과가 2개인 경우:
      · 내용 일치/보완적 → Anlaysis Agent 결과인 json을 정해진 형식으로 변환하고, Question Agent 결과를 그 뒤에 붙여서 전달. 형식을 합치지 않음
      · 내용 충돌 → Anlaysis Agent 결과인 json을 정해진 변환하고, Question Agent 결과를 그 뒤에 붙임 + 충돌 명시해서 전달. 형식을 합치지 않음
"""
import json
import logging

import boto3

from app.core.config import settings
from app.schemas.agent import SummaryRequest, SummaryResponse

logger = logging.getLogger(__name__)


class SummaryAgent:
    def __init__(self):
        # 로컬 테스트 모드: OpenAI 사용
        if settings.USE_LOCAL_TEST:
            from openai import OpenAI
            self.client_openai = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.use_openai = True
            # Gemini 사용 시 아래로 교체
            # import google.generativeai as genai
            # genai.configure(api_key=settings.GEMINI_API_KEY)
            # self.model = genai.GenerativeModel(settings.GEMINI_MODEL_ID)
            # self.use_gemini = True
        # 실제 배포: Bedrock 사용
        else:
            session = boto3.Session(region_name=settings.AWS_REGION)
            self.client = session.client("bedrock-runtime")
            self.use_openai = False

    async def run(self, req: SummaryRequest) -> SummaryResponse:
        """
        LLM 호출해 최종 응답 생성.
        analysis_result / question_result 중 None인 항목은 입력에서 제외.
        """
        print(f"\n[SUMMARY AGENT] Received request from {req.cognito_id}")
        print(f"  - analysis_result: {req.analysis_result}")
        print(f"  - question_result: {req.question_result}")
        
        # 1. Analysis만 있는 경우
        if req.analysis_result and not req.question_result:
            answer = _format_analysis(req.analysis_result)
        
        # 2. Question만 있는 경우
        elif req.question_result and not req.analysis_result:
            answer = req.question_result.get("answer", "")
        
        # 3. 둘 다 있는 경우 - LLM으로 충돌 판단만
        elif req.analysis_result and req.question_result:
            formatted_analysis = _format_analysis(req.analysis_result)
            question_answer = req.question_result.get("answer", "")
            
            # LLM에게 충돌 판단 요청
            conflict_prompt = f"""다음 두 정보를 비교하여 상충되는 내용이 있는지 판단하세요.

**분석 결과**:
{formatted_analysis}

**일반 정보**:
{question_answer}

상충되는 내용이 있으면 "※ 상충 내용: [구체적 설명]" 형식으로 출력하세요.
상충이 없으면 "없음"만 출력하세요."""

            # LLM 호출
            if self.use_openai:
                response = self.client_openai.chat.completions.create(
                    model=settings.OPENAI_MODEL_ID,
                    messages=[{"role": "user", "content": conflict_prompt}],
                    max_tokens=256,
                    temperature=0.3,
                )
                conflict_result = response.choices[0].message.content.strip()
            else:
                response = self.client.invoke_model(
                    modelId=settings.BEDROCK_MODEL_ID,
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 256,
                        "messages": [{"role": "user", "content": conflict_prompt}],
                    }),
                    contentType="application/json",
                    accept="application/json",
                )
                body = json.loads(response["body"].read())
                conflict_result = body["content"][0]["text"].strip()
            
            # 텍스트 직접 합치기
            answer = f"{formatted_analysis}\n\n---\n\n{question_answer}"
            if conflict_result != "없음":
                answer += f"\n\n---\n\n{conflict_result}"
        
        else:
            answer = "결과가 없습니다."

        print(f"[SUMMARY AGENT] Answer: {answer[:200]}...")
        return SummaryResponse(cognito_id=req.cognito_id, response=answer)



def _format_analysis(result: dict) -> str:
    """
    analysisagent JSON을 텍스트로 변환
    """
    lines = []
    
    # 섭취 목적
    intake_purpose = result.get("intake_purpose", "")
    if intake_purpose:
        lines.append(f"[섭취 목적] {intake_purpose}")
    
    # 복용 약물
    medications = result.get("medications", [])
    if medications:
        lines.append(f"[복용 약물] {', '.join(medications)}")
    else:
        lines.append("[복용 약물] 없음")
    
    # step1: summary
    step1 = result.get("step1", {})
    summary = step1.get("summary", {})
    
    if summary:
        lines.append(f"[전반적 평가] {summary.get('overall_assessment', '')}")
        key_concerns = summary.get("key_concerns", [])
        if key_concerns:
            lines.append(f"[주요 우려사항] {', '.join(key_concerns)}")
        lifestyle = summary.get("lifestyle_notes", "")
        if lifestyle:
            lines.append(f"[생활습관] {lifestyle}")
    
    # step1: required_nutrients
    required = step1.get("required_nutrients", [])
    if required:
        lines.append("\n[필요 영양소]")
        for n in required:
            lines.append(
                f"- {n.get('name_ko')} ({n.get('name_en', '')}): "
                f"{n.get('rda_amount')}{n.get('unit')} — {n.get('reason', '')}"
            )
    
    # step2: gaps
    step2 = result.get("step2", {})
    gaps = step2.get("gaps", [])
    if gaps:
        lines.append("\n[영양소 부족량]")
        for g in gaps:
            lines.append(
                f"- {g.get('name_ko')} ({g.get('name_en', '')}): "
                f"현재 {g.get('current_amount')}{g.get('unit')} / "
                f"부족 {g.get('gap_amount')}{g.get('unit')}"
            )
    
    # step3: recommendations
    step3 = result.get("step3", {})
    recs = step3.get("recommendations", [])
    if recs:
        lines.append("\n[추천 영양제]")
        for r in recs:
            nutrients = r.get("covered_nutrients", [])
            nutrients_str = ", ".join(nutrients) if nutrients else ""
            lines.append(
                f"{r.get('rank')}. ({r.get('product_brand')}) {r.get('product_name')} "
                f"— 하루 {r.get('serving_per_day', 1)}회 {r.get('recommend_serving')}정"
            )
            if nutrients_str:
                lines.append(f"   포함 영양소: {nutrients_str}")
    
    return "\n".join(lines)
