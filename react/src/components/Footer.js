import { Link } from 'react-router-dom';
import { Instagram, Linkedin } from 'lucide-react';
import './Footer.css';

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-container">
        <div className="footer-row">
          <div className="footer-brand">
            <span className="footer-logo">ME</span>
            <span className="footer-tagline">
              Personalised Skin and Scalp Assistant
            </span>
          </div>

          <div className="footer-socials">
            <a
              href="https://instagram.com"
              target="_blank"
              rel="noreferrer"
              aria-label="Instagram"
              className="footer-social"
            >
              <Instagram size={16} />
            </a>
            <a
              href="https://linkedin.com"
              target="_blank"
              rel="noreferrer"
              aria-label="LinkedIn"
              className="footer-social"
            >
              <Linkedin size={16} />
            </a>
          </div>
        </div>

        <nav className="footer-links">
          <Link to="/privacy">Privacy Policy</Link>
          <Link to="/consent">Consent Form</Link>
          <Link to="/scalp-treatment">Scalp Treatment</Link>
          <Link to="/skin-treatment">Skin Treatment</Link>
          <Link to="/report">Report</Link>
          <Link to="/terms">Terms</Link>
          <Link to="/contact">Contact</Link>
          {/*
          // Makeup section removed
          <Link to="/makeup">Makeup</Link>
          */}
        </nav>

        <p className="footer-copy">
          © {new Date().getFullYear()} ME · All rights reserved.
        </p>
      </div>
    </footer>
  );
}
