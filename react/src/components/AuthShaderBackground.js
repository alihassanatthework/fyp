/**
 * AuthShaderBackground — Face + Body Particle Morph
 * ──────────────────────────────────────────────────
 * Cycle:
 *   Phase 0  "scatter"    Particles at random scatter positions.
 *   Phase 1  "assemble"   Each particle eases toward its target on a
 *                         pre-sampled face+body silhouette outline.
 *   Phase 2  "hold"       Silhouette breathes with a faint sway.
 *   Phase 3  "dissolve"   Each particle eases back to its scatter slot.
 *   → loops.
 *
 * Targets are sampled analytically from a head circle, neck box,
 * trapezoidal torso, and tapered legs — no model files. ~600 particles.
 *
 * Stack: raw Canvas 2D — same as the previous galaxy implementation.
 * No new libraries. Respects prefers-reduced-motion.
 */
import { useEffect, useRef } from 'react';
import './AuthShaderBackground.css';

const PARTICLE_COUNT = 620;

// Phase durations in seconds — total cycle ≈ 12 s.
const T_SCATTER   = 1.2;
const T_ASSEMBLE  = 3.5;
const T_HOLD      = 3.6;
const T_DISSOLVE  = 2.8;
const T_CYCLE     = T_SCATTER + T_ASSEMBLE + T_HOLD + T_DISSOLVE;

// Easing — cubic out for a satisfying snap to target.
const ease = (t) => 1 - Math.pow(1 - t, 3);

/**
 * Build a list of target points on a head+body silhouette, in a
 * canonical [-1, 1] coordinate space (x widens, y from +1 top to -1 bottom).
 * Points are distributed along outlines + interior fill so the silhouette
 * reads cleanly even at sparse density.
 */
function buildSilhouetteTargets(n) {
  const pts = [];

  // ── Anatomy in normalised "stick figure" coordinates ──
  // y axis: +1 top of head, -1 toes
  const HEAD_CY      =  0.70;
  const HEAD_R       =  0.16;
  const NECK_TOP     =  HEAD_CY - HEAD_R;            // ≈ 0.54
  const NECK_BOT     =  NECK_TOP - 0.05;             // ≈ 0.49
  const NECK_HALF    =  0.05;
  const SHOULDER_Y   =  NECK_BOT;                    // ≈ 0.49
  const SHOULDER_HALF=  0.32;
  const WAIST_Y      =  0.16;
  const WAIST_HALF   =  0.22;
  const HIP_Y        =  0.02;
  const HIP_HALF     =  0.26;
  const KNEE_Y       = -0.45;
  const KNEE_HALF_OUT=  0.18;
  const ANKLE_Y      = -0.92;
  const ANKLE_HALF_OUT= 0.16;
  const INSEAM_X     =  0.03;   // gap between the inner thigh edges

  // ── Head circle outline + a few interior dots ──
  const HEAD_OUTLINE = 70;
  for (let i = 0; i < HEAD_OUTLINE; i++) {
    const ang = (i / HEAD_OUTLINE) * Math.PI * 2;
    pts.push([Math.cos(ang) * HEAD_R, HEAD_CY + Math.sin(ang) * HEAD_R]);
  }
  // Sparse fill of the face — eyes, mouth area, cheeks.
  const HEAD_FILL = 60;
  for (let i = 0; i < HEAD_FILL; i++) {
    const r = Math.sqrt(Math.random()) * HEAD_R * 0.78;
    const a = Math.random() * Math.PI * 2;
    pts.push([Math.cos(a) * r, HEAD_CY + Math.sin(a) * r]);
  }

  // ── Neck (two short vertical edges) ──
  const NECK_PTS = 14;
  for (let i = 0; i < NECK_PTS; i++) {
    const t = i / (NECK_PTS - 1);
    const y = NECK_TOP - t * (NECK_TOP - NECK_BOT);
    pts.push([-NECK_HALF, y]);
    pts.push([ NECK_HALF, y]);
  }

  // ── Shoulders → arms (two curved tapers down to wrists) ──
  // Outer arm runs from shoulder out-tip down to wrist.
  const ARM_PTS = 60;
  for (let side of [-1, 1]) {
    for (let i = 0; i < ARM_PTS; i++) {
      const t = i / (ARM_PTS - 1);
      // Outer edge: shoulder tip → wrist (slightly outside hip line)
      const x = side * (SHOULDER_HALF - t * 0.05);     // arm hangs almost straight
      const y = SHOULDER_Y - t * (SHOULDER_Y - HIP_Y); // top to hip-ish height
      pts.push([x, y]);
    }
  }

  // ── Shoulder line (top of torso) ──
  const SHOULDER_PTS = 24;
  for (let i = 0; i < SHOULDER_PTS; i++) {
    const t = i / (SHOULDER_PTS - 1);
    pts.push([-SHOULDER_HALF + t * (SHOULDER_HALF * 2), SHOULDER_Y]);
  }

  // ── Torso outline (left + right curve from shoulder → waist → hip) ──
  const TORSO_PTS = 36;
  for (let i = 0; i < TORSO_PTS; i++) {
    const t = i / (TORSO_PTS - 1);
    // smooth interpolation through waist for natural body curve
    const y = SHOULDER_Y - t * (SHOULDER_Y - HIP_Y);
    let halfW;
    if (t < 0.5) {
      const s = t / 0.5;
      halfW = SHOULDER_HALF + (WAIST_HALF - SHOULDER_HALF) * s;
    } else {
      const s = (t - 0.5) / 0.5;
      halfW = WAIST_HALF + (HIP_HALF - WAIST_HALF) * s;
    }
    pts.push([-halfW, y]);
    pts.push([ halfW, y]);
  }

  // Torso interior fill — sparse so the body reads as solid not hollow.
  const TORSO_FILL = 80;
  for (let i = 0; i < TORSO_FILL; i++) {
    const t = Math.random();
    const y = SHOULDER_Y - t * (SHOULDER_Y - HIP_Y);
    let halfW;
    if (t < 0.5) {
      const s = t / 0.5;
      halfW = SHOULDER_HALF + (WAIST_HALF - SHOULDER_HALF) * s;
    } else {
      const s = (t - 0.5) / 0.5;
      halfW = WAIST_HALF + (HIP_HALF - WAIST_HALF) * s;
    }
    pts.push([(Math.random() * 2 - 1) * halfW * 0.85, y]);
  }

  // ── Two legs ──
  const LEG_PTS = 80;
  for (let side of [-1, 1]) {
    for (let i = 0; i < LEG_PTS; i++) {
      const t = i / (LEG_PTS - 1);
      const y = HIP_Y - t * (HIP_Y - ANKLE_Y);
      // outer edge: hip-out → knee-out → ankle-out
      const outerHalf =
        t < 0.5
          ? HIP_HALF + (KNEE_HALF_OUT - HIP_HALF) * (t / 0.5)
          : KNEE_HALF_OUT + (ANKLE_HALF_OUT - KNEE_HALF_OUT) * ((t - 0.5) / 0.5);
      // inner edge: stays close to center until ankles widen slightly
      const innerHalf =
        t < 0.5
          ? INSEAM_X + (KNEE_HALF_OUT * 0.30 - INSEAM_X) * (t / 0.5)
          : KNEE_HALF_OUT * 0.30 + (ANKLE_HALF_OUT * 0.55 - KNEE_HALF_OUT * 0.30) * ((t - 0.5) / 0.5);

      pts.push([side * outerHalf, y]);
      pts.push([side * innerHalf, y]);
    }
  }

  // Leg interior fill.
  const LEG_FILL = 90;
  for (let i = 0; i < LEG_FILL; i++) {
    const side = Math.random() < 0.5 ? -1 : 1;
    const t = Math.random();
    const y = HIP_Y - t * (HIP_Y - ANKLE_Y);
    const outerHalf =
      t < 0.5
        ? HIP_HALF + (KNEE_HALF_OUT - HIP_HALF) * (t / 0.5)
        : KNEE_HALF_OUT + (ANKLE_HALF_OUT - KNEE_HALF_OUT) * ((t - 0.5) / 0.5);
    pts.push([side * (INSEAM_X + Math.random() * (outerHalf - INSEAM_X) * 0.9), y]);
  }

  // If we have too many, sample down; too few, duplicate with jitter.
  if (pts.length === n) return pts;
  if (pts.length > n) {
    // even-stride sample
    const out = [];
    const step = pts.length / n;
    for (let i = 0; i < n; i++) out.push(pts[Math.floor(i * step)]);
    return out;
  }
  const out = pts.slice();
  while (out.length < n) {
    const p = pts[Math.floor(Math.random() * pts.length)];
    out.push([p[0] + (Math.random() - 0.5) * 0.01, p[1] + (Math.random() - 0.5) * 0.01]);
  }
  return out;
}

export default function AuthShaderBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    // Pre-compute targets once.
    const targets = buildSilhouetteTargets(PARTICLE_COUNT);

    // ── Dark-grey particle palette with occasional silver/white
    //    highlights. Same palette in light + dark mode (the wrapper
    //    background flips, but the particles themselves stay grey).
    //    Primary: slate-300 / 400 / 500 + bright highlight stars.
    const PALETTE = [
      '#94a3b8', '#94a3b8', '#94a3b8',  // slate-400 (most common)
      '#64748b', '#64748b',             // slate-500
      '#475569',                         // slate-600 (subtle)
    ];
    const HIGHLIGHTS = ['#e2e8f0', '#f1f5f9', '#ffffff'];
    const HIGHLIGHT_PROB = 0.12; // 12 % of particles glow silver/white

    const particles = targets.map(([tx, ty]) => {
      const isHighlight = Math.random() < HIGHLIGHT_PROB;
      const color = isHighlight
        ? HIGHLIGHTS[Math.floor(Math.random() * HIGHLIGHTS.length)]
        : PALETTE[Math.floor(Math.random() * PALETTE.length)];
      return {
        tx, ty,
        sx: (Math.random() - 0.5) * 2.4,
        sy: (Math.random() - 0.5) * 2.4,
        cx: 0, cy: 0,
        delay: Math.random() * 0.18,
        phase: Math.random() * Math.PI * 2,
        color,                    // fixed hex, no hue spin
        isHighlight,
      };
    });

    // Initialise current pos to scatter so frame 0 isn't a flash.
    particles.forEach((p) => { p.cx = p.sx; p.cy = p.sy; });

    let dpr = Math.min(window.devicePixelRatio || 1, 1.6);
    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 1.6);
      canvas.width  = window.innerWidth  * dpr;
      canvas.height = window.innerHeight * dpr;
    };
    resize();
    window.addEventListener('resize', resize);

    // Respect reduced-motion: render a single static frame at the
    // "hold" phase (silhouette fully formed) and skip the loop.
    const reduceMotion =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let raf;
    const start = performance.now();

    const draw = () => {
      const t = ((performance.now() - start) / 1000) % T_CYCLE;
      const W = canvas.width;
      const H = canvas.height;
      const cx = W / 2;
      const cy = H / 2;
      const scale = Math.min(W, H) * 0.42;

      // Motion-trail veil — dark cosmic.
      ctx.fillStyle = 'rgba(11, 18, 32, 0.22)';
      ctx.fillRect(0, 0, W, H);

      // Subtle global "breathing" sway during the hold phase.
      const swayX = Math.sin(t * 0.6) * 0.012;
      const swayY = Math.cos(t * 0.5) * 0.008;

      for (const p of particles) {
        // Resolve which phase we're in (with per-particle delay).
        const tt = Math.max(0, t - p.delay * T_CYCLE);
        let nx, ny;
        if (reduceMotion) {
          // Static: hold the silhouette.
          nx = p.tx + swayX;
          ny = p.ty + swayY;
        } else if (tt < T_SCATTER) {
          // Phase 0: scattered — slow drift around scatter point.
          const drift = Math.sin(t + p.phase) * 0.015;
          nx = p.sx + drift;
          ny = p.sy + Math.cos(t * 1.1 + p.phase) * 0.015;
        } else if (tt < T_SCATTER + T_ASSEMBLE) {
          // Phase 1: assemble.
          const k = ease((tt - T_SCATTER) / T_ASSEMBLE);
          nx = p.sx + (p.tx - p.sx) * k;
          ny = p.sy + (p.ty - p.sy) * k;
        } else if (tt < T_SCATTER + T_ASSEMBLE + T_HOLD) {
          // Phase 2: hold + breathe.
          nx = p.tx + swayX;
          ny = p.ty + swayY;
        } else {
          // Phase 3: dissolve.
          const k = ease((tt - T_SCATTER - T_ASSEMBLE - T_HOLD) / T_DISSOLVE);
          nx = p.tx + (p.sx - p.tx) * k + swayX * (1 - k);
          ny = p.ty + (p.sy - p.ty) * k + swayY * (1 - k);
        }

        // Project to screen — flip Y so silhouette stands upright.
        const sx = cx + nx * scale;
        const sy = cy - ny * scale;
        p.cx = sx; p.cy = sy;

        // Brightness peaks during hold, dims at scatter.
        let alpha = 0.55;
        if (!reduceMotion) {
          if (tt < T_SCATTER)                                            alpha = 0.30;
          else if (tt < T_SCATTER + T_ASSEMBLE)                          alpha = 0.30 + 0.55 * ease((tt - T_SCATTER) / T_ASSEMBLE);
          else if (tt < T_SCATTER + T_ASSEMBLE + T_HOLD)                 alpha = 0.85 + 0.08 * Math.sin(t * 2 + p.phase);
          else                                                            alpha = 0.85 * (1 - ease((tt - T_SCATTER - T_ASSEMBLE - T_HOLD) / T_DISSOLVE)) + 0.20;
        }

        // Highlight particles glow a touch bigger + brighter than the
        // common slate ones so the silhouette has visible "stars" in it.
        const size = (p.isHighlight ? 1.55 : 1.15) + Math.sin(t * 1.7 + p.phase) * 0.4;
        ctx.globalAlpha = alpha;
        ctx.fillStyle   = p.color;
        ctx.shadowBlur  = (p.isHighlight ? 12 : 6) * dpr;
        ctx.shadowColor = p.color;
        ctx.beginPath();
        ctx.arc(sx, sy, size * dpr, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;

      // ── Faint connective lines along the silhouette during hold ──
      // Connect each particle to its nearest neighbour within a radius
      // ONLY during the hold phase so the shape feels articulated.
      if (!reduceMotion) {
        const ttGlobal = t;
        const inHold = ttGlobal > T_SCATTER + T_ASSEMBLE * 0.8 &&
                       ttGlobal < T_SCATTER + T_ASSEMBLE + T_HOLD + T_DISSOLVE * 0.4;
        if (inHold) {
          ctx.lineWidth = 1 * dpr;
          const R = 28 * dpr;
          const R2 = R * R;
          for (let i = 0; i < particles.length; i += 2) {
            const a = particles[i];
            let bestJ = -1, bestD2 = R2;
            // sample a small subset of neighbours rather than O(n²) full pass
            for (let off = 1; off <= 6; off++) {
              const j = (i + off) % particles.length;
              const b = particles[j];
              const d2 = (a.cx - b.cx) ** 2 + (a.cy - b.cy) ** 2;
              if (d2 < bestD2) { bestD2 = d2; bestJ = j; }
            }
            if (bestJ !== -1) {
              const k = 1 - Math.sqrt(bestD2) / R;
              // Connective lines: #2a2a2a at distance-scaled alpha.
              ctx.strokeStyle = `rgba(42, 42, 42, ${k * 0.42})`;
              ctx.beginPath();
              ctx.moveTo(a.cx, a.cy);
              ctx.lineTo(particles[bestJ].cx, particles[bestJ].cy);
              ctx.stroke();
            }
          }
        }
      }

      if (!reduceMotion) raf = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      if (raf) cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <div className="auth-shader-wrap" aria-hidden="true">
      <canvas ref={canvasRef} className="auth-shader-canvas"/>
    </div>
  );
}
