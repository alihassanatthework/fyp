/**
 * ForgotPassword — collects email, POSTs to /auth/forgot-password/.
 * Always shows the same success message so attackers can't enumerate
 * registered emails. (P2.)
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, ArrowLeft } from 'lucide-react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../api/config';
import './NotFound.css';

export default function ForgotPassword() {
  const [email, setEmail]       = useState('');
  const [submitting, setSubmit] = useState(false);
  const [done, setDone]         = useState(false);
  const [error, setError]       = useState('');

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!email) return;
    setSubmit(true); setError('');
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.FORGOT_PASSWORD, { email });
      setDone(true);
    } catch (err) {
      setError(err.message || 'Could not send reset link. Please try again.');
    } finally {
      setSubmit(false);
    }
  };

  return (
    <div className="nf-page">
      <div className="nf-card" style={{ maxWidth: 440 }}>
        <div className="nf-icon" style={{ background: 'var(--blue-50)', color: 'var(--nav-accent)' }}>
          <Mail size={26}/>
        </div>
        <h1 className="nf-title">Reset your password</h1>
        {done ? (
          <>
            <p className="nf-sub">
              If an account with <strong>{email}</strong> exists, we've sent a reset link.
              Check your inbox — the link expires in 1 hour.
            </p>
            <Link to="/" className="btn btn-secondary">
              <ArrowLeft size={14}/> Back to login
            </Link>
          </>
        ) : (
          <form onSubmit={onSubmit} style={{ textAlign: 'left' }}>
            <p className="nf-sub" style={{ textAlign: 'center' }}>
              Enter your email address. We'll send you a link to set a new password.
            </p>
            <div className="form-group">
              <label htmlFor="fp-email">Email address</label>
              <input
                id="fp-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="input-field"
                required
                autoComplete="email"
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
              <Link to="/" className="btn btn-secondary">
                <ArrowLeft size={14}/> Cancel
              </Link>
              <button type="submit" className="btn btn-primary" disabled={submitting || !email}>
                {submitting ? 'Sending…' : 'Send reset link'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
