/**
 * SkinTwin
 * ────────
 * Anatomical SVG face with glowing zones whose intensity comes from
 * detected condition counts. Pure SVG — no Three.js dependency, ~5 KB
 * bundle cost, looks great in both themes.
 *
 * Map: each known condition maps to one or more facial zones. The zones
 * we currently model are: forehead, leftCheek, rightCheek, nose, chin.
 * For scalp analyses the scalp zone above the face glows instead.
 */
import './SkinTwin.css';

const ZONE_MAP = {
  acne:        ['forehead', 'leftCheek', 'rightCheek', 'chin'],
  pimples:     ['forehead', 'leftCheek', 'rightCheek', 'chin'],
  dark_spots:  ['leftCheek', 'rightCheek', 'forehead'],
  pigmentation:['leftCheek', 'rightCheek'],
  dryness:     ['forehead', 'chin'],
  redness:     ['leftCheek', 'rightCheek', 'nose'],
  oiliness:    ['forehead', 'nose'],
  blackheads:  ['nose', 'forehead'],
  // scalp side
  dandruff:    ['scalp'],
  flakes:      ['scalp'],
  density:     ['scalp'],
};

const ZONE_COLOR = {
  forehead:   '#f59e0b',
  leftCheek:  '#ec4899',
  rightCheek: '#ec4899',
  nose:       '#ef4444',
  chin:       '#a855f7',
  scalp:      '#6366f1',
};

function zoneIntensities(recurring) {
  // recurring: [{name, count}, ...]
  const out = { forehead: 0, leftCheek: 0, rightCheek: 0, nose: 0, chin: 0, scalp: 0 };
  if (!Array.isArray(recurring)) return out;
  recurring.forEach(({ name, count }) => {
    const key = String(name || '').toLowerCase().replace(/\s+/g, '_');
    const zones = ZONE_MAP[key];
    if (!zones) return;
    zones.forEach(z => { out[z] += count; });
  });
  // Normalise to 0..1
  const max = Math.max(1, ...Object.values(out));
  Object.keys(out).forEach(k => { out[k] = out[k] / max; });
  return out;
}

export default function SkinTwin({ recurringConditions = [], healthScore = 70, onZoneClick }) {
  const z = zoneIntensities(recurringConditions);

  const glow = (zone) => {
    const v = z[zone] || 0;
    if (v === 0) return { opacity: 0.08, color: ZONE_COLOR[zone] };
    return {
      opacity: 0.25 + v * 0.55,
      color:   ZONE_COLOR[zone],
    };
  };

  const skinFill = healthScore >= 80 ? '#fde7d4'
                 : healthScore >= 60 ? '#fcd9bd'
                 : healthScore >= 40 ? '#f8c7a3'
                 : '#f3b187';

  return (
    <div className="skin-twin">
      <p className="skin-twin-label">Digital Skin Twin</p>
      <div className="skin-twin-canvas">
        <svg viewBox="0 0 220 280" className="skin-twin-svg">
          {/* Soft halo */}
          <defs>
            <radialGradient id="twinHalo" cx="50%" cy="45%" r="60%">
              <stop offset="0%"   stopColor="#a5b4fc" stopOpacity="0.55"/>
              <stop offset="100%" stopColor="#a5b4fc" stopOpacity="0"/>
            </radialGradient>
            {Object.keys(ZONE_COLOR).map(zone => {
              const g = glow(zone);
              return (
                <radialGradient key={zone} id={`twin-glow-${zone}`} cx="50%" cy="50%" r="50%">
                  <stop offset="0%"   stopColor={g.color} stopOpacity={g.opacity}/>
                  <stop offset="100%" stopColor={g.color} stopOpacity="0"/>
                </radialGradient>
              );
            })}
          </defs>

          <circle cx="110" cy="125" r="120" fill="url(#twinHalo)"/>

          {/* Scalp / hair line */}
          <path
            d="M 50 80 Q 60 30 110 28 Q 160 30 170 80 L 170 95 Q 110 70 50 95 Z"
            fill="#1f2937"
            opacity="0.75"
          />
          <ellipse cx="110" cy="72" rx="60" ry="22" fill="url(#twin-glow-scalp)"
            onClick={() => onZoneClick?.('scalp')} className="skin-twin-zone"/>

          {/* Face shape */}
          <path
            d="M 60 110
               Q 60 80 110 78
               Q 160 80 160 110
               L 158 175
               Q 150 215 110 222
               Q 70 215 62 175 Z"
            fill={skinFill}
            stroke="rgba(0,0,0,0.10)"
            strokeWidth="1"
          />

          {/* Glow zones — soft radial gradients */}
          <ellipse cx="110" cy="108" rx="38" ry="14" fill="url(#twin-glow-forehead)"
            onClick={() => onZoneClick?.('forehead')} className="skin-twin-zone"/>
          <ellipse cx="82"  cy="150" rx="20" ry="16" fill="url(#twin-glow-leftCheek)"
            onClick={() => onZoneClick?.('leftCheek')} className="skin-twin-zone"/>
          <ellipse cx="138" cy="150" rx="20" ry="16" fill="url(#twin-glow-rightCheek)"
            onClick={() => onZoneClick?.('rightCheek')} className="skin-twin-zone"/>
          <ellipse cx="110" cy="148" rx="9"  ry="22" fill="url(#twin-glow-nose)"
            onClick={() => onZoneClick?.('nose')} className="skin-twin-zone"/>
          <ellipse cx="110" cy="200" rx="22" ry="14" fill="url(#twin-glow-chin)"
            onClick={() => onZoneClick?.('chin')} className="skin-twin-zone"/>

          {/* Eyes */}
          <ellipse cx="85"  cy="135" rx="6" ry="3" fill="#1f2937"/>
          <ellipse cx="135" cy="135" rx="6" ry="3" fill="#1f2937"/>

          {/* Subtle brows */}
          <rect x="75"  y="124" width="22" height="2" rx="1" fill="#1f2937" opacity="0.8"/>
          <rect x="123" y="124" width="22" height="2" rx="1" fill="#1f2937" opacity="0.8"/>

          {/* Mouth */}
          <path d="M 95 185 Q 110 195 125 185" stroke="#7f1d1d" strokeWidth="2"
            fill="none" strokeLinecap="round"/>

          {/* Pulsing dots for the top recurring zones */}
          {Object.entries(z).filter(([,v]) => v > 0.4).map(([zone]) => {
            const pos = {
              forehead:   [110, 108],
              leftCheek:  [82,  150],
              rightCheek: [138, 150],
              nose:       [110, 148],
              chin:       [110, 200],
              scalp:      [110, 72],
            }[zone];
            return (
              <circle key={zone} cx={pos[0]} cy={pos[1]} r="4"
                fill={ZONE_COLOR[zone]} className="skin-twin-pulse"/>
            );
          })}
        </svg>
      </div>
      <p className="skin-twin-hint">Tap a glowing zone to drill in</p>
    </div>
  );
}
