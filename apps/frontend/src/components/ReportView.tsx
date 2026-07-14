import { useState } from 'react';
import type { ReportResponse } from '../lib/api';

interface ReportViewProps {
  report: ReportResponse;
}

type ReportTab = 'overview' | 'services' | 'terraform' | 'diagram' | 'risks';

export function ReportView({ report }: ReportViewProps) {
  const [tab, setTab] = useState<ReportTab>('overview');

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-surface rounded-[16px] border border-border p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(90deg, #FF9900, #F47C20)' }}>
            <svg className="w-5 h-5 text-background" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <polyline points="14,2 14,8 20,8" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-heading font-bold text-text">Discovery Report</h2>
            <p className="text-xs text-muted">{report.executive_summary}</p>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Badge label="Approved" color="success" />
          <Badge label={`${report.services.length} Services`} color="info" />
          <Badge label={`${report.risks.length} Risks`} color="warning" />
          <Badge label="Terraform Ready" color="info" />
        </div>
      </div>

      {/* Tab Bar */}
      <div className="flex gap-1 bg-surface rounded-lg p-1 border border-border">
        {(['overview', 'services', 'terraform', 'diagram', 'risks'] as ReportTab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-md text-xs font-medium transition-colors capitalize
              ${tab === t ? 'bg-surface-light text-text' : 'text-muted hover:text-text-secondary'}`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'overview' && <OverviewTab report={report} />}
      {tab === 'services' && <ServicesTab report={report} />}
      {tab === 'terraform' && <TerraformTab report={report} />}
      {tab === 'diagram' && <DiagramTab report={report} />}
      {tab === 'risks' && <RisksTab report={report} />}
    </div>
  );
}

function OverviewTab({ report }: { report: ReportResponse }) {
  return (
    <div className="space-y-6">
      {/* Well-Architected Score */}
      {report.review_score && Object.keys(report.review_score).length > 0 && (
        <div className="bg-surface rounded-[16px] border border-border p-6">
          <h3 className="text-sm font-medium text-text-secondary mb-4">Well-Architected Score</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(report.review_score).map(([pillar, score]) => (
              <ScoreCard key={pillar} pillar={pillar} score={score} />
            ))}
          </div>
        </div>
      )}

      {/* Requirements */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-surface rounded-[16px] border border-border p-6">
          <h3 className="text-sm font-medium text-text-secondary mb-3">Business Requirements</h3>
          <ul className="space-y-2">
            {report.business_requirements.length > 0 ? report.business_requirements.map((req, i) => (
              <li key={i} className="text-xs text-muted flex items-start gap-2">
                <span className="text-primary mt-0.5">•</span>
                {typeof req === 'string' ? req : JSON.stringify(req)}
              </li>
            )) : (
              <li className="text-xs text-disabled">See discovered facts</li>
            )}
          </ul>
        </div>
        <div className="bg-surface rounded-[16px] border border-border p-6">
          <h3 className="text-sm font-medium text-text-secondary mb-3">Technical Requirements</h3>
          <ul className="space-y-2">
            {report.technical_requirements.length > 0 ? report.technical_requirements.map((req, i) => (
              <li key={i} className="text-xs text-muted flex items-start gap-2">
                <span className="text-info mt-0.5">•</span>
                {typeof req === 'string' ? req : JSON.stringify(req)}
              </li>
            )) : (
              <li className="text-xs text-disabled">See discovered facts</li>
            )}
          </ul>
        </div>
      </div>

      {/* Discovered Facts */}
      <div className="bg-surface rounded-[16px] border border-border p-6">
        <h3 className="text-sm font-medium text-text-secondary mb-3">Discovered Facts</h3>
        <div className="flex flex-wrap gap-2">
          {report.known_facts.map((f, i) => (
            <span key={i} className="px-2 py-1 bg-background rounded-lg text-[11px] text-text-secondary border border-border">
              {typeof f === 'object' && f.fact ? f.fact : String(f)}
            </span>
          ))}
        </div>
      </div>

      {/* Review Findings */}
      {report.review_findings.length > 0 && (
        <div className="bg-surface rounded-[16px] border border-border p-6">
          <h3 className="text-sm font-medium text-text-secondary mb-4">Review Findings</h3>
          <div className="space-y-3">
            {report.review_findings.map((finding, i) => (
              <div key={i} className="bg-background rounded-xl p-4 border border-border">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-[10px] font-medium uppercase
                    ${finding.severity === 'critical' ? 'text-danger'
                      : finding.severity === 'major' ? 'text-warning' : 'text-muted'}`}>
                    {finding.severity}
                  </span>
                  <span className="text-[10px] text-disabled">{finding.category}</span>
                </div>
                <p className="text-xs text-text-secondary">{finding.finding}</p>
                <p className="text-xs text-muted mt-1">→ {finding.recommendation}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ServicesTab({ report }: { report: ReportResponse }) {
  return (
    <div className="space-y-4">
      <div className="bg-surface rounded-[16px] border border-border p-6">
        <h3 className="text-sm font-medium text-text-secondary mb-4">AWS Services ({report.services.length})</h3>
        <div className="space-y-3">
          {report.services.map((svc, i) => (
            <div key={i} className="bg-background rounded-xl p-4 border border-border">
              <p className="text-sm font-medium text-primary">{svc.service}</p>
              <p className="text-xs text-text-secondary mt-1">{svc.purpose}</p>
              <p className="text-xs text-muted mt-2">{svc.justification}</p>
              {svc.alternatives_considered && svc.alternatives_considered.length > 0 && (
                <p className="text-[10px] text-disabled mt-2">
                  Alternatives: {svc.alternatives_considered.join(', ')}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Architecture Decisions */}
      {report.architecture_decisions.length > 0 && (
        <div className="bg-surface rounded-[16px] border border-border p-6">
          <h3 className="text-sm font-medium text-text-secondary mb-4">Architecture Decisions</h3>
          <div className="space-y-3">
            {report.architecture_decisions.map((dec, i) => (
              <div key={i} className="bg-background rounded-xl p-4 border border-border">
                <p className="text-sm font-medium text-text">{dec.decision}</p>
                <p className="text-xs text-text-secondary mt-1">{dec.rationale}</p>
                <p className="text-xs text-muted mt-1">Trade-offs: {dec.trade_offs}</p>
                {dec.reversibility && (
                  <span className="inline-block mt-2 px-2 py-0.5 rounded-full text-[10px] bg-surface-light border border-border text-muted">
                    Reversibility: {dec.reversibility}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TerraformTab({ report }: { report: ReportResponse }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(report.terraform_snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-surface rounded-[16px] border border-border p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-text-secondary">Generated Terraform</h3>
        <button
          onClick={handleCopy}
          className="px-3 py-1.5 rounded-lg text-[11px] font-medium border border-border
            text-muted hover:text-text hover:border-primary/30 transition-colors"
        >
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      <pre className="bg-background rounded-xl p-4 border border-border overflow-x-auto
        text-xs text-text-secondary font-mono leading-relaxed whitespace-pre-wrap">
        {report.terraform_snippet || '# No Terraform generated yet'}
      </pre>
    </div>
  );
}

function DiagramTab({ report }: { report: ReportResponse }) {
  return (
    <div className="bg-surface rounded-[16px] border border-border p-6">
      <h3 className="text-sm font-medium text-text-secondary mb-4">Architecture Diagram (Mermaid)</h3>
      <pre className="bg-background rounded-xl p-4 border border-border overflow-x-auto
        text-xs text-text-secondary font-mono leading-relaxed whitespace-pre-wrap">
        {report.diagram_mermaid || 'No diagram generated yet'}
      </pre>
      <p className="text-[10px] text-disabled mt-3">
        Paste this into <a href="https://mermaid.live" target="_blank" rel="noopener" className="text-info hover:underline">mermaid.live</a> to render the diagram.
      </p>
    </div>
  );
}

function RisksTab({ report }: { report: ReportResponse }) {
  return (
    <div className="bg-surface rounded-[16px] border border-border p-6">
      <h3 className="text-sm font-medium text-text-secondary mb-4">Risk Register ({report.risks.length})</h3>
      {report.risks.length > 0 ? (
        <div className="space-y-3">
          {report.risks.map((risk, i) => (
            <div key={i} className="bg-background rounded-xl p-4 border border-border">
              <div className="flex items-center gap-2 mb-1">
                <SeverityDot severity={risk.impact} />
                <p className="text-sm font-medium text-text">{risk.risk}</p>
              </div>
              <div className="flex gap-3 mt-2 text-[10px] text-muted">
                <span>Impact: <strong className="text-text-secondary">{risk.impact}</strong></span>
                <span>Likelihood: <strong className="text-text-secondary">{risk.likelihood}</strong></span>
              </div>
              <p className="text-xs text-muted mt-2">Mitigation: {risk.mitigation}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-disabled">No risks identified.</p>
      )}
    </div>
  );
}

function Badge({ label, color }: { label: string; color: 'success' | 'info' | 'warning' }) {
  const colors = {
    success: 'bg-success/10 border-success/20 text-success',
    info: 'bg-info/10 border-info/20 text-info',
    warning: 'bg-warning/10 border-warning/20 text-warning',
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${colors[color]}`}>
      {label}
    </span>
  );
}

function ScoreCard({ pillar, score }: { pillar: string; score: number }) {
  const color = score >= 8 ? 'text-success' : score >= 6 ? 'text-warning' : 'text-danger';
  const label = pillar.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  return (
    <div className="bg-background rounded-xl p-3 border border-border text-center">
      <p className={`text-xl font-bold font-heading ${color}`}>{score}</p>
      <p className="text-[10px] text-muted mt-1 capitalize">{label}</p>
    </div>
  );
}

function SeverityDot({ severity }: { severity: string }) {
  const color = severity === 'high' ? 'bg-danger' : severity === 'medium' ? 'bg-warning' : 'bg-muted';
  return <span className={`w-2 h-2 rounded-full ${color}`} />;
}
