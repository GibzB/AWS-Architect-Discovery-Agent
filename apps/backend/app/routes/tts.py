"""Text-to-Speech endpoint — returns Polly audio as MP3 for natural voice."""

import logging

import boto3
from fastapi import APIRouter
from fastapi.responses import Response

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/v1/tts")
async def text_to_speech(text: str, voice: str = "Matthew"):
    """Convert text to speech using Amazon Polly Neural engine.
    
    Returns MP3 audio that can be played directly by the browser.
    Voices: Matthew (male), Joanna (female), Stephen (male UK), Ruth (female UK)
    """
    try:
        polly = boto3.client("polly", region_name=settings.aws_region)
        
        # Use SSML for more natural speech
        ssml_text = f'<speak><prosody rate="medium" pitch="medium">{_escape_ssml(text[:3000])}</prosody></speak>'
        
        response = polly.synthesize_speech(
            Text=ssml_text,
            TextType="ssml",
            OutputFormat="mp3",
            VoiceId=voice,
            Engine="neural",
            SampleRate="24000",
        )
        
        audio_bytes = response["AudioStream"].read()
        
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Length": str(len(audio_bytes)),
                "Cache-Control": "no-cache",
            },
        )
    except Exception as e:
        logger.error(f"Polly TTS failed: {e}")
        return Response(content=b"", status_code=500)


def _escape_ssml(text: str) -> str:
    """Escape special chars for SSML and clean markdown."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace('"', "&quot;").replace("'", "&apos;")
    # Remove markdown formatting
    text = text.replace("**", "").replace("---", "").replace("#", "").replace("`", "")
    return text
