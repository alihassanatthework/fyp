import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import {
  Smile, Scissors, FileText, Calendar, Bell, ArrowRight,
  TrendingUp, AlertTriangle, CheckCircle, Activity,
} from 'lucide-react';
import Navbar   from '../components/Navbar';
import Footer   from '../components/Footer';
// import apiClient from '../api/client'; // ── API disabled for local dev ──
import { useAuth } from '../contexts/AuthContext';

// Build smart notifications from real API stats — no hardcoding
function buildNotifications(stats) {
  if (!stats) return [];
  const notes = [];

  if (stats.total_scans === 0) {
    notes.push({ color: 'bg-blue-500', text: 'Run your first skin or scalp analysis to get personalised recommendations.' });
    return notes;
  }

  if (stats.needs_followup) {
    notes.push({ color: 'bg-amber-400', text: `Follow-up check recommended after your last ${stats.last_scan_type} analysis.` });
  }

  if (stats.severity_counts?.Severe > 0) {
    notes.push({ color: 'bg-red-500', text: `${stats.severity_counts.Severe} severe result${stats.severity_counts.Severe > 1 ? 's' : ''} found — consider consulting a dermatologist.` });
  }

  if (stats.severity_counts?.Moderate > 0) {
    notes.push({ color: 'bg-amber-400', text: `${stats.severity_counts.Moderate} moderate condition${stats.severity_counts.Moderate > 1 ? 's' : ''} detected — new treatment recommendations are available.` });
  }

  if (stats.total_scans > 0 && !stats.needs_followup && stats.severity_counts?.Severe === 0) {
    notes.push({ color: 'bg-green-500', text: 'Your skin health looks stable. Keep following your daily routine.' });
  }

  return notes.slice(0, 3); // max 3
}

export default function HomePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [stats, setStats]     = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // ── MOCK stats (no backend) ─────────────────────────────────────────
    setStats({
      total_scans: 0,
      skin_scans: 0,
      scalp_scans: 0,
      severity_counts: { Mild: 0, Moderate: 0, Severe: 0 },
      needs_followup: false,
      last_scan_date: null,
      last_scan_type: null,
    });
    setLoading(false);

    // ── REAL API call (commented out) ──────────────────────────────────────
    // apiClient.get('/analysis/stats/')
    //   .then(res => setStats(res.data))
    //   .catch(() => {})
    //   .finally(() => setLoading(false));
  }, []);

  const notifications = buildNotifications(stats);
  const firstName = user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || '';

  // Severity colours
  const severityColor = {
    Mild:     { bg: 'bg-green-100 bg-green-900/20',  text: 'text-green-600 text-green-400',  dot: 'bg-green-500' },
    Moderate: { bg: 'bg-amber-100 bg-amber-900/20',  text: 'text-amber-600 text-amber-400',  dot: 'bg-amber-400' },
    Severe:   { bg: 'bg-red-100   bg-red-900/20',    text: 'text-red-600   text-red-400',    dot: 'bg-red-500'   },
  };

  return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex flex-col">
      <Navbar title={null} subtitle={null} />

      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">

        {/* ── Page header ─────────────────────────────────────────── */}
        <div className="mb-7">
          <h1 className="font-display text-2xl font-bold text-gray-900 text-white">
            AI-Powered Skin &amp; Scalp Assistant
          </h1>
          <p className="text-sm text-gray-400 text-gray-500 mt-0.5">
            Welcome back{firstName ? `, ${firstName}` : ''} — here's your health overview
          </p>
        </div>

        {/* ── Stat cards row ──────────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          {[
            {
              label: 'Total Scans',
              value: loading ? '—' : stats?.total_scans ?? 0,
              sub:   loading ? '' : `${stats?.skin_scans ?? 0} skin · ${stats?.scalp_scans ?? 0} scalp`,
              icon:  <Activity size={18} className="text-blue-500"/>,
              bg:    'bg-blue-50 bg-blue-900/10',
            },
            {
              label: 'Mild',
              value: loading ? '—' : stats?.severity_counts?.Mild ?? 0,
              sub:   'low severity results',
              icon:  <CheckCircle size={18} className="text-green-500"/>,
              bg:    'bg-green-50 bg-green-900/10',
            },
            {
              label: 'Moderate',
              value: loading ? '—' : stats?.severity_counts?.Moderate ?? 0,
              sub:   'needs attention',
              icon:  <TrendingUp size={18} className="text-amber-500"/>,
              bg:    'bg-amber-50 bg-amber-900/10',
            },
            {
              label: 'Severe',
              value: loading ? '—' : stats?.severity_counts?.Severe ?? 0,
              sub:   'consult dermatologist',
              icon:  <AlertTriangle size={18} className="text-red-500"/>,
              bg:    'bg-red-50 bg-red-900/10',
            },
          ].map((card, i) => (
            <div key={i} className={`card p-4 ${card.bg}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-gray-500 text-gray-400 uppercase tracking-wide">{card.label}</span>
                {card.icon}
              </div>
              <p className="text-3xl font-bold text-gray-900 text-white">{card.value}</p>
              <p className="text-xs text-gray-400 text-gray-500 mt-1">{card.sub}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

          {/* ── Main column ─────────────────────────────────────── */}
          <div className="xl:col-span-2 space-y-5">

            {/* Quick Actions */}
            <section>
              <p className="text-sm font-semibold text-gray-500 text-gray-400 mb-3">Quick actions</p>
              <div className="flex flex-col gap-4">
                {[
                  {
                    icon:     <Smile size={28} className="text-blue-500"/>,
                    title:    'Skin Analysis',
                    desc:     'Upload a face image for AI-based skin detection. Get instant insights on skin conditions, texture, and personalised care.',
                    btn:      'Analyze Skin',
                    to:       '/analysis?type=skin',
                    accent:   'border-blue-500',
                    bg:       'bg-blue-50 bg-blue-900/10',
                    btnClass: 'bg-blue-500 hover:bg-blue-600 text-white',
                  },
                  {
                    icon:     <Scissors size={28} className="text-indigo-500"/>,
                    title:    'Scalp Analysis',
                    desc:     'Upload a scalp image to detect dandruff, dryness & more. Receive targeted scalp health recommendations.',
                    btn:      'Analyze Scalp',
                    to:       '/analysis?type=scalp',
                    accent:   'border-indigo-500',
                    bg:       'bg-indigo-50 bg-indigo-900/10',
                    btnClass: 'bg-indigo-500 hover:bg-indigo-600 text-white',
                  },
                  {
                    icon:     <FileText size={28} className="text-violet-500"/>,
                    title:    'Diagnosis Reports',
                    desc:     'View your history and AI-generated diagnosis summaries. Track your skin and scalp health over time.',
                    btn:      'My Reports',
                    to:       '/analysis-history',
                    accent:   'border-violet-500',
                    bg:       'bg-violet-50 bg-violet-900/10',
                    btnClass: 'bg-violet-500 hover:bg-violet-600 text-white',
                  },
                ].map((item, i) => (
                  <div key={i} className={`card p-6 flex items-center justify-between gap-6 border-l-4 ${item.accent} ${item.bg} shadow-md hover:shadow-lg transition-shadow`}>
                    <div className="flex items-center gap-5 flex-1">
                      <div className="w-14 h-14 rounded-2xl bg-white bg-gray-800 flex items-center justify-center shadow-sm shrink-0">
                        {item.icon}
                      </div>
                      <div>
                        <h3 className="font-bold text-gray-800 text-gray-100 text-base mb-1">{item.title}</h3>
                        <p className="text-sm text-gray-500 text-gray-400 leading-relaxed">{item.desc}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => navigate(item.to)}
                      className={`shrink-0 px-5 py-2.5 rounded-xl text-sm font-semibold transition-colors ${item.btnClass}`}
                    >
                      {item.btn} →
                    </button>
                  </div>
                ))}
              </div>
            </section>

            {/* Severity breakdown — only if user has scans */}
            {stats?.total_scans > 0 && (
              <div className="card p-5">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-semibold text-gray-900 text-white">Severity breakdown</h2>
                  <button
                    onClick={() => navigate('/analysis-history')}
                    className="text-xs font-semibold text-blue-500 flex items-center gap-1"
                  >
                    View all <ArrowRight size={12}/>
                  </button>
                </div>
                <div className="space-y-3">
                  {['Mild', 'Moderate', 'Severe'].map(level => {
                    const count = stats.severity_counts?.[level] ?? 0;
                    const pct   = stats.total_scans > 0 ? Math.round((count / stats.total_scans) * 100) : 0;
                    const c     = severityColor[level];
                    return (
                      <div key={level}>
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <span className={`w-2 h-2 rounded-full ${c.dot}`}/>
                            <span className={`text-sm font-medium ${c.text}`}>{level}</span>
                          </div>
                          <span className="text-xs text-gray-400">{count} scan{count !== 1 ? 's' : ''} · {pct}%</span>
                        </div>
                        <div className="w-full bg-gray-100 bg-gray-800 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${c.dot} transition-all duration-500`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Treatment Plan — linked to last diagnosis */}
            <div className="card p-6">
              <h2 className="font-semibold text-gray-900 text-white text-base mb-2">Your Personalised Treatment Plan</h2>
              <p className="text-sm text-gray-500 text-gray-400 leading-relaxed mb-4">
                Based on your health profile and AI analysis, we generate safe, step-by-step skin and scalp treatment recommendations tailored to you.
              </p>
              {stats?.total_scans > 0 ? (
                <button
                  onClick={() => navigate('/analysis-history')}
                  className="flex items-center gap-1.5 text-sm font-semibold text-blue-600 text-blue-400 transition hover:underline"
                >
                  View your treatment recommendations <ArrowRight size={15}/>
                </button>
              ) : (
                <button
                  onClick={() => navigate('/analysis?type=skin')}
                  className="flex items-center gap-1.5 text-sm font-semibold text-blue-600 text-blue-400 transition hover:underline"
                >
                  Run your first analysis to generate a plan <ArrowRight size={15}/>
                </button>
              )}
            </div>

            {/* Makeup & Fashion section removed */}

          </div>

          {/* ── Sidebar ─────────────────────────────────────────── */}
          <div className="space-y-5">

            {/* Last scan summary */}
            <div className="card p-5">
              <h2 className="font-semibold text-gray-900 text-white mb-3">Last scan</h2>
              {loading ? (
                <p className="text-sm text-gray-400">Loading…</p>
              ) : stats?.last_scan_date ? (
                <div className="space-y-2">
                  <div>
                    <p className="text-xs text-gray-400 text-gray-500">Date</p>
                    <p className="text-sm font-medium text-gray-700 text-gray-200">{stats.last_scan_date}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 text-gray-500">Type</p>
                    <p className="text-sm font-medium text-gray-700 text-gray-200 capitalize">{stats.last_scan_type} analysis</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 text-gray-500">Follow-up</p>
                    <p className={`text-sm font-medium ${stats.needs_followup ? 'text-amber-500' : 'text-green-500'}`}>
                      {stats.needs_followup ? '⚠️ Recommended' : '✅ Not required'}
                    </p>
                  </div>
                  <button
                    onClick={() => navigate('/analysis-history')}
                    className="btn-secondary w-full mt-2 text-xs py-1.5"
                  >
                    View full history
                  </button>
                </div>
              ) : (
                <div>
                  <p className="text-sm text-gray-400 text-gray-500 mb-3">No scans yet. Run your first analysis to see results here.</p>
                  <button onClick={() => navigate('/analysis?type=skin')} className="btn-primary w-full text-xs py-1.5">
                    Start first scan →
                  </button>
                </div>
              )}
            </div>

            {/* Smart Notifications — derived from real stats */}
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Bell size={17} className="text-blue-500"/>
                <h2 className="font-semibold text-gray-900 text-white">Notifications</h2>
              </div>
              {notifications.length > 0 ? (
                <ul className="space-y-3">
                  {notifications.map((n, i) => (
                    <li key={i} className="flex items-start gap-3">
                      <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${n.color}`}/>
                      <span className="text-xs text-gray-600 text-gray-400 leading-relaxed">{n.text}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-gray-400">No notifications right now.</p>
              )}
            </div>

            {/* Book Appointment */}
            <div className="card p-5">
              <h2 className="font-semibold text-gray-900 text-white mb-1">Book Appointment</h2>
              <p className="text-xs text-gray-400 text-gray-500 mb-4">
                Connect with dermatology experts or salon services based on your diagnosis.
              </p>
              <div className="flex flex-wrap gap-2 mb-4">
                {['Dermatology', 'Salon', 'Fashion'].map(tag => (
                  <span key={tag} className="bg-gray-100 bg-gray-800 text-gray-600 text-gray-300 text-xs font-medium px-3 py-1 rounded-full">{tag}</span>
                ))}
              </div>
              <button className="btn-secondary w-full">
                <Calendar size={15}/> Book an appointment
              </button>
            </div>

            {/* AR Try-On section removed */}

          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
