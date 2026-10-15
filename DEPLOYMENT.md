# AWS Discovery Orchestrator — Deployment Guide

## Prerequisites

### Quickest path — prebuilt image

- AWS CLI configured with a profile
- Docker installed and logged in to Docker Hub (`docker login`)
- `jq` installed
- Amazon Bedrock model access enabled (Nova 2 Sonic + Nova Pro) in your region

### Full build from source

- AWS CLI configured with a profile
- Docker with buildx support (Docker Desktop or similar), logged in to Docker Hub
- `jq` installed
- Amazon Bedrock model access enabled

## Enable Bedrock Models

Before deploying, ensure you have model access in your AWS region:

1. Go to Amazon Bedrock console → Model access
2. Request access to:
   - `amazon.nova-2-sonic-v1:0` (bidirectional voice)
   - `amazon.nova-pro-v1:0` (report generation)
3. Wait for access to be granted (usually immediate)

## AWS CDS — provisioning (for live sends)

The project deploys and runs in `SANDBOX_MODE` by default (channel adapters
record intended sends instead of calling AWS), so you can demo the full
voice → report → email → SMS → two-way loop before any CDS resources exist. To
send for real, provision the following in the **same region** (`us-east-1`).

### 1. Amazon SES (email channel)

1. Amazon SES console → **Verified identities** → verify a sender email or your
   domain. (CloudFormation also creates an `AWS::SES::EmailIdentity` for the
   address you pass as `--ses-sender`; you still complete the verification click
   / DNS records.)
2. If your SES account is in the sandbox, verify the recipient addresses too, or
   request production access.

### 2. AWS End User Messaging (SMS / RCS channel)

1. AWS End User Messaging SMS console → request a phone number (or create a pool
   / sender ID) capable of SMS. Note its **phone number id / ARN or pool id** —
   that is your `--sms-identity` value.
2. For two-way, enable **two-way SMS** on the number and set its **inbound SNS
   destination** to the `InboundTopicArn` printed by `deploy.sh` (the
   `aws-discovery-inbound` topic).
3. RCS: once a brand RCS agent is approved, set `RCS_AGENT_ID` and switch
   `--follow-up rcs`. The RCS adapter upgrades from text to rich cards with no
   call-site change.

### 3. Deploy live

```bash
./deploy.sh --profile <aws-profile> --password <demo-password> \
  --live \
  --ses-sender no-reply@your-domain.com \
  --sms-identity <phone-number-id-or-pool-id> \
  --follow-up sms \
  --demo-email you@your-domain.com \
  --demo-phone +1XXXXXXXXXX
```

After deploy, wire the EUM number's two-way inbound to the printed
`InboundTopicArn`.

### Inbound Lambda: demo vs production

The CloudFormation ships a **self-contained inline inbound Lambda** so the
two-way loop works immediately with no packaging. The **production** handler is
`infra/inbound_lambda.py`, which reuses the full `agent/engagement` package
(Bedrock intent routing, grounded answers, the channel layer). To use it, package
the `agent/` directory with the Lambda (a container image, or a zip that includes
`agent/channels` + `agent/engagement` + `agent/prompts`) and set the function's
`Handler` to `inbound_lambda.handler`.

### SANDBOX_MODE demo (no CDS resources)

Leave the default (omit `--live`). The agent records what it would send; check
the AgentCore / Lambda CloudWatch logs for `[sandbox] would send ...` lines to
show the omnichannel flow end-to-end.

## Deploy

```bash
git clone <your-repo-url>
cd aws-discovery-orchestrator

# ── Recommended: use prebuilt image (no Docker build needed) ──
./deploy.sh --profile <your-aws-profile> --password <your-demo-password> --prebuilt

# ── Or build from source ──
./deploy.sh --profile <your-aws-profile> --password <your-demo-password>

# With WAF (adds rate limiting + AWS managed rules, ~$7/month)
./deploy.sh --profile <your-aws-profile> --password <your-demo-password> --prebuilt --waf

# Without auth (open access — not recommended)
./deploy.sh --profile <your-aws-profile> --prebuilt
```

The script will:

1. Create an ECR repository (bootstrap stack, first run only)
2. Pull the prebuilt image from Docker Hub and push to your ECR (or build from source)
3. Deploy the main CloudFormation stack (AgentCore Runtime, API Gateway, S3, CloudFront, DynamoDB)
4. Write `frontend/config.json` with the presign API URL and auth token
5. Upload frontend assets to S3

The CloudFront URL is printed at the end.

### Login credentials

- Username: `demo`
- Password: whatever you passed via `--password`

### Cold start

The first call after a fresh deploy (or after inactivity) takes 30-60 seconds
while the container starts. Make a test call a couple of minutes before a live
demo to warm it up.

## Tear down

```bash
PROFILE=<your-aws-profile>

# 1. Empty the frontend bucket
aws --profile $PROFILE --region us-east-1 \
  s3 rm s3://aws-discovery-frontend-$(aws --profile $PROFILE sts get-caller-identity --query Account --output text)-us-east-1 --recursive

# 2. Delete the main stack
aws --profile $PROFILE --region us-east-1 \
  cloudformation delete-stack --stack-name aws-discovery-orchestrator

# 3. (Optional) Delete the bootstrap stack (ECR repo + images)
aws --profile $PROFILE --region us-east-1 \
  cloudformation delete-stack --stack-name aws-discovery-bootstrap
```

## Docker notes

### Log in to Docker Hub first

Both deploy paths pull from Docker Hub. If you haven't logged in:

```bash
docker login
```

### Linux with Docker Desktop

If Docker uses a non-default socket:

```bash
export DOCKER_HOST=unix://$HOME/.docker/desktop/docker.sock
```
