/**
 * MirrorMode
 * ──────────
 * Opens a full-screen modal with the user's webcam feed, mirrored.
 * Overlays animated heatmap dots on the facial zones most often flagged
 * by past scans (from recurring_conditions). Tapping a hotspot sends the
 * user into the new-scan flow pre-typed for that zone.
 *
 * Pure browser APIs — getUserMedia + canvas. No external face detection
 * library bundled; the dots are positioned using the same anatomical map
 * as SkinTwin since the user is facing the camera and centered.
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, X, ScanLine, AlertCircle, UploadCloud, ExternalLink } from 'lucide-react';
import './MirrorMode.css';

/**
 * Browser camera availability check.
 * mediaDevices is undefined on insecure origins (http://) for every modern
 * mobile browser — Chrome Android, Safari iOS, Samsung Internet. Localhost
 * is treated as secure by browsers, so dev still works there.
 */
function getCameraBlocker() {
  if (typeof navigator === 'undefined') return 'no-navigator';
  if (typeof window !== 'undefined' && window.isSecureContext === false) {
    return 'insecure-origin';
  }
  if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== 'function') {
    return 'no-api';
  }
  return null;
}

// Zone positions as percentages of the video element
const ZONES = [
  { id: 'forehead',   x: 50, y: 22, color: '#f59e0b', label: 'Forehead'   },
  { id: 'leftCheek',  x: 30, y: 55, color: '#ec4899', label: 'Left cheek'  },
  { id: 'rightCheek', x: 70, y: 55, color: '#ec4899', label: 'Right cheek' },
  { id: 'nose',       x: 50, y: 50, color: '#ef4444', label: 'Nose'       },
  { id: 'chin',       x: 50, y: 78, color: '#a855f7', label: 'Chin'       },
];

export default function MirrorMode({ open, onClose, recurringConditions = [] }) {
  const navigate = useNavigate();
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setError('');
    setReady(false);

    // ── Guard: bail BEFORE touching navigator.mediaDevices when it's
    // undefined (HTTP origin on mobile). Show the fallback UI instead
    // of throwing an uncaught reference error.
    const blocker = getCameraBlocker();
    if (blocker) {
      setError(
        blocker === 'insecure-origin' || blocker === 'no-api'
          ? 'Camera requires HTTPS or localhost. Open the app via https:// — or upload a photo instead.'
          : 'Camera not available in this browser. Try uploading a photo instead.'
      );
      return;
    }

    // Wrap in try/catch so synchronous failures in getUserMedia (rare,
    // but possible on stricter mobile browsers) are caught too.
    try {
      navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: 1280, height: 720 },
        audio: false,
      }).then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach(t => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadedmetadata = () => setReady(true);
        }
      }).catch((err) => {
        if (cancelled) return;
        const map = {
          NotAllowedError:     'Camera access denied. Allow camera permission and try again.',
          NotFoundError:       'No camera found on this device.',
          NotReadableError:    'Camera is in use by another app. Close it and retry.',
          OverconstrainedError:'Your camera does not support the requested settings.',
          SecurityError:       'Camera requires HTTPS or localhost.',
          AbortError:          'Camera start was interrupted. Please retry.',
        };
        setError(map[err.name] || `Could not start camera: ${err.message || err.name || 'unknown error'}.`);
      });
    } catch (err) {
      if (!cancelled) {
        setError(`Could not start camera: ${err?.message || 'unexpected error'}.`);
      }
    }

    return () => {
      cancelled = true;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
        streamRef.current = null;
      }
      setReady(false);
    };
  }, [open]);

  if (!open) return null;

  // Pull a "heat" value for each zone from recurringConditions
  const zoneHeat = (zone) => {
    if (!Array.isArray(recurringConditions)) return 0;
    const sum = recurringConditions.reduce((acc, c) => {
      const name = String(c.name || '').toLowerCase();
      const match = (name.includes('acne')        && ['forehead','leftCheek','rightCheek','chin'].includes(zone)) ||
                    (name.includes('dark')        && ['leftCheek','rightCheek','forehead'].includes(zone))        ||
                    (name.includes('dry')         && ['forehead','chin'].includes(zone))                          ||
                    (name.includes('red')         && ['leftCheek','rightCheek','nose'].includes(zone))            ||
                    (name.includes('oil')         && ['forehead','nose'].includes(zone))                          ||
                    (name.includes('blackhead')   && ['nose','forehead'].includes(zone));
      return acc + (match ? c.count : 0);
    }, 0);
    return Math.min(1, sum / 5);
  };

  return (
    <div className="mirror-overlay" onClick={onClose}>
      <div className="mirror-shell" onClick={(e) => e.stopPropagation()}>
        <div className="mirror-header">
          <span><Camera size={14}/> AI Mirror Mode</span>
          <button className="mirror-close" onClick={onClose}><X size={18}/></button>
        </div>

        <div className="mirror-stage">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="mirror-video"
          />

          {/* Scan line */}
          {ready && !error && <div className="mirror-scanline" aria-hidden="true"/>}

          {/* Hotspot dots */}
          {ready && !error && ZONES.map((z) => {
            const heat = zoneHeat(z.id);
            return (
              <button
                key={z.id}
                className="mirror-hotspot"
                style={{
                  left:  `${z.x}%`,
                  top:   `${z.y}%`,
                  color: z.color,
                  opacity: 0.5 + heat * 0.5,
                  transform: `translate(-50%, -50%) scale(${1 + heat * 0.5})`,
                }}
                title={`${z.label}${heat > 0 ? ' — frequently flagged' : ''}`}
                onClick={() => {
                  onClose();
                  navigate('/analysis?type=skin');
                }}
              />
            );
          })}

          {error && (
            <div className="mirror-error" role="alert" aria-live="assertive">
              <AlertCircle size={22} aria-hidden="true"/>
              <p>{error}</p>
              <div className="mirror-error-actions">
                <button
                  type="button"
                  className="mirror-error-btn primary"
                  onClick={() => { onClose(); navigate('/analysis'); }}
                >
                  <UploadCloud size={14} aria-hidden="true"/> Upload a photo instead
                </button>
                {typeof window !== 'undefined' && window.location.protocol === 'http:' && (
                  <a
                    className="mirror-error-btn"
                    href={`https://${window.location.host}${window.location.pathname}`}
                    rel="noreferrer"
                  >
                    <ExternalLink size={14} aria-hidden="true"/> Open over HTTPS
                  </a>
                )}
              </div>
            </div>
          )}
          {!ready && !error && (
            <div className="mirror-loading">
              <p>Starting camera…</p>
            </div>
          )}
        </div>

        <div className="mirror-footer">
          <p className="mirror-tip">
            <ScanLine size={12}/> Glowing dots show where past scans flagged conditions most often.
          </p>
          <button className="mirror-cta" onClick={() => { onClose(); navigate('/analysis'); }}>
            Run a real scan
          </button>
        </div>
      </div>
    </div>
  );
}
