"""Amazon Bedrock client — shared LLM invocation for all agents."""

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)


class BedrockClient:
    """Wraps Bedrock Converse API for Nova models."""

    def __init__(
        self,
        region: str | None = None,
        model_id: str | None = None,
    ):
        self.region = region or settings.aws_region
        self.model_id = model_id or settings.bedrock_model_id
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client("bedrock-runtime", region_name=self.region)
        return self._client

    async def invoke(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        """Invoke Bedrock model and return text response."""
        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": user_prompt}]}],
                system=[{"text": system_prompt}],
                inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
            )
            return response["output"]["message"]["content"][0]["text"]
        except ClientError as e:
            logger.error(f"Bedrock invocation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Bedrock: {e}")
            raise

    async def invoke_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Invoke Bedrock and parse JSON response."""
        raw = await self.invoke(system_prompt, user_prompt, max_tokens, temperature)
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last lines (fences)
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)
        return json.loads(cleaned)


# Singleton instance
bedrock = BedrockClient()
