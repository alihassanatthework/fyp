import { useNavigate } from 'react-router-dom';
import { Download, Bookmark, Bell, ArrowRight, CheckCircle2, ShieldCheck } from 'lucide-react';
import Navbar from '../components/Navbar';
import './DiagnosisReport.css';

const steps = [
  { title: 'Consult a certified dermatologist', desc: 'Schedule an in-person or telehealth visit within 7 days.' },
  { title: 'Topical treatment options', desc: 'Discuss retinoids or benzoyl peroxide-based treatments if appropriate.' },
  { title: 'Daily skincare routine', desc: 'Use a gentle, non-comedogenic cleanser and avoid harsh scrubbing.' },
  { title: 'Follow-up scan', desc: 'Re-scan in 4–6 weeks to track your skin health progress.' },
];

export default function DiagnosisReport() {
  const navigate = useNavigate();

  return (
    <div className="diagnosis-page">
      <Navbar title="Diagnosis Report" />
      <main className="diagnosis-main">
        <div>
          <h1 className="diagnosis-page-title">Diagnosis Report & Actions</h1>
          <p className="diagnosis-page-subtitle">Complete analysis results with actionable next steps.</p>
        </div>
        <div className="card diagnosis-meta-grid">
          <div className="meta-item">
            <p className="meta-label">REPORT NAME</p>
            <p className="meta-value">Facial Skin Analysis #04</p>
          </div>
          <div className="meta-item">
            <p className="meta-label">DATE & TIME</p>
            <p className="meta-value">October 24, 2025 • 10:42 AM</p>
          </div>
          <div className="meta-item">
            <p className="meta-label">REPORT ID</p>
            <p className="meta-value">#SR-2948-XJ</p>
          </div>
        </div>
        <div className="diagnosis-grid">
          <div className="card p-6">
            <div className="condition-header">
              <ShieldCheck size={18} className="condition-header-icon"/>
              <h2 className="condition-header-title">Detected Condition</h2>
            </div>
            <div className="flex items-start gap-4 mb-4">
              <div className="condition-icon-badge">
                <span className="condition-icon-text">!</span>
              </div>
              <div className="condition-info">
                <h2 className="condition-name">Acne Vulgaris</h2>
                <p className="condition-confidence">Confidence: 98.2%</p>
              </div>
            </div>
            <p className="condition-description">
              A common skin condition that occurs when hair follicles become clogged with oil and dead skin cells. It causes whiteheads, blackheads or pimples.
            </p>
            <div className="severity-box">
              <div className="severity-header">
                <span className="severity-label">Severity Level: <span className="severity-level">Moderate</span></span>
                <span className="severity-score">65/100</span>
              </div>
              <div className="severity-bar">
                <div className="severity-bar-fill" style={{width: '65%'}}/>
              </div>
              <div className="severity-range">
                <span>Mild</span><span>Severe</span>
              </div>
            </div>
          </div>
          <div className="card book-card p-6">
            <div>
              <h2 className="book-title">Ready to treat this?</h2>
              <p className="book-desc">Book a consultation with a specialist.</p>
              <button className="btn btn-primary w-full py-3">Book Appointment <ArrowRight size={15}/></button>
            </div>
            <div className="book-footer">
              <ShieldCheck size={14}/>Securely verified report
            </div>
          </div>
        </div>
        <div className="diagnosis-grid">
          <div className="card p-6">
            <div className="recommendation-header">
              <span className="recommendation-emoji">🩺</span>
              <h2 className="condition-header-title">Dermatologist Recommendation</h2>
            </div>
            <p className="recommendation-text">
              Based on the analysis of the affected areas, consulting a certified dermatologist is recommended to assess underlying causes and prevent potential scarring. Over-the-counter treatments alone may not be sufficient for this severity level.
            </p>
            <div className="disclaimer-box">
              <p className="disclaimer-text">
                <span className="disclaimer-label">Medical Disclaimer:</span> This report is AI-generated for informational purposes only and does not constitute a medical diagnosis. Always seek the advice of a physician or other qualified health provider.
              </p>
            </div>
          </div>
          <div className="card p-6">
            <div className="recommendation-header">
              <span className="recommendation-emoji">📋</span>
              <h2 className="condition-header-title">Suggested Next Steps</h2>
            </div>
            <ul className="steps-list">
              {steps.map((s, i) => (
                <li key={i} className="step-item">
                  <CheckCircle2 size={16} className="step-icon"/>
                  <div>
                    <p className="step-title">{s.title}</p>
                    <p className="step-desc">{s.desc}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="card footer-bar">
          <div className="footer-info">
            <span className="footer-emoji">🗄️</span>
            <div>
              <p className="footer-info-title">Data auto-saved</p>
              <p className="footer-info-desc">This report is securely stored and can be accessed in your history.</p>
            </div>
          </div>
          <div className="footer-actions">
            <button className="btn btn-secondary"><Download size={14}/> Download PDF</button>
            <button className="btn btn-secondary"><Bookmark size={14}/> Save Scan</button>
            <button className="btn btn-secondary"><Bell size={14}/> Set Reminder</button>
          </div>
        </div>
        <p className="footer-note">Regular monitoring helps track your skin health progress over time.</p>
      </main>
    </div>
  );
}