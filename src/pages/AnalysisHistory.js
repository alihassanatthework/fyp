import { useNavigate } from 'react-router-dom';
import { useState, useMemo } from 'react';
import { Home, Download, FileText, ArrowUpDown, Droplets, Wind, Calendar } from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

const records = [
  { type: 'Skin Analysis',  condition: 'Acne, mild redness',     date: '12 Mar 2025 · 09:24 AM', ts: new Date('2025-03-12T09:24').getTime(), severity: 'Mild',     sClass: 'badge-mild' },
  { type: 'Scalp Analysis', condition: 'Dandruff and dryness',   date: '03 Mar 2025 · 06:15 PM', ts: new Date('2025-03-03T18:15').getTime(), severity: 'Moderate', sClass: 'badge-moderate' },
  { type: 'Skin Analysis',  condition: 'Pigmentation',           date: '18 Feb 2025 · 01:42 PM', ts: new Date('2025-02-18T13:42').getTime(), severity: 'Severe',   sClass: 'badge-severe' },
];

const TYPES = ['All', 'Skin', 'Scalp'];

export default function AnalysisHistory() {
  const navigate = useNavigate();
  const [activeType, setActiveType] = useState('All');
  const [sortDesc, setSortDesc] = useState(true);

  const filtered = useMemo(() => {
    let list = records.slice();
    if (activeType !== 'All') list = list.filter(r => r.type.toLowerCase().startsWith(activeType.toLowerCase()));
    list.sort((a, b) => sortDesc ? b.ts - a.ts : a.ts - b.ts);
    return list;
  }, [activeType, sortDesc]);

  const handleDownload = (rec) => {
    const blob = new Blob(
      [`Analysis Report\n\nType: ${rec.type}\nDate: ${rec.date}\nCondition: ${rec.condition}\nSeverity: ${rec.severity}\n`],
      { type: 'text/plain' }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${rec.type.replace(/\s+/g, '_')}_${rec.date.split(' ')[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex flex-col">
      <Navbar title="Analysis History" />

      <main className="flex-1 page-container py-8">

        {/* Page header */}
        <div className="flex items-start justify-between mb-6 flex-wrap gap-3">
          <div>
            <h1 className="font-display text-2xl font-bold text-gray-900 text-white">Analysis History</h1>
            <p className="text-sm text-gray-400 text-gray-500 mt-1">A record of your previous skin and scalp analyses.</p>
          </div>
          <button onClick={() => navigate('/home')} className="btn-secondary text-sm py-2">
            <Home size={14}/> Home
          </button>
        </div>

        {/* Filter / sort bar */}
        <div className="card flex items-center justify-between mb-5 flex-wrap gap-3" style={{ padding: '0.75rem 1rem' }}>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-gray-500 text-gray-400" style={{ letterSpacing: '0.04em', textTransform: 'uppercase' }}>Type</span>
            <div className="flex items-center gap-1" style={{ background: 'var(--bg-tertiary)', padding: 4, borderRadius: 999 }}>
              {TYPES.map(t => (
                <button
                  key={t}
                  onClick={() => setActiveType(t)}
                  className="text-xs font-semibold transition-all"
                  style={{
                    padding: '0.4rem 0.95rem',
                    borderRadius: 999,
                    border: 'none',
                    cursor: 'pointer',
                    background: activeType === t ? 'var(--bg-secondary)' : 'transparent',
                    color: activeType === t ? 'var(--nav-accent)' : 'var(--text-secondary)',
                    boxShadow: activeType === t ? 'var(--shadow-sm)' : 'none',
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={() => setSortDesc(s => !s)}
            className="btn-secondary text-xs py-1.5"
            aria-label="Toggle sort order"
          >
            <ArrowUpDown size={13}/> {sortDesc ? 'Newest first' : 'Oldest first'}
          </button>
        </div>

        {/* Records list */}
        <div className="flex flex-col gap-3">
          {filtered.map((rec, i) => {
            const isScalp = rec.type.includes('Scalp');
            return (
              <div
                key={i}
                className="card"
                style={{ padding: '1.1rem 1.25rem' }}
              >
                <div className="flex items-center gap-4 flex-wrap" style={{ rowGap: '0.85rem' }}>

                  {/* Icon tile */}
                  <div
                    className="shrink-0 flex items-center justify-center"
                    style={{
                      width: 56,
                      height: 56,
                      borderRadius: 14,
                      background: 'var(--blue-50)',
                      color: 'var(--nav-accent)',
                    }}
                  >
                    {isScalp ? <Wind size={24}/> : <Droplets size={24}/>}
                  </div>

                  {/* Title block */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <p className="font-semibold text-gray-900 text-white text-sm" style={{ margin: 0 }}>{rec.type}</p>
                      <span className={rec.sClass}>{rec.severity}</span>
                    </div>
                    <p className="text-sm text-gray-500 text-gray-400" style={{ margin: 0, lineHeight: 1.4 }}>{rec.condition}</p>
                    <p
                      className="text-xs text-gray-400 text-gray-500 flex items-center gap-1.5"
                      style={{ marginTop: 6 }}
                    >
                      <Calendar size={12}/> {rec.date}
                    </p>
                  </div>

                  {/* Action buttons — right-aligned stack */}
                  <div className="flex flex-col gap-2 shrink-0 history-actions" style={{ marginLeft: 'auto', minWidth: 140 }}>
                    <button
                      onClick={() => navigate('/diagnosis')}
                      className="history-btn history-btn-primary"
                    >
                      <FileText size={14}/> View Report
                    </button>
                    <button
                      onClick={() => handleDownload(rec)}
                      className="history-btn history-btn-ghost"
                    >
                      <Download size={14}/> Download
                    </button>
                  </div>
                </div>
              </div>
            );
          })}

          {filtered.length === 0 && (
            <div className="card px-6 py-10 text-center">
              <h3 className="font-bold text-gray-800 text-gray-100 mb-1">No matching analyses</h3>
              <p className="text-sm text-gray-400 text-gray-500">
                Try a different analysis type filter.
              </p>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
