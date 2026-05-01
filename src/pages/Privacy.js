import { ShieldCheck } from 'lucide-react';
import StaticPage from '../components/StaticPage';

export default function Privacy() {
  return (
    <StaticPage
      title="Privacy Policy"
      subtitle="How we handle your data."
      icon={<ShieldCheck size={20} />}
    >
      <h2>What we collect</h2>
      <ul>
        <li>Account details (name, email, account type).</li>
        <li>Health profile information you choose to provide.</li>
        <li>Images you upload for analysis.</li>
        <li>Basic usage analytics (page views, feature usage).</li>
      </ul>

      <h2>How we use it</h2>
      <p>
        We use your data exclusively to deliver your personalised analysis and to
        improve the safety and quality of recommendations.
      </p>

      <h2>What we don't do</h2>
      <ul>
        <li>We never sell your data.</li>
        <li>We never share images with third-party advertisers, insurers, or partners.</li>
        <li>We do not retain raw images longer than necessary for analysis.</li>
      </ul>

      <h2>Your rights</h2>
      <ul>
        <li>Request a copy of your data at any time.</li>
        <li>Request deletion of your account and associated data.</li>
        <li>Withdraw consent for image processing.</li>
      </ul>

      <h2>Contact</h2>
      <p>
        For privacy questions email <a href="mailto:privacy@meapp.placeholder.com">privacy@meapp.placeholder.com</a>.
      </p>

      <p style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>
        (Placeholder policy — replace with reviewed copy before launch.)
      </p>
    </StaticPage>
  );
}
