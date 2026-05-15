import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import TimeWindowSelector from './components/TimeWindowSelector';
import WeightTrendChart from './components/WeightTrendChart';
import ExerciseBreakdown from './components/ExerciseBreakdown';
import FoodPatternView from './components/FoodPatternView';
import CorrelationChart from './components/CorrelationChart';
import BriefingPanel from './components/BriefingPanel';
import ChatInterface from './components/ChatInterface';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || '';
const ENVIRONMENT = process.env.REACT_APP_ENVIRONMENT || 'demo';
const DASHBOARD_NAME = process.env.REACT_APP_DASHBOARD_NAME || 'The Quantified Everyman';

function App() {
  const [darkMode, setDarkMode] = useState(true);
  const [timeWindow, setTimeWindow] = useState(30);

  useEffect(() => {
    const saved = localStorage.getItem('darkMode');
    if (saved !== null) setDarkMode(saved === 'true');
  }, []);

  useEffect(() => {
    document.body.className = darkMode ? 'dark' : 'light';
    localStorage.setItem('darkMode', darkMode);
  }, [darkMode]);

  return (
    <div className="app">
      <Header
        darkMode={darkMode}
        onToggleDark={() => setDarkMode(d => !d)}
        environment={ENVIRONMENT}
        dashboardName={DASHBOARD_NAME}
      />

      <main className="main-content">
        <div className="time-window-row">
          <TimeWindowSelector value={timeWindow} onChange={setTimeWindow} />
        </div>

        <div className="dashboard-grid">
          <section className="card card--wide">
            <h2 className="card-title">Weight Trend</h2>
            <WeightTrendChart apiUrl={API_URL} timeWindow={timeWindow} />
          </section>

          <section className="card">
            <h2 className="card-title">Exercise Breakdown</h2>
            <ExerciseBreakdown apiUrl={API_URL} timeWindow={timeWindow} />
          </section>

          <section className="card">
            <h2 className="card-title">Food Patterns</h2>
            <FoodPatternView apiUrl={API_URL} timeWindow={timeWindow} />
          </section>

          <section className="card card--wide">
            <h2 className="card-title">Weight vs Exercise</h2>
            <CorrelationChart apiUrl={API_URL} timeWindow={timeWindow} />
          </section>

          <section className="card card--wide">
            <h2 className="card-title">Briefings</h2>
            <BriefingPanel apiUrl={API_URL} />
          </section>

          <section className="card card--full">
            <h2 className="card-title">Ask About Your Data</h2>
            <ChatInterface apiUrl={API_URL} />
          </section>
        </div>
      </main>

      <footer className="footer">
        <span className="footer-mono">quantified-self-dashboard</span>
        <span className="footer-sep">·</span>
        <span className="footer-mono">aws · bedrock · lambda · s3</span>
      </footer>
    </div>
  );
}

export default App;
