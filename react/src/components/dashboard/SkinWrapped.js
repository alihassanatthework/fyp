/**
 * SkinWrapped
 * ───────────
 * Spotify-Wrapped style story modal. Auto-advances slides every 4s,
 * with click / arrow-key controls. Each slide is generated from the
 * user's actual stats — no static content.
 */
import { useEffect, useMemo, useState } from 'react';
import { X, ChevronLeft, ChevronRight, Sparkles, Trophy } from 'lucide-react';
import './SkinWrapped.css';

function buildSlides(stats) {
  const total = stats?.total_scans ?? 0;
  const skin = stats?.skin_scans ?? 0;
  const scalp = stats?.scalp_scans ?? 0;
  const sev = stats?.severity_counts || {};
  const top = stats?.recurring_conditions?.[0];
  const score = stats?.health_score ?? 0;
  const streak = stats?.streak_days ?? 0;
  const trend = stats?.health_trend ?? 0;

  // P3 — when there's no data yet, skip slides 2-6 to avoid "0 mild · 0
  // moderate · 0 severe" cards that feel broken. Show intro + CTA only.
  if (total === 0) {
    return [
      {
        title:    'Your Skin, Wrapped',
        headline: 'Just getting started?',
        sub:      'Run your first scan to unlock your story.',
        gradient: ['#6366f1', '#a855f7', '#ec4899'],
        icon: <Sparkles size={28}/>,
      },
      {
        title:    'See you next year ✨',
        headline: 'Start scanning to build your story.',
        sub:      'Even one scan a week reveals patterns you can act on.',
        gradient: ['#6366f1', '#ec4899', '#f59e0b'],
        icon: <Sparkles size={28}/>,
      },
    ];
  }

  const slides = [
    {
      title:    'Your Skin, Wrapped',
      headline: total > 0 ? `${total} scans this year` : 'Just getting started?',
      sub:      total > 0
                  ? `You analysed your skin and scalp ${total} times to take charge of your health.`
                  : 'Run your first scan to unlock your story.',
      gradient: ['#6366f1', '#a855f7', '#ec4899'],
      icon: <Sparkles size={28}/>,
    },
    {
      title:    'Your split',
      headline: `${skin} face · ${scalp} scalp`,
      sub:      skin >= scalp
                  ? `You're a face-first tracker — your skin got the most attention.`
                  : `You spent more time on scalp health than skin. Nice balance.`,
      gradient: ['#6366f1', '#06b6d4'],
    },
    {
      title:    'Your most-tracked concern',
      headline: top ? top.name : 'Nothing recurring',
      sub:      top
                  ? `Detected ${top.count} time${top.count>1?'s':''} this year. Watching it pays off.`
                  : `No condition appeared more than twice. Healthy skin year!`,
      gradient: ['#f59e0b', '#ec4899'],
    },
    {
      title:    'Your severity mix',
      headline: `${sev.Mild||0} mild · ${sev.Moderate||0} moderate · ${sev.Severe||0} severe`,
      sub:      (sev.Severe || 0) > (sev.Mild || 0)
                  ? `Important to keep checking — book a derma soon.`
                  : `Most findings were on the milder side. Keep it up.`,
      gradient: ['#10b981', '#6366f1'],
    },
    {
      title:    'Your health score',
      headline: `${score} / 100`,
      sub:      trend > 0
                  ? `Up ${trend} points this month. Trajectory is your friend.`
                  : trend < 0
                    ? `Down ${Math.abs(trend)} points — time to refocus.`
                    : `Stable. Consistency wins.`,
      gradient: ['#ec4899', '#a855f7'],
    },
    {
      title:    'Your streak',
      headline: streak > 0 ? `🔥 ${streak} day${streak>1?'s':''}` : 'Build a streak',
      sub:      streak > 0
                  ? `You scanned ${streak} day${streak>1?'s':''} in a row. Habit unlocked.`
                  : `Scan two days in a row to start a streak.`,
      gradient: ['#f59e0b', '#ef4444'],
      icon: <Trophy size={28}/>,
    },
    {
      title:    'See you next year ✨',
      headline: 'Thanks for taking care of yourself.',
      sub:      `Share your year — or run another scan to keep the streak alive.`,
      gradient: ['#6366f1', '#ec4899', '#f59e0b'],
      icon: <Sparkles size={28}/>,
    },
  ];
  return slides;
}

export default function SkinWrapped({ open, onClose, stats }) {
  const slides = useMemo(() => buildSlides(stats), [stats]);
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    if (!open) { setIdx(0); return; }
    const timer = setInterval(() => {
      setIdx((i) => (i + 1) % slides.length);
    }, 4000);
    return () => clearInterval(timer);
  }, [open, slides.length]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === 'ArrowLeft')  setIdx((i) => Math.max(0, i - 1));
      if (e.key === 'ArrowRight') setIdx((i) => Math.min(slides.length - 1, i + 1));
      if (e.key === 'Escape')     onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, slides.length, onClose]);

  if (!open) return null;

  const slide = slides[idx];

  return (
    <div className="wrapped-overlay" onClick={onClose}>
      <div
        className="wrapped-stage"
        style={{ background: `linear-gradient(135deg, ${slide.gradient.join(', ')})` }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Progress bars */}
        <div className="wrapped-progress">
          {slides.map((_, i) => (
            <div key={i} className="wrapped-progress-track">
              <div
                className="wrapped-progress-fill"
                style={{
                  width: i < idx ? '100%' : i === idx ? '100%' : '0%',
                  transitionDuration: i === idx ? '4s' : '0s',
                }}
              />
            </div>
          ))}
        </div>

        <button className="wrapped-close" onClick={onClose}><X size={20}/></button>

        <div className="wrapped-nav-left"  onClick={() => setIdx((i) => Math.max(0, i - 1))}>
          <ChevronLeft size={28}/>
        </div>
        <div className="wrapped-nav-right" onClick={() => setIdx((i) => Math.min(slides.length - 1, i + 1))}>
          <ChevronRight size={28}/>
        </div>

        <div className="wrapped-content" key={idx}>
          {slide.icon && <div className="wrapped-icon">{slide.icon}</div>}
          <p className="wrapped-title">{slide.title}</p>
          <h1 className="wrapped-headline">{slide.headline}</h1>
          <p className="wrapped-sub">{slide.sub}</p>
        </div>
      </div>
    </div>
  );
}
