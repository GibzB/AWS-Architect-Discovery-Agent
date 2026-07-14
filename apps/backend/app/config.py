"""Application configuration via environment variables."""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    """App settings — loaded from environment."""

    aws_region: str = os.getenv("AWS_REGION_NAME", os.getenv("AWS_REGION", "eu-west-1"))
    dynamodb_table: str = os.getenv("DYNAMODB_TABLE_NAME", "asa-discovery-dev-sessions")
    s3_reports_bucket: str = os.getenv("S3_REPORTS_BUCKET", "asa-discovery-dev-reports")
    bedrock_model_id: str = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")
    bedrock_voice_model_id: str = os.getenv("BEDROCK_VOICE_MODEL_ID", "amazon.nova-sonic-v1:0")
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "DEBUG")


settings = Settings()
