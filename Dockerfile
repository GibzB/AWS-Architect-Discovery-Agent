FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY apps/backend/requirements.txt .
RUN pip install --no-cache-dir fastapi 'uvicorn[standard]' pydantic boto3 python-dotenv httpx websockets mangum aws-sdk-bedrock-runtime smithy-aws-core smithy-core awscrt botocore==1.42.78 boto3==1.42.78

# Copy all source code
COPY apps/backend/app/ app/
COPY packages/ packages/
COPY agents/ agents/
COPY tools/ tools/

# Ensure __init__.py files exist
RUN touch packages/__init__.py agents/__init__.py tools/__init__.py

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
