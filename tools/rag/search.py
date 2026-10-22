"""RAG Tool — search Bedrock Knowledge Base for AWS best practices."""

import logging
from typing import Any

import boto3

from app.config import settings

logger = logging.getLogger(__name__)


class KnowledgeBaseSearch:
    """Search Amazon Bedrock Knowledge Base for relevant AWS documentation."""

    def __init__(self, knowledge_base_id: str | None = None):
        self.knowledge_base_id = knowledge_base_id
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                "bedrock-agent-runtime",
                region_name=settings.aws_region,
            )
        return self._client

    async def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Search the knowledge base and return relevant passages.

        Returns a list of results with text and metadata.
        """
        if not self.knowledge_base_id:
            logger.warning("No Knowledge Base ID configured — returning empty results")
            return []

        try:
            response = self.client.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": max_results,
                    }
                },
            )

            results = []
            for item in response.get("retrievalResults", []):
                content = item.get("content", {}).get("text", "")
                metadata = item.get("metadata", {})
                score = item.get("score", 0.0)
                location = item.get("location", {})

                results.append({
                    "text": content,
                    "score": score,
                    "source": location.get("s3Location", {}).get("uri", ""),
                    "metadata": metadata,
                })

            return results

        except Exception as e:
            logger.error(f"Knowledge Base search failed: {e}")
            return []


# Singleton — will be configured with KB ID from environment
kb_search = KnowledgeBaseSearch()
