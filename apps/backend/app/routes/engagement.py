"""
Engagement API routes — AWS CDS omnichannel follow-up.

  POST /v1/sessions/{id}/engage   capture contact details and deliver the report
                                  over SES + SMS/RCS, opening a two-way thread.
  POST /v1/inbound                webhook for an inbound customer reply (one
                                  agentic turn); also accepts an SNS/EUM event.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.engagement_service import engagement_service
from app.services.memory_store import memory_store
from app.services.orchestrator import orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["engagement"])


class EngageRequest(BaseModel):
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=20)
    follow_up_channel: str = Field(default="sms", pattern="^(sms|rcs)$")


class InboundRequest(BaseModel):
    channel: str = Field(default="sms", pattern="^(sms|rcs|email)$")
    sender: str = Field(..., min_length=1, max_length=320)
    text: str = Field(..., min_length=1, max_length=4000)


@router.post("/v1/sessions/{session_id}/engage")
async def engage(session_id: str, request: EngageRequest):
    """Deliver the report over AWS CDS and open the two-way follow-up thread."""
    report = await orchestrator.get_report(session_id)
    if report is None:
        raise HTTPException(
            status_code=409,
            detail="Report not ready. Finish the workshop and get Review approval first.",
        )
    session = memory_store.get_session(session_id)

    # Record contact details on the customer record (used for replies).
    customer = dict(session.get("customer", {}))
    if request.email:
        customer["email"] = request.email
    if request.phone:
        customer["phone"] = request.phone
    memory_store.update_session(session_id, {"customer": customer})
    session = memory_store.get_session(session_id)

    results = engagement_service.deliver_report(
        session, report,
        email=request.email, phone=request.phone,
        follow_up_channel=request.follow_up_channel,
    )
    return {"session_id": session_id, "delivered": results}


@router.post("/v1/inbound")
async def inbound(request: InboundRequest):
    """Process one inbound customer reply through the agentic engagement loop."""
    result = await engagement_service.handle_inbound(
        request.channel, request.sender, request.text
    )
    return result
