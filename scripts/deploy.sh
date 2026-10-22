#!/bin/bash
set -e

# ──────────────────────────────────────────────────────────────
# Atlas Discovery — Deployment Script
# ──────────────────────────────────────────────────────────────
# Usage: ./scripts/deploy.sh [--profile PROFILE] [--region REGION] [--env ENV]

PROFILE="K1-Kitstek-Billy"
REGION="us-east-1"
ENVIRONMENT="dev"
PROJECT="atlas-discovery"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --profile) PROFILE="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --env) ENVIRONMENT="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "🚀 Atlas Discovery — Deploying"
echo "  Profile:     $PROFILE"
echo "  Region:      $REGION"
echo "  Environment: $ENVIRONMENT"
echo ""

# ──────────────────────────────────────────────────────────────
# Step 1: Terraform
# ──────────────────────────────────────────────────────────────
echo "🏗️  Deploying infrastructure..."
cd infra/terraform

export AWS_PROFILE="$PROFILE"
export AWS_REGION="$REGION"

terraform init -input=false
terraform apply -auto-approve \
  -var="aws_region=$REGION" \
  -var="environment=$ENVIRONMENT" \
  -var="project_name=$PROJECT"

# Capture outputs
DYNAMODB_TABLE=$(terraform output -raw dynamodb_table_name)
S3_REPORTS=$(terraform output -raw reports_bucket_name)
S3_FRONTEND=$(terraform output -raw frontend_bucket_name)
COGNITO_POOL=$(terraform output -raw cognito_user_pool_id)
COGNITO_CLIENT=$(terraform output -raw cognito_client_id)

cd ../..

echo "  ✓ DynamoDB: $DYNAMODB_TABLE"
echo "  ✓ S3 Reports: $S3_REPORTS"
echo "  ✓ S3 Frontend: $S3_FRONTEND"
echo "  ✓ Cognito Pool: $COGNITO_POOL"
echo ""

# ──────────────────────────────────────────────────────────────
# Step 2: Build Frontend
# ──────────────────────────────────────────────────────────────
echo "🎨 Building frontend..."
cd apps/frontend

# Write runtime config
cat > public/config.json <<EOF
{
  "apiUrl": "https://api.${PROJECT}.example.com/v1",
  "cognitoPoolId": "${COGNITO_POOL}",
  "cognitoClientId": "${COGNITO_CLIENT}",
  "region": "${REGION}"
}
EOF

npm run build
cd ../..
echo "  ✓ Frontend built"
echo ""

# ──────────────────────────────────────────────────────────────
# Step 3: Deploy Frontend to S3
# ──────────────────────────────────────────────────────────────
echo "📤 Deploying frontend to S3..."
aws s3 sync apps/frontend/dist "s3://$S3_FRONTEND" \
  --delete \
  --profile "$PROFILE" \
  --region "$REGION"
echo "  ✓ Frontend deployed to s3://$S3_FRONTEND"
echo ""

# ──────────────────────────────────────────────────────────────
# Step 4: Backend (local for hackathon — container for prod)
# ──────────────────────────────────────────────────────────────
echo "📋 Backend Configuration"
echo ""
echo "  To run the backend locally:"
echo "    cd apps/backend"
echo "    source .venv/bin/activate"
echo "    export AWS_PROFILE=$PROFILE"
echo "    export AWS_REGION=$REGION"
echo "    export DYNAMODB_TABLE_NAME=$DYNAMODB_TABLE"
echo "    export S3_REPORTS_BUCKET=$S3_REPORTS"
echo "    export COGNITO_USER_POOL_ID=$COGNITO_POOL"
echo "    export COGNITO_CLIENT_ID=$COGNITO_CLIENT"
echo "    uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""

# ──────────────────────────────────────────────────────────────
# Done
# ──────────────────────────────────────────────────────────────
echo "✅ Deployment complete!"
echo ""
echo "  Frontend: s3://$S3_FRONTEND (add CloudFront for HTTPS)"
echo "  Backend:  Run locally or deploy to ECS/AgentCore"
echo ""
