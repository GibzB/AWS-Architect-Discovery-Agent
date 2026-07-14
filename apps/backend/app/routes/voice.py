"""Voice WebSocket endpoint — bridges browser audio to ASA orchestrator.

Architecture:
- Speech-to-Text: Browser's Web Speech API (client-side, zero latency)
- Orchestration: Same agent pipeline as chat (Planner → Agent → Response)
- Text-to-Speech: Amazon Polly via boto3 (streaming audio back to client)

This avoids the Python 3.12 requirement of the Nova Sonic SDK while
still delivering a compelling voice demo.
"""

import asyncio
import base64
import json
import logging
import uuid
from io import BytesIO

import boto3
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.services.orchestrator import orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_polly():
    """Get Polly client for TTS."""
    return boto3.client("polly", region_name=settings.aws_region)


def _synthesize_speech(text: str) -> bytes | None:
    """Convert text to speech using Amazon Polly. Returns PCM audio bytes."""
    try:
        polly = _get_polly()
        response = polly.synthesize_speech(
            Text=text,
            OutputFormat="pcm",
            SampleRate="16000",
            VoiceId="Matthew",  # Professional male voice
            Engine="neural",
        )
        return response["AudioStream"].read()
    except Exception as e:
        logger.error(f"Polly synthesis failed: {e}")
        return None


@router.websocket("/v1/sessions/{session_id}/voice")
async def voice_websocket(ws: WebSocket, session_id: str):
    """
    Voice WebSocket endpoint.

    Protocol:
    Client → Server:
      {"type": "start"}                    — begin session
      {"type": "transcript", "text": "…"}  — speech-to-text result from browser
      {"type": "hangup"}                   — end session

    Server → Client:
      {"type": "status", "state": "ready|thinking|speaking|done"}
      {"type": "text", "content": "…"}     — ASA text response
      {"type": "audio", "data": "base64"}  — TTS audio chunk
      {"type": "agent_trace", "data": {}}  — agent reasoning trace
      {"type": "error", "message": "…"}
    """
    await ws.accept()
    logger.info(f"Voice WebSocket connected: session={session_id}")

    # Verify session exists
    session = await orchestrator.get_session(session_id)
    if session is None:
        await ws.send_json({"type": "error", "message": "Session not found"})
        await ws.close()
        return

    try:
        await ws.send_json({"type": "status", "state": "ready"})

        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "start":
                # Send ASA greeting as audio
                greeting = (
                    "Good afternoon. I'm ASA, your Autonomous Solutions Architect. "
                    "I'll guide you through today's cloud discovery workshop. "
                    "Tell me about your organisation and what's driving this cloud initiative."
                )
                await ws.send_json({"type": "text", "content": greeting})
                await _send_audio_response(ws, greeting)
                await ws.send_json({"type": "status", "state": "ready"})

            elif msg_type == "transcript":
                # User spoke — process through agent pipeline
                user_text = msg.get("text", "").strip()
                if not user_text:
                    continue

                await ws.send_json({"type": "status", "state": "thinking"})

                # Run through orchestrator (same as chat)
                result = await orchestrator.process_message(session_id, user_text)

                if "error" in result:
                    await ws.send_json({"type": "error", "message": result["error"]})
                    continue

                response_text = result.get("content", "")

                # Send text response
                await ws.send_json({"type": "text", "content": response_text})

                # Send agent trace
                await ws.send_json({"type": "agent_trace", "data": result.get("agent_trace", {})})

                # Synthesize and stream audio
                await ws.send_json({"type": "status", "state": "speaking"})
                await _send_audio_response(ws, response_text)
                await ws.send_json({"type": "status", "state": "ready"})

            elif msg_type == "hangup":
                logger.info(f"Voice session hangup: {session_id}")
                await ws.send_json({"type": "status", "state": "done"})
                break

    except WebSocketDisconnect:
        logger.info(f"Voice WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.exception(f"Voice WebSocket error: {e}")
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


async def _send_audio_response(ws: WebSocket, text: str):
    """Synthesize text to speech and send as base64 audio chunks."""
    # Run Polly in thread to avoid blocking
    audio_bytes = await asyncio.to_thread(_synthesize_speech, text)

    if audio_bytes is None:
        return

    # Send in 4KB chunks for smoother playback
    chunk_size = 4096
    for i in range(0, len(audio_bytes), chunk_size):
        chunk = audio_bytes[i:i + chunk_size]
        b64_chunk = base64.b64encode(chunk).decode("ascii")
        await ws.send_json({"type": "audio", "data": b64_chunk})

    # Signal end of audio
    await ws.send_json({"type": "audio_end"})
