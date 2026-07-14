# API Specification

## Base URL

```
Production: https://api.{domain}/v1
Local:      http://localhost:8000/v1
```

## Authentication

All endpoints require a valid Cognito JWT in the `Authorization` header:

```
Authorization: Bearer <id_token>
```

---

## Endpoints

### POST /sessions

Create a new discovery workshop session.

**Request:**
```json
{
  "customer_name": "string",
  "customer_industry": "string (optional)",
  "mode": "chat | voice"
}
```

**Response (201):**
```json
{
  "session_id": "uuid",
  "status": "discovery",
  "created_at": "iso8601",
  "websocket_url": "wss://... (if voice mode)"
}
```

---

### POST /sessions/{session_id}/messages

Send a message to Atlas within an active session.

**Request:**
```json
{
  "content": "string",
  "role": "user"
}
```

**Response (200):**
```json
{
  "message_id": "uuid",
  "content": "string",
  "role": "assistant",
  "agent_trace": {
    "planner_decision": "string",
    "agent_invoked": "string",
    "tools_used": ["string"],
    "reasoning": "string"
  },
  "session_status": "discovery | architecture | review | complete",
  "metadata": {
    "facts_gathered": 0,
    "questions_remaining": 0,
    "review_status": "pending | approved | rejected | null"
  }
}
```

---

### GET /sessions/{session_id}

Retrieve current session state including memory.

**Response (200):**
```json
{
  "session_id": "uuid",
  "status": "discovery | architecture | review | complete",
  "created_at": "iso8601",
  "updated_at": "iso8601",
  "customer": {},
  "facts_count": 0,
  "questions_remaining": 0,
  "architecture_ready": false,
  "review_status": "null | pending | approved | rejected",
  "conversation_length": 0
}
```

---

### GET /sessions/{session_id}/report

Retrieve the final generated report.

**Response (200):**
```json
{
  "session_id": "uuid",
  "generated_at": "iso8601",
  "report_markdown": "string",
  "executive_summary": "string",
  "architecture_decisions": [],
  "services": [],
  "risks": [],
  "cost_estimate": {},
  "diagram_mermaid": "string",
  "terraform_snippet": "string"
}
```

**Response (404):** Report not yet generated (review not approved).

---

### GET /sessions/{session_id}/diagram

Retrieve the architecture diagram.

**Response (200):**
```json
{
  "session_id": "uuid",
  "diagram_mermaid": "string",
  "diagram_url": "string (S3 presigned URL for rendered PNG, if available)"
}
```

---

### WebSocket /sessions/{session_id}/voice

Bidirectional voice stream via Nova Sonic.

**Connection:** Upgrade to WebSocket with Cognito token.

**Client → Server frames:**
```json
{
  "type": "audio",
  "data": "base64-encoded PCM audio chunk"
}
```

**Server → Client frames:**
```json
{
  "type": "audio | text | status | agent_trace",
  "data": "base64-encoded audio | text content | status object"
}
```

**Status frame:**
```json
{
  "type": "status",
  "data": {
    "session_status": "discovery",
    "agent_active": "DiscoveryAgent",
    "thinking": true
  }
}
```

---

## Error Responses

All errors follow:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `session_not_found` | 404 | Session ID does not exist |
| `session_complete` | 409 | Session already finalized |
| `unauthorized` | 401 | Invalid or expired token |
| `rate_limited` | 429 | Too many requests |
| `internal_error` | 500 | Unexpected server error |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| POST /sessions | 10/min per user |
| POST /messages | 30/min per session |
| GET endpoints | 60/min per user |
| WebSocket | 1 concurrent per user |
