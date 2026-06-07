import { Mail, Phone, MapPin } from 'lucide-react';
import StaticPage from '../components/StaticPage';

export default function Contact() {
  return (
    <StaticPage
      title="Contact Us"
      subtitle="We'd love to hear from you."
      icon={<Mail size={20} />}
    >
      <h2>Get in touch</h2>
      <p>
        Questions, feedback, or partnership requests? Reach out and the ME team will
        get back to you within two business days.
      </p>

      <ul>
        <li><strong><Mail size={14} style={{display:'inline',marginRight:6}}/>Email:</strong> <a href="mailto:contact@meapp.placeholder.com">contact@meapp.placeholder.com</a></li>
        <li><strong><Phone size={14} style={{display:'inline',marginRight:6}}/>Phone:</strong> +1 (555) 010-2024</li>
        <li><strong><MapPin size={14} style={{display:'inline',marginRight:6}}/>Address:</strong> ME HQ — Placeholder Address, City, Country</li>
      </ul>

      <h2>Team</h2>
      <ul>
        <li>Huda Masood</li>
        <li>Ali Hassan</li>
        <li>Aqsa Mustafa</li>
        <li>Sibgha Shezadi</li>
      </ul>

      <p style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>
        (Placeholder contact information — replace with real values before launch.)
      </p>
    </StaticPage>
  );
}
