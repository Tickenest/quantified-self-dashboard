import React from 'react';

function Header({ darkMode, onToggleDark, environment, dashboardName }) {
  return (
    <header className="header">
      <div className="header-inner">
        <div className="header-logo">
          <span className="header-logo-text">
            [qsd<span className="accent-dot">·</span>dashboard]
          </span>
          <span className="header-env-badge">{environment}</span>
        </div>

        <div className="header-actions">
          <span className="header-name">{dashboardName}</span>
          <button className="dark-toggle" onClick={onToggleDark}>
            {darkMode ? '○' : '●'}
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;
