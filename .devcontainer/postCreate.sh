#!/usr/bin/env bash
# Codespace post-create setup for the AWS CDS Agentic Omnichannel project.
# Installs Python deps, jq, and makes the guard-hook scripts executable.
set -euo pipefail

echo "→ Installing jq…"
sudo apt-get update -y >/dev/null 2>&1 || true
sudo apt-get install -y jq >/dev/null 2>&1 || true

echo "→ Installing Python dependencies (agent)…"
python -m pip install --upgrade pip >/dev/null
# Local dev deps let you run uvicorn local_server; full container deps are in requirements.txt.
if [ -f agent/requirements-local.txt ]; then
  pip install -r agent/requirements-local.txt || pip install -r agent/requirements.txt || true
else
  pip install -r agent/requirements.txt || true
fi

echo "→ Making guard-hook scripts executable…"
chmod +x .kiro/hooks/scripts/*.sh 2>/dev/null || true

echo "→ Preparing agent/.env (SANDBOX_MODE on by default)…"
if [ ! -f agent/.env ] && [ -f agent/.env.example ]; then
  cp agent/.env.example agent/.env
fi

cat <<'MSG'

Codespace ready.

Next steps:
  1. Configure AWS credentials:   aws configure            (or set AWS_* env vars)
  2. Enable Bedrock model access for Nova in the AWS console (us-east-1).
  3. Deploy the full app (Docker is available here):
        ./deploy.sh --profile <aws-profile> --password <demo-password>
     Add --live --ses-sender <verified-email> --sms-identity <id> for real CDS sends.
  4. Or run locally in sandbox:
        cd agent && uvicorn local_server:app --reload --port 8000

MSG
