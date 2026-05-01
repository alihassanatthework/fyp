import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Sun, Moon, Eye, EyeOff, CheckSquare, Square, ChevronDown, ChevronUp } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import './SignUp.css';

const healthOptions = ['Allergies', 'Diabetes', 'Pregnancy', 'Heart-related condition', 'Other medical condition', 'None'];

export default function SignUp() {
  const [form, setForm] = useState({ fullName: '', email: '', password: '', confirmPassword: '' });
  const [accountType, setAccountType] = useState('free');
  const [healthConditions, setHealthConditions] = useState([]);
  const [agreed, setAgreed] = useState(false);
  const [showConsent, setShowConsent] = useState(false);
  const [showPass, setShowPass] = useState(false);
  const [serverError, setServerError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { register } = useAuth();

  const toggleHealth = (item) => {
    setHealthConditions(prev => prev.includes(item) ? prev.filter(h => h !== item) : [...prev, item]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');

    if (form.password !== form.confirmPassword) {
      setServerError('Passwords do not match.');
      return;
    }
    if (!agreed) {
      setServerError('Please agree to the terms to continue.');
      return;
    }

    setSubmitting(true);
    const result = await register({
      fullName: form.fullName,
      email: form.email,
      password: form.password,
      confirmPassword: form.confirmPassword,
      healthConditions,
    });
    setSubmitting(false);

    if (result.success) {
      navigate('/home');
    } else {
      setServerError(result.error || 'Registration failed. Please try again.');
    }
  };

  return (
    <div className="signup-page">
      <div className="signup-container">
        <div className="signup-grid">
          <div className="card signup-form-panel p-8">
            <div className="signup-header">
              <div>
                <h1 className="signup-title">
                  AI-Powered Skin, Scalp, Makeup &<br/>Fashion Personalized Assistant
                </h1>
                <p className="signup-subtitle">Sign up once, sync your profile across light & dark themes.</p>
              </div>
              <div className="theme-toggle">
                <button onClick={() => toggleTheme('light')} className={`theme-btn ${theme==='light' ? 'active' : ''}`}>
                  <Sun size={12}/> Light
                </button>
                <button onClick={() => toggleTheme('dark')} className={`theme-btn ${theme==='dark' ? 'active' : ''}`}>
                  <Moon size={12}/> Dark
                </button>
              </div>
            </div>

            <h2 className="text-2xl font-bold mb-2">Create your account</h2>
            <p className="signup-subtitle mb-5">Basic profile, health context, and AI analysis focus in one screen.</p>

            <form onSubmit={handleSubmit}>
              <div className="signup-fields-grid">
                <div style={{display:'flex',flexDirection:'column',gap:'1rem'}}>
                  <p className="section-label">Basic Information</p>
                  <div className="form-group">
                    <label>Full Name</label>
                    <input type="text" placeholder="Jane Doe" value={form.fullName} onChange={e => setForm({...form, fullName: e.target.value})} className="input-field" required />
                  </div>
                  <div className="form-group">
                    <label>Email Address</label>
                    <input type="email" placeholder="jane@example.com" value={form.email} onChange={e => setForm({...form, email: e.target.value})} className="input-field" required />
                  </div>
                  <div className="form-group">
                    <label>Password</label>
                    <div className="password-wrapper">
                      <input type={showPass ? 'text' : 'password'} placeholder="••••••••" value={form.password} onChange={e => setForm({...form, password: e.target.value})} className="input-field" style={{paddingRight:'2.5rem'}} required />
                      <button type="button" onClick={() => setShowPass(!showPass)} className="password-toggle">
                        {showPass ? <EyeOff size={16}/> : <Eye size={16}/>}
                      </button>
                    </div>
                  </div>
                  <div className="form-group">
                    <label>Confirm Password</label>
                    <input type="password" placeholder="••••••••" value={form.confirmPassword} onChange={e => setForm({...form, confirmPassword: e.target.value})} className="input-field" required />
                  </div>
                  <div>
                    <p className="section-label">Account Type</p>
                    <div className="account-type-btns">
                      {['free', 'premium'].map(t => (
                        <button key={t} type="button" onClick={() => setAccountType(t)} className={`account-type-btn ${accountType === t ? 'selected' : ''}`}>
                          {t === 'free' ? 'Free Account' : 'Premium Account'}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div style={{display:'flex',flexDirection:'column',gap:'1.25rem'}}>
                  <div>
                    <p className="section-label">Health Profile</p>
                    <p className="text-xs" style={{color:'var(--text-tertiary)',marginBottom:'0.75rem'}}>Treatment suggestions are adjusted according to your health condition.</p>
                    <div className="health-options">
                      {healthOptions.map(opt => (
                        <button key={opt} type="button" onClick={() => toggleHealth(opt)} className={`health-option-btn ${healthConditions.includes(opt) ? 'selected' : ''}`}>
                          {opt}
                        </button>
                      ))}
                    </div>
                  </div>

                  <button type="button" onClick={() => setAgreed(!agreed)} className={`terms-checkbox ${agreed ? 'checked' : ''}`}>
                    <span className="terms-icon">
                      {agreed ? <CheckSquare size={18}/> : <Square size={18}/>}
                    </span>
                    <span className="terms-text">
                      I agree to the <Link to="/terms" onClick={(e) => e.stopPropagation()}>Terms &amp; Conditions</Link> and consent to upload my face/scalp images for AI-based analysis.
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowConsent((s) => !s)}
                    className="consent-see-more"
                  >
                    {showConsent ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
                    {showConsent ? 'Hide details' : 'See more'}
                  </button>

                  {showConsent && (
                    <div className="consent-details">
                      <ul>
                        <li><strong>No third-party sharing.</strong> Your images and personal data are never shared with advertisers, insurers, or external partners.</li>
                        <li><strong>LLM binary masks only.</strong> AI models receive de-identified binary masks derived from your image, not the raw photo, for inference.</li>
                        <li><strong>Exclusive processing.</strong> All analysis runs on our isolated infrastructure; data is processed exclusively for your personalised diagnosis.</li>
                        <li><strong>Right to withdraw.</strong> You may revoke consent and request deletion at any time from your profile settings.</li>
                      </ul>
                    </div>
                  )}
                </div>
              </div>

              {serverError && (
                <div style={{
                  background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
                  borderRadius: '0.75rem', padding: '0.75rem 1rem',
                  color: '#ef4444', fontSize: '0.875rem', marginTop: '1rem',
                }}>
                  {serverError}
                </div>
              )}

              <div className="signup-footer">
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Creating account…' : 'Create Account'}
                </button>
                <p className="signup-footer-text">
                  Already have an account? <Link to="/">Login</Link>
                </p>
              </div>
            </form>
          </div>

          <div className="card signup-info-panel p-8">
            <div>
              <h2 className="info-panel-title">All-in-one beauty &<br/>wellness profile</h2>
              <p className="info-panel-desc">Your skin, scalp, makeup, and fashion preferences live in a single AI-powered hub.</p>
              <ul className="info-list">
                {[
                  'Health-aware recommendations that respect allergies, diabetes, pregnancy, and heart conditions.',
                  'Guided skin & scalp analysis to match treatments, routines, and styles to your goals.',
                  'Switch seamlessly between free and premium plans as your needs evolve.',
                ].map((item, i) => (
                  <li key={i} className="info-list-item">
                    <span className="info-bullet"/>
                    <span className="info-list-text">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <p className="info-footer">
              Your theme preference and profile details are securely saved to your account so you can pick up where you left off on any device.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}