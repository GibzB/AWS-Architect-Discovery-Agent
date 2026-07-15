"""
Nova Sonic bidirectional voice handler for ASA.

Direct port of the vox-brief pattern — sends raw audio to Nova Sonic
which handles all turn-taking, VAD, and response generation natively.
No browser STT needed — Nova Sonic does everything.
"""

import asyncio
import json
import logging
import os
import uuid

import boto3
from aws_sdk_bedrock_runtime.client import (
    BedrockRuntimeClient,
    InvokeModelWithBidirectionalStreamOperationInput,
)
from aws_sdk_bedrock_runtime.config import Config, HTTPAuthSchemeResolver, SigV4AuthScheme
from aws_sdk_bedrock_runtime.models import (
    BidirectionalInputPayloadPart,
    InvokeModelWithBidirectionalStreamInputChunk,
    ValidationException,
)
from smithy_aws_core.identity.static import StaticCredentialsResolver
from smithy_core.shapes import ShapeID

from app.config import settings

logger = logging.getLogger(__name__)

MODEL_ID = "amazon.nova-2-sonic-v1:0"
SAMPLE_RATE = 16000

# ASA system prompt for voice discovery
ASA_VOICE_PROMPT = """You are ASA, an Autonomous Solutions Architect conducting a cloud discovery workshop.

You are speaking with a customer through a real-time voice call. Your role is to:
1. Understand their business objectives and technical requirements
2. Ask intelligent, adaptive follow-up questions
3. Identify gaps in information needed for cloud architecture design
4. Be warm, professional, and conversational — like a Principal Solutions Architect

## Conversation Rules
- Ask ONE question at a time — never stack multiple questions
- Keep responses to 2-3 sentences maximum (this is voice, not text)
- Listen carefully and follow up on interesting points
- Give the customer space to think and speak — never rush them
- Use natural speech: "That's helpful, thank you", "Tell me more about that"
- Cover: business context, technical stack, compliance, scale, DR objectives

## Interview Flow
1. Greet them warmly and explain you'll help design their cloud architecture
2. Ask about their business and what's driving the cloud initiative
3. Ask about current technical architecture and workloads
4. Ask about compliance and regulatory requirements
5. Ask about scale expectations and growth plans
6. Ask about availability and disaster recovery needs
7. Summarize what you've learned and confirm understanding

## Important
- You are speaking — keep it conversational, not formal
- One question at a time
- Acknowledge their answers before asking the next question
- If they give a short answer, probe once before moving on
""".strip()


def _make_client() -> BedrockRuntimeClient:
    """Create the Bedrock Runtime client with SigV4 auth."""
    # Nova Sonic is only available in us-east-1
    region = "us-east-1"
    session = boto3.Session()
    creds = session.get_credentials().get_frozen_credentials()
    resolver = StaticCredentialsResolver()
    config = Config(
        endpoint_uri=f"https://bedrock-runtime.{region}.amazonaws.com",
        region=region,
        aws_credentials_identity_resolver=resolver,
        auth_scheme_resolver=HTTPAuthSchemeResolver(),
        auth_schemes={ShapeID("aws.auth#sigv4"): SigV4AuthScheme(service="bedrock")},
        aws_access_key_id=creds.access_key,
        aws_secret_access_key=creds.secret_key,
        aws_session_token=creds.token,
    )
    return BedrockRuntimeClient(config=config)


class NovaSonicSession:
    """Manages a bidirectional voice session with Nova 2 Sonic."""

    def __init__(self, on_audio, on_transcript, on_done, on_error, system_prompt=None):
        self.on_audio = on_audio
        self.on_transcript = on_transcript
        self.on_done = on_done
        self.on_error = on_error
        self._system_prompt = system_prompt or ASA_VOICE_PROMPT

        self._client = _make_client()
        self._stream = None
        self._prompt_name = str(uuid.uuid4())
        self._audio_name = str(uuid.uuid4())
        self._closed = False
        self._audio_block_open = False
        self._send_queue: asyncio.Queue = asyncio.Queue()
        self._seen_transcripts: set = set()

    async def start(self):
        """Open the bidirectional stream and begin the session."""
        self._stream = await self._client.invoke_model_with_bidirectional_stream(
            InvokeModelWithBidirectionalStreamOperationInput(model_id=MODEL_ID)
        )

        # Start receiver FIRST (calls await_output internally) — vox-brief pattern
        asyncio.create_task(self._receiver())
        asyncio.create_task(self._sender())

        # Send setup events
        await self._send_session_start()
        await asyncio.sleep(0.2)
        await self._send_prompt_start()
        await asyncio.sleep(0.2)
        await self._send_system_prompt()
        await asyncio.sleep(0.2)
        # Open audio block BEFORE greeting (so Nova Sonic has somewhere to listen)
        await self._send_audio_start()
        self._audio_block_open = True
        await asyncio.sleep(0.2)
        await self._send_greeting_trigger()
        logger.info("[start] all setup events sent")

    async def send_audio(self, audio_b64: str):
        """Queue an audio chunk for sending to Nova Sonic."""
        if not self._closed:
            await self._send_queue.put(("audio", audio_b64))

    async def close(self):
        """Gracefully close the session."""
        if not self._closed:
            self._closed = True
            await self._send_queue.put(("close", None))

    # ── Sender task ──

    async def _sender(self):
        try:
            while True:
                kind, data = await self._send_queue.get()
                if kind == "audio":
                    await self._send_audio_chunk(data)
                elif kind == "close":
                    if self._audio_block_open:
                        await self._send_audio_end()
                    await self._send_prompt_end()
                    await self._send_connection_end()
                    break
        except Exception as exc:
            logger.exception("sender error: %s", exc)
            await self.on_error(str(exc))

    # ── Receiver task ──

    async def _receiver(self):
        role = None
        try:
            logger.info("[rx] waiting for output...")
            _, output = await self._stream.await_output()
            logger.info("[rx] stream open")
            while True:
                result = await output.receive()
                if result is None or not result.value or not result.value.bytes_:
                    continue
                ev = json.loads(result.value.bytes_.decode()).get("event", {})

                if "contentStart" in ev:
                    role = ev["contentStart"].get("role")

                elif "audioOutput" in ev:
                    b64 = ev["audioOutput"].get("content", "")
                    if b64:
                        await self.on_audio(b64)

                elif "textOutput" in ev:
                    text = ev["textOutput"].get("content", "").strip()
                    if text and not text.startswith("{"):
                        mapped = "agent" if role == "ASSISTANT" else "user"
                        key = (mapped, text)
                        if key in self._seen_transcripts:
                            continue
                        self._seen_transcripts.add(key)
                        logger.info("[rx] transcript %s: %r", mapped, text[:80])
                        await self.on_transcript(mapped, text)

                elif "completionEnd" in ev:
                    logger.info("[rx] completionEnd")

        except StopAsyncIteration:
            logger.info("[rx] stream closed")
        except ValidationException as exc:
            if "No events to transform were found" not in str(exc):
                await self.on_error(str(exc))
        except Exception as exc:
            logger.exception("[rx] error: %s", exc)
            await self.on_error(str(exc))
        finally:
            await self.on_done()

    # ── Low-level send helpers ──

    async def _send(self, payload: dict):
        await self._stream.input_stream.send(
            InvokeModelWithBidirectionalStreamInputChunk(
                value=BidirectionalInputPayloadPart(
                    bytes_=json.dumps(payload).encode()
                )
            )
        )

    async def _send_session_start(self):
        await self._send({"event": {"sessionStart": {
            "inferenceConfiguration": {
                "maxTokens": 1024,
                "topP": 0.9,
                "temperature": 0.7,
            }
        }}})

    async def _send_prompt_start(self):
        await self._send({"event": {"promptStart": {
            "promptName": self._prompt_name,
            "textOutputConfiguration": {"mediaType": "text/plain"},
            "audioOutputConfiguration": {
                "mediaType": "audio/lpcm",
                "sampleRateHertz": SAMPLE_RATE,
                "sampleSizeBits": 16,
                "channelCount": 1,
                "voiceId": "matthew",
                "encoding": "base64",
                "audioType": "SPEECH",
            },
        }}})

    async def _send_system_prompt(self):
        name = str(uuid.uuid4())
        logger.info(f"[tx] sending system prompt, contentName={name}")
        # Send all three events with small delays to ensure ordering
        payload_start = {"event": {"contentStart": {
            "promptName": self._prompt_name,
            "contentName": name,
            "type": "TEXT",
            "interactive": False,
            "role": "SYSTEM",
            "textInputConfiguration": {"mediaType": "text/plain"},
        }}}
        payload_text = {"event": {"textInput": {
            "promptName": self._prompt_name,
            "contentName": name,
            "content": self._system_prompt,
        }}}
        payload_end = {"event": {"contentEnd": {
            "promptName": self._prompt_name,
            "contentName": name,
        }}}
        await self._send(payload_start)
        await asyncio.sleep(0.1)
        await self._send(payload_text)
        await asyncio.sleep(0.1)
        await self._send(payload_end)
        logger.info(f"[tx] system prompt sent OK")

    async def _send_greeting_trigger(self):
        name = str(uuid.uuid4())
        logger.info(f"[tx] sending greeting trigger, contentName={name}")
        payload_start = {"event": {"contentStart": {
            "promptName": self._prompt_name,
            "contentName": name,
            "type": "TEXT",
            "interactive": False,
            "role": "USER",
            "textInputConfiguration": {"mediaType": "text/plain"},
        }}}
        payload_text = {"event": {"textInput": {
            "promptName": self._prompt_name,
            "contentName": name,
            "content": "Hello",
        }}}
        payload_end = {"event": {"contentEnd": {
            "promptName": self._prompt_name,
            "contentName": name,
        }}}
        await self._send(payload_start)
        await asyncio.sleep(0.1)
        await self._send(payload_text)
        await asyncio.sleep(0.1)
        await self._send(payload_end)
        logger.info(f"[tx] greeting trigger sent OK")

    async def _send_audio_start(self):
        await self._send({"event": {"contentStart": {
            "promptName": self._prompt_name,
            "contentName": self._audio_name,
            "type": "AUDIO",
            "interactive": True,
            "role": "USER",
            "audioInputConfiguration": {
                "mediaType": "audio/lpcm",
                "sampleRateHertz": SAMPLE_RATE,
                "sampleSizeBits": 16,
                "channelCount": 1,
                "audioType": "SPEECH",
                "encoding": "base64",
            },
        }}})

    async def _send_audio_chunk(self, audio_b64: str):
        await self._send({"event": {"audioInput": {
            "promptName": self._prompt_name,
            "contentName": self._audio_name,
            "content": audio_b64,
        }}})

    async def _send_audio_end(self):
        await self._send({"event": {"contentEnd": {
            "promptName": self._prompt_name,
            "contentName": self._audio_name,
        }}})

    async def _send_prompt_end(self):
        await self._send({"event": {"promptEnd": {
            "promptName": self._prompt_name,
        }}})

    async def _send_connection_end(self):
        await self._send({"event": {"connectionEnd": {}}})
