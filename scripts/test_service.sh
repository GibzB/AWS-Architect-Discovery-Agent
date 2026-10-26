#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Atlas service smoke test — drives the full flow end to end against a running
# backend (local or deployed) and exercises the AWS CDS engagement path.
#
# Usage:
#   scripts/test_service.sh [BASE_URL]
#
#   BASE_URL   Backend base (no trailing /v1). Defaults to http://localhost:8010
#
# Examples:
#   scripts/test_service.sh                                   # local on :8010
#   scripts/test_service.sh https://i4k4sgqeub.execute-api.us-east-1.amazonaws.com
#
# What it does:
#   1. Health check
#   2. Create a discovery session
#   3. Drive a scripted workshop until a report is approved (or max turns)
#   4. Fetch the report
#   5. Trigger CDS delivery (/engage) — email + SMS/RCS follow-up
#   6. Exercise the two-way inbound loop (/inbound) for each intent
#
# Requires: curl, python3. No extra installs.
# ──────────────────────────────────────────────────────────────────────────
set -uo pipefail

BASE="${1:-http://localhost:8010}"
API="$BASE/v1"
EMAIL="${TEST_EMAIL:-customer@example.com}"
PHONE="${TEST_PHONE:-+15550100123}"

pass=0; fail=0
ok()   { echo "  [PASS] $1"; pass=$((pass+1)); }
bad()  { echo "  [FAIL] $1"; fail=$((fail+1)); }

jqget() { python3 -c "import sys,json;d=json.load(sys.stdin);print(d$1)" 2>/dev/null; }

echo "== Atlas service test =="
echo "backend: $BASE"
echo

# 1. Health ------------------------------------------------------------------
echo "1) Health"
H=$(curl -s -m 30 "$BASE/health")
if echo "$H" | grep -q '"status":"healthy"'; then ok "health is healthy"; else bad "health: $H"; fi

# 2. Create session ----------------------------------------------------------
echo "2) Create session"
SID=$(curl -s -m 60 -X POST "$API/sessions" -H 'Content-Type: application/json' \
  -d '{"customer_name":"Acme Retail","customer_industry":"e-commerce retail"}' | jqget "['session_id']")
if [ -n "$SID" ]; then ok "session created ($SID)"; else bad "no session id"; echo "aborting"; exit 1; fi

# 3. Drive the workshop ------------------------------------------------------
echo "3) Drive workshop toward an approved report"
MSGS=(
"We are a mid-size e-commerce retailer, ~2M users, currently on-premises, moving to AWS to handle seasonal traffic peaks."
"Main workloads: web storefront, order processing, real-time inventory, and payments. Data ~5TB and growing."
"Compliance: PCI-DSS for payments, US data residency. Identity is Okta. We expect 3x growth in 2 years and a new mobile app."
"Availability target 99.95% uptime, RTO 1 hour, RPO 5 minutes. Budget is flexible for the right design."
"No further constraints. Please design the architecture and recommend services."
"That looks good — please finalize and complete the workshop."
"Please proceed and approve the final architecture."
"Confirm and complete — generate the report."
)
REVIEW=""
for m in "${MSGS[@]}"; do
  R=$(curl -s -m 120 -X POST "$API/sessions/$SID/messages" -H 'Content-Type: application/json' \
    -d "$(python3 -c "import json,sys;print(json.dumps({'content':sys.argv[1]}))" "$m")")
  AGENT=$(echo "$R" | jqget "['agent_trace']['agent_invoked']")
  STATUS=$(echo "$R" | jqget "['session_status']")
  REVIEW=$(echo "$R" | jqget "['metadata']['review_status']")
  echo "   turn -> agent=$AGENT status=$STATUS review=$REVIEW"
  [ "$REVIEW" = "approved" ] && break
done
[ "$STATUS" ] && ok "workshop advanced (status=$STATUS, review=$REVIEW)" || bad "workshop did not advance"

# 4. Report ------------------------------------------------------------------
echo "4) Fetch report"
RPT=$(curl -s -m 60 "$API/sessions/$SID/report")
if echo "$RPT" | grep -q 'executive_summary\|report_markdown'; then
  ok "report available"
else
  bad "report not available yet (review=$REVIEW) — engagement needs an approved report"
  echo "   (The agents may need more turns to approve. Re-run or continue the chat.)"
fi

# 5. CDS engagement (/engage) ------------------------------------------------
echo "5) CDS delivery (/engage) — SES email + SMS/RCS follow-up"
ENG=$(curl -s -m 90 -X POST "$API/sessions/$SID/engage" -H 'Content-Type: application/json' \
  -d "$(python3 -c "import json,sys;print(json.dumps({'email':sys.argv[1],'phone':sys.argv[2],'follow_up_channel':'sms'}))" "$EMAIL" "$PHONE")")
if echo "$ENG" | grep -q '"delivered"'; then
  EMAIL_OK=$(echo "$ENG" | jqget "['delivered']['email']['ok']")
  FU_OK=$(echo "$ENG" | jqget "['delivered']['follow_up']['ok']")
  SANDBOX=$(echo "$ENG" | jqget "['delivered']['email']['sandbox']")
  ok "engage delivered (email_ok=$EMAIL_OK follow_up_ok=$FU_OK sandbox=$SANDBOX)"
else
  bad "engage failed: $ENG"
fi

# 6. Two-way inbound (/inbound) ----------------------------------------------
echo "6) Two-way inbound loop (/inbound)"
declare -a REPLIES=("1" "what about the cost?" "can I talk to a human" "hello")
declare -a EXPECT=("book_deepdive" "cost_estimate" "talk_to_human" "unknown")
for i in "${!REPLIES[@]}"; do
  IN=$(curl -s -m 60 -X POST "$API/inbound" -H 'Content-Type: application/json' \
    -d "$(python3 -c "import json,sys;print(json.dumps({'channel':'sms','sender':sys.argv[1],'text':sys.argv[2]}))" "$PHONE" "${REPLIES[$i]}")")
  ACT=$(echo "$IN" | jqget "['action']")
  if [ "$ACT" = "${EXPECT[$i]}" ]; then ok "inbound '${REPLIES[$i]}' -> $ACT"; else bad "inbound '${REPLIES[$i]}' -> $ACT (expected ${EXPECT[$i]}; raw: $IN)"; fi
done
# unknown sender must be ignored
UNK=$(curl -s -m 60 -X POST "$API/inbound" -H 'Content-Type: application/json' \
  -d '{"channel":"sms","sender":"+15559999999","text":"hi"}' | jqget "['ok']")
[ "$UNK" = "False" ] && ok "unknown sender ignored" || bad "unknown sender not ignored (ok=$UNK)"

echo
echo "== Result: $pass passed, $fail failed =="
[ "$fail" -eq 0 ] && exit 0 || exit 1
