import { useState, useEffect } from 'react';

function getDateRange(timeWindow) {
  if (timeWindow >= 9999) return {};
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - timeWindow);
  return {
    start_date: start.toISOString().split('T')[0],
    end_date: end.toISOString().split('T')[0],
  };
}

export function useQuery(apiUrl, queryType, timeWindow, extraParams = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!apiUrl) return;
    setLoading(true);
    setError(null);

    const params = { ...getDateRange(timeWindow), ...extraParams };

    fetch(`${apiUrl}query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query_type: queryType, params }),
    })
      .then(r => r.json())
      .then(response => {
        const body = typeof response.body === 'string'
          ? JSON.parse(response.body)
          : response;
        setData(body.data || []);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [apiUrl, queryType, timeWindow, JSON.stringify(extraParams)]);

  return { data, loading, error };
}
