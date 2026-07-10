"""
Post-session report generator.

Takes the full conversation transcript and calls Nova Pro via Bedrock
to produce a structured Markdown discovery report: architecture
recommendations, service breakdown, security considerations, and next steps.
"""

import json
import logging
import os

import boto3

from prompts.report import REPORT_PROMPT

log = logging.getLogger(__name__)

MODEL_ID = "amazon.nova-pro-v1:0"


def _bedrock_client():
    session = boto3.Session()
    return session.client(
        "bedrock-runtime",
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    )


def _format_transcript(turns: list[dict]) -> str:
    """Convert transcript list into readable text."""
    lines = []
    for t in turns:
        role = "Architect (interviewer)" if t["role"] == "agent" else "Client"
        lines.append(f"{role}: {t['text']}")
    return "\n".join(lines)


def generate_report(transcript: list[dict]) -> dict:
    """
    Generate a structured discovery report from the conversation transcript.

    Args:
        transcript: list of {"role": "agent"|"user", "text": "..."}

    Returns:
        Dict with 'report_md' (full markdown) and 'summary' (brief summary).
    """
    formatted = _format_transcript(transcript)
    if not formatted.strip():
        raise ValueError("Empty transcript — cannot generate report")

    client = _bedrock_client()
    log.info("[report] calling Nova Pro, transcript turns=%d", len(transcript))

    response = client.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "system": [{"text": REPORT_PROMPT}],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": (
                                f"Here is the full discovery conversation transcript:\n\n"
                                f"{formatted}\n\n"
                                "Please generate the discovery report now."
                            )
                        }
                    ],
                }
            ],
            "inferenceConfig": {
                "maxTokens": 4096,
                "temperature": 0.2,
                "topP": 0.9,
            },
        }),
    )

    body = json.loads(response["body"].read())
    report_md = body["output"]["message"]["content"][0]["text"].strip()
    log.info("[report] generated successfully (%d chars)", len(report_md))

    # Extract a brief summary (first paragraph after Executive Summary header)
    summary = ""
    lines = report_md.split("\n")
    in_summary = False
    for line in lines:
        if "Executive Summary" in line:
            in_summary = True
            continue
        if in_summary and line.strip():
            summary = line.strip()
            break

    return {
        "report_md": report_md,
        "summary": summary,
    }


def generate_digest(transcript: list[dict]) -> dict:
    """
    Generate a quick digest (JSON) for the UI card display.
    Similar to vox-brief's digest but focused on architecture discovery.

    Returns structured JSON with summary, recommendations, action_items, etc.
    """
    formatted = _format_transcript(transcript)
    if not formatted.strip():
        raise ValueError("Empty transcript — cannot generate digest")

    digest_prompt = """
You are an AWS solutions architecture analyst. You have just received a transcript
of a structured architecture discovery interview. Produce a concise, actionable
digest for the solutions team.

Return ONLY valid JSON — no markdown, no explanation, no code fences.

The JSON must match this exact schema:
{
  "summary": "<2-3 sentence plain-English summary of the discovery session>",
  "client_industry": "<industry of the client>",
  "client_size": "<organization size if mentioned>",
  "primary_driver": "<main driver for cloud adoption>",
  "recommended_services": ["<top AWS services recommended>", ...],
  "highlights": ["<key positive findings>", ...],
  "concerns": ["<risk factors or challenges identified>", ...],
  "action_items": ["<concrete next steps>", ...],
  "complexity": "low" | "medium" | "high"
}

Rules:
- ONLY include information EXPLICITLY stated in the transcript.
- If the interview was cut short, reflect that honestly.
- recommended_services: 3-8 items
- highlights: 0-5 items
- concerns: 0-5 items
- action_items: 0-5 items
- complexity: based on requirements discussed
""".strip()

    client = _bedrock_client()
    log.info("[digest] calling Nova Pro for digest, transcript turns=%d", len(transcript))

    response = client.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "system": [{"text": digest_prompt}],
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": f"Here is the interview transcript:\n\n{formatted}"}],
                }
            ],
            "inferenceConfig": {
                "maxTokens": 1024,
                "temperature": 0.1,
                "topP": 0.9,
            },
        }),
    )

    body = json.loads(response["body"].read())
    raw = body["output"]["message"]["content"][0]["text"].strip()
    log.info("[digest] raw response: %r", raw[:200])

    digest = json.loads(raw)
    log.info("[digest] parsed successfully")
    return digest
