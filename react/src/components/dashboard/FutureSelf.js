/**
 * FutureSelf
 * ──────────
 * Card showing current vs predicted health score using the backend's
 * linear-regression `projection_30d`. The dashed line in the mini-chart
 * is the projection trajectory.
 */
import { AreaChart, Area, ResponsiveContainer, ReferenceLine } from 'recharts';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import './FutureSelf.css';

export default function FutureSelf({ stats }) {
  const current   = stats?.health_score ?? 70;
  const projected = stats?.projection_30d ?? current;
  const delta     = projected - current;

  // Build a 60-pt timeline: 30 historical + 30 projected (linear interp).
  const hist = (stats?.daily_timeline || []).map(d => d.score);
  // Carry-forward gaps so the area chart doesn't dip to 0.
  let last = current;
  const filledHist = hist.map(v => {
    if (v !== null && v !== undefined) { last = v; return v; }
    return last;
  });
  const data = [
    ...filledHist.map((v, i) => ({ x: i, hist: v, future: null })),
    ...Array.from({ length: 30 }, (_, i) => ({
      x: filledHist.length + i,
      hist: i === 0 ? filledHist[filledHist.length - 1] : null,
      future: current + ((projected - current) * (i + 1) / 30),
    })),
  ];

  const TrendIcon = delta > 2 ? TrendingUp : delta < -2 ? TrendingDown : Minus;
  const trendLabel = delta > 2 ? 'Improving'
                   : delta < -2 ? 'Declining' : 'Stable';
  const trendColor = delta > 2 ? '#10b981' : delta < -2 ? '#ef4444' : '#94a3b8';

  return (
    <div className="future-self">
      <p className="future-self-label">Predictive Future Self</p>
      <div className="future-self-numbers">
        <div className="future-self-now">
          <span className="future-self-num">{current}</span>
          <span className="future-self-sub">today</span>
        </div>
        <div className="future-self-arrow" style={{ color: trendColor }}>
          <TrendIcon size={20}/>
        </div>
        <div className="future-self-future">
          <span className="future-self-num">{projected}</span>
          <span className="future-self-sub">in 30 days</span>
        </div>
      </div>

      <div className="future-self-chart">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="fsHist" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"  stopColor="#6366f1" stopOpacity={0.65}/>
                <stop offset="100%" stopColor="#6366f1" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="fsFuture" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"  stopColor={trendColor} stopOpacity={0.55}/>
                <stop offset="100%" stopColor={trendColor} stopOpacity={0}/>
              </linearGradient>
            </defs>
            <Area type="monotone" dataKey="hist"   stroke="#6366f1" strokeWidth={1.8}
                  fill="url(#fsHist)" isAnimationActive={false}/>
            <Area type="monotone" dataKey="future" stroke={trendColor} strokeWidth={1.8}
                  strokeDasharray="4 3" fill="url(#fsFuture)" isAnimationActive={false}/>
            <ReferenceLine x={filledHist.length - 0.5} stroke="rgba(255,255,255,0.18)" strokeDasharray="2 2"/>
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <p className="future-self-caption" style={{ color: trendColor }}>
        <TrendIcon size={12}/> {trendLabel} · projection based on linear regression of your last 30 days
      </p>
    </div>
  );
}
