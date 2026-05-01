import { FileText } from 'lucide-react';
import StaticPage from '../components/StaticPage';

export default function Terms() {
  return (
    <StaticPage
      title="Terms & Conditions"
      subtitle="Last updated: placeholder date."
      icon={<FileText size={20} />}
    >
      <h2>1. Acceptance of Terms</h2>
      <p>
        By creating an account or using ME, you agree to these placeholder
        Terms &amp; Conditions. (Replace this entire document with reviewed legal copy
        before production launch.)
      </p>

      <h2>2. Use of Service</h2>
      <p>
        ME provides AI-assisted skin and scalp analysis for informational purposes
        only. Results do not constitute medical advice and should not replace
        consultation with a qualified clinician.
      </p>

      <h2>3. User Content</h2>
      <p>
        You retain ownership of images you upload. By uploading, you grant ME a
        limited licence to process those images solely for the purpose of generating
        your personalised analysis.
      </p>

      <h2>4. Account Responsibility</h2>
      <p>
        You are responsible for keeping your credentials secure and for all activity
        under your account.
      </p>

      <h2>5. Limitation of Liability</h2>
      <p>
        ME is provided "as is" without warranty. We are not liable for any decisions
        made on the basis of analysis output.
      </p>

      <h2>6. Changes</h2>
      <p>
        We may update these terms. Material changes will be communicated to you via
        the app or email.
      </p>

      <p style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>
        (Placeholder content — not legal advice. Replace before launch.)
      </p>
    </StaticPage>
  );
}
