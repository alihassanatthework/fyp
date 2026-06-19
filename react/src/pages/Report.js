import { Flag } from 'lucide-react';
import { useState } from 'react';
import StaticPage from '../components/StaticPage';
import apiClient from '../api/client';

export default function Report() {
  const [submitted, setSubmitted] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({ category: 'bug', email: '', message: '' });

  const OFFICIAL_EMAIL = 'me.offical.team.system@gmail.com';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSending(true);
    setError('');
    try {
      // Send server-side — the backend emails the official ME inbox directly.
      await apiClient.post('/report/', {
        category: form.category,
        email: form.email,
        message: form.message,
      });
      setSubmitted(true);
    } catch (err) {
      setError(
        err?.response?.data?.error ||
        `Could not send right now. Please email us at ${OFFICIAL_EMAIL}.`
      );
    } finally {
      setSending(false);
    }
  };

  return (
    <StaticPage
      title="Report an Issue"
      subtitle="Tell us about a bug, inappropriate result, or safety concern."
      icon={<Flag size={20} />}
    >
      {submitted ? (
        <>
          <h2>Report sent ✓</h2>
          <p style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.35)',
                       borderRadius: '0.75rem', padding: '0.75rem 1rem', margin: '0.75rem 0' }}>
            Thanks — your report was delivered to the ME team. We'll review it and get
            back to you{form.email ? ` at ${form.email}` : ''} if a reply is needed.
          </p>
          <button className="btn btn-primary" onClick={() => { setSubmitted(false); setForm({ category: 'bug', email: '', message: '' }); }}>
            Submit another
          </button>
        </>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label className="profile-field-label" htmlFor="rpt-cat">Category</label>
            <select
              id="rpt-cat"
              className="input-field"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
            >
              <option value="bug">Bug / technical issue</option>
              <option value="result">Inaccurate analysis result</option>
              <option value="safety">Safety or content concern</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div>
            <label className="profile-field-label" htmlFor="rpt-email">Your email (optional)</label>
            <input
              id="rpt-email"
              type="email"
              className="input-field"
              placeholder="you@example.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>

          <div>
            <label className="profile-field-label" htmlFor="rpt-msg">Description</label>
            <textarea
              id="rpt-msg"
              className="input-field"
              rows={5}
              required
              placeholder="What happened? Steps to reproduce, screenshots, anything that helps us investigate."
              value={form.message}
              onChange={(e) => setForm({ ...form, message: e.target.value })}
            />
          </div>

          {error && (
            <p style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.3)',
                         borderRadius: '0.75rem', padding: '0.6rem 0.9rem', margin: 0, color: '#ef4444', fontSize: '0.85rem' }}>
              {error}
            </p>
          )}
          <button type="submit" className="btn btn-primary" disabled={sending} style={{ alignSelf: 'flex-start' }}>
            {sending ? 'Sending…' : 'Submit report'}
          </button>
        </form>
      )}
    </StaticPage>
  );
}
