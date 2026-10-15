#!/usr/bin/env bash
# Hook: Credential Guard (hackathon-adapted)
# Trigger: Pre Tool Use (write)
# Purpose: Block writes containing hardcoded credentials / secrets.
# Exit code: 0 = pass (allow), non-zero = block
set -euo pipefail

TOOL_INPUT=$(cat)

# Note: the tool input arrives as JSON, so quotes inside file content are
# backslash-escaped (\"). Patterns allow an optional backslash before quotes so
# they match both raw source and JSON-escaped tool input.
Q="[\\\\]?['\"]"
PATTERNS=(
  "AKIA[A-Z0-9]{16}"
  "aws_secret_access_key[[:space:]]*=[[:space:]]*${Q}[^'\"\\\\]+${Q}"
  "password[[:space:]]*=[[:space:]]*${Q}[^'\"\\\\]+${Q}"
  "secret_key[[:space:]]*=[[:space:]]*${Q}[^'\"\\\\]+${Q}"
  "api_key[[:space:]]*=[[:space:]]*${Q}[^'\"\\\\]+${Q}"
  "-----BEGIN RSA"
  "-----BEGIN PRIVATE"
  "-----BEGIN EC PRIVATE"
  "mongodb://.*:.*@"
)

for pattern in "${PATTERNS[@]}"; do
  if echo "$TOOL_INPUT" | grep -qEi -- "$pattern"; then
    # Allow obvious placeholders used in docs/examples
    if echo "$TOOL_INPUT" | grep -qEi "(your-|<your|changeme|example|placeholder|xxxxxxxx|REDACTED)"; then
      continue
    fi
    echo "BLOCKED: Potential hardcoded credential detected."
    echo "Pattern matched: $pattern"
    echo "Use environment variables or AWS Secrets Manager for all credentials."
    exit 1
  fi
done
exit 0
