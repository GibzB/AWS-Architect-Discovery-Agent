#!/usr/bin/env bash
set -euo pipefail
# Hook: Prompt Security Guard (hackathon-adapted)
# Trigger: Prompt Submit
# Purpose: Block prompts that try to bypass the security controls or disable the
#          guard hooks in this project.
# Exit code: 0 = PASS, 1 = BLOCK

PROMPT_INPUT=$(cat)
LOWER_INPUT=$(echo "$PROMPT_INPUT" | tr '[:upper:]' '[:lower:]')

BLOCKED_PHRASES=(
  "skip security"
  "disable hook"
  "bypass guard"
  "turn off scan"
  "remove security"
  "disable validation"
  "skip validation"
  "ignore security"
  "disable guard"
  "no security check"
  "without security"
)

for phrase in "${BLOCKED_PHRASES[@]}"; do
  if echo "$LOWER_INPUT" | grep -qF "$phrase"; then
    echo "BLOCKED: Security bypass attempt detected."
    echo "Phrase: '$phrase'"
    echo ""
    echo "The credential / PII guards protect customer contact data handled by"
    echo "this messaging app and cannot be bypassed via prompt."
    exit 1
  fi
done

exit 0
