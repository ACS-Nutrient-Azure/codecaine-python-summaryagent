from fastapi import APIRouter, HTTPException
from app.schemas.agent import SummaryRequest, SummaryResponse
from app.services.summary_agent import SummaryAgent

router = APIRouter()


@router.post("/invocations", response_model=SummaryResponse)
async def invocations(req: SummaryRequest):
    try:
        agent = SummaryAgent()
        return await agent.run(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
