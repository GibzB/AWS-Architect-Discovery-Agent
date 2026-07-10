"""
Production server for AWS Discovery Orchestrator — runs inside AgentCore Runtime container.

- WebSocket path: /ws  (AgentCore routes wss://.../ws to container /ws)
- Health check: POST /invocations  (AgentCore platform contract)
- Port 8080 (set in Dockerfile CMD)

The agent conducts a voice-based architecture discovery interview using
Nova 2 Sonic, then generates a structured report using Nova Pro.
"""

import asyncio
import json
import logging
import os
import uuid

import boto3
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from nova_sonic import NovaSonicSession
from prompts.orchestrator import DISCOVERY_SYSTEM_PROMPT
from report import generate_report, generate_digest

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="aws-discovery-orchestrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# DynamoDB table for session persistence
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "aws-discovery-sessions")
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


def _get_dynamodb():
    """Get a DynamoDB resource."""
    return boto3.resource("dynamodb", region_name=REGION)


def _save_session(session_id: str, transcript: list, report: dict | None = None):
    """Persist session data to DynamoDB."""
    try:
        table = _get_dynamodb().Table(DYNAMODB_TABLE)
        item = {
            "session_id": session_id,
            "transcript": transcript,
            "status": "completed" if report else "in_progress",
        }
        if report:
            item["report_md"] = report.get("report_md", "")
            item["summary"] = report.get("summary", "")
        table.put_item(Item=item)
        log.info("[db] Saved session %s", session_id)
    except Exception as exc:
        log.warning("[db] Failed to save session %s: %s", session_id, exc)


@app.get("/ping")
async def ping():
    return {"status": "ok"}


@app.post("/invocations")
async def invocations():
    """AgentCore Runtime health check endpoint."""
    return JSONResponse({"status": "ok"})


@app.websocket("/ws")
async def discovery_ws(ws: WebSocket):
    """
    WebSocket endpoint for the architecture discovery voice session.

    Protocol:
    - Client sends: {"type": "start"} to begin
    - Client sends: {"type": "audio", "data": "<base64>"} for audio chunks
    - Client sends: {"type": "hangup"} to end and trigger report generation
    - Server sends: {"type": "status", "state": "connecting|live|processing|done"}
    - Server sends: {"type": "audio", "data": "<base64>"} for audio playback
    - Server sends: {"type": "transcript", "role": "agent|user", "text": "..."}
    - Server sends: {"type": "digest", "data": {...}} with the discovery digest
    - Server sends: {"type": "report", "data": {...}} with the full report
    """
    await ws.accept()
    log.info("WebSocket connected")

    session_id = str(uuid.uuid4())
    transcript = []
    done_event = asyncio.Event()
    session = None

    # AgentCore's WS proxy only delivers server→client messages while the
    # server is handling a client message. Background tasks queue outgoing
    # messages; the main loop flushes the queue each time it processes a frame.
    outgoing: asyncio.Queue = asyncio.Queue()

    def enqueue(msg: dict):
        outgoing.put_nowait(json.dumps(msg))

    async def flush():
        while not outgoing.empty():
            data = outgoing.get_nowait()
            try:
                await ws.send_text(data)
            except Exception:
                pass

    async def send_now(msg: dict):
        """Send immediately — only safe inside a client-message handler."""
        try:
            await ws.send_text(json.dumps(msg))
        except Exception:
            pass

    # ── Nova Sonic callbacks (run in background tasks → enqueue) ──

    async def on_audio(audio_b64: str):
        enqueue({"type": "audio", "data": audio_b64})

    async def on_transcript(role: str, text: str):
        log.info("[transcript] %s: %s", role, text[:80])
        transcript.append({"role": role, "text": text})
        enqueue({"type": "transcript", "role": role, "text": text})

    async def on_done():
        log.info("Nova Sonic session done")
        if transcript:
            try:
                enqueue({"type": "status", "state": "processing"})

                # Generate digest (quick summary for UI)
                digest = await asyncio.to_thread(generate_digest, transcript)
                enqueue({"type": "digest", "data": digest})

                # Generate full report
                report = await asyncio.to_thread(generate_report, transcript)
                enqueue({"type": "report", "data": report})

                # Persist to DynamoDB
                await asyncio.to_thread(_save_session, session_id, transcript, report)

            except Exception as exc:
                log.exception("Report generation failed: %s", exc)
                enqueue({"type": "error", "message": f"Report generation failed: {exc}"})

            enqueue({"type": "status", "state": "done"})
        else:
            enqueue({"type": "status", "state": "done"})
        done_event.set()

    async def on_error(message: str):
        log.error("Nova Sonic error: %s", message)
        enqueue({"type": "error", "message": message})

    try:
        # Wait for the client's first message before starting.
        # AgentCore's WS proxy doesn't forward server→client messages
        # until the client has sent at least one message.
        raw = await ws.receive_text()
        msg = json.loads(raw)
        log.info("First client message: %s", msg.get("type"))

        session = NovaSonicSession(
            on_audio=on_audio,
            on_transcript=on_transcript,
            on_done=on_done,
            on_error=on_error,
            system_prompt=DISCOVERY_SYSTEM_PROMPT,
        )

        await send_now({"type": "status", "state": "connecting"})
        await session.start()
        await send_now({"type": "status", "state": "live"})

        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)

            if msg.get("type") == "audio":
                await session.send_audio(msg["data"])

            elif msg.get("type") == "hangup":
                log.info("Hangup received — generating report")
                await session.close()
                await done_event.wait()
                await flush()
                break

            # Deliver any queued output to the client
            await flush()

    except WebSocketDisconnect:
        log.info("WebSocket disconnected")
        if session:
            await session.close()
    except Exception as exc:
        log.exception("Unexpected error: %s", exc)
        await send_now({"type": "error", "message": str(exc)})
        if session:
            await session.close()
