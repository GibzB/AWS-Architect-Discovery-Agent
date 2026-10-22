import type { SessionResponse } from '../lib/api';

interface SessionPanelProps {
  session: SessionResponse | null;
}

const STATUS_COLORS: Record<string, string> = {
  discovery: 'text-info',
  architecture: 'text-warning',
  review: 'text-primary',
  complete: 'text-success',
};

const STATUS_LABELS: Record<string, string> = {
  discovery: 'Discovery',
  architecture: 'Designing',
  review: 'Reviewing',
  complete: 'Complete',
};

export function SessionPanel({ session }: SessionPanelProps) {
  if (!session) return null;

  const statusColor = STATUS_COLORS[session.status] || 'text-muted';
  const statusLabel = STATUS_LABELS[session.status] || session.status;

  return (
    <aside className="flex-none w-64 border-l border-border bg-surface overflow-y-auto hidden lg:block">
      <div className="p-5 space-y-6">
        {/* Session Status */}
        <div>
          <h3 className="text-[10px] font-medium text-muted uppercase tracking-wider mb-3">Status</h3>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${statusColor === 'text-success' ? 'bg-success' : statusColor === 'text-info' ? 'bg-info' : statusColor === 'text-warning' ? 'bg-warning' : 'bg-primary'}`} />
            <span className={`text-sm font-medium ${statusColor}`}>{statusLabel}</span>
          </div>
        </div>

        {/* Progress */}
        <div>
          <h3 className="text-[10px] font-medium text-muted uppercase tracking-wider mb-3">Progress</h3>
          <div className="space-y-3">
            <ProgressItem
              label="Facts Gathered"
              value={session.facts_count}
              target={5}
              color="bg-info"
            />
            <ProgressItem
              label="Questions Remaining"
              value={session.questions_remaining}
              target={0}
              color="bg-warning"
              inverted
            />
            <ProgressItem
              label="Messages"
              value={session.conversation_length}
              target={20}
              color="bg-muted"
            />
          </div>
        </div>

        {/* Milestones */}
        <div>
          <h3 className="text-[10px] font-medium text-muted uppercase tracking-wider mb-3">Milestones</h3>
          <div className="space-y-2">
            <Milestone label="Discovery" done={session.facts_count >= 3} />
            <Milestone label="Architecture" done={session.architecture_ready} />
            <Milestone label="Review" done={session.review_status === 'approved'} />
            <Milestone label="Report Ready" done={session.status === 'complete'} />
          </div>
        </div>

        {/* Review Status */}
        {session.review_status && (
          <div>
            <h3 className="text-[10px] font-medium text-muted uppercase tracking-wider mb-3">Review</h3>
            <div className={`px-3 py-2 rounded-lg text-xs font-medium border
              ${session.review_status === 'approved'
                ? 'bg-success/10 border-success/20 text-success'
                : session.review_status === 'rejected'
                  ? 'bg-danger/10 border-danger/20 text-danger'
                  : 'bg-warning/10 border-warning/20 text-warning'
              }`}>
              {session.review_status === 'approved' && '✓ Approved'}
              {session.review_status === 'rejected' && '✗ Rejected — Revising'}
              {session.review_status === 'pending' && '◦ Pending Review'}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

function ProgressItem({ label, value, target, color, inverted }: {
  label: string;
  value: number;
  target: number;
  color: string;
  inverted?: boolean;
}) {
  const progress = inverted
    ? Math.max(0, Math.min(100, ((target - value) / Math.max(target, 1)) * 100))
    : Math.min(100, (value / Math.max(target, 1)) * 100);

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-text-secondary">{label}</span>
        <span className="text-xs text-muted font-medium">{value}</span>
      </div>
      <div className="h-1 bg-background rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

function Milestone({ label, done }: { label: string; done: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <div className={`w-4 h-4 rounded-full border flex items-center justify-center
        ${done
          ? 'border-success bg-success/10'
          : 'border-border bg-background'
        }`}>
        {done && (
          <svg className="w-2.5 h-2.5 text-success" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
            <polyline points="20,6 9,17 4,12" />
          </svg>
        )}
      </div>
      <span className={`text-xs ${done ? 'text-text-secondary' : 'text-muted'}`}>{label}</span>
    </div>
  );
}
