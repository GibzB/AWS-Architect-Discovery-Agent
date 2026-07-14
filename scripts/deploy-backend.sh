#!/bin/bash
set -e

PROFILE="K1-Kitstek-Billy"
REGION="eu-west-1"
STACK_NAME="asa-discovery-backend"
BUCKET_NAME="asa-discovery-lambda-${RANDOM}"
FUNCTION_NAME="asa-discovery-api"

echo "🚀 ASA Backend — Lambda Deployment"
echo "  Profile: $PROFILE"
echo "  Region:  $REGION"
echo ""

# ──────────────────────────────────────────────────────────────
# Step 1: Package the Lambda
# ──────────────────────────────────────────────────────────────
echo "📦 Packaging Lambda..."

cd apps/backend
rm -rf /tmp/asa-lambda-pkg /tmp/asa-lambda.zip

# Install deps into package dir
pip install --quiet --target /tmp/asa-lambda-pkg \
  fastapi pydantic boto3 mangum uvicorn httpx

# Copy application code
cp -r app /tmp/asa-lambda-pkg/
cp lambda_handler.py /tmp/asa-lambda-pkg/

# Copy project-level packages
cp -r ../../packages /tmp/asa-lambda-pkg/
cp -r ../../agents /tmp/asa-lambda-pkg/
cp -r ../../tools /tmp/asa-lambda-pkg/

# Create zip
cd /tmp/asa-lambda-pkg
zip -qr /tmp/asa-lambda.zip . -x "*.pyc" "__pycache__/*" "*.dist-info/*" "bin/*"
cd -

ZIPSIZE=$(du -h /tmp/asa-lambda.zip | cut -f1)
echo "  ✓ Package created: ${ZIPSIZE}"

# ──────────────────────────────────────────────────────────────
# Step 2: Create S3 bucket for deployment artifact
# ──────────────────────────────────────────────────────────────
echo ""
echo "📤 Uploading to S3..."

# Use a deterministic bucket name
BUCKET_NAME="asa-discovery-deploy-742710068514"
aws s3 mb "s3://${BUCKET_NAME}" --profile "$PROFILE" --region "$REGION" 2>/dev/null || true
aws s3 cp /tmp/asa-lambda.zip "s3://${BUCKET_NAME}/lambda.zip" \
  --profile "$PROFILE" --region "$REGION" --quiet
echo "  ✓ Uploaded to s3://${BUCKET_NAME}/lambda.zip"

# ──────────────────────────────────────────────────────────────
# Step 3: Deploy CloudFormation stack
# ──────────────────────────────────────────────────────────────
echo ""
echo "🏗️  Deploying CloudFormation stack..."

aws cloudformation deploy \
  --template-file ../../infra/backend-lambda.yaml \
  --stack-name "$STACK_NAME" \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    S3Bucket="$BUCKET_NAME" \
    S3Key="lambda.zip" \
  --profile "$PROFILE" \
  --region "$REGION" \
  --no-fail-on-empty-changeset

# ──────────────────────────────────────────────────────────────
# Step 4: Get the API URL
# ──────────────────────────────────────────────────────────────
echo ""
API_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --profile "$PROFILE" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text)

echo "✅ Backend deployed!"
echo ""
echo "  API URL: ${API_URL}"
echo "  Health:  ${API_URL}health"
echo ""
echo "  Update your frontend to point to this URL."
echo ""
