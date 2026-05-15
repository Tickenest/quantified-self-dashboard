import React, { useState, useEffect } from 'react';

const MESSAGES = [
  'querying data...',
  'running analysis...',
  'crunching numbers...',
  'fetching results...',
];

function LoadingBar() {
  const [msgIdx, setMsgIdx] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setMsgIdx(i => (i + 1) % MESSAGES.length);
    }, 1400);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="loading-wrap">
      <div className="loading-bar-wrap">
        <div className="loading-bar" />
      </div>
      <span className="loading-status">{MESSAGES[msgIdx]}</span>
    </div>
  );
}

export default LoadingBar;
