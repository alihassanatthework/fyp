import { Flag } from 'lucide-react';
import { useState } from 'react';
import StaticPage from '../components/StaticPage';

export default function Report() {
  const [submitted, setSubmitted] = useState(false);
  const [form, setForm] = useState({ category: 'bug', email: '', message: '' });

  const handleSubmit = (e) => {
    e.preventDefault();
    // Backend reporting endpoint not yet implemented — flag this clearly
    // instead of pretending the message was received.
    setSubmitted(true);
  };

  return (
    <StaticPage
      title="Report an Issue"
      subtitle="Tell us about a bug, inappropriate result, or safety concern."
      icon={<Flag size={20} />}
    >
      {submitted ? (
        <>
          <h2>Report system not yet active</h2>
          <p style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.35)',
                       borderRadius: '0.75rem', padding: '0.75rem 1rem', margin: '0.75rem 0' }}>
            Our reporting endpoint isn't connected yet. Your message wasn't sent.
            Please email <a href="mailto:contact@meapp.placeholder.com">contact@meapp.placeholder.com</a>
            for now.
          </p>
          <button className="btn btn-primary" onClick={() => { setSubmitted(false); setForm({ category: 'bug', email: '', message: '' }); }}>
            Try again
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

          <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start' }}>
            Submit report
          </button>
        </form>
      )}
    </StaticPage>
  );
}
