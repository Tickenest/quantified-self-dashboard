import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Cell,
} from 'recharts';
import { useQuery } from './useQuery';
import LoadingBar from './LoadingBar';

function CorrelationChart({ apiUrl, timeWindow }) {
  const { data, loading, error } = useQuery(apiUrl, 'exercise_correlation', timeWindow, { limit: 365 });

  if (loading) return <LoadingBar />;
  if (error) return <div className="error-text">error: {error}</div>;
  if (!data?.length) return <div className="empty-text">no data</div>;

  const chartData = [...data]
    .filter(d => d.sample_size >= 3)
    .sort((a, b) => a.avg_next_day_change - b.avg_next_day_change)
    .slice(0, 12);

  return (
    <div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 0, right: 32, bottom: 0, left: 80 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fontSize: 10 }}
            tickFormatter={v => `${v > 0 ? '+' : ''}${v.toFixed(1)}`}
          />
          <YAxis type="category" dataKey="activity" tick={{ fontSize: 10 }} width={80} />
          <ReferenceLine x={0} stroke="var(--border)" strokeWidth={1.5} />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              fontFamily: 'JetBrains Mono',
              fontSize: 11,
            }}
            formatter={(val, name, props) => [
              `${val > 0 ? '+' : ''}${val.toFixed(2)} lbs (n=${props.payload.sample_size})`,
              'avg next-day change',
            ]}
          />
          <Bar dataKey="avg_next_day_change" radius={[0, 4, 4, 0]}>
            {chartData.map((d, i) => (
              <Cell
                key={i}
                fill={d.avg_next_day_change <= 0 ? 'var(--positive)' : 'var(--negative)'}
                fillOpacity={0.75}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div style={{
        fontFamily: 'JetBrains Mono',
        fontSize: '0.67rem',
        color: 'var(--text-muted)',
        marginTop: 10,
        letterSpacing: '0.03em',
      }}>
        avg weight change the day after each activity type · green = lost · red = gained
      </div>
    </div>
  );
}

export default CorrelationChart;
