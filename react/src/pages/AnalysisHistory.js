import { useNavigate } from 'react-router-dom';
import { useState, useMemo, useEffect } from 'react';
import { Home, Download, FileText, ArrowUpDown, Droplets, Wind, Calendar, Sparkles, Shirt, ChevronDown, ChevronUp } from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { analysisService } from '../services/analysisService';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../api/config';

const TYPES = ['All', 'Skin', 'Scalp', 'Makeup', 'Fashion'];

function fmt(created) {
  const ts = new Date(created).getTime() || 0;
  const date = new Date(created).toLocaleString('en-US', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
  return { ts, date };
}

// ── Skin / Scalp record ──────────────────────────────────────────────
function adaptAnalysis(rec) {
  const isScalp = (rec.analysis_type || rec.type || '').toLowerCase().includes('scalp');
  const { ts, date } = fmt(rec.created_at || rec.date || rec.timestamp);
  const conditions = rec.conditions || rec.detected_conditions || [];
  const conditionText = conditions.length
    ? conditions.slice(0, 3).map(c => c.name || c.condition || c.class).filter(Boolean).join(', ')
    : 'Normal';
  const sev = (conditions[0]?.severity_level || conditions[0]?.severity || 'Mild').toString();
  const sl = sev.toLowerCase();
  const sClass = sl.includes('severe') ? 'badge-severe' : sl.includes('moderate') ? 'badge-moderate' : 'badge-mild';
  return {
    id: rec.analysis_id || rec.id,
    kind: isScalp ? 'scalp' : 'skin',
    type: isScalp ? 'Scalp Analysis' : 'Skin Analysis',
    subtitle: conditionText || 'No conditions detected',
    badge: sev.charAt(0).toUpperCase() + sev.slice(1).toLowerCase(),
    sClass, date, ts, raw: rec,
  };
}

// ── Makeup record ────────────────────────────────────────────────────
function adaptMakeup(rec) {
  const { ts, date } = fmt(rec.created_at);
  const bits = [rec.face_shape, rec.skin_tone].filter(Boolean).join(' · ');
  return {
    id: `mk-${rec.id}`, kind: 'makeup', type: 'Makeup Assistance',
    subtitle: bits || 'Personalised makeup look', badge: 'Makeup', sClass: 'badge-mild',
    date, ts, suggestions: rec.suggestions || {}, raw: rec,
  };
}

// ── Fashion record ───────────────────────────────────────────────────
function adaptFashion(rec) {
  const { ts, date } = fmt(rec.created_at);
  const bits = [rec.body_type, rec.event_type, rec.skin_tone].filter(Boolean).join(' · ');
  return {
    id: `fa-${rec.id}`, kind: 'fashion', type: 'Fashion Assistance',
    subtitle: bits || 'Personalised outfit guidance', badge: 'Fashion', sClass: 'badge-mild',
    date, ts, suggestions: rec.suggestions || {}, raw: rec,
  };
}

// Render a saved makeup/fashion suggestions object readably.
function SuggestionView({ suggestions }) {
  const entries = Object.entries(suggestions || {}).filter(([, v]) => v != null && v !== '');
  if (!entries.length) return <p className="text-sm text-gray-500 text-gray-400">No saved details for this report.</p>;
  const label = (k) => k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  const renderVal = (v) => {
    if (Array.isArray(v)) return v.map(x => (typeof x === 'object' ? (x.name || x.label || JSON.stringify(x)) : x)).join(', ');
    if (v && typeof v === 'object') {
      if (v.tip || v.shade) return [v.shade, v.tip].filter(Boolean).join(' — ');
      return Object.entries(v).map(([kk, vv]) => `${label(kk)}: ${typeof vv === 'object' ? JSON.stringify(vv) : vv}`).join('; ');
    }
    return String(v);
  };
  return (
    <div className="hist-report-grid">
      {entries.map(([k, v]) => (
        <div key={k} className="hist-report-item">
          <span className="hist-report-key">{label(k)}</span>
          <span className="hist-report-val">{renderVal(v)}</span>
        </div>
      ))}
    </div>
  );
}

export default function AnalysisHistory() {
  const navigate = useNavigate();
  const [activeType, setActiveType] = useState('All');
  const [sortDesc, setSortDesc] = useState(true);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');
  const [openingId, setOpeningId] = useState(null);
  const [showAll, setShowAll] = useState(false);
  const [expandedId, setExpandedId] = useState(null);   // inline makeup/fashion report

  const RECENT_COUNT = 6;

  // Skin/Scalp → full DiagnosisReport. Makeup/Fashion → expand inline.
  const handleViewReport = async (rec) => {
    if (rec.kind === 'makeup' || rec.kind === 'fashion') {
      setExpandedId(prev => (prev === rec.id ? null : rec.id));
      return;
    }
    if (!rec.id) { navigate('/diagnosis', { state: { data: rec.raw } }); return; }
    try {
      setOpeningId(rec.id);
      const full = await analysisService.getAnalysisById(rec.id);
      navigate('/diagnosis', { state: { data: full } });
    } catch (e) {
      navigate('/diagnosis', { state: { data: rec.raw } });
    } finally {
      setOpeningId(null);
    }
  };

  useEffect(() => {
    (async () => {
      try {
        setLoading(true); setError('');
        // Fetch skin/scalp, makeup, and fashion histories together.
        const [analysis, makeup, fashion] = await Promise.allSettled([
          analysisService.getHistory(),
          apiClient.get(API_ENDPOINTS.MAKEUP.HISTORY).then(r => r.data),
          apiClient.get(API_ENDPOINTS.FASHION.HISTORY).then(r => r.data),
        ]);
        const out = [];
        if (analysis.status === 'fulfilled') {
          const list = Array.isArray(analysis.value) ? analysis.value : (analysis.value?.results || []);
          out.push(...list.map(adaptAnalysis));
        }
        if (makeup.status === 'fulfilled' && Array.isArray(makeup.value)) out.push(...makeup.value.map(adaptMakeup));
        if (fashion.status === 'fulfilled' && Array.isArray(fashion.value)) out.push(...fashion.value.map(adaptFashion));
        setRecords(out);
      } catch (e) {
        setError(e?.message || 'Could not load history.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const filtered = useMemo(() => {
    let list = records.slice();
    if (activeType !== 'All') list = list.filter(r => r.kind === activeType.toLowerCase());
    list.sort((a, b) => sortDesc ? b.ts - a.ts : a.ts - b.ts);
    return list;
  }, [records, activeType, sortDesc]);

  const handleDownload = (rec) => {
    let body = `Report\n\nType: ${rec.type}\nDate: ${rec.date}\n`;
    if (rec.kind === 'skin' || rec.kind === 'scalp') {
      body += `Condition: ${rec.subtitle}\nSeverity: ${rec.badge}\n`;
    } else {
      body += `${rec.subtitle}\n\n` + Object.entries(rec.suggestions || {})
        .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`).join('\n');
    }
    const blob = new Blob([body], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${rec.type.replace(/\s+/g, '_')}_${rec.date.split(' ')[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const iconFor = (kind) => kind === 'scalp' ? <Wind size={24}/>
    : kind === 'makeup' ? <Sparkles size={24}/>
    : kind === 'fashion' ? <Shirt size={24}/>
    : <Droplets size={24}/>;

  return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex flex-col">
      <Navbar title="Analysis History" />
      <main className="flex-1 page-container py-8">

        <div className="flex items-start justify-between mb-6 flex-wrap gap-3">
          <div>
            <h1 className="font-display text-2xl font-bold text-gray-900 text-white">Analysis History</h1>
            <p className="text-sm text-gray-400 text-gray-500 mt-1">A record of your skin, scalp, makeup, and fashion reports.</p>
          </div>
          <button onClick={() => navigate('/home')} className="btn-secondary text-sm py-2">
            <Home size={14}/> Home
          </button>
        </div>

        {/* Filter / sort bar */}
        <div className="card flex items-center justify-between mb-5 flex-wrap gap-3" style={{ padding: '0.75rem 1rem' }}>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-gray-500 text-gray-400" style={{ letterSpacing: '0.04em', textTransform: 'uppercase' }}>Type</span>
            <div className="flex items-center gap-1 flex-wrap" style={{ background: 'var(--bg-tertiary)', padding: 4, borderRadius: 999 }}>
              {TYPES.map(t => (
                <button
                  key={t}
                  onClick={() => { setActiveType(t); setShowAll(false); setExpandedId(null); }}
                  className="text-xs font-semibold transition-all"
                  style={{
                    padding: '0.4rem 0.95rem', borderRadius: 999, border: 'none', cursor: 'pointer',
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
          <button onClick={() => setSortDesc(s => !s)} className="btn-secondary text-xs py-1.5" aria-label="Toggle sort order">
            <ArrowUpDown size={13}/> {sortDesc ? 'Newest first' : 'Oldest first'}
          </button>
        </div>

        {loading && (
          <div className="card px-6 py-10 text-center">
            <p className="text-sm text-gray-500 text-gray-400">Loading your reports…</p>
          </div>
        )}
        {error && !loading && (
          <div className="card px-6 py-6" style={{ background: 'rgba(239,68,68,0.06)', borderColor: 'rgba(239,68,68,0.25)' }}>
            <p className="text-sm" style={{ color: '#ef4444' }}>{error}</p>
          </div>
        )}

        {!loading && !error && filtered.length > 0 && (
          <p className="text-sm text-gray-500 text-gray-400" style={{ margin: '0 0 0.75rem' }}>
            {showAll ? `Showing all ${filtered.length} reports`
                     : `Showing ${Math.min(RECENT_COUNT, filtered.length)} of ${filtered.length} recent reports`}
          </p>
        )}

        <div className="flex flex-col gap-3">
          {(showAll ? filtered : filtered.slice(0, RECENT_COUNT)).map((rec) => {
            const isExpandable = rec.kind === 'makeup' || rec.kind === 'fashion';
            const isOpen = expandedId === rec.id;
            return (
              <div key={rec.id} className="card" style={{ padding: '1.1rem 1.25rem' }}>
                <div className="flex items-center gap-4 flex-wrap" style={{ rowGap: '0.85rem' }}>
                  <div className="shrink-0 flex items-center justify-center"
                       style={{ width: 56, height: 56, borderRadius: 14, background: 'var(--blue-50)', color: 'var(--nav-accent)' }}>
                    {iconFor(rec.kind)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <p className="font-semibold text-gray-900 text-white text-sm" style={{ margin: 0 }}>{rec.type}</p>
                      <span className={rec.sClass}>{rec.badge}</span>
                    </div>
                    <p className="text-sm text-gray-500 text-gray-400" style={{ margin: 0, lineHeight: 1.4 }}>{rec.subtitle}</p>
                    <p className="text-xs text-gray-400 text-gray-500 flex items-center gap-1.5" style={{ marginTop: 6 }}>
                      <Calendar size={12}/> {rec.date}
                    </p>
                  </div>
                  <div className="flex flex-col gap-2 shrink-0 history-actions" style={{ marginLeft: 'auto', minWidth: 140 }}>
                    <button onClick={() => handleViewReport(rec)} disabled={openingId === rec.id} className="history-btn history-btn-primary">
                      {isExpandable ? (isOpen ? <ChevronUp size={14}/> : <ChevronDown size={14}/>) : <FileText size={14}/>}
                      {isExpandable ? (isOpen ? ' Hide Report' : ' View Report')
                                    : (openingId === rec.id ? ' Loading…' : ' View Report')}
                    </button>
                    <button onClick={() => handleDownload(rec)} className="history-btn history-btn-ghost">
                      <Download size={14}/> Download
                    </button>
                  </div>
                </div>

                {/* Inline makeup/fashion report */}
                {isExpandable && isOpen && (
                  <div className="hist-report-panel">
                    <SuggestionView suggestions={rec.suggestions} />
                  </div>
                )}
              </div>
            );
          })}

          {filtered.length === 0 && !loading && (
            <div className="card px-6 py-10 text-center">
              <h3 className="font-bold text-gray-800 text-gray-100 mb-1">No matching reports</h3>
              <p className="text-sm text-gray-400 text-gray-500">Try a different type filter.</p>
            </div>
          )}

          {filtered.length > RECENT_COUNT && (
            <div className="flex justify-center" style={{ marginTop: '0.5rem' }}>
              <button onClick={() => setShowAll(s => !s)} className="history-viewall-btn">
                {showAll ? 'Show less' : `View all ${filtered.length} reports`}
              </button>
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
