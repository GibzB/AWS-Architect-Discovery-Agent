"""
Voice WebSocket endpoint — real-time bidirectional audio via Nova Sonic.

Based on the vox-brief pattern:
- Client sends raw PCM audio chunks as base64 over WebSocket
- Server streams Nova Sonic audio responses back
- Transcripts are sent as text events for the UI

This requires Python 3.12+ for the Nova Sonic SDK, or falls back to
Polly TTS + Web Speech API STT for Python 3.10.
"""

import asyncio
import json
import logging
import os
import uuid

import boto3
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.services.orchestrator import orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

# Check if Nova Sonic SDK is available (requires Python 3.12+)
NOVA_SONIC_AVAILABLE = False
try:
    from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient
    NOVA_SONIC_AVAILABLE = True
except ImportError:
    logger.info("Nova Sonic SDK not available — using Polly fallback for voice")


@router.websocket("/ws/call")
async def voice_call(ws: WebSocket):
    """
    Bidirectional voice WebSocket — mirrors vox-brief protocol.

    Client → Server:
      {"type": "start"}                — begin session
      {"type": "audio", "data": "b64"} — PCM audio chunk
      {"type": "hangup"}               — end session

    Server → Client:
      {"type": "status", "state": "connecting|live|processing|done"}
      {"type": "audio", "data": "b64"} — PCM audio from Nova Sonic
      {"type": "transcript", "role": "agent|user", "text": "..."}
      {"type": "digest", "data": {...}} — session summary
      {"type": "error", "message": "..."}
    """
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

        # Create a session for this voice call
        result = await orchestrator.create_session(
            customer_name="Voice Session",
            customer_industry="",
        )
        session_id = result["session_id"]

        if NOVA_SONIC_AVAILABLE:
            await _run_nova_sonic_session(ws, session_id, transcript, send)
        else:
            await _run_polly_fallback_session(ws, session_id, transcript, send)

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")
    except Exception as e:
        logger.exception(f"Voice WebSocket error: {e}")
        await send({"type": "error", "message": str(e)})


async def _run_polly_fallback_session(ws, session_id, transcript, send):
    """
    Fallback voice mode: uses Polly for TTS, expects client to handle STT.
    Client sends transcribed text via {"type": "transcript_input", "text": "..."}.
    Also handles raw audio for recording purposes.
    """
    import base64

    await send({"type": "status", "state": "connecting"})

    # Send greeting audio via Polly
    greeting = (
        "Hello, I'm ASA, your Autonomous Solutions Architect. "
        "Tell me about your organisation and what's driving this cloud initiative."
    )
    await send({"type": "status", "state": "live"})
    await send({"type": "transcript", "role": "agent", "text": greeting})
    await _send_polly_audio(ws, send, greeting)

    transcript.append({"role": "agent", "text": greeting})

    while True:
        raw = await ws.receive_text()
        msg = json.loads(raw)

        if msg.get("type") == "hangup":
            logger.info("Voice hangup")
            await send({"type": "status", "state": "processing"})
            # Generate digest
            digest = _generate_voice_digest(transcript, session_id)
            await send({"type": "digest", "data": digest})
            break

        elif msg.get("type") == "transcript_input":
            # Client-side STT sent the text
            user_text = msg.get("text", "").strip()
            if not user_text:
                continue

            transcript.append({"role": "user", "text": user_text})
            await send({"type": "transcript", "role": "user", "text": user_text})

            # Process through agent pipeline
            result = await orchestrator.process_message(session_id, user_text)
            response_text = result.get("content", "I'm processing your request.")

            transcript.append({"role": "agent", "text": response_text})
            await send({"type": "transcript", "role": "agent", "text": response_text})

            # Send TTS audio
            await _send_polly_audio(ws, send, response_text)

        elif msg.get("type") == "audio":
            # Raw audio — just acknowledge (client handles STT)
            pass


async def _send_polly_audio(ws, send, text: str):
    """Synthesize speech with Polly and stream back as base64 PCM chunks."""
    try:
        polly = boto3.client("polly", region_name=settings.aws_region)
        response = polly.synthesize_speech(
            Text=text[:3000],  # Polly limit
            OutputFormat="pcm",
            SampleRate="16000",
            VoiceId="Matthew",
            Engine="neural",
        )
        audio_bytes = response["AudioStream"].read()

        # Send in chunks for smooth playback
        chunk_size = 4096
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i + chunk_size]
            import base64
            b64 = base64.b64encode(chunk).decode("ascii")
            await send({"type": "audio", "data": b64})

    except Exception as e:
        logger.warning(f"Polly TTS failed: {e}")


async def _run_nova_sonic_session(ws, session_id, transcript, send):
    """Full Nova Sonic bidirectional voice — requires Python 3.12+ SDK."""
    from nova_sonic_handler import NovaSonicHandler

    handler = NovaSonicHandler(
        session_id=session_id,
        orchestrator=orchestrator,
        on_audio=lambda b64: send({"type": "audio", "data": b64}),
        on_transcript=lambda role, text: send({"type": "transcript", "role": role, "text": text}),
    )

    await send({"type": "status", "state": "connecting"})
    await handler.start()
    await send({"type": "status", "state": "live"})

    while True:
        raw = await ws.receive_text()
        msg = json.loads(raw)

        if msg.get("type") == "audio":
            await handler.send_audio(msg["data"])
        elif msg.get("type") == "hangup":
            await handler.close()
            await send({"type": "status", "state": "processing"})
            digest = _generate_voice_digest(transcript, session_id)
            await send({"type": "digest", "data": digest})
            break


def _generate_voice_digest(transcript: list[dict], session_id: str) -> dict:
    """Generate a summary digest from the voice conversation."""
    user_messages = [t["text"] for t in transcript if t["role"] == "user"]
    agent_messages = [t["text"] for t in transcript if t["role"] == "agent"]

    return {
        "session_id": session_id,
        "summary": f"Discovery workshop with {len(user_messages)} user turns and {len(agent_messages)} ASA responses.",
        "highlights": user_messages[:5] if user_messages else ["No user input captured"],
        "action_items": ["Review the generated architecture report", "Validate against Well-Architected Framework"],
        "sentiment": "positive" if len(user_messages) > 2 else "neutral",
        "transcript_length": len(transcript),
    }
