import React from 'react';

const OPTIONS = [
  { label: '7d',  value: 7 },
  { label: '30d', value: 30 },
  { label: '90d', value: 90 },
  { label: 'all', value: 9999 },
];

function TimeWindowSelector({ value, onChange }) {
  return (
    <div className="time-window-selector">
      <span className="time-window-label">window</span>
      {OPTIONS.map(opt => (
        <button
          key={opt.value}
          className={`time-window-btn ${value === opt.value ? 'active' : ''}`}
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

export default TimeWindowSelector;
