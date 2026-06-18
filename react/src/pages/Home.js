import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import {
  HeartPulse, Scissors, Sparkles, Shirt, ScanLine,
  History as HistoryIcon, ChevronRight, Flame, Trophy, Command,
  Calendar, Camera, AlertTriangle,
} from 'lucide-react';
import Navbar   from '../components/Navbar';
import Footer   from '../components/Footer';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../api/config';
import { useAuth } from '../contexts/AuthContext';

// Bento dashboard widgets
import AuroraBackground   from '../components/dashboard/AuroraBackground';
import SkinCopilot        from '../components/dashboard/SkinCopilot';
import SkinTwin           from '../components/dashboard/SkinTwin';
import TimeMachine        from '../components/dashboard/TimeMachine';
import SkinConstellation  from '../components/dashboard/SkinConstellation';
import FutureSelf         from '../components/dashboard/FutureSelf';
import MirrorMode         from '../components/dashboard/MirrorMode';
import SkinWrapped        from '../components/dashboard/SkinWrapped';
import CommandPalette     from '../components/dashboard/CommandPalette';

import './Home.css';

// Animated counter — counts a number from 0 to target over `duration` ms.
function useCountUp(target, duration = 700) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (target === null || target === undefined) { setVal(0); return; }
    const start = performance.now();
    let raf;
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      // Ease-out quart
      const eased = 1 - Math.pow(1 - t, 4);
      setVal(Math.round(target * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  return val;
}

function StatTile({ label, value, sub, accent }) {
  const animated = useCountUp(typeof value === 'number' ? value : 0);
  return (
    <div className="bento-stat" style={{ '--accent': accent }}>
      <span className="bento-stat-label">{label}</span>
      <span className="bento-stat-value">{typeof value === 'number' ? animated : '—'}</span>
      <span className="bento-stat-sub">{sub}</span>
      <span className="bento-stat-glow" aria-hidden="true"/>
    </div>
  );
}

function HealthScoreCard({ score, trend, streak, onWrapped }) {
  const animated = useCountUp(score || 0);
  const ringPct = (score || 0) / 100;
  const ringColor = score >= 80 ? '#10b981'
                  : score >= 60 ? '#6366f1'
                  : score >= 40 ? '#f59e0b'
                  : '#ef4444';
  const trendLabel = trend > 0 ? `▲ +${trend}`
                    : trend < 0 ? `▼ ${trend}`
                    : '— stable';
  const trendColor = trend > 0 ? '#10b981'
                   : trend < 0 ? '#ef4444' : 'var(--text-tertiary)';

  return (
    <div className="bento-health">
      <div className="bento-health-left">
        <p className="bento-health-label">Skin Health</p>
        <div className="bento-health-value">
          <span>{animated}</span>
          <span className="bento-health-out">/100</span>
        </div>
        <div className="bento-health-trend" style={{ color: trendColor }}>
          {trendLabel} vs last month
        </div>
        {streak > 0 && (
          <div className="bento-health-streak">
            <Flame size={14} color="#f97316"/> {streak}-day streak
          </div>
        )}
        <button className="bento-health-wrapped" onClick={onWrapped}>
          <Trophy size={13}/> Open Skin Wrapped
        </button>
      </div>
      <div className="bento-health-ring">
        <svg viewBox="0 0 120 120">
          <circle className="bento-health-track" cx="60" cy="60" r="50" strokeWidth="10" fill="none"/>
          <circle
            cx="60" cy="60" r="50"
            stroke={ringColor}
            strokeWidth="10"
            strokeLinecap="round"
            fill="none"
            strokeDasharray={2 * Math.PI * 50}
            strokeDashoffset={2 * Math.PI * 50 * (1 - ringPct)}
            style={{ transition: 'stroke-dashoffset 1s cubic-bezier(0.2, 0.8, 0.2, 1)' }}
            transform="rotate(-90 60 60)"
          />
        </svg>
      </div>
    </div>
  );
}

export default function HomePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [stats, setStats]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [bookingChoice, setBookingChoice] = useState('dermatology');

  // Modal/overlay state
  const [mirrorOpen,  setMirrorOpen]  = useState(false);
  const [wrappedOpen, setWrappedOpen] = useState(false);
  const [cmdOpen,     setCmdOpen]     = useState(false);

  // Fetch stats
  useEffect(() => {
    apiClient.get(API_ENDPOINTS.ANALYSIS.STATS)
      .then(res => setStats(res.data))
      .catch(() => setStats({
        total_scans: 0, skin_scans: 0, scalp_scans: 0,
        severity_counts: { Mild: 0, Moderate: 0, Severe: 0 },
        needs_followup: false, last_scan_date: null, last_scan_type: null,
        health_score: 50, health_trend: 0, projection_30d: 50, streak_days: 0,
        daily_timeline: [], recurring_conditions: [], recent_scans: [],
      }))
      .finally(() => setLoading(false));
  }, []);

  // Global ⌘K / Ctrl+K listener
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCmdOpen((s) => !s);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const firstName = user?.first_name || user?.full_name?.split(' ')[0]
                    || user?.email?.split('@')[0] || '';

  // Copilot action router
  const handleCopilotAction = (action) => {
    if (action === 'mirror')   setMirrorOpen(true);
    if (action === 'wrapped')  setWrappedOpen(true);
    if (action === 'time')     window.scrollTo({ top: 800, behavior: 'smooth' });
    if (action === 'tip')      alert('💡 Tip: Hydrated skin reflects more light — moisturise within 60 seconds of cleansing.');
    if (action === 'reminder') navigate('/diagnosis');
  };

  return (
    <div className="bento-page">
      {/* Aurora ambient background — only mounted after stats arrive so
          the hue intensity prop is meaningful on first paint. */}
      {!loading && <AuroraBackground score={stats?.health_score ?? 70}/>}

      <Navbar title={null} subtitle={null} />

      <main className="bento-main">
        {/* Severe alert banner */}
        {stats?.severity_counts?.Severe > 0 && (
          <div className="bento-alert">
            <AlertTriangle size={18}/>
            <span>
              You have <strong>{stats.severity_counts.Severe}</strong> severe finding{stats.severity_counts.Severe>1?'s':''} —
              consider booking a dermatologist.
            </span>
            <button className="bento-alert-btn" onClick={() => navigate('/bookings?type=dermatologist')}>
              Book now <ChevronRight size={14}/>
            </button>
          </div>
        )}

        {/* ── Bento grid ─────────────────────────────────────────── */}
        <section className="bento-grid">

          {/* Skin Copilot (hero) — spans 2 cols */}
          <div className="bento-cell bento-glass span-col-2">
            {loading
              ? <div className="bento-skeleton h-copilot"/>
              : <SkinCopilot stats={stats} firstName={firstName} onAction={handleCopilotAction}/>}
          </div>

          {/* Health Score */}
          <div className="bento-cell bento-glass span-col-2">
            {loading
              ? <div className="bento-skeleton h-health"/>
              : <HealthScoreCard
                  score={stats?.health_score}
                  trend={stats?.health_trend}
                  streak={stats?.streak_days}
                  onWrapped={() => setWrappedOpen(true)}/>}
          </div>

          {/* Stats row — 4 small tiles */}
          <div className="bento-cell bento-glass">
            <StatTile label="Total Scans"
              value={stats?.total_scans ?? 0}
              sub={loading ? '' : `${stats?.skin_scans ?? 0} skin · ${stats?.scalp_scans ?? 0} scalp`}
              accent="#6366f1"/>
          </div>
          <div className="bento-cell bento-glass">
            <StatTile label="Mild" value={stats?.severity_counts?.Mild ?? 0}
              sub="low severity" accent="#10b981"/>
          </div>
          <div className="bento-cell bento-glass">
            <StatTile label="Moderate" value={stats?.severity_counts?.Moderate ?? 0}
              sub="needs attention" accent="#f59e0b"/>
          </div>
          <div className="bento-cell bento-glass">
            <StatTile label="Severe" value={stats?.severity_counts?.Severe ?? 0}
              sub="consult derma" accent="#ef4444"/>
          </div>

          {/* Digital Skin Twin — anatomical hero (2x2) */}
          <div className="bento-cell bento-glass span-col-2 span-row-2">
            {loading
              ? <div className="bento-skeleton h-twin"/>
              : <SkinTwin
                  recurringConditions={stats?.recurring_conditions || []}
                  healthScore={stats?.health_score}
                  onZoneClick={() => navigate('/analysis-history')}/>}
          </div>

          {/* Predictive Future Self */}
          <div className="bento-cell bento-glass span-col-2">
            {loading
              ? <div className="bento-skeleton h-future"/>
              : <FutureSelf stats={stats}/>}
          </div>

          {/* Time Machine scrubber */}
          <div className="bento-cell bento-glass span-col-2">
            {loading
              ? <div className="bento-skeleton h-time"/>
              : <TimeMachine recentScans={stats?.recent_scans || []}/>}
          </div>

          {/* ── Row 1 — Skin → Scalp → Makeup → Fashion ───────────── */}

          {/* Skin scan */}
          <div className="bento-cell bento-glass bento-feature" onClick={() => navigate('/analysis?type=skin')}>
            <div className="bento-feature-icon">
              <ScanLine size={20} color="#fff"/>
            </div>
            <p className="bento-feature-title">Skin Analysis</p>
            <p className="bento-feature-sub">Acne, pigmentation, texture.</p>
            <ChevronRight size={16} className="bento-feature-arrow"/>
          </div>

          {/* Scalp scan */}
          <div className="bento-cell bento-glass bento-feature" onClick={() => navigate('/analysis?type=scalp')}>
            <div className="bento-feature-icon">
              <ScanLine size={20} color="#fff"/>
            </div>
            <p className="bento-feature-title">Scalp Analysis</p>
            <p className="bento-feature-sub">Dandruff, dryness, density.</p>
            <ChevronRight size={16} className="bento-feature-arrow"/>
          </div>

          {/* Makeup */}
          <div className="bento-cell bento-glass bento-feature" onClick={() => navigate('/makeup-assistance')}>
            <div className="bento-feature-icon">
              <Sparkles size={20} color="#fff"/>
            </div>
            <p className="bento-feature-title">Makeup Assistance</p>
            <p className="bento-feature-sub">AI-personalised palettes for any event.</p>
            <ChevronRight size={16} className="bento-feature-arrow"/>
          </div>

          {/* Fashion */}
          <div className="bento-cell bento-glass bento-feature" onClick={() => navigate('/fashion-assistance')}>
            <div className="bento-feature-icon">
              <Shirt size={20} color="#fff"/>
            </div>
            <p className="bento-feature-title">Fashion Assistance</p>
            <p className="bento-feature-sub">Body-aware outfit ideas tailored to you.</p>
            <ChevronRight size={16} className="bento-feature-arrow"/>
          </div>

          {/* ── Row 2 — AI Mirror → Diagnosis History → Book Appointment widget ── */}

          {/* AI Mirror Mode */}
          <div className="bento-cell bento-glass bento-feature" onClick={() => setMirrorOpen(true)}>
            <div className="bento-feature-icon">
              <Camera size={20} color="#fff"/>
            </div>
            <p className="bento-feature-title">AI Mirror Mode</p>
            <p className="bento-feature-sub">Open your camera — see live overlays of past hotspots.</p>
            <ChevronRight size={16} className="bento-feature-arrow"/>
          </div>

          {/* Diagnosis History */}
          <div className="bento-cell bento-glass bento-feature" onClick={() => navigate('/analysis-history')}>
            <div className="bento-feature-icon">
              <HistoryIcon size={20} color="#fff"/>
            </div>
            <p className="bento-feature-title">Diagnosis History</p>
            <p className="bento-feature-sub">Browse every report, filter by type.</p>
            <ChevronRight size={16} className="bento-feature-arrow"/>
          </div>

          {/* Book Appointment quick choice */}
          <div className="bento-cell bento-glass bento-book span-col-2">
            <div className="bento-book-head">
              <Calendar size={16}/>
              <span>Book Appointment</span>
            </div>
            <div className="bento-book-options">
              {[
                { id: 'dermatology', label: 'Dermatology', icon: <HeartPulse size={18}/>, type: 'dermatologist' },
                { id: 'salon',       label: 'Salon',       icon: <Scissors  size={18}/>, type: 'salon'         },
              ].map((opt) => {
                const active = bookingChoice === opt.id;
                return (
                  <button
                    key={opt.id}
                    className={`bento-book-opt ${active ? 'active' : ''}`}
                    onClick={() => setBookingChoice(opt.id)}
                  >
                    {opt.icon}<span>{opt.label}</span>
                  </button>
                );
              })}
            </div>
            <button
              className="bento-book-cta"
              onClick={() => navigate(`/bookings?type=${bookingChoice === 'salon' ? 'salon' : 'dermatologist'}`)}
            >
              <Calendar size={14}/> Book {bookingChoice === 'salon' ? 'salon' : 'dermatology'} appointment
              <ChevronRight size={14}/>
            </button>
          </div>

        </section>

        {/* ── Skin Constellation — dedicated full-width section, taken
            out of the bento grid so its tall starfield doesn't break
            row alignment with the smaller feature tiles. */}
        <section className="bento-constellation-section bento-glass">
          {loading
            ? <div className="bento-skeleton h-const"/>
            : <SkinConstellation recentScans={stats?.recent_scans || []}/>}
        </section>

        {/* Floating Cmd+K hint */}
        <button className="bento-cmdk-fab" onClick={() => setCmdOpen(true)} aria-label="Open command palette">
          <Command size={14}/> <kbd>⌘K</kbd>
        </button>
      </main>

      {/* Modals */}
      <MirrorMode    open={mirrorOpen}  onClose={() => setMirrorOpen(false)}
                     recurringConditions={stats?.recurring_conditions || []}/>
      <SkinWrapped   open={wrappedOpen} onClose={() => setWrappedOpen(false)} stats={stats}/>
      <CommandPalette open={cmdOpen}    onClose={() => setCmdOpen(false)}
                      onAction={(a) => {
                        if (a === 'mirror')  setMirrorOpen(true);
                        if (a === 'wrapped') setWrappedOpen(true);
                        if (a === 'reminder') navigate('/diagnosis');
                      }}/>

      <Footer />
    </div>
  );
}
