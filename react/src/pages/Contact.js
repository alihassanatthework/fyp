import { Mail, Instagram, Linkedin } from 'lucide-react';
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
        <li><strong><Mail size={14} style={{display:'inline',marginRight:6}}/>Email:</strong> <a href="mailto:me.offical.team.system@gmail.com">me.offical.team.system@gmail.com</a></li>
        <li><strong><Instagram size={14} style={{display:'inline',marginRight:6}}/>Instagram:</strong> <a href="https://www.instagram.com/me.offical.team.system/" target="_blank" rel="noreferrer">@me.offical.team.system</a></li>
        <li><strong><Linkedin size={14} style={{display:'inline',marginRight:6}}/>LinkedIn:</strong> <a href="https://www.linkedin.com/in/me-admin-team/" target="_blank" rel="noreferrer">ME Admin Team</a></li>
      </ul>

      
    </StaticPage>
  );
}
