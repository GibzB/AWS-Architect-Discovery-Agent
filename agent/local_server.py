"""
Local development server for AWS Discovery Orchestrator.

Differences from server.py (production):
  - Loads .env file for local credentials
  - Serves static frontend files
  - WebSocket path: /ws/call  (more explicit for local dev)
  - Port 8000 (default uvicorn)
"""

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from nova_sonic import NovaSonicSession
from prompts.orchestrator import DISCOVERY_SYSTEM_PROMPT
from report import generate_report, generate_digest

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="aws-discovery-orchestrator-local")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/ping")
async def ping():
    return {"status": "ok"}


@app.websocket("/ws/call")
async def discovery_ws(ws: WebSocket):
    """Local dev WebSocket endpoint — same logic as production server.py."""
    await ws.accept()
    log.info("WebSocket connected (local)")

    session_id = str(uuid.uuid4())
    transcript = []
    done_event = asyncio.Event()
    session = None

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
        try:
            await ws.send_text(json.dumps(msg))
        except Exception:
            pass

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
                digest = await asyncio.to_thread(generate_digest, transcript)
                enqueue({"type": "digest", "data": digest})
                report = await asyncio.to_thread(generate_report, transcript)
                enqueue({"type": "report", "data": report})
            except Exception as exc:
                log.exception("Report generation failed: %s", exc)
                enqueue({"type": "error", "message": f"Report failed: {exc}"})
            enqueue({"type": "status", "state": "done"})
        else:
            enqueue({"type": "status", "state": "done"})
        done_event.set()

    async def on_error(message: str):
        log.error("Nova Sonic error: %s", message)
        enqueue({"type": "error", "message": message})

    try:
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
                log.info("Hangup received")
                await session.close()
                await done_event.wait()
                await flush()
                break

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


# Serve frontend static files in local dev
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
