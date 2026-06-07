/**
 * ResetPassword — accepts uid + token from URL, posts new password.
 * Maps to backend /auth/reset-password/. (P2.)
 */
import { useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Lock, Eye, EyeOff, CheckCircle2 } from 'lucide-react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../api/config';
import './NotFound.css';

export default function ResetPassword() {
  const { uid, token } = useParams();
  const navigate = useNavigate();
  const [pw, setPw]               = useState('');
  const [pw2, setPw2]             = useState('');
  const [showPw, setShowPw]       = useState(false);
  const [submitting, setSubmit]   = useState(false);
  const [error, setError]         = useState('');
  const [done, setDone]           = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (pw !== pw2) { setError('Passwords do not match.'); return; }
    if (pw.length < 8) { setError('Password must be at least 8 characters.'); return; }
    setSubmit(true); setError('');
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.RESET_PASSWORD, {
        uid, token,
        password: pw,
        confirm_password: pw2,
      });
      setDone(true);
      setTimeout(() => navigate('/'), 2500);
    } catch (err) {
      setError(err.message || 'Reset failed — the link may have expired.');
    } finally {
      setSubmit(false);
    }
  };

  if (done) {
    return (
      <div className="nf-page">
        <div className="nf-card" style={{ maxWidth: 420 }}>
          <div className="nf-icon" style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981' }}>
            <CheckCircle2 size={28}/>
          </div>
          <h1 className="nf-title">Password reset</h1>
          <p className="nf-sub">Redirecting you to login…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="nf-page">
      <div className="nf-card" style={{ maxWidth: 440 }}>
        <div className="nf-icon" style={{ background: 'var(--blue-50)', color: 'var(--nav-accent)' }}>
          <Lock size={26}/>
        </div>
        <h1 className="nf-title">Set a new password</h1>
        <form onSubmit={onSubmit} style={{ textAlign: 'left' }}>
          <div className="form-group">
            <label htmlFor="rp-pw">New password</label>
            <div style={{ position: 'relative' }}>
              <input
                id="rp-pw"
                type={showPw ? 'text' : 'password'}
                value={pw}
                onChange={(e) => setPw(e.target.value)}
                className="input-field"
                style={{ paddingRight: '2.5rem' }}
                placeholder="Min 8 characters"
                required
                autoComplete="new-password"
                minLength={8}
              />
              <button
                type="button" onClick={() => setShowPw((s) => !s)}
                style={{
                  position: 'absolute', right: '0.75rem', top: '50%',
                  transform: 'translateY(-50%)', background: 'none', border: 'none',
                  color: 'var(--text-tertiary)', cursor: 'pointer',
                }}
                aria-label={showPw ? 'Hide password' : 'Show password'}
              >
                {showPw ? <EyeOff size={16}/> : <Eye size={16}/>}
              </button>
            </div>
          </div>
          <div className="form-group">
            <label htmlFor="rp-pw2">Confirm password</label>
            <input
              id="rp-pw2"
              type={showPw ? 'text' : 'password'}
              value={pw2}
              onChange={(e) => setPw2(e.target.value)}
              className="input-field"
              placeholder="Re-enter"
              required
              autoComplete="new-password"
            />
          </div>
          {error && (
            <div role="alert" aria-live="assertive" style={{
              background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: '0.75rem', padding: '0.6rem 0.85rem',
              color: '#ef4444', fontSize: '0.85rem', marginTop: '0.75rem', textAlign: 'center',
            }}>
              {error}
            </div>
          )}
          <div style={{ display: 'flex', gap: '0.6rem', marginTop: '1.2rem', justifyContent: 'center' }}>
            <Link to="/" className="btn btn-secondary">Cancel</Link>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Saving…' : 'Reset password'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
