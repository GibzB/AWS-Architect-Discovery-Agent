"""Test the sessions API — end-to-end with mocked Bedrock."""

import json
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def mock_bedrock():
    """Mock the Bedrock client to avoid real AWS calls."""
    planner_response = json.dumps({
        "next_agent": "DiscoveryAgent",
        "reason": "Only 0 facts known. Need more information.",
        "priority": "high",
        "context_for_agent": {
            "focus_area": "Gather core requirements",
            "specific_instructions": "Ask about business context.",
        },
        "workshop_complete": False,
    })

    discovery_response = json.dumps({
        "facts_extracted": [
            {"fact": "Customer is a fintech startup", "category": "business", "confidence": 0.95}
        ],
        "questions": [
            {
                "question": "What's your expected transaction volume per day?",
                "category": "technical",
                "reason": "Need to size infrastructure appropriately",
                "priority": "critical",
            }
        ],
        "gaps_remaining": ["technical architecture", "compliance", "DR objectives"],
        "sufficient_for_architecture": False,
        "response_to_customer": (
            "Thank you. I see you're a fintech startup — that's helpful context. "
            "To design the right architecture, I need to understand your scale. "
            "What's your expected transaction volume per day?"
        ),
    })

    with patch("app.services.bedrock.bedrock.invoke_json") as mock:
        mock.side_effect = [
            # First call is the Planner
            json.loads(planner_response),
            # Second call is the Discovery Agent
            json.loads(discovery_response),
        ]
        yield mock


@pytest.mark.asyncio
async def test_create_session():
    """Test session creation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/sessions",
            json={"customer_name": "Acme Corp", "customer_industry": "Fintech"},
        )
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "discovery"


@pytest.mark.asyncio
async def test_send_message(mock_bedrock):
    """Test sending a message and getting an agentic response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        create_resp = await client.post(
            "/v1/sessions",
            json={"customer_name": "Acme Corp", "customer_industry": "Fintech"},
        )
        session_id = create_resp.json()["session_id"]

        # Send a message
        msg_resp = await client.post(
            f"/v1/sessions/{session_id}/messages",
            json={"content": "We're a fintech startup expanding into Europe."},
        )

    assert msg_resp.status_code == 200
    data = msg_resp.json()
    assert data["role"] == "assistant"
    assert "transaction volume" in data["content"].lower()
    assert data["agent_trace"]["agent_invoked"] == "DiscoveryAgent"
    assert data["metadata"]["facts_gathered"] == 1


@pytest.mark.asyncio
async def test_get_session_not_found():
    """Test 404 for non-existent session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/sessions/non-existent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_report_not_ready():
    """Test that report returns 404 before completion."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/v1/sessions",
            json={"customer_name": "Test Co"},
        )
        session_id = create_resp.json()["session_id"]
        report_resp = await client.get(f"/v1/sessions/{session_id}/report")
    assert report_resp.status_code == 404
