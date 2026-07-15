"""
Voice WebSocket — Polly TTS + browser STT fallback.

Until Nova Sonic model access is enabled for this account,
voice uses:
- STT: Browser Web Speech API (client-side) → sends text via transcript_input
- TTS: Amazon Polly → streams PCM audio back to client
- Turn-taking: 5-second debounce on client side

Protocol:
Client → Server:
  {"type": "start"}                         — begin session
  {"type": "transcript_input", "text": "…"} — user speech (from browser STT)
  {"type": "audio", "data": "b64"}          — raw audio (ignored for now)
  {"type": "hangup"}                        — end session

Server → Client:
  {"type": "status", "state": "connecting|live|processing|done"}
  {"type": "audio", "data": "b64"}  — Polly TTS audio (PCM 16-bit 16kHz)
  {"type": "transcript", "role": "agent|user", "text": "..."}
  {"type": "digest", "data": {...}} — session summary on hangup
  {"type": "error", "message": "..."}
"""

import asyncio
import base64
import json
import logging

import boto3
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.services.orchestrator import orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/call")
async def voice_call(ws: WebSocket):
    await ws.accept()
    logger.info("Voice WebSocket connected")

    transcript: list[dict] = []
    session_id: str | None = None

    async def send(msg: dict):
        try:
            await ws.send_text(json.dumps(msg))
        except Exception:
            pass

    try:
        # Wait for start message
        raw = await ws.receive_text()
        msg = json.loads(raw)
        logger.info(f"Voice start: {msg}")

        # Create session
        result = await orchestrator.create_session(
            customer_name="Voice Session",
            customer_industry="",
        )
        session_id = result["session_id"]

        await send({"type": "status", "state": "connecting"})

        # Send greeting
        greeting = (
            "Hello, I'm ASA, your Autonomous Solutions Architect. "
            "I'll guide you through today's cloud discovery workshop. "
            "Tell me about your organisation and what's driving this cloud initiative."
        )
        await send({"type": "status", "state": "live"})
        await send({"type": "transcript", "role": "agent", "text": greeting})
        transcript.append({"role": "agent", "text": greeting})

        # Stream greeting as Polly audio
        await _send_polly_audio(send, greeting)

        # Main loop — process user speech
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)

            if msg.get("type") == "hangup":
                logger.info("Voice hangup")
                await send({"type": "status", "state": "processing"})
                digest = _generate_digest(transcript, session_id)
                await send({"type": "digest", "data": digest})
                break

            elif msg.get("type") == "transcript_input":
                user_text = msg.get("text", "").strip()
                if not user_text:
                    continue

                logger.info(f"User said: {user_text[:80]}")
                transcript.append({"role": "user", "text": user_text})
                await send({"type": "transcript", "role": "user", "text": user_text})

                # Process through agent pipeline
                response = await orchestrator.process_message(session_id, user_text)
                response_text = response.get("content", "Let me think about that.")

                logger.info(f"ASA responds: {response_text[:80]}")
                transcript.append({"role": "agent", "text": response_text})
                await send({"type": "transcript", "role": "agent", "text": response_text})

                # Stream TTS audio
                await _send_polly_audio(send, response_text)

            elif msg.get("type") == "audio":
                # Raw audio from mic — ignored in Polly mode (STT is client-side)
                pass

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")
    except Exception as e:
        logger.exception(f"Voice WebSocket error: {e}")
        await send({"type": "error", "message": str(e)})


async def _send_polly_audio(send, text: str):
    """Synthesize speech with Polly and stream as PCM audio chunks."""
    try:
        polly = boto3.client("polly", region_name=settings.aws_region)
        response = await asyncio.to_thread(
            polly.synthesize_speech,
            Text=text[:3000],
            OutputFormat="pcm",
            SampleRate="16000",
            VoiceId="Matthew",
            Engine="neural",
        )
        audio_bytes = response["AudioStream"].read()

        # Send in 4KB chunks
        chunk_size = 4096
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i + chunk_size]
            b64 = base64.b64encode(chunk).decode("ascii")
            await send({"type": "audio", "data": b64})

    except Exception as e:
        logger.warning(f"Polly TTS failed: {e}")


def _generate_digest(transcript: list[dict], session_id: str) -> dict:
    """Generate a summary from the conversation."""
    user_msgs = [t["text"] for t in transcript if t["role"] == "user"]
    agent_msgs = [t["text"] for t in transcript if t["role"] == "agent"]
    return {
        "session_id": session_id,
        "summary": f"Discovery session: {len(user_msgs)} user turns, {len(agent_msgs)} ASA responses.",
        "highlights": user_msgs[:5],
        "action_items": [
            "Review architecture recommendations",
            "Validate requirements captured",
        ],
        "sentiment": "positive" if len(user_msgs) > 2 else "neutral",
    }
