import React, { useState, useEffect } from 'react';
import LoadingBar from './LoadingBar';

function BriefingPanel({ apiUrl }) {
  const [activeTab, setActiveTab] = useState('daily_briefing');
  const [briefings, setBriefings] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!apiUrl) return;
    setLoading(true);

    Promise.all([
      fetch(`${apiUrl}query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query_type: 'get_briefing',
          params: { briefing_type: 'daily_briefing' },
        }),
      }).then(r => r.json()),
      fetch(`${apiUrl}query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query_type: 'get_briefing',
          params: { briefing_type: 'weekly_briefing' },
        }),
      }).then(r => r.json()),
    ])
      .then(([daily, weekly]) => {
        const parse = r => {
          const body = typeof r.body === 'string' ? JSON.parse(r.body) : r;
          return body.data?.[0] || null;
        };
        setBriefings({
          daily_briefing: parse(daily),
          weekly_briefing: parse(weekly),
        });
        setLoading(false);
      })
      .catch(err => { setError(err.message); setLoading(false); });
  }, [apiUrl]);

  if (loading) return <LoadingBar />;
  if (error) return <div className="error-text">error: {error}</div>;

  const current = briefings[activeTab];

  return (
    <div>
      <div className="briefing-tabs">
        <button
          className={`briefing-tab ${activeTab === 'daily_briefing' ? 'active' : ''}`}
          onClick={() => setActiveTab('daily_briefing')}
        >
          daily
        </button>
        <button
          className={`briefing-tab ${activeTab === 'weekly_briefing' ? 'active' : ''}`}
          onClick={() => setActiveTab('weekly_briefing')}
        >
          weekly
        </button>
      </div>

      {!current ? (
        <div className="empty-text">
          no {activeTab === 'daily_briefing' ? 'daily' : 'weekly'} briefing yet
        </div>
      ) : (
        <>
          <div className="briefing-meta">
            {current.timestamp?.split('T')[0]} · {activeTab.replace('_', ' ')}
          </div>
          <div className="briefing-text">{current.text}</div>
        </>
      )}
    </div>
  );
}

export default BriefingPanel;
