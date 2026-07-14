import { useState, useRef, useEffect } from 'react';
import { sendMessage, getSession, getReport, type SendMessageResponse, type SessionResponse, type ReportResponse } from '../lib/api';
import { ChatMessage } from './ChatMessage';
import { SessionPanel } from './SessionPanel';
import { ReportView } from './ReportView';
import { VoiceButton } from './VoiceButton';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agentInvoked?: string;
  reasoning?: string;
  timestamp: string;
}

interface WorkshopProps {
  sessionId: string;
  customerName: string;
  onReset: () => void;
}

type Tab = 'chat' | 'architecture' | 'report';

export function Workshop({ sessionId, customerName, onReset }: WorkshopProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'intro',
      role: 'assistant',
      content: `Good afternoon. I'm ASA, your Autonomous Solutions Architect. I'll guide you through today's cloud discovery workshop.\n\nMy role is to understand your business objectives, identify technical constraints, evaluate risks, and work with my specialist colleagues to produce an implementation-ready architecture.\n\nLet's begin. Can you tell me about your organisation and what's driving this cloud initiative?`,
      timestamp: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('chat');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Refresh session state periodically
  useEffect(() => {
    const refresh = async () => {
      try {
        const s = await getSession(sessionId);
        setSession(s);
        if (s.review_status === 'approved' && !report) {
          const r = await getReport(sessionId);
          setReport(r);
        }
      } catch { /* ignore */ }
    };
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [sessionId, report]);

  const handleSend = async () => {
    const content = input.trim();
    if (!content || loading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response: SendMessageResponse = await sendMessage(sessionId, content);

      const assistantMsg: Message = {
        id: response.message_id,
        role: 'assistant',
        content: response.content,
        agentInvoked: response.agent_trace.agent_invoked,
        reasoning: response.agent_trace.reasoning,
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMsg]);

      // Refresh session
      const s = await getSession(sessionId);
      setSession(s);

      // Check if report is ready
      if (s.review_status === 'approved') {
        try {
          const r = await getReport(sessionId);
          setReport(r);
        } catch { /* not ready yet */ }
      }
    } catch (err) {
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="flex-none border-b border-border bg-surface px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-background border border-border flex items-center justify-center">
              <svg className="w-4 h-4 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <div>
              <h1 className="text-sm font-semibold font-heading text-text">ASA</h1>
              <p className="text-xs text-muted">Discovery Workshop — {customerName}</p>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 bg-background rounded-lg p-1 border border-border">
            {(['chat', 'architecture', 'report'] as Tab[]).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors capitalize
                  ${activeTab === tab
                    ? 'bg-surface-light text-text'
                    : 'text-muted hover:text-text-secondary'
                  }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <button onClick={onReset} className="text-xs text-muted hover:text-text-secondary transition-colors">
            New Session
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Chat / Content Area */}
        <div className="flex-1 flex flex-col">
          {activeTab === 'chat' && (
            <>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
                {messages.map(msg => (
                  <ChatMessage key={msg.id} message={msg} />
                ))}
                {loading && (
                  <div className="flex items-center gap-2 text-muted text-sm pl-12">
                    <div className="flex gap-1">
                      <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span>ASA is thinking...</span>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="flex-none border-t border-border bg-surface px-6 py-4">
                <div className="flex gap-3 items-end max-w-4xl mx-auto">
                  <VoiceButton
                    sessionId={sessionId}
                    onTranscript={(role, text) => {
                      const msg: Message = {
                        id: `voice-${Date.now()}`,
                        role,
                        content: text,
                        timestamp: new Date().toISOString(),
                      };
                      setMessages(prev => [...prev, msg]);
                    }}
                  />
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Describe your cloud initiative..."
                    rows={1}
                    className="flex-1 resize-none px-4 py-3 rounded-[10px] bg-background border border-border
                      text-text placeholder:text-disabled text-sm
                      focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30
                      transition-colors duration-200 max-h-32"
                    disabled={loading}
                  />
                  <button
                    onClick={handleSend}
                    disabled={!input.trim() || loading}
                    className="px-4 py-3 rounded-[12px] text-background font-medium text-sm
                      disabled:opacity-30 disabled:cursor-not-allowed
                      transition-all duration-200 hover:shadow-[0_15px_40px_rgba(255,153,0,0.12)]
                      active:scale-[0.98]"
                    style={{ background: 'linear-gradient(90deg, #FF9900, #F47C20)' }}
                  >
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M22 2L11 13" />
                      <path d="M22 2L15 22L11 13L2 9L22 2Z" />
                    </svg>
                  </button>
                </div>
              </div>
            </>
          )}

          {activeTab === 'architecture' && (
            <div className="flex-1 overflow-y-auto p-6">
              {session?.architecture_ready && report ? (
                <ArchitectureView report={report} />
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <div className="w-12 h-12 rounded-xl bg-surface border border-border flex items-center justify-center mb-4">
                    <svg className="w-6 h-6 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <rect x="3" y="3" width="18" height="18" rx="2" />
                      <path d="M9 3v18M3 9h18" />
                    </svg>
                  </div>
                  <p className="text-text-secondary text-sm">Architecture will appear here once designed.</p>
                  <p className="text-muted text-xs mt-1">Continue the discovery conversation first.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'report' && (
            <div className="flex-1 overflow-y-auto p-6">
              {report ? (
                <ReportView report={report} />
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <div className="w-12 h-12 rounded-xl bg-surface border border-border flex items-center justify-center mb-4">
                    <svg className="w-6 h-6 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                      <polyline points="14,2 14,8 20,8" />
                    </svg>
                  </div>
                  <p className="text-text-secondary text-sm">Report will be generated after review approval.</p>
                  <p className="text-muted text-xs mt-1">The Review Agent must validate the architecture first.</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Session Sidebar */}
        <SessionPanel session={session} />
      </div>
    </div>
  );
}

function ArchitectureView({ report }: { report: ReportResponse }) {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-xl font-heading font-bold text-text">Architecture</h2>

      {/* Mermaid Diagram (raw) */}
      {report.diagram_mermaid && (
        <div className="bg-surface rounded-[16px] border border-border p-6">
          <h3 className="text-sm font-medium text-text-secondary mb-3">Diagram</h3>
          <pre className="text-xs text-muted overflow-x-auto whitespace-pre-wrap font-mono">
            {report.diagram_mermaid}
          </pre>
        </div>
      )}

      {/* Services */}
      <div className="bg-surface rounded-[16px] border border-border p-6">
        <h3 className="text-sm font-medium text-text-secondary mb-4">AWS Services</h3>
        <div className="space-y-3">
          {report.services.map((svc, i) => (
            <div key={i} className="bg-background rounded-xl p-4 border border-border">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-primary">{svc.service}</p>
                  <p className="text-xs text-text-secondary mt-1">{svc.purpose}</p>
                </div>
              </div>
              <p className="text-xs text-muted mt-2">{svc.justification}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Decisions */}
      {report.architecture_decisions.length > 0 && (
        <div className="bg-surface rounded-[16px] border border-border p-6">
          <h3 className="text-sm font-medium text-text-secondary mb-4">Architecture Decisions</h3>
          <div className="space-y-3">
            {report.architecture_decisions.map((dec, i) => (
              <div key={i} className="bg-background rounded-xl p-4 border border-border">
                <p className="text-sm font-medium text-text">{dec.decision}</p>
                <p className="text-xs text-text-secondary mt-1">{dec.rationale}</p>
                <p className="text-xs text-muted mt-1">Trade-offs: {dec.trade_offs}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
