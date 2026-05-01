import { CheckSquare } from 'lucide-react';
import StaticPage from '../components/StaticPage';

export default function Consent() {
  return (
    <StaticPage
      title="Consent Form"
      subtitle="What you agree to when using ME."
      icon={<CheckSquare size={20} />}
    >
      <h2>Consent to image processing</h2>
      <p>
        By uploading face or scalp images you consent to AI-based analysis on the
        terms below. You may revoke consent at any time from your profile.
      </p>

      <h2>What happens to your image</h2>
      <ul>
        <li>The image is processed to generate de-identified binary masks used by our LLM and detection models.</li>
        <li>Raw images are retained only for the duration required to complete your analysis.</li>
        <li>No image is shared with any third party — advertisers, insurers, partners, or model providers.</li>
        <li>Processing happens exclusively on ME's isolated infrastructure.</li>
      </ul>

      <h2>What this analysis is not</h2>
      <p>
        AI output is for informational and wellness purposes only. It is not a
        medical diagnosis. For any concerning result, consult a licensed clinician.
      </p>

      <h2>Withdrawal of consent</h2>
      <p>
        You can withdraw consent at any time. After withdrawal, no further analysis
        will be performed and your data will be deleted on request.
      </p>

      <p style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>
        (Placeholder consent text — review with counsel before launch.)
      </p>
    </StaticPage>
  );
}
