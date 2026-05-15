import React, { useState, useEffect } from 'react';
import LoadingBar from './LoadingBar';

const INDULGENT_KEYWORDS = [
  'burger', 'fries', 'pizza', 'milkshake', 'ice cream', 'donut', 'doughnut',
  'bacon', 'fried', 'wings', 'nachos', 'cheesesteak', 'brownie', 'cookie',
  'chocolate', 'candy', 'chips', 'cheesecake', 'cake', 'pie', 'ribs',
  'pulled pork', 'mac and cheese', 'hot dog', 'corn dog', 'soda', 'beer',
  'alcohol', 'wine', 'brisket', 'loaded', 'double',
];

const HEALTHY_KEYWORDS = [
  'salad', 'salmon', 'chicken breast', 'broccoli', 'asparagus', 'quinoa',
  'brown rice', 'greek yogurt', 'fruit', 'vegetables', 'spinach', 'kale',
  'oatmeal', 'banana', 'apple', 'blueberries', 'berries', 'green beans',
  'cucumber', 'tomato', 'avocado', 'egg white', 'turkey', 'tuna',
];

function classifyFood(foodStr) {
  if (!foodStr) return 'no-data';
  const lower = foodStr.toLowerCase();
  let indulgentScore = 0;
  let healthyScore = 0;
  INDULGENT_KEYWORDS.forEach(k => { if (lower.includes(k)) indulgentScore++; });
  HEALTHY_KEYWORDS.forEach(k => { if (lower.includes(k)) healthyScore++; });
  if (indulgentScore >= 2) return 'indulgent';
  if (indulgentScore === 1 && healthyScore === 0) return 'indulgent';
  if (healthyScore >= 2 && indulgentScore === 0) return 'healthy';
  if (healthyScore >= 1 && indulgentScore <= 1) return 'mixed';
  return 'mixed';
}

function getDateRange(timeWindow) {
  const end = new Date();
  const start = new Date();
  if (timeWindow < 9999) {
    start.setDate(start.getDate() - timeWindow);
    return {
      start_date: start.toISOString().split('T')[0],
      end_date: end.toISOString().split('T')[0],
      limit: timeWindow,
    };
  } else {
    return {
      end_date: end.toISOString().split('T')[0],
      limit: 9999,
    };
  }
}

function FoodDay({ day }) {
  const [hovered, setHovered] = useState(false);
  const dateStr = day.date?.split('T')[0] || '';
  const foods = day.food ? day.food.split(',').map(f => f.trim()) : ['no data'];

  return (
    <div
      className={`food-day ${day.category}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ position: 'relative' }}
    >
      {hovered && (
        <div className="food-tooltip">
          <div className="food-tooltip-date">{dateStr}</div>
          {foods.map((f, i) => (
            <div key={i} className="food-tooltip-item">{f}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function FoodPatternView({ apiUrl, timeWindow }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!apiUrl) return;
    setLoading(true);
    const params = getDateRange(timeWindow);
    fetch(`${apiUrl}query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query_type: 'food_entries',
        params,
      }),
    })
      .then(r => r.json())
      .then(response => {
        const body = typeof response.body === 'string'
          ? JSON.parse(response.body)
          : response;
        setData(body.data || []);
        setLoading(false);
      })
      .catch(err => { setError(err.message); setLoading(false); });
  }, [apiUrl, timeWindow]);

  if (loading) return <LoadingBar />;
  if (error) return <div className="error-text">error: {error}</div>;
  if (!data?.length) return <div className="empty-text">no data</div>;

  const classified = [...data].reverse().map(d => ({
    date: d.date,
    category: classifyFood(d.food),
    food: d.food,
  }));

  const counts = { healthy: 0, mixed: 0, indulgent: 0 };
  classified.forEach(d => { if (counts[d.category] !== undefined) counts[d.category]++; });

  return (
    <div>
      <div className="food-calendar" style={{ position: 'relative' }}>
        {classified.map((d, i) => (
          <FoodDay key={i} day={d} />
        ))}
      </div>
      <div className="food-legend">
        <div className="food-legend-item">
          <div className="food-legend-dot healthy" />
          healthy ({counts.healthy})
        </div>
        <div className="food-legend-item">
          <div className="food-legend-dot mixed" />
          mixed ({counts.mixed})
        </div>
        <div className="food-legend-item">
          <div className="food-legend-dot indulgent" />
          indulgent ({counts.indulgent})
        </div>
      </div>
    </div>
  );
}

export default FoodPatternView;
