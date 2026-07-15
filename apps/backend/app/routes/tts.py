"""Text-to-Speech endpoint — Amazon Polly Neural for human-like voice."""

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
    
    Returns MP3 audio for natural human-like voice.
    """
    try:
        polly = boto3.client("polly", region_name=settings.aws_region)
        
        # Clean markdown from text
        clean = text.replace("**", "").replace("---", "").replace("#", "").replace("`", "").replace("*", "")
        
        response = polly.synthesize_speech(
            Text=clean[:3000],
            TextType="text",
            OutputFormat="mp3",
            VoiceId=voice,
            Engine="neural",
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
