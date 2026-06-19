import { FileText } from 'lucide-react';
import StaticPage from '../components/StaticPage';

export default function Terms() {
  return (
    <StaticPage
      title="Terms and Conditions"
      subtitle="Last updated: 19 June 2026"
      icon={<FileText size={20} />}
    >
      <h2>1. About ME</h2>
      <p>
        ME ("ME", "the Service", "we", "us") is an AI-powered personalised skin and
        scalp assistant. It analyses user-submitted images to detect common skin and
        scalp conditions and to generate informational care routines, product and
        medication suggestions, and fashion and makeup guidance. By creating an
        account or using ME you agree to these Terms and Conditions.
      </p>

      <h2>2. Not a Medical Service</h2>
      <p>
        ME provides AI-assisted analysis for informational and wellness purposes only.
        Its output — including detected conditions, severity estimates, and medication
        suggestions — is <strong>not a medical diagnosis or prescription</strong> and
        must not replace consultation with a qualified clinician, dermatologist, or
        pharmacist. Always seek professional advice before acting on any result, and
        never start, stop, or change a medication based solely on ME.
      </p>

      <h2>3. Eligibility &amp; Accounts</h2>
      <ul>
        <li>You must provide accurate registration details and keep your credentials secure.</li>
        <li>You are responsible for all activity under your account.</li>
        <li>Free accounts are subject to a daily analysis limit; premium accounts receive expanded access. Limits are described in the app and may change.</li>
      </ul>

      <h2>4. Acceptable Use</h2>
      <ul>
        <li>Upload only images of yourself, or images you have explicit permission to submit.</li>
        <li>Do not upload unlawful, abusive, or non-consensual content.</li>
        <li>Do not attempt to disrupt, reverse-engineer, or overload the Service or its AI models.</li>
      </ul>

      <h2>5. Your Content</h2>
      <p>
        You retain ownership of the images and health information you submit. By
        submitting them, you grant ME a limited licence to process that content solely
        to generate your personalised analysis, as described in our{' '}
        <a href="/privacy">Privacy Policy</a> and <a href="/consent">Consent Form</a>.
      </p>

      <h2>6. AI &amp; Third-Party Processing</h2>
      <p>
        Recommendations are generated using machine-learning models and a large
        language model provider. AI output can be incomplete or inaccurate. Medication
        suggestions are screened against the medical history you provide, but you remain
        responsible for verifying suitability with a healthcare professional.
      </p>

      <h2>7. Limitation of Liability</h2>
      <p>
        ME is provided "as is" without warranty of any kind. To the maximum extent
        permitted by law, we are not liable for any loss, injury, or decision made on
        the basis of analysis output.
      </p>

      <h2>8. Changes to These Terms</h2>
      <p>
        We may update these Terms from time to time. Material changes will be
        communicated via the app or email, and continued use constitutes acceptance.
      </p>

      <h2>9. Contact</h2>
      <p>
        Questions about these Terms? Email{' '}
        <a href="mailto:me.offical.team.system@gmail.com">me.offical.team.system@gmail.com</a>.
      </p>
    </StaticPage>
  );
}
