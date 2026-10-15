"""
Inbound messaging Lambda — AWS CDS two-way entry point.

Deployed by infra/template.yaml and subscribed to the SNS topic that AWS End User
Messaging publishes inbound SMS/RCS replies to. For each inbound message it runs
one agentic turn via the engagement layer (classify -> act -> reply on the same
channel) and persists conversation state.

The Lambda packages the `agent/` directory (channels/ + engagement/) so this
handler reuses exactly the same code path as the runtime — the CDS calls are the
real ones; SANDBOX_MODE only changes whether a send hits AWS.
"""

from __future__ import annotations

import json
import logging

# The deployment bundles the agent package onto the path (see template.yaml).
from engagement import parse_sns_eum_event, process_inbound

log = logging.getLogger()
log.setLevel(logging.INFO)


def handler(event, context):
    """SNS -> inbound EUM messages -> one agentic turn each."""
    try:
        messages = parse_sns_eum_event(event)
    except Exception as exc:  # defensive: never fail the whole batch on a parse error
        log.exception("[inbound-lambda] event parse failed: %s", exc)
        return {"statusCode": 400, "body": "could not parse event"}

    results = []
    for msg in messages:
        try:
            results.append(process_inbound(msg))
        except Exception as exc:
            log.exception("[inbound-lambda] processing failed: %s", exc)
            results.append({"ok": False, "reason": "processing error"})

    log.info("[inbound-lambda] processed %d message(s)", len(results))
    return {"statusCode": 200, "body": json.dumps({"processed": len(results), "results": results})}
