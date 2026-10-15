#!/usr/bin/env bash
set -euo pipefail
# Hook: PII Detection Guard (hackathon-adapted)
# Trigger: Pre Tool Use (write)
# Purpose: Block hardcoded customer PII in source — the contact data this
#          messaging app handles: email addresses, E.164 phone numbers,
#          and payment-card-length digit runs.
# Exit code: 0 = PASS (no PII), 1 = BLOCK (hardcoded PII detected)
#
# Adapted from the Kiro-SDLC-Scrum skill: the Singapore-specific NRIC/passport
# rules are dropped; phone matching is generalized to international E.164.

TOOL_INPUT=$(cat)

# Scan the full tool input. We deliberately do not try to extract only the
# "text"/"content" field: portable (BSD + GNU) extraction of a JSON string is
# fragile, and scanning the whole payload is strictly safer for a guard.
FILE_CONTENT="$TOOL_INPUT"

BLOCKED=0

# Credit-card-length digit runs (13-19 digits, optional separators) in a literal
if echo "$FILE_CONTENT" | grep -qE "['\"][^'\"]*[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{1,7}[^'\"]*['\"]"; then
  echo "BLOCKED: Hardcoded card-length number detected (13-19 digits)."
  echo "Never store card numbers in source. Use tokenization."
  BLOCKED=1
fi

# Hardcoded email addresses in string literals (allow docs/sample/test domains)
if echo "$FILE_CONTENT" | grep -qE "['\"][^'\"]*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^'\"]*['\"]"; then
  if echo "$FILE_CONTENT" | grep -E "['\"][^'\"]*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^'\"]*['\"]" \
      | grep -qvE "(example\.(com|org|net)|test\.|localhost|@param|@return|noreply@|no-reply@)"; then
    echo "BLOCKED: Hardcoded email address detected in a string literal."
    echo "Use environment variables / config, or an example.com placeholder."
    BLOCKED=1
  fi
fi

# International E.164 phone numbers in literals: + then 8-15 digits (optional
# spaces/dashes). Allow the reserved +1 555-01xx range used for examples.
if echo "$FILE_CONTENT" | grep -qE "['\"][^'\"]*\+[0-9][0-9[:space:]-]{7,16}[0-9][^'\"]*['\"]"; then
  if echo "$FILE_CONTENT" | grep -E "['\"][^'\"]*\+[0-9][0-9[:space:]-]{7,16}[0-9][^'\"]*['\"]" \
      | grep -qvE "\+1[[:space:]]?555[[:space:]-]?01[0-9]{2}"; then
    echo "BLOCKED: Hardcoded phone number detected (E.164-style)."
    echo "Use secure storage/config. For samples use the +1 555-01xx range."
    BLOCKED=1
  fi
fi

if [ $BLOCKED -eq 1 ]; then
  echo ""
  echo "Privacy: customer contact data must not be hardcoded in source."
  exit 1
fi
exit 0
