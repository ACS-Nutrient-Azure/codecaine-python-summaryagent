import json
import logging
import traceback

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas.agent import SummaryRequest
from app.services.summary_agent import SummaryAgent

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/invocations")
async def invocations(request: Request):
    raw = await request.body()
    logger.info(f"[INVOCATIONS] raw body: {raw[:500]}")

    try:
        data = json.loads(raw)
        req = SummaryRequest(**data)
    except Exception as e:
        logger.error(f"[INVOCATIONS] Request parse failed: {e} | raw={raw[:500]}")
        return JSONResponse(status_code=422, content={"error": f"Request parse error: {e}"})

    try:
        agent = SummaryAgent()
        result = await agent.run(req)
        return JSONResponse(content={
            "cognito_id": result.cognito_id,
            "response": result.response,
        })
    except Exception as e:
        error_detail = traceback.format_exc()
        logger.error(f"[INVOCATIONS] Agent run failed: {error_detail}")
        return JSONResponse(status_code=500, content={"error": f"{type(e).__name__}: {str(e)}"})
