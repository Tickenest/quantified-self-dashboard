import React, { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { useQuery } from './useQuery';
import LoadingBar from './LoadingBar';

const COLORS = [
  'var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)',
  'var(--chart-4)', 'var(--chart-5)',
];

function normalizeActivity(exercise) {
  if (!exercise) return [];
  return exercise.split(',').map(e => {
    const trimmed = e.trim().toLowerCase();
    if (trimmed.includes('walk')) return 'walking';
    if (trimmed.includes('bike') || trimmed.includes('cycling')) return 'cycling';
    if (trimmed.includes('run') || trimmed.includes('treadmill')) return 'running';
    if (trimmed.includes('disc golf')) return 'disc golf';
    if (trimmed.includes('ring fit')) return 'ring fit';
    if (trimmed.includes('ddr')) return 'ddr';
    if (trimmed.includes('weight') || trimmed.includes('strength')) return 'weights';
    if (trimmed.includes('swim')) return 'swimming';
    if (trimmed.includes('basketball')) return 'basketball';
    if (trimmed.includes('soccer')) return 'soccer';
    if (trimmed.includes('yoga')) return 'yoga';
    if (trimmed.includes('rest')) return null;
    return trimmed.split(' ').slice(-2).join(' ');
  }).filter(Boolean);
}

function ExerciseBreakdown({ apiUrl, timeWindow }) {
  const { data, loading, error } = useQuery(apiUrl, 'exercise_entries', timeWindow, { limit: 365 });

  const chartData = useMemo(() => {
    if (!data) return [];
    const counts = {};
    data.forEach(d => {
      normalizeActivity(d.exercise).forEach(act => {
        counts[act] = (counts[act] || 0) + 1;
      });
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([name, count]) => ({ name, count }));
  }, [data]);

  if (loading) return <LoadingBar />;
  if (error) return <div className="error-text">error: {error}</div>;
  if (!chartData.length) return <div className="empty-text">no data</div>;

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 0, right: 16, bottom: 0, left: 72 }}
      >
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 10 }} />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={72} />
        <Tooltip
          contentStyle={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            fontFamily: 'JetBrains Mono',
            fontSize: 11,
          }}
          formatter={(val) => [`${val} days`, 'count']}
        />
        <Bar dataKey="count" radius={[0, 4, 4, 0]}>
          {chartData.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.8} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export default ExerciseBreakdown;
