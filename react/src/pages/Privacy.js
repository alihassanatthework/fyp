import { ShieldCheck } from 'lucide-react';
import StaticPage from '../components/StaticPage';

export default function Privacy() {
  return (
    <StaticPage
      title="Privacy Policy"
      subtitle="Last updated: 19 June 2026"
      icon={<ShieldCheck size={20} />}
    >
      <h2>1. Introduction</h2>
      <p>
        This Privacy Policy explains how ME collects, uses, and protects your
        information when you use our AI skin and scalp assistant. We are committed to
        handling your health-related data responsibly and transparently.
      </p>

      <h2>2. Information we collect</h2>
      <ul>
        <li><strong>Account details:</strong> name, email, and account type (free or premium).</li>
        <li><strong>Health profile:</strong> optional information such as skin/hair type, allergies, pregnancy, diabetes, and current medications, used to personalise and safety-filter results.</li>
        <li><strong>Images:</strong> face, scalp, or body photos you upload for analysis.</li>
        <li><strong>Usage data:</strong> analyses performed, daily scan counts, and basic feature usage.</li>
      </ul>

      <h2>3. How we use your information</h2>
      <ul>
        <li>To run AI analysis and generate your personalised report, routines, and medication suggestions.</li>
        <li>To screen recommendations against your medical history for safety.</li>
        <li>To maintain your analysis history and enforce account scan limits.</li>
        <li>To respond to reports and inquiries you send us.</li>
      </ul>

      <h2>4. AI &amp; third-party processing</h2>
      <p>
        Recommendation text is generated using a large language model provider. Only
        the text context needed to produce recommendations is sent; your raw images are
        not used to train third-party models. Detection and classification of images is
        performed by ME's own models.
      </p>

      <h2>5. What we never do</h2>
      <ul>
        <li>We never sell your personal or health data.</li>
        <li>We never share your images or results with advertisers, insurers, or unrelated partners.</li>
        <li>We do not retain raw images longer than necessary to produce your analysis.</li>
      </ul>

      <h2>6. Data retention &amp; security</h2>
      <p>
        Account data and analysis results are stored securely and linked to your
        account so you can review your history. Access is restricted to your
        authenticated account.
      </p>

      <h2>7. Your rights</h2>
      <ul>
        <li>Request a copy of your data.</li>
        <li>Request deletion of your account and associated data.</li>
        <li>Withdraw consent for image processing at any time.</li>
      </ul>

      <h2>8. Contact</h2>
      <p>
        For privacy requests or questions, email{' '}
        <a href="mailto:me.offical.team.system@gmail.com">me.offical.team.system@gmail.com</a>.
      </p>
    </StaticPage>
  );
}
