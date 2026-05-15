import React, { useState, useEffect } from 'react';
import LoadingBar from './LoadingBar';

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
  }
  return {
    end_date: end.toISOString().split('T')[0],
    limit: 9999,
  };
}

async function queryData(apiUrl, queryType, params = {}) {
  const response = await fetch(`${apiUrl}query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query_type: queryType, params }),
  });
  const data = await response.json();
  const body = typeof data.body === 'string' ? JSON.parse(data.body) : data;
  return body.data || [];
}

function StatRow({ label, value, accent = false }) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'baseline',
      padding: '8px 0',
      borderBottom: '1px solid var(--border-light)',
    }}>
      <span style={{
        fontFamily: 'JetBrains Mono',
        fontSize: '0.72rem',
        color: 'var(--text-muted)',
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
      }}>
        {label}
      </span>
      <span style={{
        fontFamily: 'DM Sans',
        fontSize: '0.9rem',
        color: accent ? 'var(--accent)' : 'var(--text-primary)',
        fontWeight: accent ? 500 : 300,
        maxWidth: '60%',
        textAlign: 'right',
      }}>
        {value}
      </span>
    </div>
  );
}

function SectionLabel({ text }) {
  return (
    <div style={{
      fontFamily: 'JetBrains Mono',
      fontSize: '0.65rem',
      color: 'var(--accent)',
      letterSpacing: '0.1em',
      textTransform: 'uppercase',
      marginTop: 20,
      marginBottom: 8,
    }}>
      {text}
    </div>
  );
}

function LearningPanel({ apiUrl, timeWindow }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!apiUrl) return;
    setLoading(true);
    setError(null);

    const dateParams = getDateRange(timeWindow);

    Promise.all([
      queryData(apiUrl, 'book_current'),
      queryData(apiUrl, 'books_finished', dateParams),
      queryData(apiUrl, 'books_abandoned'),
      queryData(apiUrl, 'training_entries', dateParams),
    ])
      .then(([currentBook, booksFinished, booksAbandoned, trainingEntries]) => {
        // Parse training courses — explode multi-course days and count frequency
        const courseCounts = {};
        const courseDates = {};
        trainingEntries.forEach(entry => {
          if (!entry.training) return;
          entry.training.split(',').map(c => c.trim()).forEach(course => {
            if (!course) return;
            courseCounts[course] = (courseCounts[course] || 0) + 1;
            const d = entry.date?.split('T')[0];
            if (!courseDates[course] || d > courseDates[course]) {
              courseDates[course] = d;
            }
          });
        });

        const courses = Object.entries(courseCounts)
          .map(([name, days]) => ({ name, days, lastSeen: courseDates[name] }))
          .sort((a, b) => b.lastSeen.localeCompare(a.lastSeen));

        // Consistency: days with any training logged
        const totalDays = trainingEntries.length;
        const daysWithTraining = trainingEntries.filter(e => e.training).length;

        setData({
          currentBook: currentBook[0] || null,
          booksFinished,
          booksAbandoned,
          courses,
          totalDays,
          daysWithTraining,
        });
        setLoading(false);
      })
      .catch(err => { setError(err.message); setLoading(false); });
  }, [apiUrl, timeWindow]);

  if (loading) return <LoadingBar />;
  if (error) return <div className="error-text">error: {error}</div>;
  if (!data) return <div className="empty-text">no data</div>;

  const { currentBook, booksFinished, booksAbandoned, courses, totalDays, daysWithTraining } = data;
  const consistencyPct = totalDays > 0 ? Math.round((daysWithTraining / totalDays) * 100) : 0;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px' }}>

      {/* Books column */}
      <div>
        <SectionLabel text="Reading" />

        {currentBook && (
          <StatRow
            label="currently reading"
            value={currentBook.title}
            accent
          />
        )}

        <StatRow
          label="finished this period"
          value={booksFinished.length > 0 ? `${booksFinished.length} book${booksFinished.length !== 1 ? 's' : ''}` : 'none'}
        />

        {booksFinished.length > 0 && (
          <div style={{ marginTop: 8 }}>
            {booksFinished.map((book, i) => (
              <div key={i} style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '5px 0 5px 12px',
                borderLeft: '2px solid var(--accent)',
                marginBottom: 4,
              }}>
                <span style={{ fontFamily: 'DM Sans', fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 300 }}>
                  {book.title}
                </span>
                <span style={{ fontFamily: 'JetBrains Mono', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                  {book.finished_date?.split('T')[0]}
                </span>
              </div>
            ))}
          </div>
        )}

        {booksAbandoned.length > 0 && (
          <>
            <StatRow
              label="abandoned"
              value={`${booksAbandoned.length} book${booksAbandoned.length !== 1 ? 's' : ''}`}
            />
            <div style={{ marginTop: 8 }}>
              {booksAbandoned.map((book, i) => (
                <div key={i} style={{
                  padding: '5px 0 5px 12px',
                  borderLeft: '2px solid var(--text-muted)',
                  marginBottom: 4,
                }}>
                  <span style={{ fontFamily: 'DM Sans', fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 300, fontStyle: 'italic' }}>
                    {book.title}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Training column */}
      <div>
        <SectionLabel text="Training" />

        <StatRow
          label="consistency"
          value={totalDays > 0 ? `${consistencyPct}% (${daysWithTraining} of ${totalDays} days)` : 'no data'}
          accent={consistencyPct >= 70}
        />

        {courses.length > 0 && (
          <div style={{ marginTop: 12 }}>
            {courses.slice(0, 8).map((course, i) => (
              <div key={i} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'baseline',
                padding: '6px 0 6px 12px',
                borderLeft: `2px solid ${i === 0 ? 'var(--accent)' : 'var(--border)'}`,
                marginBottom: 4,
              }}>
                <span style={{
                  fontFamily: 'DM Sans',
                  fontSize: '0.85rem',
                  color: i === 0 ? 'var(--text-primary)' : 'var(--text-secondary)',
                  fontWeight: 300,
                  maxWidth: '65%',
                }}>
                  {course.name}
                </span>
                <span style={{
                  fontFamily: 'JetBrains Mono',
                  fontSize: '0.68rem',
                  color: 'var(--text-muted)',
                  whiteSpace: 'nowrap',
                }}>
                  {course.days}d
                </span>
              </div>
            ))}
          </div>
        )}

        {courses.length === 0 && (
          <div className="empty-text">no training logged this period</div>
        )}
      </div>

    </div>
  );
}

export default LearningPanel;
