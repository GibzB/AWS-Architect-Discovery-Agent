import { useState } from 'react';
import { engageSession, type EngageResponse } from '../lib/api';

interface EngagementPanelProps {
  sessionId: string;
}

/**
 * AWS CDS omnichannel engagement panel.
 *
 * Lets the customer have their discovery report delivered over AWS
 * Communication Developer Services: an email via Amazon SES and an interactive
 * follow-up via AWS End User Messaging (SMS/RCS). After delivery, the customer
 * can reply on that channel and the agent continues the conversation.
 */
export function EngagementPanel({ sessionId }: EngagementPanelProps) {
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [channel, setChannel] = useState<'sms' | 'rcs'>('sms');
  const [status, setStatus] = useState<'idle' | 'sending' | 'done' | 'error'>('idle');
  const [result, setResult] = useState<EngageResponse | null>(null);
  const [error, setError] = useState('');

  const handleSend = async () => {
    setStatus('sending');
    setError('');
    try {
      const res = await engageSession(sessionId, {
        email: email || undefined,
        phone: phone || undefined,
        follow_up_channel: channel,
      });
      setResult(res);
      setStatus('done');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delivery failed');
      setStatus('error');
    }
  };

  const canSend = (email.trim() || phone.trim()) && status !== 'sending';

  return (
    <div className="bg-surface rounded-[16px] border border-border p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: 'linear-gradient(90deg, #FF9900, #F47C20)' }}>
          <svg className="w-5 h-5 text-background" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 4h16v16H4z" />
            <polyline points="4,6 12,13 20,6" />
          </svg>
        </div>
        <div>
          <h3 className="text-sm font-heading font-bold text-text">Send & continue over AWS CDS</h3>
          <p className="text-xs text-muted">
            Email the report (Amazon SES) and start a two-way SMS/RCS follow-up (AWS End User Messaging).
          </p>
        </div>
      </div>

      {status !== 'done' && (
        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="customer@example.com"
              className="bg-background border border-border rounded-lg px-3 py-2 text-xs text-text
                placeholder:text-disabled focus:outline-none focus:border-primary/40"
            />
            <input
              type="tel"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              placeholder="+1 555 010 0123"
              className="bg-background border border-border rounded-lg px-3 py-2 text-xs text-text
                placeholder:text-disabled focus:outline-none focus:border-primary/40"
            />
          </div>
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex gap-1 bg-background rounded-lg p-1 border border-border">
              {(['sms', 'rcs'] as const).map(c => (
                <button
                  key={c}
                  onClick={() => setChannel(c)}
                  className={`px-3 py-1.5 rounded-md text-[11px] font-medium uppercase transition-colors
                    ${channel === c ? 'bg-surface-light text-text' : 'text-muted hover:text-text-secondary'}`}
                >
                  {c}
                </button>
              ))}
            </div>
            <button
              onClick={handleSend}
              disabled={!canSend}
              className="px-4 py-2 rounded-lg text-xs font-medium text-background transition-opacity
                disabled:opacity-40"
              style={{ background: 'linear-gradient(90deg, #FF9900, #F47C20)' }}
            >
              {status === 'sending' ? 'Sending…' : 'Send over CDS'}
            </button>
          </div>
          {status === 'error' && (
            <p className="text-xs text-danger">{error}</p>
          )}
        </div>
      )}

      {status === 'done' && result && (
        <div className="space-y-2">
          <DeliveryRow
            label="Email (Amazon SES)"
            res={result.delivered.email}
          />
          <DeliveryRow
            label={`Follow-up (${result.delivered.follow_up?.channel?.toUpperCase() || 'SMS'} · End User Messaging)`}
            res={result.delivered.follow_up}
          />
          <p className="text-[10px] text-disabled mt-2">
            Reply to the follow-up message and the agent will continue the conversation on that channel.
          </p>
        </div>
      )}
    </div>
  );
}

function DeliveryRow({
  label,
  res,
}: {
  label: string;
  res: { ok: boolean; sandbox: boolean; to: string } | null;
}) {
  if (!res) {
    return (
      <div className="flex items-center justify-between bg-background rounded-xl p-3 border border-border">
        <span className="text-xs text-muted">{label}</span>
        <span className="text-[10px] text-disabled">not sent (no recipient)</span>
      </div>
    );
  }
  return (
    <div className="flex items-center justify-between bg-background rounded-xl p-3 border border-border">
      <span className="text-xs text-text-secondary">{label}</span>
      <span className="flex items-center gap-2">
        <span className="text-[10px] text-muted">to {res.to}</span>
        {res.sandbox && (
          <span className="px-2 py-0.5 rounded-full text-[10px] bg-info/10 border border-info/20 text-info">
            sandbox
          </span>
        )}
        <span className={`px-2 py-0.5 rounded-full text-[10px] border
          ${res.ok ? 'bg-success/10 border-success/20 text-success' : 'bg-danger/10 border-danger/20 text-danger'}`}>
          {res.ok ? 'sent' : 'failed'}
        </span>
      </span>
    </div>
  );
}
