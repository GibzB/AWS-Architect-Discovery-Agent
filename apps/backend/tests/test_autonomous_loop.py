"""Test the full autonomous reasoning loop: Discovery → Architect → Review → Complete."""

import json
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.memory_store import memory_store


def _planner_decision(next_agent, reason, complete=False):
    return {
        "next_agent": next_agent,
        "reason": reason,
        "priority": "high",
        "context_for_agent": {"focus_area": "test", "specific_instructions": "test"},
        "workshop_complete": complete,
    }


def _discovery_response(facts, sufficient=False):
    return {
        "facts_extracted": facts,
        "questions": [
            {"question": "Next question?", "category": "technical", "reason": "testing", "priority": "critical"}
        ],
        "gaps_remaining": [] if sufficient else ["something"],
        "sufficient_for_architecture": sufficient,
        "response_to_customer": "Thank you. What about your database requirements?",
    }


def _architect_response():
    return {
        "services": [
            {"service": "Amazon ECS", "purpose": "Container hosting", "justification": "Scalable", "alternatives_considered": ["Lambda"]},
            {"service": "Amazon RDS", "purpose": "Database", "justification": "Managed SQL", "alternatives_considered": ["DynamoDB"]},
            {"service": "Amazon CloudFront", "purpose": "CDN", "justification": "Global delivery", "alternatives_considered": ["Direct S3"]},
        ],
        "decisions": [
            {"decision": "Multi-AZ deployment", "rationale": "High availability", "trade_offs": "Higher cost", "reversibility": "high"}
        ],
        "diagram_mermaid": "graph TD\n  A[Client] --> B[CloudFront]\n  B --> C[ALB]\n  C --> D[ECS]\n  D --> E[RDS]",
        "risks": [
            {"risk": "Single region", "impact": "medium", "likelihood": "low", "mitigation": "Add DR region"}
        ],
        "cost_estimate": {"monthly_low": 500, "monthly_high": 2000, "currency": "USD", "assumptions": ["100k req/day"]},
        "non_functional": {"availability_target": "99.9%", "rto": "4 hours", "rpo": "1 hour", "regions": ["us-east-1"], "multi_region": False},
        "response_to_customer": "I've designed an architecture using ECS, RDS, and CloudFront. Let me validate this with my review team.",
    }


def _review_approved():
    return {
        "status": "approved",
        "findings": [
            {"category": "security", "severity": "minor", "finding": "Consider WAF", "recommendation": "Add WAF rules", "well_architected_pillar": "Security"}
        ],
        "score": {"availability": 8, "security": 7, "performance": 8, "cost_optimization": 7, "operational_excellence": 7, "sustainability": 6},
        "approval_conditions": ["Add WAF before production"],
        "revision_instructions": "",
        "response_to_customer": "Architecture approved. Minor recommendation: add WAF for production.",
    }


@pytest.mark.asyncio
async def test_full_workshop_loop():
    """Simulate a complete workshop: Discovery → Architect → Review → Done."""
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        create_resp = await client.post(
            "/v1/sessions",
            json={"customer_name": "FinCo", "customer_industry": "Fintech"},
        )
        session_id = create_resp.json()["session_id"]

        # Turn 1: Discovery — gather facts
        with patch("app.services.bedrock.bedrock.invoke_json") as mock_bedrock:
            mock_bedrock.side_effect = [
                _planner_decision("DiscoveryAgent", "Not enough facts"),
                _discovery_response([
                    {"fact": "Fintech company", "category": "business", "confidence": 0.9},
                    {"fact": "10k users", "category": "technical", "confidence": 0.9},
                    {"fact": "PCI-DSS required", "category": "compliance", "confidence": 0.95},
                    {"fact": "Python backend", "category": "technical", "confidence": 0.9},
                    {"fact": "99.9% uptime needed", "category": "operations", "confidence": 0.9},
                ]),
            ]
            msg1 = await client.post(
                f"/v1/sessions/{session_id}/messages",
                json={"content": "We're a fintech with 10k users, need PCI-DSS, Python backend, 99.9% uptime."},
            )

        assert msg1.status_code == 200
        data1 = msg1.json()
        assert data1["agent_trace"]["agent_invoked"] == "DiscoveryAgent"
        assert data1["metadata"]["facts_gathered"] == 5

        # Turn 2: Architect — design
        with patch("app.services.bedrock.bedrock.invoke_json") as mock_bedrock:
            mock_bedrock.side_effect = [
                _planner_decision("ArchitectAgent", "Sufficient facts, ready to design"),
                _architect_response(),
            ]
            msg2 = await client.post(
                f"/v1/sessions/{session_id}/messages",
                json={"content": "That covers it. Please design the architecture."},
            )

        assert msg2.status_code == 200
        data2 = msg2.json()
        assert data2["agent_trace"]["agent_invoked"] == "ArchitectAgent"

        # Turn 3: Review — validate and approve
        with patch("app.services.bedrock.bedrock.invoke_json") as mock_bedrock:
            mock_bedrock.side_effect = [
                _planner_decision("ReviewAgent", "Architecture needs review"),
                _review_approved(),
            ]
            msg3 = await client.post(
                f"/v1/sessions/{session_id}/messages",
                json={"content": "Looks good, let's validate it."},
            )

        assert msg3.status_code == 200
        data3 = msg3.json()
        assert data3["agent_trace"]["agent_invoked"] == "ReviewAgent"
        assert data3["session_status"] == "complete"
        assert data3["metadata"]["review_status"] == "approved"

        # Turn 4: Workshop complete
        with patch("app.services.bedrock.bedrock.invoke_json") as mock_bedrock:
            mock_bedrock.side_effect = [
                _planner_decision(None, "Workshop complete", complete=True),
            ]
            msg4 = await client.post(
                f"/v1/sessions/{session_id}/messages",
                json={"content": "Great work!"},
            )

        data4 = msg4.json()
        assert "complete" in data4["content"].lower()

        # Report should now be available
        report_resp = await client.get(f"/v1/sessions/{session_id}/report")
        assert report_resp.status_code == 200
        report = report_resp.json()
        assert "services" in report
        assert len(report["services"]) == 3
        assert "report_markdown" in report
        assert "terraform_snippet" in report
        assert "diagram_mermaid" in report
