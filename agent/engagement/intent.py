"""
Agentic intent router.

Classifies a customer's inbound free-text reply into a fixed action enum using
Amazon Bedrock (Nova Pro). In SANDBOX_MODE — or if Bedrock is unavailable — a
deterministic keyword fallback keeps the two-way loop runnable without AWS.

The returned action is always one of ALLOWED_ACTIONS; anything else collapses to
"unknown". This containment is the core defense against prompt injection in the
customer's message.
"""

from __future__ import annotations

import json
import logging
import os

from prompts.intent_router import INTENT_ROUTER_PROMPT

log = logging.getLogger(__name__)

MODEL_ID = os.environ.get("INTENT_MODEL_ID", "amazon.nova-pro-v1:0")
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

ALLOWED_ACTIONS = {
    "book_deepdive",
    "cost_estimate",
    "talk_to_human",
    "ask_question",
    "unknown",
}


def _sandbox() -> bool:
    return os.environ.get("SANDBOX_MODE", "true").lower() in ("1", "true", "yes")


def _coerce(result: dict) -> dict:
    action = str(result.get("action", "unknown")).strip()
    if action not in ALLOWED_ACTIONS:
        action = "unknown"
    try:
        confidence = float(result.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    question = str(result.get("question", "")) if action == "ask_question" else ""
    return {"action": action, "confidence": confidence, "question": question}


def classify_fallback(text: str) -> dict:
    """Deterministic keyword classifier used in sandbox / when Bedrock is off."""
    t = (text or "").strip().lower()
    if t in {"1", "one"} or "book" in t or "deep" in t or "schedul" in t or "meeting" in t:
        return {"action": "book_deepdive", "confidence": 0.6, "question": ""}
    if t in {"2", "two"} or "cost" in t or "price" in t or "budget" in t or "estimate" in t:
        return {"action": "cost_estimate", "confidence": 0.6, "question": ""}
    if t in {"3", "three"} or "human" in t or "person" in t or "call" in t or "sales" in t:
        return {"action": "talk_to_human", "confidence": 0.6, "question": ""}
    if "?" in t or t.startswith(("what", "how", "why", "which", "can", "does", "is ")):
        return {"action": "ask_question", "confidence": 0.5, "question": text.strip()}
    if not t:
        return {"action": "unknown", "confidence": 0.0, "question": ""}
    return {"action": "unknown", "confidence": 0.3, "question": ""}


def classify_intent(text: str) -> dict:
    """Return {"action", "confidence", "question"} for a customer reply."""
    if _sandbox():
        return _coerce(classify_fallback(text))

    try:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=REGION)
        resp = client.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "system": [{"text": INTENT_ROUTER_PROMPT}],
                "messages": [{"role": "user", "content": [{"text": f"Customer reply:\n{text}"}]}],
                "inferenceConfig": {"maxTokens": 256, "temperature": 0.0, "topP": 0.9},
            }),
        )
        body = json.loads(resp["body"].read())
        raw = body["output"]["message"]["content"][0]["text"].strip()
        parsed = json.loads(raw)
        return _coerce(parsed)
    except Exception as exc:
        log.warning("[intent] Bedrock classify failed (%s); using fallback", exc)
        return _coerce(classify_fallback(text))
