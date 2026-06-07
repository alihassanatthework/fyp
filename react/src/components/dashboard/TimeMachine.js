/**
 * TimeMachine
 * ───────────
 * Drag a slider through your scan history. The thumbnail, condition,
 * severity ring and date all swap in real time as you scrub. Drives
 * "watch yourself heal" narrative on the dashboard.
 *
 * Data source: stats.recent_scans (ordered newest-first by backend).
 * We reverse here so the slider goes left=oldest → right=newest, which
 * matches everyone's mental model of time.
 */
import { useState, useMemo } from 'react';
import { Clock, ArrowLeft, ArrowRight, FileText } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { analysisService } from '../../services/analysisService';
import './TimeMachine.css';

export default function TimeMachine({ recentScans = [] }) {
  const navigate = useNavigate();
  // Reverse so the slider reads oldest → newest left → right.
  const scans = useMemo(() => [...recentScans].reverse(), [recentScans]);
  const [idx, setIdx] = useState(Math.max(0, scans.length - 1));
  const [opening, setOpening] = useState(false);

  if (!scans.length) {
    return (
      <div className="time-machine empty">
        <Clock size={24} />
        <p>Run a few scans to unlock the Time Machine.</p>
      </div>
    );
  }

  const scan = scans[idx];
  const date = new Date(scan.date);
  const dateLabel = date.toLocaleDateString(undefined, {
    day: '2-digit', month: 'short', year: 'numeric',
  });

  const severityColor = scan.severity === 'Severe' ? '#ef4444'
                       : scan.severity === 'Moderate' ? '#f59e0b'
                       : '#10b981';

  const openReport = async () => {
    if (!scan.analysis_id) return;
    try {
      setOpening(true);
      const full = await analysisService.getAnalysisById(scan.analysis_id);
      navigate('/diagnosis', { state: { data: full } });
    } catch {
      navigate('/diagnosis', { state: { data: scan } });
    } finally {
      setOpening(false);
    }
  };

  return (
    <div className="time-machine">
      <div className="time-machine-header">
        <span className="time-machine-label">
          <Clock size={13}/> Time Machine
        </span>
        <span className="time-machine-counter">
          Scan {idx + 1} of {scans.length}
        </span>
      </div>

      <div className="time-machine-card">
        <div className="time-machine-thumb-wrap">
          {scan.thumbnail ? (
            <img src={scan.thumbnail} alt="" className="time-machine-thumb" />
          ) : (
            <div className="time-machine-thumb time-machine-thumb-fallback">
              {(scan.analysis_type || 'S').slice(0,1).toUpperCase()}
            </div>
          )}
          <div
            className="time-machine-ring"
            style={{
              background: `conic-gradient(${severityColor} ${scan.severity_score * 3.6}deg, rgba(255,255,255,0.12) 0deg)`,
            }}
          />
        </div>
        <div className="time-machine-meta">
          <p className="time-machine-date">{dateLabel}</p>
          <p className="time-machine-condition">{scan.top_condition || scan.analysis_type}</p>
          <span className="time-machine-badge" style={{ background: severityColor }}>
            {scan.severity} · {scan.severity_score}/100
          </span>
        </div>
      </div>

      <div className="time-machine-controls">
        <button
          className="time-machine-arrow"
          onClick={() => setIdx(i => Math.max(0, i - 1))}
          disabled={idx === 0}
          aria-label="Older"
        ><ArrowLeft size={14} aria-hidden="true"/></button>
        <input
          type="range"
          min="0"
          max={scans.length - 1}
          value={idx}
          onChange={(e) => setIdx(Number(e.target.value))}
          className="time-machine-slider"
          aria-label="Scrub through scan history"
        />
        <button
          className="time-machine-arrow"
          onClick={() => setIdx(i => Math.min(scans.length - 1, i + 1))}
          disabled={idx === scans.length - 1}
          aria-label="Newer"
        ><ArrowRight size={14} aria-hidden="true"/></button>
      </div>

      <button className="time-machine-open" onClick={openReport} disabled={opening}>
        <FileText size={13}/> {opening ? 'Loading…' : 'Open this report'}
      </button>
    </div>
  );
}
