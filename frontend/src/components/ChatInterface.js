import React, { useState, useRef, useEffect } from 'react';
import LoadingBar from './LoadingBar';

const SUGGESTIONS = [
  'How is my weight trending?',
  'What should I eat this week?',
  'What book should I read next?',
  'How consistent is my exercise?',
  'Give me recommendations across all areas.',
  'How was my week overall?',
];

function ChatInterface({ apiUrl }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const historyRef = useRef(null);

  useEffect(() => {
    if (historyRef.current) {
      historyRef.current.scrollTop = historyRef.current.scrollHeight;
    }
  }, [messages, loading]);

  function detectRequestType(text) {
    const lower = text.toLowerCase();
    if (lower.includes('recommend') || lower.includes('suggest') || lower.includes('should i')) {
      return 'recommendations';
    }
    const summaryKeywords = [
      'overall', 'summary', 'summarize', 'describe', 'overview',
      'how have i been', 'how am i doing', 'how\'s my', 'last 7 days',
      'last week', 'this week', 'past week', 'week overall',
      'everything', 'all areas', 'across the board',
    ];
    if (summaryKeywords.some(k => lower.includes(k))) {
      return 'weekly_briefing';
    }
    return 'chat';
  }

  async function sendMessage(text) {
    if (!text.trim() || loading) return;
    const userMsg = text.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setLoading(true);

    try {
      const requestType = detectRequestType(userMsg);
      const response = await fetch(`${apiUrl}agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_type: requestType, message: userMsg }),
      });
      const data = await response.json();
      const body = typeof data.body === 'string' ? JSON.parse(data.body) : data;
      const replyText = body.response || body.error || 'No response received.';
      setMessages(prev => [...prev, { role: 'assistant', text: replyText }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', text: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  return (
    <div>
      {messages.length === 0 && (
        <div className="chat-suggestion-row">
          {SUGGESTIONS.map((s, i) => (
            <button
              key={i}
              className="chat-suggestion"
              onClick={() => sendMessage(s)}
              disabled={loading}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {messages.length > 0 && (
        <div className="chat-history" ref={historyRef}>
          {messages.map((msg, i) => (
            <div key={i} className="chat-message">
              <span className={`chat-message-label ${msg.role}`}>
                {msg.role === 'user' ? 'you' : 'dashboard'}
              </span>
              <div className={`chat-message-body ${msg.role}`}>
                {msg.text}
              </div>
            </div>
          ))}
          {loading && (
            <div className="chat-message">
              <span className="chat-message-label">dashboard</span>
              <div className="chat-message-body">
                <LoadingBar />
              </div>
            </div>
          )}
        </div>
      )}

      <div className="chat-input-row">
        <textarea
          className="chat-input"
          placeholder="Ask anything about your data..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          rows={1}
        />
        <button
          className="chat-send-btn"
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
        >
          send
        </button>
      </div>
    </div>
  );
}

export default ChatInterface;
