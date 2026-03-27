from pydantic import BaseModel


class SummaryRequest(BaseModel):
    cognito_id: str
    analysis_result: dict | None = None
    question_result: dict | None = None


class SummaryResponse(BaseModel):
    cognito_id: str
    response: str
