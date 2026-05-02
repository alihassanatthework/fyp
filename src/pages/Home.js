import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import {
  HeartPulse, Scissors, ClipboardList, Calendar,
  AlertCircle, ShieldAlert, Leaf, ScanLine, History as HistoryIcon,
} from 'lucide-react';
import Navbar   from '../components/Navbar';
import Footer   from '../components/Footer';
import AnalysisCard from '../components/AnalysisCard';
// import apiClient from '../api/client'; // ── API disabled for local dev ──
import { useAuth } from '../contexts/AuthContext';

export default function HomePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [stats, setStats]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [bookingChoice, setBookingChoice] = useState('dermatology');

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

      <main className="flex-1 page-container py-8">

        {/* ── Page header ─────────────────────────────────────────── */}
        <div className="mb-7">
          <h1 className="font-display text-2xl font-bold text-gray-900 text-white">
            Welcome back{firstName ? `, ${firstName}` : ''}
          </h1>
          <p className="text-sm text-gray-400 text-gray-500 mt-0.5">
            Dashboard
          </p>
        </div>

        {/* ── Stat cards row ──────────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          {[
            {
              label: 'Total Scans',
              value: loading ? '—' : stats?.total_scans ?? 0,
              sub:   loading ? '' : `${stats?.skin_scans ?? 0} skin · ${stats?.scalp_scans ?? 0} scalp`,
              icon:  <ScanLine size={18} className="text-blue-500"/>,
              bg:    'bg-blue-50 bg-blue-900/10',
            },
            {
              label: 'Mild',
              value: loading ? '—' : stats?.severity_counts?.Mild ?? 0,
              sub:   'low severity results',
              icon:  <Leaf size={18} className="text-green-500"/>,
              bg:    'bg-green-50 bg-green-900/10',
            },
            {
              label: 'Moderate',
              value: loading ? '—' : stats?.severity_counts?.Moderate ?? 0,
              sub:   'needs attention',
              icon:  <AlertCircle size={18} className="text-amber-500"/>,
              bg:    'bg-amber-50 bg-amber-900/10',
            },
            {
              label: 'Severe',
              value: loading ? '—' : stats?.severity_counts?.Severe ?? 0,
              sub:   'consult dermatologist',
              icon:  <ShieldAlert size={18} className="text-red-500"/>,
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

        {/* ── Quick Actions: Skin + Scalp ───────────────────────── */}
        <section className="flex flex-col gap-4 mb-6">
          <p className="text-sm font-semibold text-gray-500 text-gray-400">Quick actions</p>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <div style={{ flex: '1 1 260px', display: 'flex' }}>
              <AnalysisCard type="skin" />
            </div>
            <div style={{ flex: '1 1 260px', display: 'flex' }}>
              <AnalysisCard type="scalp" />
            </div>
          </div>
        </section>

        {/* ── Diagnosis Reports + Last Scan (vertical, side-by-side) ── */}
        <section className="flex flex-col gap-4 mb-6">
          <p className="text-sm font-semibold text-gray-500 text-gray-400">Your activity</p>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>

            {/* Diagnosis Reports card */}
            <div className="info-card" style={{ flex: '1 1 260px' }}>
              <div className="info-card-icon" style={{ background: 'var(--blue-50)', color: 'var(--nav-accent)' }}>
                <ClipboardList size={26}/>
              </div>
              <h3 className="info-card-title">Diagnosis Reports</h3>
              <p className="info-card-desc">View your history and AI-generated diagnosis summaries.</p>
              <ul className="info-card-bullets">
                <li>Past skin analyses</li>
                <li>Past scalp analyses</li>
                <li>Downloadable reports</li>
              </ul>
              <button
                onClick={() => navigate('/analysis-history')}
                className="info-card-btn"
              >
                View Reports
              </button>
            </div>

            {/* Last scan card */}
            <div className="info-card" style={{ flex: '1 1 260px' }}>
              <div className="info-card-icon" style={{ background: 'var(--blue-50)', color: 'var(--nav-accent)' }}>
                <HistoryIcon size={26}/>
              </div>
              <h3 className="info-card-title">Last Scan</h3>
              {loading ? (
                <p className="info-card-desc">Loading…</p>
              ) : stats?.last_scan_date ? (
                <>
                  <p className="info-card-desc">
                    Your most recent analysis snapshot.
                  </p>
                  <ul className="info-card-bullets">
                    <li>Date: {stats.last_scan_date}</li>
                    <li style={{ textTransform: 'capitalize' }}>Type: {stats.last_scan_type} analysis</li>
                    <li>Follow-up: {stats.needs_followup ? 'Recommended' : 'Not required'}</li>
                  </ul>
                  <button
                    onClick={() => navigate('/analysis-history')}
                    className="info-card-btn"
                  >
                    View Full History
                  </button>
                </>
              ) : (
                <>
                  <p className="info-card-desc">No scans yet. Run your first analysis to see results here.</p>
                  <ul className="info-card-bullets">
                    <li>Tracks date and type</li>
                    <li>Highlights follow-up</li>
                    <li>Links to full report</li>
                  </ul>
                  <button
                    onClick={() => navigate('/analysis')}
                    className="info-card-btn"
                  >
                    Start First Scan
                  </button>
                </>
              )}
            </div>
          </div>
        </section>

        {/* ── Severity breakdown (full width) ───────────────────── */}
        {stats?.total_scans > 0 && (
          <div className="card p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-900 text-white">Severity breakdown</h2>
              <button
                onClick={() => navigate('/analysis-history')}
                className="text-xs font-semibold"
                style={{ color: 'var(--nav-accent)', background: 'none', border: 'none', cursor: 'pointer' }}
              >
                View all
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

        {/* ── Book Appointment (centered) ───────────────────────── */}
        <div className="card" style={{ padding: '2.25rem 1.5rem' }}>
          <div style={{ maxWidth: 720, margin: '0 auto', textAlign: 'center' }}>
            <h2 className="font-display text-gray-900 text-white" style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.4rem' }}>
              Book Appointment
            </h2>
            <p className="text-sm text-gray-500 text-gray-400" style={{ marginBottom: '1.75rem' }}>
              Choose a service, then book a time that works for you.
            </p>

            <div
              role="radiogroup"
              aria-label="Service type"
              style={{
                display: 'flex',
                gap: '1.25rem',
                justifyContent: 'center',
                flexWrap: 'wrap',
                marginBottom: '1.75rem',
              }}
            >
              {[
                { id: 'dermatology', label: 'Dermatology', desc: 'Skin specialist',  icon: <HeartPulse size={28}/> },
                { id: 'salon',       label: 'Salon',       desc: 'Scalp and hair',   icon: <Scissors size={28}/> },
              ].map(opt => {
                const active = bookingChoice === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => setBookingChoice(opt.id)}
                    className="transition-all"
                    style={{
                      cursor: 'pointer',
                      flex: '1 1 220px',
                      maxWidth: 260,
                      background: active ? 'var(--blue-50)' : 'var(--bg-secondary)',
                      border: `2px solid ${active ? 'var(--nav-accent)' : 'var(--border-color)'}`,
                      boxShadow: active ? '0 6px 18px rgba(67, 56, 202, 0.18)' : 'var(--shadow-sm)',
                      borderRadius: '1rem',
                      padding: '1.5rem 1rem',
                      transform: active ? 'translateY(-2px)' : 'none',
                    }}
                  >
                    <span
                      className="flex items-center justify-center"
                      style={{
                        width: 56,
                        height: 56,
                        borderRadius: 14,
                        margin: '0 auto 0.85rem',
                        background: active ? 'var(--nav-accent)' : 'var(--blue-50)',
                        color: active ? '#fff' : 'var(--nav-accent)',
                        transition: 'all 0.2s',
                      }}
                    >
                      {opt.icon}
                    </span>
                    <div className="text-base font-semibold text-gray-800 text-gray-100" style={{ marginBottom: 2 }}>
                      {opt.label}
                    </div>
                    <div className="text-xs text-gray-500 text-gray-400">
                      {opt.desc}
                    </div>
                  </button>
                );
              })}
            </div>

            <button
              className="btn-primary"
              style={{ padding: '0.75rem 2rem', fontSize: '0.95rem' }}
              onClick={() => navigate(bookingChoice === 'salon' ? '/scalp-treatment' : '/skin-treatment')}
            >
              <Calendar size={16}/> Book {bookingChoice === 'salon' ? 'Salon' : 'Dermatology'} Appointment
            </button>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
