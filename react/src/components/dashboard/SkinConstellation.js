/**
 * SkinConstellation
 * ─────────────────
 * Plots each scan as a "star" in a starfield. X = days since scan,
 * Y = severity score (higher = brighter star). Connects them in time
 * order with a faint line — your "skin journey constellation".
 *
 * Pure SVG, no chart lib needed for this look.
 */
import { useMemo, useState } from 'react';
import './SkinConstellation.css';

export default function SkinConstellation({ recentScans = [] }) {
  const [hover, setHover] = useState(null);

  const points = useMemo(() => {
    if (!recentScans.length) return [];
    // Map dates to x positions over a 30-day window.
    const now = Date.now();
    const oldest = now - 30 * 86400000;
    const span = now - oldest;
    // Inset stars away from the sky's outer edges so the 12px star body
    // + 26px glow shadow never get clipped at the left / right / top /
    // bottom of the container. 4% horizontal + 6% vertical safe area.
    const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
    return [...recentScans].reverse().map((s) => {
      const t = new Date(s.date).getTime();
      const clampedT = Math.max(oldest, Math.min(now, t));
      const xRaw = ((clampedT - oldest) / span) * 100;
      const yRaw = 100 - (s.severity_score || 0);
      const x = clamp(xRaw, 4, 96);  // %
      // Larger top safe-area (12 %) so dots near a perfect score (severity
      // near 0 → y near 0) sit ~40 px below the card edge on a 360 px sky.
      const y = clamp(yRaw, 12, 94); // %
      const brightness = 0.35 + (s.severity_score || 0) / 100 * 0.65;
      const color = s.severity === 'Severe'   ? '#fca5a5'
                  : s.severity === 'Moderate' ? '#fcd34d'
                  : '#86efac';
      return { ...s, x, y, brightness, color };
    });
  }, [recentScans]);

  if (!points.length) {
    return (
      <div className="constellation empty">
        <p>✨ Your scan constellation will appear once you start scanning.</p>
      </div>
    );
  }

  return (
    <div className="constellation">
      <p className="constellation-label">Skin Constellation · last 30 days</p>
      <div className="constellation-sky">
        {/* Faint static starfield */}
        {Array.from({ length: 22 }).map((_, i) => (
          <span
            key={i}
            className="constellation-bg-star"
            style={{
              left:  `${(i * 37) % 100}%`,
              top:   `${(i * 53) % 100}%`,
              animationDelay: `${i * 0.3}s`,
            }}
          />
        ))}

        {/* Connecting line */}
        <svg className="constellation-line" viewBox="0 0 100 100" preserveAspectRatio="none">
          <polyline
            points={points.map(p => `${p.x},${p.y}`).join(' ')}
            fill="none"
            stroke="rgba(165, 180, 252, 0.25)"
            strokeWidth="0.3"
            strokeDasharray="0.6 0.8"
          />
        </svg>

        {/* Stars */}
        {points.map((p, i) => (
          <button
            key={i}
            className="constellation-star"
            style={{
              left: `${p.x}%`,
              top:  `${p.y}%`,
              color: p.color,
              opacity: p.brightness,
              animationDelay: `${i * 0.15}s`,
            }}
            onMouseEnter={() => setHover(p)}
            onMouseLeave={() => setHover(null)}
            aria-label={`Scan from ${new Date(p.date).toLocaleDateString()}`}
          />
        ))}

        {hover && (
          <div
            className="constellation-tooltip"
            // Flip tooltip below the dot when the dot is in the top 30 %
            // of the sky (otherwise the tooltip would overflow above the
            // card and get clipped). Bottom 30 % and middle both use the
            // default "above" position. Inline transform overrides the
            // baseline rule in SkinConstellation.css.
            style={{
              left: `${hover.x}%`,
              top:  `${hover.y}%`,
              transform: hover.y < 30
                ? 'translate(-50%, 30%)'    // below dot
                : 'translate(-50%, -130%)', // above dot (default + bottom-30 case)
            }}
          >
            <strong>{new Date(hover.date).toLocaleDateString(undefined, { day: '2-digit', month: 'short' })}</strong>
            <span style={{ color: hover.color }}>{hover.severity}</span>
            <em>{hover.top_condition || hover.analysis_type}</em>
          </div>
        )}
      </div>
      <div className="constellation-legend">
        <span><i style={{ background: '#86efac' }}/> Mild</span>
        <span><i style={{ background: '#fcd34d' }}/> Moderate</span>
        <span><i style={{ background: '#fca5a5' }}/> Severe</span>
      </div>
    </div>
  );
}
