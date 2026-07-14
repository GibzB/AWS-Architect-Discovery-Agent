/**
 * Atlas Discovery API client
 */

const BASE_URL = import.meta.env.VITE_API_URL || '/v1';

export interface CreateSessionRequest {
  customer_name?: string;
  customer_industry?: string;
  mode?: 'chat' | 'voice';
}

export interface CreateSessionResponse {
  session_id: string;
  status: string;
  created_at: string;
}

export interface AgentTrace {
  planner_decision: string;
  agent_invoked: string;
  tools_used: string[];
  reasoning: string;
}

export interface MessageMetadata {
  facts_gathered: number;
  questions_remaining: number;
  review_status: string | null;
}

export interface SendMessageResponse {
  message_id: string;
  content: string;
  role: string;
  agent_trace: AgentTrace;
  session_status: string;
  metadata: MessageMetadata;
}

export interface SessionResponse {
  session_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  customer: Record<string, string>;
  facts_count: number;
  questions_remaining: number;
  architecture_ready: boolean;
  review_status: string | null;
  conversation_length: number;
}

export interface ReportResponse {
  session_id: string;
  generated_at: string;
  report_markdown: string;
  executive_summary: string;
  architecture_decisions: Array<{ decision: string; rationale: string; trade_offs: string; reversibility?: string }>;
  services: Array<{ service: string; purpose: string; justification: string; alternatives_considered?: string[] }>;
  risks: Array<{ risk: string; impact: string; likelihood: string; mitigation: string }>;
  cost_estimate: Record<string, unknown>;
  diagram_mermaid: string;
  terraform_snippet: string;
  review_score: Record<string, number>;
  review_findings: Array<{ category: string; severity: string; finding: string; recommendation: string }>;
  business_requirements: string[];
  technical_requirements: string[];
  known_facts: Array<{ fact: string; category?: string; confidence?: number }>;
}

export async function createSession(data: CreateSessionRequest): Promise<CreateSessionResponse> {
  const res = await fetch(`${BASE_URL}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create session: ${res.status}`);
  return res.json();
}

export async function sendMessage(sessionId: string, content: string): Promise<SendMessageResponse> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, role: 'user' }),
  });
  if (!res.ok) throw new Error(`Failed to send message: ${res.status}`);
  return res.json();
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}`);
  if (!res.ok) throw new Error(`Failed to get session: ${res.status}`);
  return res.json();
}

export async function getReport(sessionId: string): Promise<ReportResponse> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/report`);
  if (!res.ok) throw new Error(`Report not available: ${res.status}`);
  return res.json();
}
