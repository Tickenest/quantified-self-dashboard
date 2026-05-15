import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { useQuery } from './useQuery';
import LoadingBar from './LoadingBar';

function formatDate(dateStr) {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: '10px 14px',
    }}>
      <div style={{ fontFamily: 'JetBrains Mono', fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>
        {label}
      </div>
      {payload.map(p => (
        <div key={p.name} style={{ fontFamily: 'JetBrains Mono', fontSize: 12, color: p.color }}>
          {p.name}: {p.value?.toFixed(1)} lbs
        </div>
      ))}
    </div>
  );
}

function WeightTrendChart({ apiUrl, timeWindow }) {
  const { data, loading, error } = useQuery(apiUrl, 'weight_moving_avg', timeWindow, { limit: 365 });

  if (loading) return <LoadingBar />;
  if (error) return <div className="error-text">error: {error}</div>;
  if (!data?.length) return <div className="empty-text">no data</div>;

  const chartData = [...data].reverse().map(d => ({
    date: formatDate(d.date),
    weight: d.weight,
    avg7d: d.moving_avg_7d ? parseFloat(d.moving_avg_7d.toFixed(1)) : null,
  }));

  const weights = chartData.map(d => d.weight).filter(Boolean);
  const min = Math.floor(Math.min(...weights)) - 2;
  const max = Math.ceil(Math.max(...weights)) + 2;

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10 }}
          interval={Math.floor(chartData.length / 8)}
        />
        <YAxis domain={[min, max]} tick={{ fontSize: 10 }} width={48} />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontFamily: 'JetBrains Mono', fontSize: 11, paddingTop: 8 }}
        />
        <Line
          type="monotone"
          dataKey="weight"
          stroke="var(--chart-1)"
          dot={false}
          strokeWidth={1.5}
          name="weight"
          connectNulls={false}
        />
        <Line
          type="monotone"
          dataKey="avg7d"
          stroke="var(--chart-2)"
          dot={false}
          strokeWidth={2}
          strokeDasharray="4 2"
          name="7d avg"
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export default WeightTrendChart;
