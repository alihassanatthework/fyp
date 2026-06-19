import { useNavigate } from 'react-router-dom';
import { useState, useMemo, useEffect } from 'react';
import { Home, Download, FileText, ArrowUpDown, Droplets, Wind, Calendar } from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { analysisService } from '../services/analysisService';

const TYPES = ['All', 'Skin', 'Scalp'];

// Map a backend AnalysisRecord into the shape this UI expects.
function adaptRecord(rec) {
  const isScalp = (rec.analysis_type || rec.type || '').toLowerCase().includes('scalp');
  const created = rec.created_at || rec.date || rec.timestamp || new Date().toISOString();
  const ts = new Date(created).getTime() || 0;
  const dateStr = new Date(created).toLocaleString('en-US', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
  const conditions = rec.conditions || rec.detected_conditions || [];
  const conditionText = conditions.length
    ? conditions.slice(0, 3).map(c => c.name || c.condition || c.class).filter(Boolean).join(', ')
    : 'Normal';
  // Pick the most-severe label as the badge
  const sev = (conditions[0]?.severity_level || conditions[0]?.severity || 'Mild').toString();
  const sevLower = sev.toLowerCase();
  const sClass = sevLower.includes('severe') ? 'badge-severe'
              : sevLower.includes('moderate') ? 'badge-moderate'
              : 'badge-mild';
  return {
    id: rec.analysis_id || rec.id,
    type: isScalp ? 'Scalp Analysis' : 'Skin Analysis',
    condition: conditionText || 'No conditions detected',
    date: dateStr,
    ts,
    severity: sev.charAt(0).toUpperCase() + sev.slice(1).toLowerCase(),
    sClass,
    raw: rec,                        // keep full payload so View Report can re-use it
  };
}

export default function AnalysisHistory() {
  const navigate = useNavigate();
  const [activeType, setActiveType] = useState('All');
  const [sortDesc, setSortDesc] = useState(true);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');
  const [openingId, setOpeningId] = useState(null);  // shows spinner on clicked card
  const [showAll, setShowAll] = useState(false);     // collapse to recent few by default

  const RECENT_COUNT = 6;

  // The history endpoint returns only summary fields. To render DiagnosisReport
  // we need the full pipeline payload, which lives at /analysis/<id>/.
  const handleViewReport = async (rec) => {
    if (!rec.id) {
      navigate('/diagnosis', { state: { data: rec.raw } });
      return;
    }
    try {
      setOpeningId(rec.id);
      const full = await analysisService.getAnalysisById(rec.id);
      navigate('/diagnosis', { state: { data: full } });
    } catch (e) {
      // Fall back to whatever summary we have so the page at least opens
      navigate('/diagnosis', { state: { data: rec.raw } });
    } finally {
      setOpeningId(null);
    }
  };

  useEffect(() => {
    (async () => {
      try {
        setLoading(true); setError('');
        const data = await analysisService.getHistory();
        const list = Array.isArray(data) ? data : (data?.results || []);
        setRecords(list.map(adaptRecord));
      } catch (e) {
        setError(e?.message || 'Could not load history.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const filtered = useMemo(() => {
    let list = records.slice();
    if (activeType !== 'All') list = list.filter(r => r.type.toLowerCase().startsWith(activeType.toLowerCase()));
    list.sort((a, b) => sortDesc ? b.ts - a.ts : a.ts - b.ts);
    return list;
  }, [records, activeType, sortDesc]);

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

        {loading && (
          <div className="card px-6 py-10 text-center">
            <p className="text-sm text-gray-500 text-gray-400">Loading your analyses…</p>
          </div>
        )}
        {error && !loading && (
          <div className="card px-6 py-6" style={{ background: 'rgba(239,68,68,0.06)', borderColor: 'rgba(239,68,68,0.25)' }}>
            <p className="text-sm" style={{ color: '#ef4444' }}>{error}</p>
          </div>
        )}

        {/* Recent count header */}
        {!loading && !error && filtered.length > 0 && (
          <p className="text-sm text-gray-500 text-gray-400" style={{ margin: '0 0 0.75rem' }}>
            {showAll
              ? `Showing all ${filtered.length} analyses`
              : `Showing ${Math.min(RECENT_COUNT, filtered.length)} of ${filtered.length} recent analyses`}
          </p>
        )}

        {/* Records list */}
        <div className="flex flex-col gap-3">
          {(showAll ? filtered : filtered.slice(0, RECENT_COUNT)).map((rec, i) => {
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
                      onClick={() => handleViewReport(rec)}
                      disabled={openingId === rec.id}
                      className="history-btn history-btn-primary"
                    >
                      <FileText size={14}/>
                      {openingId === rec.id ? ' Loading…' : ' View Report'}
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

          {/* View All / Show Less toggle */}
          {filtered.length > RECENT_COUNT && (
            <div className="flex justify-center" style={{ marginTop: '0.5rem' }}>
              <button
                onClick={() => setShowAll(s => !s)}
                className="history-viewall-btn"
              >
                {showAll
                  ? 'Show less'
                  : `View all ${filtered.length} analyses`}
              </button>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
