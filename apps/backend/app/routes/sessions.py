"""Session API routes — the primary interface for the Atlas workshop."""

import logging
from fastapi import APIRouter, HTTPException

from packages.schemas.session import (
    CreateSessionRequest,
    CreateSessionResponse,
    SendMessageRequest,
    SendMessageResponse,
    SessionResponse,
    ReportResponse,
    SessionStatus,
    ReviewStatus,
    AgentTrace,
    MessageMetadata,
)
from app.services.orchestrator import orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=CreateSessionResponse, status_code=201)
async def create_session(request: CreateSessionRequest):
    """Create a new discovery workshop session."""
    result = await orchestrator.create_session(
        customer_name=request.customer_name,
        customer_industry=request.customer_industry or "",
    )
    return CreateSessionResponse(
        session_id=result["session_id"],
        status=SessionStatus.DISCOVERY,
        created_at=result["created_at"],
    )


@router.post("/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(session_id: str, request: SendMessageRequest):
    """Send a message to Atlas and receive the next response."""
    result = await orchestrator.process_message(session_id, request.content)

    if "error" in result:
        if result["error"] == "session_not_found":
            raise HTTPException(status_code=404, detail="Session not found")
        raise HTTPException(status_code=500, detail=result["error"])

    # Map review_status string to enum
    review_status_raw = result.get("metadata", {}).get("review_status")
    review_status = None
    if review_status_raw in ("pending", "approved", "rejected"):
        review_status = ReviewStatus(review_status_raw)

    trace = result.get("agent_trace", {})
    return SendMessageResponse(
        message_id=result["message_id"],
        content=result["content"],
        role=result["role"],
        agent_trace=AgentTrace(
            planner_decision=trace.get("planner_decision") or "",
            agent_invoked=trace.get("agent_invoked") or "",
            tools_used=trace.get("tools_used") or [],
            reasoning=trace.get("reasoning") or "",
        ),
        session_status=SessionStatus(result.get("session_status", "discovery")),
        metadata=MessageMetadata(
            facts_gathered=result.get("metadata", {}).get("facts_gathered", 0),
            questions_remaining=result.get("metadata", {}).get("questions_remaining", 0),
            review_status=review_status,
        ),
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get current session state."""
    session = await orchestrator.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    review_status_raw = session.get("review", {}).get("status")
    review_status = None
    if review_status_raw in ("pending", "approved", "rejected"):
        review_status = ReviewStatus(review_status_raw)

    return SessionResponse(
        session_id=session["session_id"],
        status=SessionStatus(session.get("status", "discovery")),
        created_at=session["created_at"],
        updated_at=session["updated_at"],
        customer=session.get("customer", {}),
        facts_count=len(session.get("known_facts", [])),
        questions_remaining=len(session.get("questions_remaining", [])),
        architecture_ready=bool(session.get("architecture", {}).get("services")),
        review_status=review_status,
        conversation_length=len(session.get("conversation_history", [])),
    )


@router.get("/{session_id}/report")
async def get_report(session_id: str):
    """Get the final report (only available after review approval)."""
    report = await orchestrator.get_report(session_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Report not available. Workshop must be completed and architecture approved.",
        )
    return report
