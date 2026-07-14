interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agentInvoked?: string;
  reasoning?: string;
  timestamp: string;
}

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`flex-none w-8 h-8 rounded-lg flex items-center justify-center border
        ${isUser
          ? 'bg-surface-light border-border'
          : 'bg-surface border-border'
        }`}>
        {isUser ? (
          <svg className="w-4 h-4 text-text-secondary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        ) : (
          <svg className="w-4 h-4 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        )}
      </div>

      {/* Content */}
      <div className={`max-w-[75%] ${isUser ? 'text-right' : ''}`}>
        {/* Agent badge */}
        {!isUser && message.agentInvoked && (
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-medium text-muted uppercase tracking-wider">
              {message.agentInvoked.replace('Agent', '')}
            </span>
            {message.reasoning && (
              <span className="text-[10px] text-disabled">· {message.reasoning}</span>
            )}
          </div>
        )}

        <div className={`inline-block px-4 py-3 rounded-[12px] text-sm leading-relaxed
          ${isUser
            ? 'bg-surface-light text-text border border-border'
            : 'bg-surface text-text-secondary border border-border'
          }`}>
          {/* Render content with basic line break support */}
          {message.content.split('\n').map((line, i) => (
            <span key={i}>
              {line.startsWith('**') && line.endsWith('**')
                ? <strong className="text-text">{line.slice(2, -2)}</strong>
                : line}
              {i < message.content.split('\n').length - 1 && <br />}
            </span>
          ))}
        </div>

        <p className="text-[10px] text-disabled mt-1">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  );
}
