/**
 * AuroraBackground
 * ────────────────
 * Ambient gradient that fills the page background. Hues are LOCKED to
 * the site's signature indigo → purple → pink palette (same colours as
 * --btn-primary-bg) so the dashboard never clashes with the rest of the
 * app. Only the intensity adjusts: brighter when the user's health is
 * high, calmer (and slightly cooler) when it's low.
 *
 * Pure CSS — no JS hot loops.
 */
import './AuroraBackground.css';

// Indigo (240°), violet (270°), magenta-pink (320°) — same family as
// `linear-gradient(135deg, #4f46e5, #7c3aed, #db2777)` used by btn-primary.
const SITE_HUES = { h1: 240, h2: 275, h3: 320 };

export default function AuroraBackground({ score = 70 }) {
  // Intensity ramps gently with score — high score → more luminous;
  // low score → calmer, more recessed. Hue NEVER changes.
  const intensity = Math.max(0.5, Math.min(1, 0.6 + (score / 100) * 0.4));
  return (
    <div
      className="aurora-bg"
      style={{
        '--aurora-h1': SITE_HUES.h1,
        '--aurora-h2': SITE_HUES.h2,
        '--aurora-h3': SITE_HUES.h3,
        '--aurora-intensity': intensity,
      }}
      aria-hidden="true"
    >
      <div className="aurora-blob aurora-blob-1" />
      <div className="aurora-blob aurora-blob-2" />
      <div className="aurora-blob aurora-blob-3" />
    </div>
  );
}
